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
  XCircle
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Progress } from '@heroui/react';

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
          flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium
          ${overallHealth === 'healthy' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' :
            overallHealth === 'warning' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' :
            'bg-rose-500/10 text-rose-600 dark:text-rose-400'}
        `}>
          <OverallIcon className="w-3.5 h-3.5" />
          {overallHealth === 'healthy' ? t('admin.allSystemsGo', 'Всё в норме') :
           overallHealth === 'warning' ? t('admin.needsAttention', 'Требует внимания') :
           t('admin.critical', 'Критично')}
        </div>
      </div>
      
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
