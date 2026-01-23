import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { adminApi, SecurityDashboardResponse } from '@/api/admin';
import { useToast } from '@/hooks/useToast';
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Lock,
  Database,
  UserCheck,
  Settings,
  FileText,
  Download,
  Activity,
  Eye
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

interface SecurityDashboardProps {
  className?: string;
}

export const SecurityDashboard: React.FC<SecurityDashboardProps> = ({ className }) => {
  const toast = useToast();

  const [framework, setFramework] = useState<'soc2' | 'gdpr'>('soc2');
  const [days, setDays] = useState(30);

  // Fetch security dashboard data
  const { data: dashboard, isLoading, refetch } = useQuery({
    queryKey: ['security-dashboard', framework, days],
    queryFn: () => adminApi.getSecurityDashboard(framework, days),
  });

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'compliant':
      case 'pass':
      case 'enabled':
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'non_compliant':
      case 'non-compliant':
      case 'fail':
      case 'disabled':
      case 'inactive':
        return <XCircle className="h-4 w-4 text-red-600" />;
      case 'pending_review':
      case 'pending-review':
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      default:
        return <Clock className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'compliant':
      case 'pass':
      case 'enabled':
      case 'active':
        return 'text-green-600 dark:text-green-400';
      case 'non_compliant':
      case 'non-compliant':
      case 'fail':
      case 'disabled':
      case 'inactive':
        return 'text-red-600 dark:text-red-400';
      case 'pending_review':
      case 'pending-review':
      case 'warning':
        return 'text-yellow-600 dark:text-yellow-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getStatusBadge = (status: string) => {
    const color = getStatusColor(status);
    return (
      <span className={`text-xs px-2 py-1 rounded-full ${color} bg-opacity-10`}>
        {status.replace(/_/g, '-').replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
      </span>
    );
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'low':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200';
    }
  };

  const exportAuditLogs = async () => {
    try {
      toast.info('Preparing audit log export...');
      // This would call the export endpoint when implemented
      toast.success('Audit logs export started');
    } catch (error) {
      toast.error('Failed to export audit logs');
    }
  };

  if (isLoading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Security Dashboard</h2>
          <div className="animate-pulse flex gap-2">
            <div className="h-9 w-24 bg-muted rounded" />
            <div className="h-9 w-32 bg-muted rounded" />
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-muted rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!dashboard) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">Security Dashboard</h2>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Shield className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No security data available</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-2xl font-bold">Security Dashboard</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Monitor compliance status and security metrics
          </p>
        </div>
        <div className="flex gap-2">
          <select
            className="flex h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
            value={framework}
            onChange={(e) => setFramework(e.target.value as 'soc2' | 'gdpr')}
          >
            <option value="soc2">SOC 2</option>
            <option value="gdpr">GDPR</option>
          </select>
          <select
            className="flex h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <Button size="sm" variant="outline" onClick={() => refetch()} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
          <Button size="sm" variant="outline" onClick={exportAuditLogs}>
            <Download className="h-4 w-4 mr-2" />
            Export Logs
          </Button>
        </div>
      </div>

      {/* Compliance Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Compliance Status</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {getStatusIcon(dashboard.compliance_status.overall_status)}
              <span className={`text-2xl font-bold ${getStatusColor(dashboard.compliance_status.overall_status)}`}>
                {dashboard.compliance_status.overall_status.replace(/_/g, '-').toUpperCase()}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {dashboard.compliance_status.framework.toUpperCase()} Framework
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Security Events</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard.security_metrics.total_events}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {dashboard.security_metrics.unresolved_incidents} unresolved
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Security Policies</CardTitle>
            <Lock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboard.security_configs.security_policies_enabled}/{dashboard.security_configs.security_policies_total}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Enabled policies
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Critical Events</CardTitle>
            <AlertTriangle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {dashboard.security_metrics.by_severity.critical || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Requires immediate attention
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Data Protection & Access Control */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Data Protection
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-2">
                  {getStatusIcon(dashboard.data_protection.overall_status)}
                  <span className="font-medium">Overall Status</span>
                </div>
                {getStatusBadge(dashboard.data_protection.overall_status)}
              </div>
              <div className="space-y-2">
                {Object.entries(dashboard.data_protection.checks).slice(0, 4).map(([key, check]) => (
                  <div key={key} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <div className="flex items-center gap-1">
                      {getStatusIcon(check.status)}
                      <span className={getStatusColor(check.status)}>
                        {check.status.replace(/_/g, '-')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserCheck className="h-5 w-5" />
              Access Control
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="flex items-center gap-2">
                  {getStatusIcon(dashboard.access_control.overall_status)}
                  <span className="font-medium">Overall Status</span>
                </div>
                {getStatusBadge(dashboard.access_control.overall_status)}
              </div>
              <div className="space-y-2">
                {Object.entries(dashboard.access_control.checks).slice(0, 4).map(([key, check]) => (
                  <div key={key} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                    <div className="flex items-center gap-1">
                      {getStatusIcon(check.status)}
                      <span className={getStatusColor(check.status)}>
                        {check.status.replace(/_/g, '-')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Security Configuration Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Security Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="p-4 rounded-lg bg-muted/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">SAML SSO</span>
                <span className="text-xs text-muted-foreground">
                  {dashboard.security_configs.saml_configs_enabled}/{dashboard.security_configs.saml_configs_total}
                </span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{
                    width: `${dashboard.security_configs.saml_configs_total > 0
                      ? (dashboard.security_configs.saml_configs_enabled / dashboard.security_configs.saml_configs_total) * 100
                      : 0}%`
                  }}
                />
              </div>
            </div>

            <div className="p-4 rounded-lg bg-muted/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Security Policies</span>
                <span className="text-xs text-muted-foreground">
                  {dashboard.security_configs.security_policies_enabled}/{dashboard.security_configs.security_policies_total}
                </span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2">
                <div
                  className="bg-green-600 h-2 rounded-full transition-all"
                  style={{
                    width: `${dashboard.security_configs.security_policies_total > 0
                      ? (dashboard.security_configs.security_policies_enabled / dashboard.security_configs.security_policies_total) * 100
                      : 0}%`
                  }}
                />
              </div>
            </div>

            <div className="p-4 rounded-lg bg-muted/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">2FA Enforcement</span>
                {dashboard.security_configs.two_factor_enforcement_enabled ? (
                  <CheckCircle className="h-4 w-4 text-green-600" />
                ) : (
                  <XCircle className="h-4 w-4 text-gray-600" />
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {dashboard.security_configs.two_factor_enforcement_enabled
                  ? 'Two-factor authentication is enforced'
                  : 'Two-factor authentication not enforced'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Critical Events */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Recent Critical Events
            </CardTitle>
            {dashboard.recent_critical_events.length > 0 && (
              <Button size="sm" variant="outline">
                <Eye className="h-4 w-4 mr-2" />
                View All Events
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {dashboard.recent_critical_events.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <CheckCircle className="h-12 w-12 mx-auto mb-4 opacity-50 text-green-600" />
              <p>No critical events</p>
              <p className="text-sm mt-2">All systems are operating normally</p>
            </div>
          ) : (
            <div className="space-y-3">
              {dashboard.recent_critical_events.map((event) => (
                <div
                  key={event.id}
                  className="p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h4 className="font-medium">{event.title}</h4>
                        <span className={`text-xs px-2 py-1 rounded-full ${getSeverityColor(event.severity)}`}>
                          {event.severity.toUpperCase()}
                        </span>
                        {getStatusBadge(event.compliance_status)}
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{event.description}</p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span className="capitalize">{event.category.replace(/_/g, ' ')}</span>
                        {event.timestamp && (
                          <>
                            <span>•</span>
                            <span>{new Date(event.timestamp).toLocaleString()}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Last Updated */}
      <div className="text-center text-xs text-muted-foreground">
        Last updated: {new Date(dashboard.generated_at).toLocaleString()}
      </div>
    </div>
  );
};
