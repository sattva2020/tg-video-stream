/**
 * ComplianceStatus Component
 * Feature: 025-advanced-security-compliance-features
 *
 * Badge component for displaying compliance status (SOC 2, GDPR, etc.)
 * with visual indicators and detailed status information.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { Shield, CheckCircle, XCircle, AlertTriangle, Clock, LucideIcon } from 'lucide-react';

export type ComplianceStatusType = 'compliant' | 'non_compliant' | 'pending_review' | 'unknown';
export type ComplianceFramework = 'SOC 2' | 'GDPR' | 'ISO 27001' | 'HIPAA' | 'PCI DSS';

interface ComplianceStatusProps {
  framework: ComplianceFramework;
  status: ComplianceStatusType;
  description?: string;
  lastUpdated?: string;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  className?: string;
}

const statusConfig = {
  compliant: {
    gradient: 'from-emerald-500 to-green-600',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-600 dark:text-emerald-400',
    border: 'border-emerald-500/20',
    glow: 'shadow-emerald-500/25',
    icon: CheckCircle,
    label: 'Compliant',
    description: 'All requirements met',
  },
  non_compliant: {
    gradient: 'from-rose-500 to-red-600',
    bg: 'bg-rose-500/10',
    text: 'text-rose-600 dark:text-rose-400',
    border: 'border-rose-500/20',
    glow: 'shadow-rose-500/25',
    icon: XCircle,
    label: 'Non-Compliant',
    description: 'Action required',
  },
  pending_review: {
    gradient: 'from-amber-500 to-orange-600',
    bg: 'bg-amber-500/10',
    text: 'text-amber-600 dark:text-amber-400',
    border: 'border-amber-500/20',
    glow: 'shadow-amber-500/25',
    icon: AlertTriangle,
    label: 'Pending Review',
    description: 'Under review',
  },
  unknown: {
    gradient: 'from-gray-500 to-slate-600',
    bg: 'bg-gray-500/10',
    text: 'text-gray-600 dark:text-gray-400',
    border: 'border-gray-500/20',
    glow: 'shadow-gray-500/25',
    icon: Clock,
    label: 'Unknown',
    description: 'Status unavailable',
  },
};

const sizeConfig = {
  sm: {
    padding: 'p-3',
    iconSize: 'w-4 h-4',
    textSize: 'text-sm',
    titleSize: 'text-xs',
  },
  md: {
    padding: 'p-4',
    iconSize: 'w-5 h-5',
    textSize: 'text-base',
    titleSize: 'text-sm',
  },
  lg: {
    padding: 'p-6',
    iconSize: 'w-6 h-6',
    textSize: 'text-xl',
    titleSize: 'text-base',
  },
};

export const ComplianceStatus: React.FC<ComplianceStatusProps> = ({
  framework,
  status,
  description,
  lastUpdated,
  showIcon = true,
  size = 'md',
  loading = false,
  className = '',
}) => {
  const config = statusConfig[status];
  const sizeStyle = sizeConfig[size];
  const StatusIcon = config.icon;

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`
          relative overflow-hidden rounded-xl ${sizeStyle.padding}
          bg-[color:var(--color-panel)]
          border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]
          shadow-md shadow-black/5
          ${className}
        `}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg bg-[color:var(--color-border)] animate-pulse ${sizeStyle.iconSize}`} />
          <div className="flex-1">
            <div className="h-4 bg-[color:var(--color-border)] rounded animate-pulse w-24 mb-2" />
            <div className="h-3 bg-[color:var(--color-border)] rounded animate-pulse w-16" />
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        relative overflow-hidden rounded-xl ${sizeStyle.padding}
        bg-[color:var(--color-panel)]
        border border-[color:var(--color-border)] ring-1 ring-inset ring-[color:var(--color-border)]
        shadow-md shadow-black/5
        transition-all hover:shadow-lg hover:${config.glow}
        ${className}
      `}
    >
      {/* Gradient Background */}
      <div className={`absolute inset-0 bg-gradient-to-br ${config.gradient} opacity-5`} />

      {/* Content */}
      <div className="relative z-10">
        <div className="flex items-start gap-3">
          {/* Icon */}
          {showIcon && (
            <div className={`p-2 rounded-lg ${config.bg} flex-shrink-0`}>
              <Shield className={`${sizeStyle.iconSize} ${config.text}`} />
            </div>
          )}

          {/* Status Information */}
          <div className="flex-1 min-w-0">
            {/* Framework and Status */}
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h3 className={`font-semibold ${sizeStyle.titleSize} text-[color:var(--color-text)]`}>
                {framework}
              </h3>
              <div className={`flex items-center gap-1 ${config.text}`}>
                <StatusIcon className={sizeStyle.iconSize} />
                <span className={`font-medium ${sizeStyle.textSize}`}>
                  {config.label}
                </span>
              </div>
            </div>

            {/* Description */}
            {(description || config.description) && (
              <p className="text-xs text-[color:var(--color-text-muted)] mb-1">
                {description || config.description}
              </p>
            )}

            {/* Last Updated */}
            {lastUpdated && (
              <p className="text-xs text-[color:var(--color-text-muted)]">
                Updated: {new Date(lastUpdated).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

interface ComplianceBadgeProps {
  status: ComplianceStatusType;
  size?: 'sm' | 'md';
  showText?: boolean;
  className?: string;
}

/**
 * Compact badge version for inline usage
 */
export const ComplianceBadge: React.FC<ComplianceBadgeProps> = ({
  status,
  size = 'sm',
  showText = true,
  className = '',
}) => {
  const config = statusConfig[status];
  const StatusIcon = config.icon;

  const sizeStyles = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1.5 text-sm',
  };

  return (
    <span
      className={`
        inline-flex items-center gap-1.5 rounded-full font-medium
        ${config.bg} ${config.text}
        ${sizeStyles[size]}
        ${className}
      `}
    >
      <StatusIcon className="w-3 h-3" />
      {showText && <span>{config.label}</span>}
    </span>
  );
};

interface ComplianceStatusGridProps {
  frameworks: Array<{
    framework: ComplianceFramework;
    status: ComplianceStatusType;
    description?: string;
    lastUpdated?: string;
  }>;
  loading?: boolean;
  className?: string;
}

/**
 * Grid layout for multiple compliance statuses
 */
export const ComplianceStatusGrid: React.FC<ComplianceStatusGridProps> = ({
  frameworks,
  loading = false,
  className = '',
}) => {
  return (
    <div className={`grid gap-4 md:grid-cols-2 ${className}`}>
      {frameworks.map((item, index) => (
        <motion.div
          key={item.framework}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
        >
          <ComplianceStatus
            framework={item.framework}
            status={item.status}
            description={item.description}
            lastUpdated={item.lastUpdated}
            loading={loading}
          />
        </motion.div>
      ))}
    </div>
  );
};

export default ComplianceStatus;
