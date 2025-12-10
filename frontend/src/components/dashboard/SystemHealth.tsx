import React from 'react';
import { motion } from 'framer-motion';
import { 
  Server, 
  Cpu, 
  HardDrive, 
  Wifi, 
  Database,
  Activity,
  CheckCircle,
  AlertTriangle,
  XCircle,
  RefreshCw
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Progress } from '@heroui/react';
import { useSystemMetrics } from '../../hooks/useSystemMetrics';
import { formatUptime } from '../../types/system';

interface SystemMetric {
  id: string;
  name: string;
  value: number;
  max: number;
  unit: string;
  status: 'healthy' | 'warning' | 'critical';
}

interface SystemHealthProps {
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  networkLatency: number;
  dbConnections: number;
  maxDbConnections: number;
  loading?: boolean;
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'healthy': return 'success';
    case 'warning': return 'warning';
    case 'critical': return 'danger';
    default: return 'default';
  }
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'healthy': return CheckCircle;
    case 'warning': return AlertTriangle;
    case 'critical': return XCircle;
    default: return Activity;
  }
};

const getStatusFromValue = (value: number, warningThreshold: number, criticalThreshold: number): 'healthy' | 'warning' | 'critical' => {
  if (value >= criticalThreshold) return 'critical';
  if (value >= warningThreshold) return 'warning';
  return 'healthy';
};

const MetricCard: React.FC<{ 
  icon: React.ElementType; 
  label: string; 
  value: number; 
  unit: string;
  status: 'healthy' | 'warning' | 'critical';
  showProgress?: boolean;
  index: number;
}> = ({ icon: Icon, label, value, unit, status, showProgress = true, index }) => {
  const StatusIcon = getStatusIcon(status);
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="p-3 rounded-xl bg-[color:var(--color-surface-muted)]/50 border border-[color:var(--color-border)]"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-[color:var(--color-text-muted)]" />
          <span className="text-xs font-medium text-[color:var(--color-text-muted)]">
            {label}
          </span>
        </div>
        <StatusIcon className={`w-4 h-4 ${
          status === 'healthy' ? 'text-emerald-500' :
          status === 'warning' ? 'text-amber-500' :
          'text-rose-500'
        }`} />
      </div>
      
      <div className="flex items-end justify-between">
        <span className="text-lg font-bold text-[color:var(--color-text)]">
          {value}{unit}
        </span>
      </div>
      
      {showProgress && (
        <Progress
          size="sm"
          value={value}
          maxValue={100}
          color={getStatusColor(status) as any}
          className="mt-2"
        />
      )}
    </motion.div>
  );
};

