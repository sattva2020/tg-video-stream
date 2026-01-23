/**
 * Edge Deployment & Monitoring Page
 *
 * Dashboard for monitoring global CDN edge deployment and performance metrics.
 * Shows edge locations, health status, latency by region, and geographic distribution.
 *
 * Feature: 024-global-cdn-integration-edge-deployment
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { AppLayout } from '../components/layout';
import {
  cdnApi,
  type EdgeLocation,
  type CDNHealthStatusResponse,
  type HealthCheckInfo,
  type CDNProviderType,
  type CDNProvider
} from '../services/cdnApi';

// === Types ===

interface RegionMetrics {
  region: string;
  country: string;
  latency: number;
  requests: number;
  healthyNodes: number;
  totalNodes: number;
  status: 'healthy' | 'degraded' | 'unhealthy';
}

interface ProviderStats {
  provider: CDNProviderType;
  name: string;
  locations: number;
  healthyLocations: number;
  avgLatency: number;
  status: 'healthy' | 'degraded' | 'unhealthy';
}

// === Helper Components ===

const StatusBadge: React.FC<{ status: 'healthy' | 'degraded' | 'unhealthy'; size?: 'sm' | 'md' }> = ({ status, size = 'md' }) => {
  const statusConfig = {
    healthy: {
      label: 'Healthy',
      className: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400',
      dotColor: 'bg-emerald-500'
    },
    degraded: {
      label: 'Degraded',
      className: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
      dotColor: 'bg-amber-500'
    },
    unhealthy: {
      label: 'Unhealthy',
      className: 'bg-rose-500/10 border-rose-500/20 text-rose-400',
      dotColor: 'bg-rose-500'
    }
  };

  const config = statusConfig[status];
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm';

  return (
    <span className={`inline-flex items-center rounded-full font-medium border ${config.className} ${sizeClasses}`}>
      <span className={`w-1.5 h-1.5 mr-1.5 rounded-full ${config.dotColor}`} />
      {config.label}
    </span>
  );
};

const ProviderIcon: React.FC<{ provider: CDNProviderType; size?: number }> = ({ provider, size = 24 }) => {
  const icons = {
    cloudflare: '🌐',
    cloudfront: '☁️',
    fastly: '⚡'
  };
  return <span className="flex items-center justify-center" style={{ fontSize: `${size}px`, lineHeight: 1 }}>{icons[provider]}</span>;
};

const MetricCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  icon: string;
  color?: 'green' | 'blue' | 'yellow' | 'red' | 'gray';
  trend?: { value: number; isUp: boolean };
}> = ({ title, value, subtitle, icon, color = 'blue', trend }) => {
  const colorClasses = {
    green: 'text-emerald-400',
    blue: 'text-blue-400',
    yellow: 'text-amber-400',
    red: 'text-rose-400',
    gray: 'text-gray-400'
  };

  const bgClasses = {
    green: 'bg-emerald-500/10',
    blue: 'bg-blue-500/10',
    yellow: 'bg-amber-500/10',
    red: 'bg-rose-500/10',
    gray: 'bg-gray-500/10'
  };

  return (
    <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-4">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={`inline-block h-2 w-2 rounded-full ${bgClasses[color]}`}></span>
            <p className="text-sm font-medium text-[color:var(--color-text-muted)]">{title}</p>
          </div>
          <p className="text-2xl font-bold text-[color:var(--color-text)] mt-1">{value}</p>
          {subtitle && <p className="text-xs text-[color:var(--color-text-muted)] mt-1">{subtitle}</p>}
          {trend && (
            <div className={`flex items-center gap-1 mt-1 text-xs ${colorClasses[trend.isUp ? 'green' : 'red']}`}>
              <span>{trend.isUp ? '↑' : '↓'}</span>
              <span>{Math.abs(trend.value)}%</span>
            </div>
          )}
        </div>
        <span className="text-3xl ml-2">{icon}</span>
      </div>
    </div>
  );
};

// === Map Component (Simplified World Map Visualization) ===

const EdgeMap: React.FC<{
  locations: EdgeLocation[];
  healthStatus?: CDNHealthStatusResponse;
}> = ({ locations, healthStatus }) => {
  // Group locations by region for display
  const regionsByContinent = useMemo(() => {
    const regions: Record<string, EdgeLocation[]> = {
      'North America': [],
      'Europe': [],
      'Asia': [],
      'South America': [],
      'Africa': [],
      'Oceania': []
    };

    locations.forEach(loc => {
      // Simple continent mapping based on country
      const country = loc.country.toLowerCase();
      if (['us', 'ca', 'mx'].includes(country)) regions['North America'].push(loc);
      else if (['gb', 'de', 'fr', 'nl', 'it', 'es', 'pl', 'se', 'no', 'fi', 'ch', 'at', 'be', 'ie', 'pt', 'gr', 'cz', 'hu', 'ro', 'bg', 'dk', 'ua'].includes(country)) regions['Europe'].push(loc);
      else if (['cn', 'jp', 'kr', 'sg', 'hk', 'in', 'au', 'tw', 'my', 'th', 'id', 'ph', 'vn'].includes(country)) {
        if (country === 'au') regions['Oceania'].push(loc);
        else regions['Asia'].push(loc);
      }
      else if (['br', 'ar', 'cl', 'co', 'pe', 've'].includes(country)) regions['South America'].push(loc);
      else if (['za', 'ng', 'eg', 'ke', 'ma'].includes(country)) regions['Africa'].push(loc);
      else regions['North America'].push(loc); // Default
    });

    return regions;
  }, [locations]);

  const getRegionStatus = (regionLocations: EdgeLocation[]): 'healthy' | 'degraded' | 'unhealthy' => {
    if (regionLocations.length === 0) return 'healthy';
    const activeCount = regionLocations.filter(l => l.active).length;
    const ratio = activeCount / regionLocations.length;
    if (ratio >= 0.9) return 'healthy';
    if (ratio >= 0.5) return 'degraded';
    return 'unhealthy';
  };

  return (
    <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-6">
      <h3 className="text-lg font-semibold text-[color:var(--color-text)] mb-4">Global Edge Distribution</h3>

      {/* Simplified Map Visualization */}
      <div className="relative bg-[color:var(--color-surface)] rounded-xl p-6 mb-4" style={{ minHeight: '300px' }}>
        <div className="grid grid-cols-3 gap-4 h-full">
          {Object.entries(regionsByContinent).map(([continent, locs]) => {
            const status = getRegionStatus(locs);
            const statusColors = {
              healthy: 'bg-emerald-500/20 border-emerald-500/40',
              degraded: 'bg-amber-500/20 border-amber-500/40',
              unhealthy: 'bg-rose-500/20 border-rose-500/40'
            };

            return (
              <div
                key={continent}
                className={`rounded-lg border-2 p-4 ${statusColors[status]} transition-all hover:scale-105`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-[color:var(--color-text)]">{continent}</h4>
                  <StatusBadge status={status} size="sm" />
                </div>
                <div className="text-2xl font-bold text-[color:var(--color-text)]">{locs.length}</div>
                <div className="text-xs text-[color:var(--color-text-muted)]">locations</div>
                {locs.length > 0 && (
                  <div className="mt-2 space-y-1 max-h-20 overflow-auto">
                    {locs.slice(0, 3).map(loc => (
                      <div key={loc.code} className="text-xs text-[color:var(--color-text-muted)] flex items-center gap-1">
                        <span className={`w-1.5 h-1.5 rounded-full ${loc.active ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
                        {loc.city}, {loc.country.toUpperCase()}
                      </div>
                    ))}
                    {locs.length > 3 && (
                      <div className="text-xs text-[color:var(--color-text-muted)]">+{locs.length - 3} more</div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs text-[color:var(--color-text-muted)]">
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span>Healthy</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-amber-500"></span>
          <span>Degraded</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-rose-500"></span>
          <span>Unhealthy</span>
        </div>
        <div className="ml-auto">{locations.length} total locations</div>
      </div>
    </div>
  );
};

// === Latency Chart Component ===

const LatencyChart: React.FC<{ metrics: RegionMetrics[] }> = ({ metrics }) => {
  const maxLatency = Math.max(...metrics.map(m => m.latency), 100);

  return (
    <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-6">
      <h3 className="text-lg font-semibold text-[color:var(--color-text)] mb-4">Latency by Region</h3>

      <div className="space-y-3">
        {metrics.map((metric, idx) => {
          const percentage = (metric.latency / maxLatency) * 100;
          const colorClass = metric.status === 'healthy' ? 'bg-emerald-500' :
                            metric.status === 'degraded' ? 'bg-amber-500' : 'bg-rose-500';

          return (
            <div key={idx} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-[color:var(--color-text)]">{metric.region}</span>
                <span className="text-[color:var(--color-text-muted)]">{metric.latency}ms</span>
              </div>
              <div className="h-2 bg-[color:var(--color-surface)] rounded-full overflow-hidden">
                <div
                  className={`h-full ${colorClass} transition-all duration-300`}
                  style={{ width: `${percentage}%` }}
                ></div>
              </div>
              <div className="flex items-center justify-between text-xs text-[color:var(--color-text-muted)]">
                <span>{metric.country}</span>
                <span>{metric.requests.toLocaleString()} req/s</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// === Main Page Component ===

const EdgeDeployment: React.FC = () => {
  const { t } = useTranslation();
  const [locations, setLocations] = useState<EdgeLocation[]>([]);
  const [healthStatus, setHealthStatus] = useState<CDNHealthStatusResponse | null>(null);
  const [providers, setProviders] = useState<CDNProvider[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);

  // Fetch edge locations
  const fetchLocations = useCallback(async () => {
    try {
      const response = await cdnApi.listEdgeLocations(selectedProvider || undefined, false);
      setLocations(response.locations);
    } catch (err: any) {
      const errorMsg = err?.response?.data?.detail || err?.message || 'Failed to fetch edge locations';
      setError(errorMsg);
    }
  }, [selectedProvider]);

  // Fetch health status
  const fetchHealthStatus = useCallback(async () => {
    try {
      const response = await cdnApi.getHealthStatus(selectedProvider || undefined, false);
      setHealthStatus(response);
    } catch (err: any) {
      console.error('Failed to fetch health status:', err);
    }
  }, [selectedProvider]);

  // Fetch providers
  const fetchProviders = useCallback(async () => {
    try {
      const response = await cdnApi.listProviders(false);
      setProviders(response.providers);
    } catch (err: any) {
      console.error('Failed to fetch providers:', err);
    }
  }, []);

  // Initial load and refresh
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      setError(null);
      await Promise.all([
        fetchLocations(),
        fetchHealthStatus(),
        fetchProviders()
      ]);
      setIsLoading(false);
    };

    loadData();
  }, [fetchLocations, fetchHealthStatus, fetchProviders]);

  const handleRefresh = () => {
    fetchLocations();
    fetchHealthStatus();
    fetchProviders();
  };

  // Calculate provider statistics
  const providerStats = useMemo((): ProviderStats[] => {
    return providers.map(provider => {
      const providerLocations = locations.filter(l => l.provider_id === provider.id);
      const healthyLocations = providerLocations.filter(l => l.active).length;
      const providerHealth = healthStatus?.providers.find(p => p.id === provider.id);

      return {
        provider: provider.provider,
        name: provider.name,
        locations: providerLocations.length,
        healthyLocations,
        avgLatency: providerHealth?.response_time_ms || 0,
        status: providerHealth?.status || 'healthy'
      };
    });
  }, [providers, locations, healthStatus]);

  // Calculate region metrics (simulated for demo)
  const regionMetrics = useMemo((): RegionMetrics[] => {
    const metrics: RegionMetrics[] = [];
    const regions = ['North America', 'Europe', 'Asia Pacific', 'South America', 'Africa'];

    regions.forEach(region => {
      const regionLocations = locations.filter(l => {
        const country = l.country.toLowerCase();
        if (region === 'North America') return ['us', 'ca', 'mx'].includes(country);
        if (region === 'Europe') return ['gb', 'de', 'fr', 'nl', 'it', 'es'].includes(country);
        if (region === 'Asia Pacific') return ['jp', 'sg', 'au', 'kr', 'hk', 'in'].includes(country);
        if (region === 'South America') return ['br', 'ar', 'cl'].includes(country);
        if (region === 'Africa') return ['za', 'ng', 'eg'].includes(country);
        return false;
      });

      if (regionLocations.length > 0) {
        const activeCount = regionLocations.filter(l => l.active).length;
        const ratio = activeCount / regionLocations.length;
        const status: 'healthy' | 'degraded' | 'unhealthy' =
          ratio >= 0.9 ? 'healthy' : ratio >= 0.5 ? 'degraded' : 'unhealthy';

        // Simulated latency based on region
        const baseLatency = region === 'North America' ? 20 :
                           region === 'Europe' ? 35 :
                           region === 'Asia Pacific' ? 80 :
                           region === 'South America' ? 120 : 150;

        metrics.push({
          region,
          country: regionLocations[0]?.country || 'Unknown',
          latency: baseLatency + Math.floor(Math.random() * 20),
          requests: Math.floor(Math.random() * 5000) + 1000,
          healthyNodes: activeCount,
          totalNodes: regionLocations.length,
          status
        });
      }
    });

    return metrics;
  }, [locations]);

  // Overall metrics
  const totalLocations = locations.length;
  const activeLocations = locations.filter(l => l.active).length;
  const overallHealth = healthStatus?.overall_status || 'healthy';
  const avgLatency = healthStatus?.providers.reduce((sum, p) => sum + p.response_time_ms, 0) /
                     (healthStatus?.providers.length || 1) || 0;

  if (isLoading) {
    return (
      <AppLayout>
        <div className="mx-auto max-w-7xl">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-cyan-500 border-t-transparent mx-auto mb-4"></div>
              <p className="text-[color:var(--color-text-muted)]">Loading edge deployment data...</p>
            </div>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[color:var(--color-text)]">Edge Deployment</h1>
            <p className="text-sm text-[color:var(--color-text-muted)]">
              Global CDN edge locations and performance monitoring
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Provider Filter */}
            <select
              value={selectedProvider || 'all'}
              onChange={(e) => setSelectedProvider(e.target.value === 'all' ? null : e.target.value)}
              className="px-3 py-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-sm text-[color:var(--color-text)] focus:outline-none focus:ring-2 focus:ring-[color:var(--color-accent)]"
            >
              <option value="all">All Providers</option>
              {providers.map(provider => (
                <option key={provider.id} value={provider.id}>{provider.name}</option>
              ))}
            </select>
            <button
              onClick={handleRefresh}
              className="px-4 py-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-sm hover:bg-[color:var(--color-surface-muted)] transition-colors"
            >
              Refresh
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400">
            {error}
          </div>
        )}

        {/* Overview Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Locations"
            value={totalLocations}
            subtitle={`${activeLocations} active`}
            icon="🌍"
            color={overallHealth === 'healthy' ? 'green' : overallHealth === 'degraded' ? 'yellow' : 'red'}
          />
          <MetricCard
            title="Providers"
            value={providers.filter(p => p.enabled).length}
            subtitle={`of ${providers.length} configured`}
            icon="🔌"
            color="blue"
          />
          <MetricCard
            title="Avg Latency"
            value={`${Math.round(avgLatency)}ms`}
            subtitle="Across all regions"
            icon="⚡"
            color={avgLatency < 50 ? 'green' : avgLatency < 100 ? 'yellow' : 'red'}
          />
          <MetricCard
            title="Health Status"
            value={overallHealth}
            icon="💚"
            color={overallHealth === 'healthy' ? 'green' : overallHealth === 'degraded' ? 'yellow' : 'red'}
          />
        </div>

        {/* Global Map */}
        <EdgeMap locations={locations} healthStatus={healthStatus || undefined} />

        {/* Two Column Layout: Provider Stats & Latency */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Provider Statistics */}
          <div>
            <h2 className="text-lg font-semibold text-[color:var(--color-text)] mb-3">Provider Statistics</h2>
            <div className="space-y-3">
              {providerStats.length === 0 ? (
                <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 p-6 text-center">
                  <span className="text-4xl mb-2 block">🔌</span>
                  <p className="text-[color:var(--color-text-muted)]">No providers configured</p>
                </div>
              ) : (
                providerStats.map(stat => (
                  <div
                    key={stat.provider}
                    className="rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] p-4 hover:border-[color:var(--color-accent)] transition-colors"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <ProviderIcon provider={stat.provider} size={28} />
                        <div>
                          <h3 className="font-semibold text-[color:var(--color-text)]">{stat.name}</h3>
                          <p className="text-xs text-[color:var(--color-text-muted)] capitalize">{stat.provider}</p>
                        </div>
                      </div>
                      <StatusBadge status={stat.status} size="sm" />
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="text-lg font-bold text-[color:var(--color-text)]">{stat.locations}</div>
                        <div className="text-xs text-[color:var(--color-text-muted)]">Locations</div>
                      </div>
                      <div>
                        <div className="text-lg font-bold text-[color:var(--color-text)]">{stat.healthyLocations}</div>
                        <div className="text-xs text-[color:var(--color-text-muted)]">Healthy</div>
                      </div>
                      <div>
                        <div className="text-lg font-bold text-[color:var(--color-text)]">{stat.avgLatency}ms</div>
                        <div className="text-xs text-[color:var(--color-text-muted)]">Avg Latency</div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Latency Chart */}
          <div>
            <h2 className="text-lg font-semibold text-[color:var(--color-text)] mb-3">Regional Performance</h2>
            <LatencyChart metrics={regionMetrics} />
          </div>
        </div>

        {/* Locations Table */}
        <div>
          <h2 className="text-lg font-semibold text-[color:var(--color-text)] mb-3">
            All Locations ({locations.length})
          </h2>
          <div className="rounded-2xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)] shadow-md shadow-black/5 overflow-hidden">
            {locations.length === 0 ? (
              <div className="p-8 text-center">
                <span className="text-4xl mb-2 block">📍</span>
                <p className="text-[color:var(--color-text-muted)]">No edge locations available</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-[color:var(--color-surface)]">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[color:var(--color-text-muted)] uppercase tracking-wider">Provider</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[color:var(--color-text-muted)] uppercase tracking-wider">Location</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[color:var(--color-text-muted)] uppercase tracking-wider">Code</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[color:var(--color-text-muted)] uppercase tracking-wider">Region</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[color:var(--color-text-muted)] uppercase tracking-wider">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[color:var(--color-border)]">
                    {locations.slice(0, 10).map((location, idx) => (
                      <tr key={idx} className="hover:bg-[color:var(--color-surface-muted)]">
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="flex items-center gap-2">
                            <ProviderIcon provider={location.provider} size={20} />
                            <span className="text-sm text-[color:var(--color-text)] capitalize">{location.provider}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <div className="text-sm text-[color:var(--color-text)]">{location.city}</div>
                          <div className="text-xs text-[color:var(--color-text-muted)]">{location.country}</div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-[color:var(--color-text-muted)] font-mono">
                          {location.code}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-sm text-[color:var(--color-text-muted)]">
                          {location.region}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          {location.active ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400">
                              Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400">
                              Inactive
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {locations.length > 10 && (
                  <div className="px-4 py-3 bg-[color:var(--color-surface)] text-center text-sm text-[color:var(--color-text-muted)]">
                    Showing 10 of {locations.length} locations
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Debug Info (dev only) */}
        {import.meta.env.DEV && (
          <details className="mt-4">
            <summary className="cursor-pointer text-sm text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)]">
              Debug Info
            </summary>
            <div className="mt-2 p-4 rounded-lg bg-[color:var(--color-surface)] text-xs font-mono overflow-auto max-h-64">
              <pre>{JSON.stringify({ locations, healthStatus, providerStats }, null, 2)}</pre>
            </div>
          </details>
        )}
      </div>
    </AppLayout>
  );
};

export default EdgeDeployment;
