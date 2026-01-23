/**
 * CDN API Client
 * Feature: 024-global-cdn-integration-edge-deployment
 *
 * Клиент для работы с CDN-провайдерами (Cloudflare, CloudFront, Fastly).
 * Управление кэшем, статусом здоровья и edge-локациями.
 */

import { client } from '../api/client';

// === Types ===

export type CDNProviderType = 'cloudflare' | 'cloudfront' | 'fastly';
export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';

// === CDN Configuration ===

export interface CDNProvider {
  id: string;
  provider: CDNProviderType;
  name: string;
  enabled: boolean;
  priority: number;
  health_status?: HealthStatus;
  last_health_check?: string;
  last_error?: string;
  zone_id?: string;
  distribution_id?: string;
  service_id?: string;
  account_id?: string;
  created_at?: string;
  api_token?: string;
}

export interface CDNProviderListResponse {
  providers: CDNProvider[];
  total: number;
}

export interface CDNConfigCreate {
  provider: CDNProviderType;
  name: string;
  enabled?: boolean;
  priority?: number;
  api_token: string;
  account_id?: string;
  zone_id?: string;
  distribution_id?: string;
  service_id?: string;
}

export interface CDNConfigUpdate {
  name?: string;
  enabled?: boolean;
  priority?: number;
  api_token?: string;
  account_id?: string;
  zone_id?: string;
  distribution_id?: string;
  service_id?: string;
}

// === Health Status ===

export interface HealthCheckInfo {
  id: string;
  name: string;
  provider: CDNProviderType;
  status: HealthStatus;
  response_time_ms: number;
  last_check?: string;
  edge_nodes_healthy?: number;
  edge_nodes_total?: number;
  error?: string;
}

export interface CDNHealthStatusResponse {
  overall_status: HealthStatus;
  providers: HealthCheckInfo[];
  last_check: string;
  error?: string;
}

// === Cache Management ===

export interface PurgeCacheRequest {
  urls: string[];
  provider_id?: string;
  purge_all: boolean;
}

export interface PurgeCacheResponse {
  success: boolean;
  purged_urls: string[];
  providers: Array<{ provider_id: string; success: boolean; error?: string }>;
  errors: string[];
}

export interface CacheRule {
  pattern: string;
  ttl: number;
  priority?: number;
}

export interface ConfigureCacheRulesRequest {
  rules: CacheRule[];
  provider_id: string;
}

export interface ConfigureCacheRulesResponse {
  success: boolean;
  applied_rules: number;
  error?: string;
}

// === Edge Locations ===

export interface EdgeLocation {
  provider: CDNProviderType;
  provider_id: string;
  code: string;
  city: string;
  country: string;
  region: string;
  latitude: number;
  longitude: number;
  active: boolean;
}

export interface EdgeLocationsResponse {
  locations: EdgeLocation[];
  total: number;
}

// === API Functions ===

/**
 * Получить список всех CDN-провайдеров.
 *
 * @param enabledOnly - Только активные провайдеры (по умолчанию true)
 * @returns Список CDN-конфигураций
 */
export async function listProviders(enabledOnly: boolean = true): Promise<CDNProviderListResponse> {
  const response = await client.get<CDNProviderListResponse>('/api/v1/cdn/providers', {
    params: { enabled_only: enabledOnly }
  });
  return response.data;
}

/**
 * Получить информацию о конкретном CDN-провайдере.
 *
 * @param providerId - UUID провайдера
 * @returns Информация о CDN-провайдере
 */
export async function getProvider(providerId: string): Promise<CDNProvider> {
  const response = await client.get<CDNProvider>(`/api/v1/cdn/providers/${providerId}`);
  return response.data;
}

/**
 * Получить текущий статус здоровья CDN.
 *
 * @param providerId - Опциональный ID провайдера (проверяет все если не указан)
 * @param useCache - Использовать кэшированный статус (по умолчанию true)
 * @returns Статус здоровья CDN
 */
export async function getHealthStatus(
  providerId?: string,
  useCache: boolean = true
): Promise<CDNHealthStatusResponse> {
  const response = await client.get<CDNHealthStatusResponse>('/api/v1/cdn/status', {
    params: {
      provider_id: providerId,
      use_cache: useCache
    }
  });
  return response.data;
}

/**
 * Очистить кэш CDN.
 *
 * @param request - Параметры очистки кэша
 * @returns Результат операции очистки
 */
export async function purgeCache(request: PurgeCacheRequest): Promise<PurgeCacheResponse> {
  const response = await client.post<PurgeCacheResponse>('/api/v1/cdn/purge', request);
  return response.data;
}

/**
 * Получить список edge-локаций.
 *
 * @param providerId - Опциональный ID провайдера (получает все если не указан)
 * @param useCache - Использовать кэшированные данные (по умолчанию true)
 * @returns Список edge-локаций
 */
export async function listEdgeLocations(
  providerId?: string,
  useCache: boolean = true
): Promise<EdgeLocationsResponse> {
  const response = await client.get<EdgeLocationsResponse>('/api/v1/cdn/locations', {
    params: {
      provider_id: providerId,
      use_cache: useCache
    }
  });
  return response.data;
}

/**
 * Настроить правила кэширования для CDN-провайдера.
 *
 * @param request - Параметры конфигурации правил
 * @returns Результат применения правил
 */
export async function configureCacheRules(
  request: ConfigureCacheRulesRequest
): Promise<ConfigureCacheRulesResponse> {
  const response = await client.put<ConfigureCacheRulesResponse>(
    '/api/v1/cdn/cache-rules',
    request
  );
  return response.data;
}

// === API Object ===

/**
 * Объект API для работы с CDN.
 */
export const cdnApi = {
  // Providers
  listProviders,
  getProvider,

  // Health & Status
  getHealthStatus,

  // Cache Management
  purgeCache,
  configureCacheRules,

  // Edge Locations
  listEdgeLocations,
};

export default cdnApi;