export const SystemHealth: React.FC<SystemHealthProps> = ({
  cpuUsage,
  memoryUsage,
  diskUsage,
  networkLatency,
  dbConnections,
  maxDbConnections,
  loading = false,
}) => {
  const { t } = useTranslation();

  const metrics: SystemMetric[] = [
    {
      id: 'cpu',
      name: t('admin.cpu', 'CPU'),
      value: cpuUsage,
      max: 100,
      unit: '%',
      status: getStatusFromValue(cpuUsage, 70, 90),
    },
    {
      id: 'memory',
      name: t('admin.memory', 'RAM'),
      value: memoryUsage,
      max: 100,
      unit: '%',
      status: getStatusFromValue(memoryUsage, 75, 90),
    },
    {
      id: 'disk',
      name: t('admin.disk', 'Диск'),
      value: diskUsage,
      max: 100,
      unit: '%',
      status: getStatusFromValue(diskUsage, 80, 95),
    },
    {
      id: 'network',
      name: t('admin.latency', 'Latency'),
      value: networkLatency,
      max: 1000,
      unit: 'ms',
      status: getStatusFromValue(networkLatency, 100, 500),
    },
  ];

  const overallHealth = metrics.every(m => m.status === 'healthy') 
    ? 'healthy' 
    : metrics.some(m => m.status === 'critical') 
      ? 'critical' 
      : 'warning';

  const attentionMetric = metrics.find(m => m.status !== 'healthy');

  const OverallIcon = getStatusIcon(overallHealth);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-cyan-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('admin.systemHealth', 'Здоровье системы')}
          </h3>
        </div>
        <div className="p-4 rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)] animate-pulse">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-cyan-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('admin.systemHealth', 'Здоровье системы')}
          </h3>
        </div>
        <div className={`
          flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border
          ${overallHealth === 'healthy' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200/60 dark:border-emerald-500/40' :
            overallHealth === 'warning' ? 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-200/80 dark:border-amber-500/40' :
            'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-200/80 dark:border-rose-500/40'}
        `}>
          <OverallIcon className="w-3.5 h-3.5" />
          {overallHealth === 'healthy' ? t('admin.allSystemsGo', 'Всё в норме') :
           overallHealth === 'warning' ? t('admin.needsAttention', 'Требует внимания') :
           t('admin.critical', 'Критично')}
        </div>
      </div>
      {attentionMetric && (
        <p className="text-xs text-amber-700 dark:text-amber-300 mt-1 leading-snug">
          {attentionMetric.name}: {attentionMetric.value}{attentionMetric.unit} — {t('admin.needsAttention', 'Требует внимания')}
        </p>
      )}
      
      <div className="p-4 rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricCard
            icon={Cpu}
            label={metrics[0].name}
            value={metrics[0].value}
            unit={metrics[0].unit}
            status={metrics[0].status}
            index={0}
          />
          <MetricCard
            icon={HardDrive}
            label={metrics[1].name}
            value={metrics[1].value}
            unit={metrics[1].unit}
            status={metrics[1].status}
            index={1}
          />
          <MetricCard
            icon={Database}
            label={metrics[2].name}
            value={metrics[2].value}
            unit={metrics[2].unit}
            status={metrics[2].status}
            index={2}
          />
          <MetricCard
            icon={Wifi}
            label={metrics[3].name}
            value={metrics[3].value}
            unit={metrics[3].unit}
            status={metrics[3].status}
            showProgress={false}
            index={3}
          />
        </div>
        
        {/* Database connections */}
        <div className="mt-4 pt-4 border-t border-[color:var(--color-border)]">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-[color:var(--color-text-muted)]" />
              <span className="text-[color:var(--color-text-muted)]">
                {t('admin.dbConnections', 'DB Connections')}
              </span>
            </div>
            <span className="font-medium text-[color:var(--color-text)]">
              {dbConnections} / {maxDbConnections}
            </span>
          </div>
          <Progress
            size="sm"
            value={dbConnections}
            maxValue={maxDbConnections}
            color={getStatusColor(getStatusFromValue((dbConnections / maxDbConnections) * 100, 70, 90)) as any}
            className="mt-2"
          />
        </div>
      </div>
    </div>
  );
};

/**
 * SystemHealthLive — компонент с реальными данными через useSystemMetrics.
 * Spec: 015-real-system-monitoring
 * 
 * Автоматически обновляется каждые 30 секунд.
 * Показывает индикатор загрузки и обработку ошибок.
 */
