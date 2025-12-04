import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardBody, CardHeader, Chip } from '@heroui/react';
import { Link } from 'react-router-dom';
import { Tv, Radio, Music, Clock, Settings, HelpCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { usePlaylistWebSocket } from '../../hooks/usePlaylistWebSocket';
import { Skeleton } from '../ui/Skeleton';
import { WelcomeCardContent } from './WelcomeCardContent';

type QuickAction = {
  id: string;
  title: string;
  description: string;
  icon: typeof Tv;
  to?: string;
  externalHref?: string;
  color: string;
};

// Skeleton for profile card
const SkeletonProfileCard: React.FC = () => (
  <Card>
    <CardHeader className="px-6 pt-6 pb-0">
      <Skeleton className="h-5 w-24" />
    </CardHeader>
    <CardBody className="px-6 pb-6">
      <div className="space-y-4">
        <div className="flex justify-between items-center border-b border-default-100 pb-2">
          <Skeleton className="h-4 w-10" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="flex justify-between items-center pt-2">
          <Skeleton className="h-4 w-12" />
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
      </div>
    </CardBody>
  </Card>
);

// Skeleton for stream status
const SkeletonStreamStatus: React.FC = () => (
  <Card>
    <CardHeader className="px-6 pt-6 pb-0">
      <div className="flex items-center gap-2">
        <Skeleton className="w-5 h-5 rounded-full" />
        <Skeleton className="h-5 w-36" />
      </div>
    </CardHeader>
    <CardBody className="px-6 pb-6">
      <div className="space-y-4">
        <Skeleton className="h-8 w-24 rounded-full" />
        <div className="p-3 rounded-lg bg-default-50 border border-default-200">
          <Skeleton className="h-3 w-24 mb-2" />
          <Skeleton className="h-5 w-48" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="w-4 h-4 rounded-full" />
          <Skeleton className="h-4 w-28" />
        </div>
      </div>
    </CardBody>
  </Card>
);

// Simple stream status for regular users
const StreamStatusBadge: React.FC = () => {
  const { streamStatus, items, isConnected } = usePlaylistWebSocket({ enabled: true });
  const [currentTrack, setCurrentTrack] = useState<string | null>(null);
  const { t } = useTranslation();
  
  useEffect(() => {
    const playing = items.find(item => item.status === 'playing');
    setCurrentTrack(playing?.title || null);
  }, [items]);

  const isOnline = streamStatus === 'running' || streamStatus === 'online' || isConnected;
  
  return (
    <Card>
      <CardHeader className="px-6 pt-6 pb-0">
        <h3 className="text-lg font-medium flex items-center gap-2">
          <Radio className={`w-5 h-5 ${isOnline ? 'text-green-500 animate-pulse' : 'text-gray-400'}`} />
          {t('user.dashboard.streamStatusTitle')}
        </h3>
      </CardHeader>
      <CardBody className="px-6 pb-6">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Chip 
              color={isOnline ? 'success' : 'default'} 
              variant="flat" 
              size="lg"
              startContent={
                <span 
                  className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} 
                />
              }
            >
              {isOnline ? t('operator.status.online') : t('operator.status.offline')}
            </Chip>
          </div>
          
          {currentTrack && (
            <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800">
              <div className="flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400 mb-1">
                <Music className="w-3 h-3" />
                {t('user.dashboard.currentTrack')}
              </div>
              <p className="font-medium text-blue-800 dark:text-blue-200 truncate">
                {currentTrack}
              </p>
            </div>
          )}
          
          <div className="flex items-center gap-2 text-sm text-default-500">
            <Clock className="w-4 h-4" />
            <span>{t('user.dashboard.queueCount', { count: items.length })}</span>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

export const UserDashboard: React.FC = () => {
  const { user, isLoading: authLoading } = useAuth();
  const { t } = useTranslation();

  const quickActions: QuickAction[] = useMemo(() => [
    {
      id: 'channels',
      title: t('user.dashboard.quickActions.channels'),
      description: t('user.dashboard.quickActions.channelsDesc'),
      to: '/channels',
      icon: Tv,
      color: 'from-blue-500/20 via-blue-500/5 to-blue-500/0 text-blue-700 dark:text-blue-300',
    },
    {
      id: 'settings',
      title: t('user.dashboard.quickActions.settings'),
      description: t('user.dashboard.quickActions.settingsDesc'),
      to: '/settings',
      icon: Settings,
      color: 'from-amber-500/20 via-amber-500/5 to-amber-500/0 text-amber-700 dark:text-amber-300',
    },
    {
      id: 'support',
      title: t('user.dashboard.quickActions.support'),
      description: t('user.dashboard.quickActions.supportDesc'),
      externalHref: '/docs/help',
      icon: HelpCircle,
      color: 'from-violet-500/20 via-violet-500/5 to-violet-500/0 text-violet-700 dark:text-violet-300',
    },
  ], [t]);

  if (authLoading) {
    return (
      <div className="space-y-6 p-4">
        {/* Welcome skeleton */}
        <Card>
          <CardHeader className="flex flex-col items-start px-6 pt-6 pb-0">
            <Skeleton className="h-6 w-64 mb-2" />
            <Skeleton className="h-4 w-48" />
          </CardHeader>
          <CardBody className="px-6 pb-6" />
        </Card>
        
        <div className="grid gap-6 md:grid-cols-2">
          <SkeletonProfileCard />
          <SkeletonStreamStatus />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4">
      <Card>
        <CardHeader className="flex flex-col items-start px-6 pt-6 pb-0">
          <h2 className="text-xl font-semibold">
            {t('user.dashboard.welcomeTitle', { name: user?.full_name || user?.email })}
          </h2>
          <p className="text-default-500 mt-1">{t('user.dashboard.welcomeSubtitle')}</p>
        </CardHeader>
        <CardBody className="px-6 pb-6">
          <WelcomeCardContent user={user || null} />
        </CardBody>
      </Card>
      
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader className="px-6 pt-6 pb-0">
            <h3 className="text-lg font-medium">{t('user.dashboard.profileTitle')}</h3>
          </CardHeader>
          <CardBody className="px-6 pb-6">
            <div className="space-y-4 text-sm">
              <div className="flex justify-between items-center border-b border-default-100 pb-2">
                <span className="text-default-500">{t('user.dashboard.emailLabel')}</span>
                <span className="font-medium">{user?.email}</span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-default-500">{t('user.dashboard.statusLabel')}</span>
                <Chip color="success" variant="flat" size="sm">
                  {t('user.status.active')}
                </Chip>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Stream Status for Users */}
        <StreamStatusBadge />
      </div>
      
      <div className="space-y-6">
        <Card>
          <CardHeader className="px-6 pt-6 pb-0">
            <h3 className="text-lg font-medium">{t('user.dashboard.quickActionsTitle')}</h3>
          </CardHeader>
          <CardBody className="px-6 pb-6">
            <div className="grid gap-4 md:grid-cols-3">
              {quickActions.map(action => {
                const Icon = action.icon;
                const baseClasses = 'flex flex-col gap-3 rounded-xl border border-[color:var(--color-border)] p-4 shadow-sm transition-colors';
                const content = (
                  <>
                    <div className={`inline-flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-r ${action.color}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="font-semibold text-[color:var(--color-text)]">{action.title}</p>
                      <p className="text-xs text-[color:var(--color-text-muted)]">{action.description}</p>
                    </div>
                  </>
                );

                if (action.externalHref) {
                  return (
                    <a
                      key={action.id}
                      href={action.externalHref}
                      target="_blank"
                      rel="noreferrer"
                      className={`${baseClasses} hover:bg-[color:var(--color-panel)]`}
                    >
                      {content}
                    </a>
                  );
                }

                return (
                  <Link
                    key={action.id}
                    to={action.to ?? '#'}
                    className={`${baseClasses} hover:bg-[color:var(--color-panel)]`}
                  >
                    {content}
                  </Link>
                );
              })}
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
};
