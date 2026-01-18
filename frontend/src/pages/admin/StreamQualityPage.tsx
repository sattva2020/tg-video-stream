import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { StreamHealthWidget } from '@/components/admin/stream-quality/StreamHealthWidget';
import { StreamQualityHistoryChart } from '@/components/admin/stream-quality/StreamQualityHistoryChart';
import { useToast } from '@/components/ui/use-toast';
import { api } from '@/lib/api';
import { AppLayout } from '@/components/layout';

// Types matching backend response
interface StreamQualityData {
  url: string;
  audio?: {
    codec?: string;
    bitrate_kbps?: number;
    quality?: string;
  };
  video?: {
    codec?: string;
    bitrate_kbps?: number;
    fps?: number;
    quality?: string;
  };
  performance?: {
    dropped_frames?: number;
    speed?: number;
    fps?: number;
    bitrate_kbps?: number;
  };
  is_audio_only: boolean;
  is_video_only: boolean;
}

interface QualityHistoryPoint {
  timestamp: string;
  bitrate_kbps: number;
  fps: number;
  quality_score: number;
}

export const StreamQualityPage: React.FC = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const [period, setPeriod] = useState('24h');
  const [isLoading, setIsLoading] = useState(true);
  const [currentQuality, setCurrentQuality] = useState<StreamQualityData | null>(null);
  const [historyData, setHistoryData] = useState<QualityHistoryPoint[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      // Fetch current status
      // Note: In a real app, we might need to pass the stream URL or ID
      // For now, the backend tries to find the active stream
      const currentResponse = await api.get('/admin/stream-quality/current');
      setCurrentQuality(currentResponse.data);

      // Fetch history
      // We need a URL for history. If currentResponse has it, use it.
      // Otherwise, we might need a way to select a stream.
      if (currentResponse.data?.url) {
        const historyResponse = await api.get('/admin/stream-quality/history', {
          params: { 
            url: currentResponse.data.url,
            period 
          }
        });
        
        // Transform backend data to chart format
        // Assuming backend returns { points: [...] } or similar
        // Adjust based on actual backend response structure
        if (historyResponse.data?.points) {
            setHistoryData(historyResponse.data.points.map((p: any) => ({
                timestamp: p.timestamp,
                bitrate_kbps: p.video_bitrate_kbps || p.audio_bitrate_kbps || 0,
                fps: p.video_fps || 0,
                quality_score: p.overall_quality === 'ultra' ? 100 : 
                               p.overall_quality === 'high' ? 80 :
                               p.overall_quality === 'medium' ? 60 :
                               p.overall_quality === 'low' ? 40 : 0
            })));
        }
      }

      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to fetch stream quality data:', error);
      toast({
        title: t('errors.generic'),
        description: t('analytics.error'),
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  }, [period, t, toast]);

  useEffect(() => {
    fetchData();
    // Poll every 30 секунд
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [period, fetchData]);

  // Calculate aggregate metrics for widget
  const bitrate = currentQuality?.performance?.bitrate_kbps || 
                  (currentQuality?.video?.bitrate_kbps || 0) + (currentQuality?.audio?.bitrate_kbps || 0);
  
  const fps = currentQuality?.performance?.fps || currentQuality?.video?.fps;
  
  // Determine overall quality score from parts if not provided explicitly
  const qualityScore = (currentQuality?.video?.quality || currentQuality?.audio?.quality || 'unknown') as any;

  return (
    <AppLayout>
    <div className="space-y-6 p-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Stream Quality</h1>
          <p className="text-muted-foreground">
            Real-time monitoring and historical analysis of stream performance
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[120px]">
              <SelectValue placeholder="Period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">1 Hour</SelectItem>
              <SelectItem value="6h">6 Hours</SelectItem>
              <SelectItem value="12h">12 Hours</SelectItem>
              <SelectItem value="24h">24 Hours</SelectItem>
              <SelectItem value="7d">7 Days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={fetchData} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <StreamHealthWidget 
        isLoading={isLoading && !currentQuality}
        isOnline={!!currentQuality}
        bitrate={bitrate}
        fps={fps}
        qualityScore={qualityScore}
        lastCheck={lastUpdated?.toISOString()}
      />

      <StreamQualityHistoryChart 
        data={historyData}
        isLoading={isLoading && historyData.length === 0}
        period={period}
      />
    </div>
    </AppLayout>
  );
};

export default StreamQualityPage;
