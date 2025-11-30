import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardBody, CardHeader, Chip } from '@heroui/react';
import { Link } from 'react-router-dom';
import { Tv, Radio, Music, Clock } from 'lucide-react';
import { usePlaylistWebSocket } from '../../hooks/usePlaylistWebSocket';
import { Skeleton } from '../ui/Skeleton';

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
          Статус трансляции
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
              {isOnline ? 'В эфире' : 'Офлайн'}
            </Chip>
          </div>
          
          {currentTrack && (
            <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800">
              <div className="flex items-center gap-2 text-xs text-blue-600 dark:text-blue-400 mb-1">
                <Music className="w-3 h-3" />
                Сейчас играет
              </div>
              <p className="font-medium text-blue-800 dark:text-blue-200 truncate">
                {currentTrack}
              </p>
            </div>
          )}
          
          <div className="flex items-center gap-2 text-sm text-default-500">
            <Clock className="w-4 h-4" />
            <span>В очереди: {items.length} треков</span>
          </div>
        </div>
      </CardBody>
    </Card>
  );
};

export const UserDashboard: React.FC = () => {
  const { user, isLoading: authLoading } = useAuth();

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
          <h2 className="text-xl font-semibold">Добро пожаловать, {user?.full_name || user?.email}!</h2>
          <p className="text-default-500 mt-1">
            Вы вошли как обычный пользователь.
          </p>
        </CardHeader>
        <CardBody className="px-6 pb-6">
          {/* Additional welcome content could go here */}
        </CardBody>
      </Card>
      
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader className="px-6 pt-6 pb-0">
            <h3 className="text-lg font-medium">Мой профиль</h3>
          </CardHeader>
          <CardBody className="px-6 pb-6">
            <div className="space-y-4 text-sm">
              <div className="flex justify-between items-center border-b border-default-100 pb-2">
                <span className="text-default-500">Email</span>
                <span className="font-medium">{user?.email}</span>
              </div>
              <div className="flex justify-between items-center pt-2">
                <span className="text-default-500">Статус</span>
                <Chip color="success" variant="flat" size="sm">
                  Активен
                </Chip>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Stream Status for Users */}
        <StreamStatusBadge />
      </div>
      
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader className="px-6 pt-6 pb-0">
            <h3 className="text-lg font-medium">Быстрые действия</h3>
          </CardHeader>
          <CardBody className="px-6 pb-6">
            <div className="space-y-4">
              <Link 
                to="/channels" 
                className="flex items-center gap-3 p-3 rounded-lg bg-blue-50 dark:bg-blue-950 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900 transition-colors"
              >
                <Tv className="w-5 h-5" />
                <div className="flex flex-col">
                  <span className="font-medium">Менеджер каналов</span>
                  <span className="text-xs opacity-80">Управление Telegram-трансляциями</span>
                </div>
              </Link>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
};
