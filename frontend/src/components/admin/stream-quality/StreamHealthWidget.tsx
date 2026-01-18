import React from 'react';
import { Activity, Wifi, WifiOff, AlertTriangle, CheckCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/Skeleton';

interface StreamHealthWidgetProps {
  isLoading: boolean;
  isOnline: boolean;
  bitrate?: number;
  fps?: number;
  qualityScore?: 'low' | 'medium' | 'high' | 'lossless' | 'ultra';
  lastCheck?: string;
  error?: string;
}

export const StreamHealthWidget: React.FC<StreamHealthWidgetProps> = ({
  isLoading,
  isOnline,
  bitrate,
  fps,
  qualityScore,
  lastCheck,
  error
}) => {
  if (isLoading) {
    return <Skeleton className="h-[200px] w-full" />;
  }

  if (error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-red-800">
            Stream Status
          </CardTitle>
          <AlertTriangle className="h-4 w-4 text-red-600" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-red-600">Error</div>
          <p className="text-xs text-red-500 mt-1">{error}</p>
        </CardContent>
      </Card>
    );
  }

  const getQualityColor = (score?: string) => {
    switch (score) {
      case 'ultra':
      case 'lossless':
      case 'high':
        return 'text-green-600';
      case 'medium':
        return 'text-yellow-600';
      case 'low':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Status</CardTitle>
          {isOnline ? (
            <Wifi className="h-4 w-4 text-green-600" />
          ) : (
            <WifiOff className="h-4 w-4 text-red-600" />
          )}
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold ${isOnline ? 'text-green-600' : 'text-red-600'}`}>
            {isOnline ? 'Online' : 'Offline'}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Last check: {lastCheck ? new Date(lastCheck).toLocaleTimeString() : 'Never'}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Bitrate</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {bitrate ? `${Math.round(bitrate)} kbps` : 'N/A'}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Audio + Video
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">FPS</CardTitle>
          <Activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {fps ? fps.toFixed(1) : 'N/A'}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Frames per second
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Quality Score</CardTitle>
          <CheckCircle className={`h-4 w-4 ${getQualityColor(qualityScore)}`} />
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold capitalize ${getQualityColor(qualityScore)}`}>
            {qualityScore || 'Unknown'}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Overall rating
          </p>
        </CardContent>
      </Card>
    </div>
  );
};
