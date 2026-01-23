"""
CDNConfig Value Object для CDN провайдеров (Feature 024).

**Architecture Layer**: Domain
**Dependencies**: None (pure Python)
**Usage**: CDN Config Entity, CDN service.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.domain.errors import ValidationError
from src.shared.kernel.result import Result
from src.shared.kernel.value_object import ValueObject


class CDNProviderType(str, Enum):
    """Типы CDN провайдеров."""
    CLOUDFLARE = "cloudflare"
    CLOUDFRONT = "cloudfront"
    FASTLY = "fastly"


@dataclass(frozen=True)
class CDNConfig(ValueObject):
    """
    Конфигурация CDN провайдера.

    **Validation**:
    - Provider должен быть валидным типом
    - API ключ не пустой
    - Zone ID или Distribution ID для некоторых провайдеров

    Examples:
        >>> config = CDNConfig(
        ...     provider=CDNProviderType.CLOUDFLARE,
        ...     api_token="secret_token",
        ...     zone_id="zone123",
        ...     enabled=True
        ... )
        >>> config.provider.value
        'cloudflare'
    """

    provider: CDNProviderType
    api_token: str
    zone_id: Optional[str] = None  # Cloudflare zone ID
    distribution_id: Optional[str] = None  # CloudFront distribution ID
    service_id: Optional[str] = None  # Fastly service ID
    account_id: Optional[str] = None  # Cloudflare account ID
    enabled: bool = True

    def __post_init__(self):
        """Валидация конфигурации CDN при создании."""
        if not self._is_valid(self.provider, self.api_token):
            raise ValidationError(f"Invalid CDNConfig: provider={self.provider}, api_token={'*' * len(self.api_token)}")

    @staticmethod
    def _is_valid(provider: CDNProviderType, api_token: str) -> bool:
        """
        Проверяет валидность конфигурации CDN.

        **Rules**:
        - Provider валидный enum
        - API токен не пустой
        - Минимальная длина токена 16 символов
        """
        if not isinstance(provider, CDNProviderType):
            return False
        if not api_token or not isinstance(api_token, str):
            return False
        if len(api_token) < 16:
            return False
        return True

    @staticmethod
    def create(
        provider: str,
        api_token: str,
        zone_id: Optional[str] = None,
        distribution_id: Optional[str] = None,
        service_id: Optional[str] = None,
        account_id: Optional[str] = None,
        enabled: bool = True
    ) -> Result["CDNConfig", ValidationError]:
        """
        Factory method с Result pattern для безопасного создания CDNConfig.

        Args:
            provider: Название провайдера (cloudflare, cloudfront, fastly)
            api_token: API токен для доступа
            zone_id: Cloudflare zone ID
            distribution_id: CloudFront distribution ID
            service_id: Fastly service ID
            account_id: Cloudflare account ID
            enabled: Включена ли конфигурация

        Returns:
            Result[CDNConfig, ValidationError]: Ok(CDNConfig) или Err(ValidationError)
        """
        try:
            provider_enum = CDNProviderType(provider)
        except ValueError:
            return Result.failure(
                ValidationError(f"Invalid CDN provider: {provider}")
            )

        if not CDNConfig._is_valid(provider_enum, api_token):
            return Result.failure(
                ValidationError(f"Invalid CDN configuration for {provider}")
            )

        return Result.success(
            CDNConfig(
                provider=provider_enum,
                api_token=api_token,
                zone_id=zone_id,
                distribution_id=distribution_id,
                service_id=service_id,
                account_id=account_id,
                enabled=enabled
            )
        )

    def is_cloudflare(self) -> bool:
        """True если это Cloudflare CDN."""
        return self.provider == CDNProviderType.CLOUDFLARE

    def is_cloudfront(self) -> bool:
        """True если это AWS CloudFront CDN."""
        return self.provider == CDNProviderType.CLOUDFRONT

    def is_fastly(self) -> bool:
        """True если это Fastly CDN."""
        return self.provider == CDNProviderType.FASTLY

    def get_identifier(self) -> Optional[str]:
        """
        Получить основной идентификатор ресурса CDN.

        Returns:
            zone_id для Cloudflare, distribution_id для CloudFront,
            service_id для Fastly
        """
        if self.is_cloudflare():
            return self.zone_id
        if self.is_cloudfront():
            return self.distribution_id
        if self.is_fastly():
            return self.service_id
        return None

    def __str__(self) -> str:
        """String representation для logging/debugging."""
        return f"CDNConfig(provider={self.provider.value}, enabled={self.enabled})"


@dataclass(frozen=True)
class CacheRule(ValueObject):
    """
    Правило кэширования CDN.

    **Attributes**:
    - pattern: Шаблон URL или файла (например, "*.mp4", "/api/*")
    - cache_ttl: Time to live в секундах
    - cache_key_static: Игнорировать query параметры в cache key
    - browser_ttl: Время кэширования в браузере в секундах

    Examples:
        >>> rule = CacheRule(
        ...     pattern="*.mp4",
        ...     cache_ttl=86400,
        ...     cache_key_static=True
        ... )
        >>> rule.pattern
        '*.mp4'
    """

    pattern: str
    cache_ttl: int
    cache_key_static: bool = True
    browser_ttl: int = 3600

    def __post_init__(self):
        """Валидация правила кэширования при создании."""
        if not self._is_valid(self.pattern, self.cache_ttl):
            raise ValidationError(
                f"Invalid CacheRule: pattern={self.pattern}, ttl={self.cache_ttl}"
            )

    @staticmethod
    def _is_valid(pattern: str, cache_ttl: int) -> bool:
        """
        Проверяет валидность правила кэширования.

        **Rules**:
        - Pattern не пустой
        - TTL положительное число (минимум 60 секунд)
        - TTL не более 31536000 (1 год)
        """
        if not pattern or not isinstance(pattern, str):
            return False
        if not isinstance(cache_ttl, int):
            return False
        if cache_ttl < 60 or cache_ttl > 31536000:
            return False
        return True

    def __str__(self) -> str:
        """String representation."""
        return f"CacheRule(pattern='{self.pattern}', ttl={self.cache_ttl}s)"
