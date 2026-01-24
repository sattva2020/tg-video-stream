import React, { useState, useEffect } from 'react';
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Settings,
  Clock,
  Shield,
  ShieldOff
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { telegramApi, TelegramSession } from '@/api/telegram';
import { useToast } from '@/components/ui/use-toast';

interface SessionHealthListProps {
  refreshTrigger?: number;
  onConfigureClick?: (sessionId: string, sessionPhone?: string) => void;
}

export const SessionHealthList: React.FC<SessionHealthListProps> = ({
  refreshTrigger,
  onConfigureClick
}) => {
  const { toast } = useToast();
  const [sessions, setSessions] = useState<TelegramSession[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshingSessions, setRefreshingSessions] = useState<Set<string>>(new Set());

  const fetchSessions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await telegramApi.listSessions();
      setSessions(data);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch sessions';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, [refreshTrigger]);

  const handleRefresh = async (accountId: string) => {
    setRefreshingSessions(prev => new Set(prev).add(accountId));
    try {
      const result = await telegramApi.refreshSession(accountId);
      toast({
        title: 'Success',
        description: result.message || 'Session refreshed successfully',
      });
      // Refresh the list to get updated data
      await fetchSessions();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to refresh session';
      toast({
        title: 'Refresh Failed',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setRefreshingSessions(prev => {
        const newSet = new Set(prev);
        newSet.delete(accountId);
        return newSet;
      });
    }
  };

  const getHealthStatusBadge = (session: TelegramSession) => {
    const status = session.health_status || session.session_health_status || 'unknown';

    if (status === 'healthy' || status === 'HEALTHY') {
      return (
        <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
          <CheckCircle className="h-3 w-3 mr-1" />
          Healthy
        </Badge>
      );
    }

    if (status === 'expiring' || status === 'EXPIRING' || status === 'expiring_soon') {
      return (
        <Badge variant="default" className="bg-yellow-100 text-yellow-800 border-yellow-200">
          <AlertTriangle className="h-3 w-3 mr-1" />
          Expiring Soon
        </Badge>
      );
    }

    if (status === 'expired' || status === 'EXPIRED') {
      return (
        <Badge variant="destructive" className="bg-red-100 text-red-800 border-red-200">
          <XCircle className="h-3 w-3 mr-1" />
          Expired
        </Badge>
      );
    }

    if (status === 'needs_2fa' || status === 'NEEDS_2FA') {
      return (
        <Badge variant="destructive" className="bg-orange-100 text-orange-800 border-orange-200">
          <ShieldOff className="h-3 w-3 mr-1" />
          Needs 2FA
        </Badge>
      );
    }

    return (
      <Badge variant="secondary" className="bg-gray-100 text-gray-800 border-gray-200">
        {status}
      </Badge>
    );
  };

  const getTimeUntilExpiry = (expiresAt?: string): string => {
    if (!expiresAt) return 'Unknown';

    const now = new Date();
    const expiry = new Date(expiresAt);
    const diffMs = expiry.getTime() - now.getTime();

    if (diffMs < 0) return 'Expired';

    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (diffDays > 0) {
      return `${diffDays}d ${diffHours}h`;
    }
    if (diffHours > 0) {
      return `${diffHours}h ${diffMins}m`;
    }
    return `${diffMins}m`;
  };

  const getLastHealthCheck = (lastCheck?: string): string => {
    if (!lastCheck) return 'Never';

    const now = new Date();
    const check = new Date(lastCheck);
    const diffMs = now.getTime() - check.getTime();

    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Session Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-red-800">
            Session Health
          </CardTitle>
          <AlertTriangle className="h-4 w-4 text-red-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-red-600">Error</div>
          <p className="text-xs text-red-500 mt-1">{error}</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={fetchSessions}
          >
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (sessions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Session Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No Telegram sessions found</p>
            <p className="text-sm mt-2">Add a Telegram account to get started</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Session Health</CardTitle>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchSessions}
          disabled={isLoading}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {sessions.map(session => (
            <div
              key={session.id}
              className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
            >
              <div className="flex-1 space-y-2">
                <div className="flex items-center gap-3">
                  <div className="font-semibold">
                    {session.username || session.phone || session.first_name || 'Unknown'}
                  </div>
                  {getHealthStatusBadge(session)}
                  {session.auto_refresh_enabled && (
                    <Badge variant="outline" className="text-xs">
                      <RefreshCw className="h-3 w-3 mr-1" />
                      Auto-refresh
                    </Badge>
                  )}
                </div>

                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>Expires: {getTimeUntilExpiry(session.session_expires_at)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3" />
                    <span>Last check: {getLastHealthCheck(session.last_health_check)}</span>
                  </div>
                  {session.consecutive_failures !== undefined && session.consecutive_failures > 0 && (
                    <div className="flex items-center gap-1 text-red-600">
                      <AlertTriangle className="h-3 w-3" />
                      <span>{session.consecutive_failures} failures</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleRefresh(session.id)}
                  disabled={refreshingSessions.has(session.id)}
                >
                  <RefreshCw className={`h-4 w-4 mr-2 ${refreshingSessions.has(session.id) ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onConfigureClick?.(session.id, session.phone)}
                >
                  <Settings className="h-4 w-4 mr-2" />
                  Configure
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
