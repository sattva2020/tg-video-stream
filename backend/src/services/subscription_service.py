"""
Subscription Service
Spec: 022-multi-tenant-architecture-organization-management

Сервис для управления подписками организаций.
Обрабатывает создание, изменение и отмену планов подписки, управление пробными периодами и платежной информацией.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.subscription import Subscription, PlanType, SubscriptionStatus
from src.models.organization import Organization

logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Сервис управления подписками.

    Обеспечивает:
    - Создание подписок с пробными периодами
    - Изменение планов подписки
    - Управление платежными данными
    - Отмену и реактивацию подписок
    - Проверку статуса подписки
    """

    def __init__(self, db: Session):
        """
        Инициализация сервиса.

        Args:
            db: SQLAlchemy сессия для работы с базой данных
        """
        self.db = db

    def create_subscription(
        self,
        organization_id: UUID,
        plan_type: PlanType,
        billing_email: Optional[str] = None,
        billing_address: Optional[Dict[str, Any]] = None,
        trial_days: Optional[int] = None
    ) -> Subscription:
        """
        Создает новую подписку для организации.

        Args:
            organization_id: UUID организации
            plan_type: Тип плана подписки
            billing_email: Опциональный email для биллинга
            billing_address: Опциональный адрес для биллинга (словарь)
            trial_days: Опциональное количество дней пробного периода

        Returns:
            Созданный объект Subscription

        Raises:
            HTTPException: Если организация не найдена или подписка уже существует
        """
        try:
            # Проверяем существование организации
            organization = self.db.query(Organization).filter(
                Organization.id == organization_id
            ).first()

            if not organization:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Organization {organization_id} not found"
                )

            # Проверяем, нет ли уже активной подписки
            existing = self.db.query(Subscription).filter(
                Subscription.organization_id == organization_id
            ).first()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Organization already has a subscription"
                )

            # Создаем подписку
            subscription = Subscription(
                organization_id=organization_id,
                plan_type=plan_type.value,
                status=SubscriptionStatus.TRIALING.value,
                billing_email=billing_email,
                billing_address=billing_address,
                current_period_start=datetime.now(timezone.utc)
            )

            # Устанавливаем пробный период если указан
            if trial_days and trial_days > 0:
                subscription.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=trial_days)
                subscription.current_period_end = subscription.trial_ends_at
            elif plan_type == PlanType.TRIAL:
                # Для TRIAL плана по умолчанию 14 дней
                subscription.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=14)
                subscription.current_period_end = subscription.trial_ends_at

            self.db.add(subscription)
            self.db.commit()
            self.db.refresh(subscription)

            logger.info(
                f"Created {plan_type.value} subscription for organization {organization_id}"
            )

            return subscription

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating subscription for org {organization_id}: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create subscription: {str(e)}"
            )

    def get_subscription(self, organization_id: UUID) -> Subscription:
        """
        Получает подписку организации.

        Args:
            organization_id: UUID организации

        Returns:
            Объект Subscription

        Raises:
            HTTPException: Если подписка не найдена
        """
        try:
            subscription = self.db.query(Subscription).filter(
                Subscription.organization_id == organization_id
            ).first()

            if not subscription:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Subscription not found for organization {organization_id}"
                )

            return subscription

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting subscription for org {organization_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get subscription: {str(e)}"
            )

    def update_subscription(
        self,
        organization_id: UUID,
        plan_type: Optional[PlanType] = None,
        billing_email: Optional[str] = None,
        billing_address: Optional[Dict[str, Any]] = None
    ) -> Subscription:
        """
        Обновляет информацию о подписке.

        Args:
            organization_id: UUID организации
            plan_type: Новый тип плана (опционально)
            billing_email: Новый email для биллинга (опционально)
            billing_address: Новый адрес для биллинга (опционально)

        Returns:
            Обновленный объект Subscription

        Raises:
            HTTPException: Если подписка не найдена
        """
        try:
            subscription = self.get_subscription(organization_id)

            if plan_type is not None:
                old_plan = subscription.plan_type
                subscription.plan_type = plan_type.value
                # При смене плана обновляем период
                subscription.current_period_start = datetime.now(timezone.utc)
                logger.info(
                    f"Changed plan from {old_plan} to {plan_type.value} for org {organization_id}"
                )

            if billing_email is not None:
                subscription.billing_email = billing_email

            if billing_address is not None:
                subscription.billing_address = billing_address

            self.db.commit()
            self.db.refresh(subscription)

            return subscription

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating subscription for org {organization_id}: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update subscription: {str(e)}"
            )

    def cancel_subscription(
        self,
        organization_id: UUID,
        at_period_end: bool = True
    ) -> Subscription:
        """
        Отменяет подписку.

        Args:
            organization_id: UUID организации
            at_period_end: Если True, отмена в конце периода, если False - немедленно

        Returns:
            Обновленный объект Subscription

        Raises:
            HTTPException: Если подписка не найдена
        """
        try:
            subscription = self.get_subscription(organization_id)

            subscription.cancel(at_period_end=at_period_end)

            self.db.commit()
            self.db.refresh(subscription)

            logger.info(
                f"Canceled subscription for org {organization_id} "
                f"(at_period_end={at_period_end})"
            )

            return subscription

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error canceling subscription for org {organization_id}: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to cancel subscription: {str(e)}"
            )

    def activate_subscription(self, organization_id: UUID) -> Subscription:
        """
        Активирует или реактивирует подписку.

        Args:
            organization_id: UUID организации

        Returns:
            Обновленный объект Subscription

        Raises:
            HTTPException: Если подписка не найдена
        """
        try:
            subscription = self.get_subscription(organization_id)

            subscription.activate()

            # Обновляем период начала
            subscription.current_period_start = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(subscription)

            logger.info(f"Activated subscription for org {organization_id}")

            return subscription

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error activating subscription for org {organization_id}: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to activate subscription: {str(e)}"
            )

    def update_subscription_status(
        self,
        organization_id: UUID,
        new_status: SubscriptionStatus
    ) -> Subscription:
        """
        Обновляет статус подписки.

        Args:
            organization_id: UUID организации
            new_status: Новый статус подписки

        Returns:
            Обновленный объект Subscription

        Raises:
            HTTPException: Если подписка не найдена
        """
        try:
            subscription = self.get_subscription(organization_id)

            old_status = subscription.status
            subscription.update_status(new_status)

            self.db.commit()
            self.db.refresh(subscription)

            logger.info(
                f"Updated subscription status for org {organization_id}: "
                f"{old_status} -> {new_status.value}"
            )

            return subscription

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating subscription status for org {organization_id}: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update subscription status: {str(e)}"
            )

    def check_subscription_access(self, organization_id: UUID) -> bool:
        """
        Проверяет, имеет ли организация доступ на основе подписки.

        Args:
            organization_id: UUID организации

        Returns:
            True если доступ разрешен, False если нет
        """
        try:
            subscription = self.db.query(Subscription).filter(
                Subscription.organization_id == organization_id
            ).first()

            if not subscription:
                logger.warning(f"No subscription found for org {organization_id}")
                return False

            # Проверяем, активна ли подписка
            if not subscription.is_active:
                logger.warning(
                    f"Subscription for org {organization_id} is not active "
                    f"(status={subscription.status})"
                )
                return False

            # Если это пробная подписка, проверяем дату окончания
            if subscription.is_trial:
                days_remaining = subscription.trial_days_remaining
                if days_remaining is not None and days_remaining <= 0:
                    logger.warning(
                        f"Trial period expired for org {organization_id}"
                    )
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking subscription access for org {organization_id}: {e}")
            # В случае ошибки возвращаем False для безопасности
            return False

    def get_subscription_info(self, organization_id: UUID) -> Dict[str, Any]:
        """
        Получает подробную информацию о подписке.

        Args:
            organization_id: UUID организации

        Returns:
            Словарь с информацией о подписке:
                - subscription_id: ID подписки
                - organization_id: ID организации
                - plan_type: тип плана
                - status: статус подписки
                - is_active: активна ли подписка
                - is_trial: пробная ли подписка
                - trial_ends_at: дата окончания пробного периода
                - trial_days_remaining: дней до окончания пробного периода
                - current_period_start: начало текущего периода
                - current_period_end: конец текущего периода
                - cancel_at_period_end: будет ли отменена в конце периода
                - billing_email: email для биллинга
                - created_at: дата создания
                - updated_at: дата обновления

        Raises:
            HTTPException: Если подписка не найдена
        """
        try:
            subscription = self.get_subscription(organization_id)

            return {
                "subscription_id": str(subscription.id),
                "organization_id": str(subscription.organization_id),
                "plan_type": subscription.plan_type,
                "status": subscription.status,
                "is_active": subscription.is_active,
                "is_trial": subscription.is_trial,
                "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else None,
                "trial_days_remaining": subscription.trial_days_remaining,
                "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
                "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "billing_email": subscription.billing_email,
                "billing_address": subscription.billing_address,
                "created_at": subscription.created_at.isoformat() if subscription.created_at else None,
                "updated_at": subscription.updated_at.isoformat() if subscription.updated_at else None
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting subscription info for org {organization_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get subscription info: {str(e)}"
            )

    def list_subscriptions(
        self,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[SubscriptionStatus] = None,
        plan_filter: Optional[PlanType] = None
    ) -> List[Subscription]:
        """
        Получает список подписок с опциональной фильтрацией.

        Args:
            skip: Количество записей для пропуска (пагинация)
            limit: Максимальное количество записей
            status_filter: Опциональная фильтрация по статусу
            plan_filter: Опциональная фильтрация по плану

        Returns:
            Список объектов Subscription
        """
        try:
            query = self.db.query(Subscription)

            if status_filter:
                query = query.filter(Subscription.status == status_filter.value)

            if plan_filter:
                query = query.filter(Subscription.plan_type == plan_filter.value)

            subscriptions = query.offset(skip).limit(limit).all()

            return subscriptions

        except Exception as e:
            logger.error(f"Error listing subscriptions: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list subscriptions: {str(e)}"
            )

    def handle_trial_expiration(self) -> int:
        """
        Обрабатывает истекшие пробные периоды.
        Переводит просроченные пробные подписки в соответствующий статус.

        Этот метод предназначен для периодического выполнения (например, через celery beat).

        Returns:
            Количество обработанных подписок
        """
        try:
            now = datetime.now(timezone.utc)

            # Находим пробные подписки с истекшим периодом
            expired_trials = self.db.query(Subscription).filter(
                Subscription.status == SubscriptionStatus.TRIALING.value,
                Subscription.trial_ends_at.isnot(None),
                Subscription.trial_ends_at <= now
            ).all()

            count = 0
            for subscription in expired_trials:
                # Если не настроена отмена в конце периода, переводим в ACTIVE
                if not subscription.cancel_at_period_end:
                    subscription.status = SubscriptionStatus.ACTIVE.value
                    logger.info(
                        f"Trial ended for org {subscription.organization_id}, "
                        f"converted to ACTIVE"
                    )
                else:
                    subscription.status = SubscriptionStatus.CANCELED.value
                    logger.info(
                        f"Trial ended for org {subscription.organization_id}, "
                        f"canceled as requested"
                    )

                count += 1

            self.db.commit()
            return count

        except Exception as e:
            logger.error(f"Error handling trial expiration: {e}")
            self.db.rollback()
            return 0


def get_subscription_service(db: Session) -> SubscriptionService:
    """
    Фабричная функция для создания SubscriptionService.

    Args:
        db: SQLAlchemy сессия

    Returns:
        Экземпляр SubscriptionService
    """
    return SubscriptionService(db=db)
