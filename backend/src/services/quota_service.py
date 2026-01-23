"""
Quota Service
Spec: 022-multi-tenant-architecture-organization-management

Сервис для управления квотами ресурсов организации.
Проверяет и обеспечивает соблюдение лимитов для стримов, хранилища, трафика и других ресурсов.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.models.organization_quota import ResourceQuota, QuotaType
from src.models.organization import Organization


logger = logging.getLogger(__name__)


class QuotaService:
    """
    Сервис управления квотами ресурсов.

    Обеспечивает:
    - Проверку превышения лимитов квот
    - Инкремент/декремент использования ресурсов
    - Получение информации об использовании квот
    - Сброс квот по периоду
    """

    def __init__(self, db: Session):
        """
        Инициализация сервиса.

        Args:
            db: SQLAlchemy сессия для работы с базой данных
        """
        self.db = db

    def check_quota(self, organization_id: UUID, quota_type: QuotaType) -> bool:
        """
        Проверяет, превышена ли квота для организации.

        Args:
            organization_id: UUID организации
            quota_type: Тип квоты для проверки

        Returns:
            True если квота не превышена, False если превышена

        Raises:
            HTTPException: Если организация не найдена
        """
        try:
            quota = self.db.query(ResourceQuota).filter(
                ResourceQuota.organization_id == organization_id,
                ResourceQuota.quota_type == quota_type.value
            ).first()

            if not quota:
                # Если квота не задана, считаем что лимит не ограничен
                logger.warning(
                    f"Quota {quota_type.value} not found for organization {organization_id}, "
                    f"assuming unlimited"
                )
                return True

            return not quota.is_exceeded

        except Exception as e:
            logger.error(f"Error checking quota {quota_type.value} for org {organization_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to check quota: {str(e)}"
            )

    def get_quota_usage(self, organization_id: UUID, quota_type: QuotaType) -> Dict[str, Any]:
        """
        Получает детализированную информацию об использовании квоты.

        Args:
            organization_id: UUID организации
            quota_type: Тип квоты

        Returns:
            Словарь с полями:
                - quota_type: тип квоты
                - limit: лимит
                - current_usage: текущее использование
                - remaining: остаток
                - usage_percentage: процент использования
                - is_exceeded: превышен ли лимит
                - reset_at: время сброса (если есть)

        Raises:
            HTTPException: Если организация не найдена
        """
        try:
            quota = self.db.query(ResourceQuota).filter(
                ResourceQuota.organization_id == organization_id,
                ResourceQuota.quota_type == quota_type.value
            ).first()

            if not quota:
                return {
                    "quota_type": quota_type.value,
                    "limit": None,
                    "current_usage": 0,
                    "remaining": None,
                    "usage_percentage": 0.0,
                    "is_exceeded": False,
                    "reset_at": None
                }

            return {
                "quota_type": quota.quota_type,
                "limit": quota.limit,
                "current_usage": quota.current_usage,
                "remaining": quota.remaining,
                "usage_percentage": round(quota.usage_percentage, 2),
                "is_exceeded": quota.is_exceeded,
                "reset_at": quota.reset_at.isoformat() if quota.reset_at else None
            }

        except Exception as e:
            logger.error(f"Error getting quota usage {quota_type.value} for org {organization_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get quota usage: {str(e)}"
            )

    def increment_usage(
        self,
        organization_id: UUID,
        quota_type: QuotaType,
        amount: int = 1
    ) -> ResourceQuota:
        """
        Увеличивает использование квоты.

        Args:
            organization_id: UUID организации
            quota_type: Тип квоты
            amount: Количество для добавления (по умолчанию 1)

        Returns:
            Обновленный объект ResourceQuota

        Raises:
            HTTPException: Если организация не найдена или квота превышена
        """
        try:
            quota = self.db.query(ResourceQuota).filter(
                ResourceQuota.organization_id == organization_id,
                ResourceQuota.quota_type == quota_type.value
            ).first()

            if not quota:
                logger.warning(
                    f"Quota {quota_type.value} not found for organization {organization_id}, "
                    f"creating new quota with unlimited limit"
                )
                # Создаем квоту с "безлимитным" значением (очень большое число)
                quota = ResourceQuota(
                    organization_id=organization_id,
                    quota_type=quota_type.value,
                    limit=999999999999,
                    current_usage=0
                )
                self.db.add(quota)
                self.db.flush()

            # Проверяем, не превысим ли мы лимит
            if quota.current_usage + amount > quota.limit:
                logger.warning(
                    f"Quota {quota_type.value} would be exceeded for org {organization_id}: "
                    f"{quota.current_usage + amount} > {quota.limit}"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Quota {quota_type.value} exceeded. Limit: {quota.limit}, "
                           f"Current: {quota.current_usage}, Requested: +{amount}"
                )

            quota.increment_usage(amount)
            self.db.commit()
            self.db.refresh(quota)

            logger.info(
                f"Incremented quota {quota_type.value} for org {organization_id} by {amount}. "
                f"New usage: {quota.current_usage}/{quota.limit}"
            )

            return quota

        except HTTPException:
            # Пробрасываем HTTPException дальше
            raise
        except Exception as e:
            logger.error(f"Error incrementing quota {quota_type.value} for org {organization_id}: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to increment quota: {str(e)}"
            )

    def decrement_usage(
        self,
        organization_id: UUID,
        quota_type: QuotaType,
        amount: int = 1
    ) -> ResourceQuota:
        """
        Уменьшает использование квоты.

        Args:
            organization_id: UUID организации
            quota_type: Тип квоты
            amount: Количество для уменьшения (по умолчанию 1)

        Returns:
            Обновленный объект ResourceQuота

        Raises:
            HTTPException: Если организация не найдена
        """
        try:
            quota = self.db.query(ResourceQuota).filter(
                ResourceQuota.organization_id == organization_id,
                ResourceQuota.quota_type == quota_type.value
            ).first()

            if not quota:
                logger.warning(
                    f"Quota {quota_type.value} not found for organization {organization_id}, "
                    f"skipping decrement"
                )
                # Если квоты нет, просто выходим
                # Возвращаем "фейковый" объект для совместимости
                return ResourceQuota(
                    organization_id=organization_id,
                    quota_type=quota_type.value,
                    limit=0,
                    current_usage=0
                )

            quota.decrement_usage(amount)
            self.db.commit()
            self.db.refresh(quota)

            logger.info(
                f"Decremented quota {quota_type.value} for org {organization_id} by {amount}. "
                f"New usage: {quota.current_usage}/{quota.limit}"
            )

            return quota

        except Exception as e:
            logger.error(f"Error decrementing quota {quota_type.value} for org {organization_id}: {e}")
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to decrement quota: {str(e)}"
            )

    def get_all_quotas(self, organization_id: UUID) -> List[Dict[str, Any]]:
        """
        Получает все квоты организации.

        Args:
            organization_id: UUID организации

        Returns:
            Список словарей с информацией о квотах

        Raises:
            HTTPException: Если организация не найдена
        """
        try:
            quotas = self.db.query(ResourceQuota).filter(
                ResourceQuota.organization_id == organization_id
            ).all()

            result = []
            for quota in quotas:
                result.append({
                    "quota_type": quota.quota_type,
                    "limit": quota.limit,
                    "current_usage": quota.current_usage,
                    "remaining": quota.remaining,
                    "usage_percentage": round(quota.usage_percentage, 2),
                    "is_exceeded": quota.is_exceeded,
                    "period": quota.period,
                    "reset_at": quota.reset_at.isoformat() if quota.reset_at else None
                })

            return result

        except Exception as e:
            logger.error(f"Error getting all quotas for org {organization_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get quotas: {str(e)}"
            )

    def can_create_resource(
        self,
        organization_id: UUID,
        resource_type: QuotaType,
        count: int = 1
    ) -> bool:
        """
        Проверяет, может ли организация создать указанное количество ресурсов.

        Args:
            organization_id: UUID организации
            resource_type: Тип ресурса (тип квоты)
            count: Количество ресурсов для создания

        Returns:
            True если ресурсы могут быть созданы, False если лимит превышен
        """
        try:
            quota = self.db.query(ResourceQuota).filter(
                ResourceQuota.organization_id == organization_id,
                ResourceQuota.quota_type == resource_type.value
            ).first()

            if not quota:
                # Если квота не задана, считаем что лимит не ограничен
                return True

            return quota.current_usage + count <= quota.limit

        except Exception as e:
            logger.error(
                f"Error checking if org {organization_id} can create {count} "
                f"resources of type {resource_type.value}: {e}"
            )
            # В случае ошибки возвращаем False для безопасности
            return False

    def reset_expired_quotas(self) -> int:
        """
        Сбрасывает квоты, у которых истек период сброса.

        Этот метод предназначен для периодического выполнения (например, через celery beat).

        Returns:
            Количество сброшенных квот
        """
        try:
            now = datetime.now(timezone.utc)
            expired_quotas = self.db.query(ResourceQuota).filter(
                ResourceQuota.reset_at.isnot(None),
                ResourceQuota.reset_at <= now
            ).all()

            count = 0
            for quota in expired_quotas:
                old_usage = quota.current_usage
                quota.reset_usage()

                # Вычисляем следующее время сброса на основе периода
                if quota.period == "hourly":
                    from datetime import timedelta
                    quota.reset_at = now + timedelta(hours=1)
                elif quota.period == "daily":
                    from datetime import timedelta
                    quota.reset_at = now + timedelta(days=1)
                elif quota.period == "monthly":
                    from datetime import timedelta
                    quota.reset_at = now + timedelta(days=30)
                else:
                    quota.reset_at = None

                count += 1
                logger.info(
                    f"Reset quota {quota.quota_type} for org {quota.organization_id}. "
                    f"Usage: {old_usage} -> 0, Next reset: {quota.reset_at}"
                )

            self.db.commit()
            return count

        except Exception as e:
            logger.error(f"Error resetting expired quotas: {e}")
            self.db.rollback()
            return 0


def get_quota_service(db: Session) -> QuotaService:
    """
    Фабричная функция для создания QuotaService.

    Args:
        db: SQLAlchemy сессия

    Returns:
        Экземпляр QuotaService
    """
    return QuotaService(db=db)