export const SystemHealthLive: React.FC = () => {
  const { t } = useTranslation();
  const { 
    metrics, 
    isLoading, 
    isError, 
    error,
    cpuStatus,
    ramStatus,
    diskStatus,
    overallStatus,
    refetch,
    isFetching,
  } = useSystemMetrics();

  // Состояние ошибки
  if (isError) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-cyan-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('dashboard.health.title', 'Здоровье системы')}
          </h3>
        </div>
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400">
              <XCircle className="w-5 h-5" />
              <span className="text-sm font-medium">
                {t('dashboard.health.unavailable', 'Данные временно недоступны')}
              </span>
            </div>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-2 rounded-lg hover:bg-rose-500/10 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 text-rose-500 ${isFetching ? 'animate-spin' : ''}`} />
            </button>
          </div>
          <p className="mt-2 text-xs text-[color:var(--color-text-muted)]">
            {error instanceof Error ? error.message : t('dashboard.health.tryAgain', 'Попробуйте обновить страницу')}
          </p>
        </div>
      </div>
    );
  }

  // Состояние загрузки
  if (isLoading || !metrics) {
    return (
      <SystemHealth
        cpuUsage={0}
        memoryUsage={0}
        diskUsage={0}
        networkLatency={0}
        dbConnections={0}
        maxDbConnections={100}
        loading={true}
      />
    );
  }

  // Нормальное состояние с данными
  // Примечание: networkLatency не доступен через psutil, используем 0
  const attentionMetric = [
    { label: t('dashboard.health.cpu', 'CPU'), status: cpuStatus, value: metrics.cpu_percent, unit: '%' },
    { label: t('dashboard.health.ram', 'RAM'), status: ramStatus, value: metrics.ram_percent, unit: '%' },
    { label: t('dashboard.health.disk', 'Диск'), status: diskStatus, value: metrics.disk_percent, unit: '%' },
  ].find(m => m.status !== 'healthy');

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Server className="w-5 h-5 text-cyan-500" />
          <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
            {t('dashboard.health.title', 'Здоровье системы')}
          </h3>
        </div>
        <div className="flex items-center gap-2">
          {/* Uptime badge */}
          <span className="text-xs text-[color:var(--color-text-muted)]">
            {t('dashboard.health.uptime', 'Uptime')}: {formatUptime(metrics.uptime_seconds)}
          </span>
          {/* Overall status badge */}
          <div className={`
            flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border
            ${overallStatus === 'healthy' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200/60 dark:border-emerald-500/40' :
              overallStatus === 'warning' ? 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-200/80 dark:border-amber-500/40' :
              'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-200/80 dark:border-rose-500/40'}
          `}>
            {overallStatus === 'healthy' && <CheckCircle className="w-3.5 h-3.5" />}
            {overallStatus === 'warning' && <AlertTriangle className="w-3.5 h-3.5" />}
            {overallStatus === 'critical' && <XCircle className="w-3.5 h-3.5" />}
            {overallStatus === 'healthy' ? t('dashboard.health.allSystemsGo', 'Всё в норме') :
             overallStatus === 'warning' ? t('dashboard.health.needsAttention', 'Требует внимания') :
             t('dashboard.health.critical', 'Критично')}
          </div>
        </div>
      </div>
      {attentionMetric && (
        <p className="text-xs text-amber-700 dark:text-amber-300 leading-snug">
          {attentionMetric.label}: {attentionMetric.value}{attentionMetric.unit} — {t('dashboard.health.needsAttention', 'Требует внимания')}
        </p>
      )}
      
      <div className="p-4 rounded-xl bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricCard
            icon={Cpu}
            label={t('dashboard.health.cpu', 'CPU')}
            value={metrics.cpu_percent}
            unit="%"
            status={cpuStatus}
            index={0}
          />
          <MetricCard
            icon={HardDrive}
            label={t('dashboard.health.ram', 'RAM')}
            value={metrics.ram_percent}
            unit="%"
            status={ramStatus}
            index={1}
          />
          <MetricCard
            icon={Database}
            label={t('dashboard.health.disk', 'Диск')}
            value={metrics.disk_percent}
            unit="%"
            status={diskStatus}
            index={2}
          />
          <MetricCard
            icon={Activity}
            label={t('dashboard.health.uptime', 'Uptime')}
            value={Math.floor(metrics.uptime_seconds / 3600)}
            unit="h"
            status="healthy"
            showProgress={false}
            index={3}
          />
        </div>
        
        {/* Database connections */}
        <div className="mt-4 pt-4 border-t border-[color:var(--color-border)]">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-[color:var(--color-text-muted)]" />
              <span className="text-[color:var(--color-text-muted)]">
                {t('dashboard.health.dbConnections', 'DB Connections')}
              </span>
            </div>
            <span className="font-medium text-[color:var(--color-text)]">
              {metrics.db_connections_active} {t('dashboard.health.active', 'активных')} / {metrics.db_connections_idle} {t('dashboard.health.idle', 'idle')}
            </span>
          </div>
          <Progress
            size="sm"
            value={metrics.db_connections_active}
            maxValue={Math.max(metrics.db_connections_active + metrics.db_connections_idle, 10)}
            color={getStatusColor(getStatusFromValue((metrics.db_connections_active / 10) * 100, 70, 90)) as any}
            className="mt-2"
          />
        </div>
      </div>
    </div>
  );
};
