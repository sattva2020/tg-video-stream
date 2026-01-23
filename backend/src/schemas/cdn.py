"""
CDN API schemas
Feature: 024-global-cdn-integration-edge-deployment
"""
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# === Types ===

CDNProviderType = Literal["cloudflare", "cloudfront", "fastly"]
HealthStatus = Literal["healthy", "degraded", "unhealthy"]


# === CDN Configuration Schemas ===

class CDNConfigBase(BaseModel):
    """Базовые поля конфигурации CDN."""
    provider: CDNProviderType = Field(..., description="Тип CDN провайдера")
    name: str = Field(..., min_length=1, max_length=255, description="Название конфигурации")
    enabled: bool = Field(True, description="Включена ли конфигурация")
    priority: int = Field(0, ge=0, description="Приоритет для failover (выше = важнее)")


class CDNConfigCreate(CDNConfigBase):
    """Схема для создания конфигурации CDN."""
    api_token: str = Field(..., min_length=16, description="API токен для доступа к CDN")
    account_id: Optional[str] = Field(None, description="Cloudflare Account ID")
    zone_id: Optional[str] = Field(None, description="Cloudflare Zone ID")
    distribution_id: Optional[str] = Field(None, description="AWS CloudFront Distribution ID")
    service_id: Optional[str] = Field(None, description="Fastly Service ID")


class CDNConfigUpdate(BaseModel):
    """Схема для обновления конфигурации CDN."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Название конфигурации")
    enabled: Optional[bool] = Field(None, description="Включена ли конфигурация")
    priority: Optional[int] = Field(None, ge=0, description="Приоритет для failover")
    api_token: Optional[str] = Field(None, min_length=16, description="API токен для доступа к CDN")
    account_id: Optional[str] = Field(None, description="Cloudflare Account ID")
    zone_id: Optional[str] = Field(None, description="Cloudflare Zone ID")
    distribution_id: Optional[str] = Field(None, description="AWS CloudFront Distribution ID")
    service_id: Optional[str] = Field(None, description="Fastly Service ID")


class CDNConfigResponse(CDNConfigBase):
    """Ответ с информацией о конфигурации CDN."""
    id: str = Field(..., description="UUID конфигурации")
    api_token: Optional[str] = Field(None, description="API токен (частично скрыт)")
    account_id: Optional[str] = Field(None, description="Cloudflare Account ID")
    zone_id: Optional[str] = Field(None, description="Cloudflare Zone ID")
    distribution_id: Optional[str] = Field(None, description="AWS CloudFront Distribution ID")
    service_id: Optional[str] = Field(None, description="Fastly Service ID")
    health_status: Optional[HealthStatus] = Field(None, description="Текущий статус здоровья")
    last_health_check: Optional[datetime] = Field(None, description="Время последней проверки")
    last_error: Optional[str] = Field(None, description="Последняя ошибка")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: Optional[datetime] = Field(None, description="Время последнего обновления")

    model_config = {"from_attributes": True}


# === Edge Location Schemas ===

class EdgeLocation(BaseModel):
    """Географическая локация edge узла CDN."""
    code: str = Field(..., min_length=3, max_length=3, description="IATA код города (например, AMS)")
    city: str = Field(..., min_length=1, description="Название города")
    country: str = Field(..., min_length=1, description="Название страны")
    region: str = Field(..., min_length=1, description="Регион (Europe, Asia, North America)")
    latitude: float = Field(..., ge=-90, le=90, description="Широта")
    longitude: float = Field(..., ge=-180, le=180, description="Долгота")
    active: bool = Field(True, description="Активна ли локация")


class EdgeHealthStatus(BaseModel):
    """Статус здоровья edge локации."""
    location: EdgeLocation = Field(..., description="Локация edge узла")
    status: HealthStatus = Field(..., description="Статус здоровья")
    response_time_ms: float = Field(..., ge=0, description="Время отклика в миллисекундах")
    last_check: Optional[datetime] = Field(None, description="Время последней проверки")
    error: Optional[str] = Field(None, description="Ошибка если есть")


class EdgeLocationsResponse(BaseModel):
    """Список всех edge локаций."""
    locations: List[EdgeLocation] = Field(default_factory=list, description="Список локаций")


class EdgeHealthResponse(BaseModel):
    """Сводка здоровья всех edge локаций."""
    total_locations: int = Field(..., ge=0, description="Общее количество локаций")
    healthy_locations: int = Field(..., ge=0, description="Количество здоровых локаций")
    degraded_locations: int = Field(..., ge=0, description="Количество деградировавших локаций")
    unhealthy_locations: int = Field(..., ge=0, description="Количество недоступных локаций")
    locations: List[EdgeHealthStatus] = Field(default_factory=list, description="Статус всех локаций")


# === Cache Control Schemas ===

class CacheRule(BaseModel):
    """Правило кэширования CDN."""
    pattern: str = Field(..., min_length=1, description="Шаблон URL или файла")
    cache_ttl: int = Field(..., ge=60, le=31536000, description="Time to live в секундах")
    cache_key_static: bool = Field(True, description="Игнорировать query параметры в cache key")
    browser_ttl: int = Field(3600, ge=0, le=86400, description="Время кэширования в браузере")


class CachePurgeRequest(BaseModel):
    """Запрос на очистку кэша CDN."""
    urls: Optional[List[str]] = Field(None, description="Список URL для очистки (пустой = весь кэш)")
    purge_all: bool = Field(False, description="Очистить весь кэш")
    tags: Optional[List[str]] = Field(None, description="Теги для выборочной очистки")


class CachePurgeResponse(BaseModel):
    """Ответ на запрос очистки кэша."""
    success: bool = Field(..., description="Успешность операции")
    purged_urls: List[str] = Field(default_factory=list, description="Список очищенных URL")
    purge_id: Optional[str] = Field(None, description="ID операции очистки (если поддерживается провайдером)")
    message: str = Field(..., description="Сообщение о результате")


# === CDN Status Schemas ===

class CDNStatusResponse(BaseModel):
    """Общий статус CDN конфигурации."""
    enabled_providers: List[CDNProviderType] = Field(
        default_factory=list,
        description="Список активных провайдеров"
    )
    total_configs: int = Field(..., ge=0, description="Общее количество конфигураций")
    healthy_configs: int = Field(..., ge=0, description="Количество здоровых конфигураций")
    unhealthy_configs: int = Field(..., ge=0, description="Количество проблемных конфигураций")
    active_edge_locations: int = Field(..., ge=0, description="Количество активных edge локаций")
    last_health_check: Optional[datetime] = Field(None, description="Время последней проверки здоровья")


# === Metrics Schemas ===

class CDNMetricsResponse(BaseModel):
    """Метрики производительности CDN."""
    period: str = Field(..., description="Период данных")
    total_requests: int = Field(..., ge=0, description="Общее количество запросов")
    cache_hit_rate: float = Field(..., ge=0, le=100, description="Процент кэш хитов")
    average_response_time_ms: float = Field(..., ge=0, description="Среднее время отклика")
    total_bandwidth_mb: float = Field(..., ge=0, description="Общий трафик в МБ")
    top_regions: List[dict] = Field(default_factory=list, description="Топ регионов по запросам")


class CDNRegionMetrics(BaseModel):
    """Метрики по региону."""
    region: str = Field(..., description="Название региона")
    requests: int = Field(..., ge=0, description="Количество запросов")
    average_latency_ms: float = Field(..., ge=0, description="Средняя задержка")
    cache_hit_rate: float = Field(..., ge=0, le=100, description="Процент кэш хитов")
    bandwidth_mb: float = Field(..., ge=0, description="Трафик в МБ")
