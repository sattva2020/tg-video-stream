"""
SAML Service
Spec: 025-advanced-security-compliance-features

Сервис для обработки SAML 2.0 аутентификации через SSO.
Поддержка Okta, Azure AD, Google Workspace и других SAML-совместимых IdP.
"""

import os
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from src.models.user import User
from src.models.saml_config import SAMLConfig
from src.core.config import settings

# SAML library imports
try:
    from onelogin.saml2.auth import OneLogin_Saml2_Auth
    from onelogin.saml2.utils import OneLogin_Saml2_Utils
    SAML_AVAILABLE = True
except ImportError:
    SAML_AVAILABLE = False


class SAMLService:
    """Сервис для управления SAML аутентификацией."""

    def __init__(self):
        self.enabled = settings.SAML_ENABLED and SAML_AVAILABLE

    def _prepare_saml_auth(
        self,
        config: SAMLConfig,
        request_data: Dict[str, Any]
    ) -> Optional[OneLogin_Saml2_Auth]:
        """
        Подготавливает экземпляр OneLogin_Saml2_Auth с конфигурацией.

        Args:
            config: Конфигурация SAML из базы данных
            request_data: Данные HTTP запроса для SAML библиотеки

        Returns:
            OneLogin_Saml2_Auth instance или None если библиотека недоступна
        """
        if not SAML_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="SAML library is not available. Install python3-saml package."
            )

        # Формируем конфигурацию для SAML библиотеки
        saml_settings = {
            'strict': True,
            'debug': settings.ENVIRONMENT == 'development',
            'sp': {
                'entityId': config.sp_entity_id,
                'assertionConsumerService': {
                    'url': config.sp_acs_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
                },
                'singleLogoutService': {
                    'url': config.sp_slo_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'NameIDFormat': config.get_name_id_format(),
                'x509cert': '',
                'privateKey': ''
            },
            'idp': {
                'entityId': config.idp_entity_id,
                'singleSignOnService': {
                    'url': config.idp_sso_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                },
                'singleLogoutService': {
                    'url': config.idp_slo_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                } if config.idp_slo_url else None,
                'x509cert': config.get_idp_cert()
            },
            'security': config.get_security_config()
        }

        # Удаляем None значения из словаря
        saml_settings['idp'] = {k: v for k, v in saml_settings['idp'].items() if v is not None}

        return OneLogin_Saml2_Auth(request_data, old_settings=saml_settings)

    def initiate_login(
        self,
        config: SAMLConfig,
        request_data: Dict[str, Any],
        return_to: Optional[str] = None
    ) -> str:
        """
        Инициирует SAML login - возвращает URL для перенаправления на IdP.

        Args:
            config: Конфигурация SAML из базы данных
            request_data: Данные HTTP запроса
            return_to: URL для возврата после успешной аутентификации

        Returns:
            URL IdP для перенаправления пользователя

        Raises:
            HTTPException: Если SAML недоступен или конфигурация неверна
        """
        if not config.is_active():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SAML configuration is not enabled"
            )

        auth = self._prepare_saml_auth(config, request_data)
        if not auth:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="SAML library is not available"
            )

        return auth.login(return_to)

    def process_response(
        self,
        config: SAMLConfig,
        request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Обрабатывает SAML Response от IdP.

        Args:
            config: Конфигурация SAML из базы данных
            request_data: Данные HTTP запроса с SAML response

        Returns:
            Словарь с атрибутами пользователя из SAML assertion

        Raises:
            HTTPException: Если валидация SAML response не удалась
        """
        auth = self._prepare_saml_auth(config, request_data)
        if not auth:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="SAML library is not available"
            )

        auth.process_response()

        errors = auth.get_errors()
        if errors:
            error_reason = auth.get_last_error_reason()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"SAML authentication failed: {error_reason}"
            )

        if not auth.is_authenticated():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="SAML authentication failed: Not authenticated"
            )

        # Получаем атрибуты пользователя из SAML assertion
        attributes = auth.get_attributes()
        name_id = auth.get_nameid()

        return {
            'name_id': name_id,
            'attributes': attributes,
            'session_index': auth.get_session_index()
        }

    def get_or_create_user(
        self,
        db: Session,
        saml_data: Dict[str, Any],
        config: SAMLConfig
    ) -> Tuple[User, bool]:
        """
        Получает или создаёт пользователя на основе SAML данных.

        Args:
            db: Сессия базы данных
            saml_data: Данные из SAML assertion (от process_response)
            config: Конфигурация SAML для маппинга атрибутов

        Returns:
            Tuple (User, is_new_user)

        Raises:
            HTTPException: Если email уже занят другим методом
        """
        attribute_mapping = config.get_attribute_mapping()
        attributes = saml_data['attributes']
        name_id = saml_data['name_id']

        # Извлекаем email из атрибутов согласно маппингу
        email_attr = attribute_mapping.get('email', 'email')
        email = self._extract_attribute(attributes, email_attr)

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email attribute not found in SAML response"
            )

        # Проверяем, существует ли пользователь с этим SAML NameID
        user = db.query(User).filter(User.saml_name_id == name_id).first()

        if user:
            # Обновляем данные пользователя при логине
            user.full_name = self._extract_attribute(attributes, attribute_mapping.get('full_name', 'displayName'))
            db.commit()
            db.refresh(user)
            return user, False

        # Проверяем, не занят ли email другим методом
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Please sign in with your original method."
            )

        # Определяем роль на основе role mapping
        role = self._map_user_role(attributes, config.role_mapping)

        # Создаём нового пользователя
        full_name = self._extract_attribute(attributes, attribute_mapping.get('full_name', 'displayName'))
        new_user = User(
            email=email,
            full_name=full_name or email.split('@')[0],
            saml_name_id=name_id,
            saml_config_id=config.id,
            role=role,
            status='active'  # SAML пользователи активны сразу (или pending по политике)
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return new_user, True

    def _extract_attribute(self, attributes: Dict[str, Any], key: str) -> Optional[str]:
        """
        Извлекает значение атрибута из SAML attributes.

        Args:
            attributes: Словарь атрибутов из SAML
            key: Ключ атрибута (может содержать выражения типа "firstName + ' ' + lastName")

        Returns:
            Строковое значение атрибута или None
        """
        if not attributes:
            return None

        # Простой случай - ключ существует в атрибутах
        if key in attributes:
            value = attributes[key]
            if isinstance(value, list):
                return value[0] if value else None
            return str(value)

        # Сложный случай - выражение с конкатенацией
        if '+' in key:
            # Простейшая обработка выражений без eval для безопасности
            parts = [p.strip().strip('"\'') for p in key.split('+')]
            result_parts = []
            for part in parts:
                if part in attributes:
                    value = attributes[part]
                    if isinstance(value, list):
                        result_parts.append(str(value[0]) if value else '')
                    else:
                        result_parts.append(str(value))
                else:
                    result_parts.append(part)
            return ''.join(result_parts).strip() or None

        return None

    def _map_user_role(self, attributes: Dict[str, Any], role_mapping: Optional[Dict]) -> str:
        """
        Определяет роль пользователя на основе SAML групп/ролей.

        Args:
            attributes: SAML атрибуты пользователя
            role_mapping: Маппинг групп IdP на роли приложения

        Returns:
            Строка с ролью пользователя
        """
        if not role_mapping:
            return 'user'  # Роль по умолчанию

        # Извлекаем группы из атрибутов
        groups = attributes.get('groups', [])
        if not isinstance(groups, list):
            groups = [groups]

        # Проверяем маппинг ролей
        for role, idp_groups in role_mapping.items():
            for idp_group in idp_groups:
                if idp_group in groups:
                    return role

        return 'user'  # Роль по умолчанию

    def initiate_logout(
        self,
        config: SAMLConfig,
        request_data: Dict[str, Any],
        name_id: Optional[str] = None,
        session_index: Optional[str] = None
    ) -> Optional[str]:
        """
        Инициирует SAML Single Logout.

        Args:
            config: Конфигурация SAML из базы данных
            request_data: Данные HTTP запроса
            name_id: Идентификатор пользователя в SAML
            session_index: Индекс сессии для logout

        Returns:
            URL IdP для перенаправления на logout или None если logout не настроен
        """
        if not config.idp_slo_url:
            return None

        auth = self._prepare_saml_auth(config, request_data)
        if not auth:
            return None

        return auth.logout(name_id=name_id, session_index=session_index)

    def process_logout_response(
        self,
        config: SAMLConfig,
        request_data: Dict[str, Any]
    ) -> bool:
        """
        Обрабатывает SAML Logout Response от IdP.

        Args:
            config: Конфигурация SAML из базы данных
            request_data: Данные HTTP запроса с SAML logout response

        Returns:
            True если logout успешен

        Raises:
            HTTPException: Если logout response неверен
        """
        auth = self._prepare_saml_auth(config, request_data)
        if not auth:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="SAML library is not available"
            )

        auth.process_slo()

        errors = auth.get_errors()
        if errors:
            error_reason = auth.get_last_error_reason()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SAML logout failed: {error_reason}"
            )

        return True

    def get_metadata(self, config: SAMLConfig) -> str:
        """
        Генерирует SP метаданные для регистрации в IdP.

        Args:
            config: Конфигурация SAML из базы данных

        Returns:
            XML с SP метаданными
        """
        if not SAML_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="SAML library is not available"
            )

        # Формируем минимальную конфигурацию для генерации метаданных
        saml_settings = {
            'strict': True,
            'sp': {
                'entityId': config.sp_entity_id,
                'assertionConsumerService': {
                    'url': config.sp_acs_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST'
                },
                'singleLogoutService': {
                    'url': config.sp_slo_url,
                    'binding': 'urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect'
                } if config.sp_slo_url else None,
                'NameIDFormat': config.get_name_id_format(),
                'x509cert': '',
                'privateKey': ''
            },
            'security': config.get_security_config()
        }

        # Удаляем None значения
        saml_settings['sp'] = {k: v for k, v in saml_settings['sp'].items() if v is not None}

        from onelogin.saml2.metadata import OneLogin_Saml2_Metadata
        metadata = OneLogin_Saml2_Metadata.build(saml_settings)

        return metadata


# Singleton instance
saml_service = SAMLService() if SAML_AVAILABLE else None
