import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import type { Formatter } from 'recharts/types/component/DefaultTooltipContent';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';

interface QualityHistoryPoint {
  timestamp: string;
  bitrate_kbps: number;
  fps: number;
  quality_score: number; // 0-100 mapped from low/medium/high
}

interface StreamQualityHistoryChartProps {
  data: QualityHistoryPoint[];
  isLoading: boolean;
  period: string;
}

export const StreamQualityHistoryChart: React.FC<StreamQualityHistoryChartProps> = ({
  data,
  isLoading,
  period
}) => {
  if (isLoading) {
    return <Skeleton className="h-[400px] w-full" />;
  }

  if (!data || data.length === 0) {
    return (
      <Card className="h-[400px] flex items-center justify-center text-muted-foreground">
        No data available for the selected period
      </Card>
    );
  }

  const formatXAxis = (tickItem: string) => {
    const date = new Date(tickItem);
    if (period === '24h' || period === '12h' || period === '6h' || period === '1h') {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const tooltipFormatter: Formatter<number, string | number> = (value, name) => {
    const safeValue = (value as number | undefined) ?? 0;
    return [
      name === 'bitrate_kbps' ? `${Math.round(safeValue)} kbps` : safeValue.toFixed(1),
      name === 'bitrate_kbps' ? 'Bitrate' : 'FPS'
    ];
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Stream Quality History</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[350px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{
                top: 5,
                right: 30,
                left: 20,
                bottom: 5,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis 
                dataKey="timestamp" 
                tickFormatter={formatXAxis}
                minTickGap={30}
              />
              <YAxis yAxisId="left" label={{ value: 'Bitrate (kbps)', angle: -90, position: 'insideLeft' }} />
              <YAxis yAxisId="right" orientation="right" label={{ value: 'FPS', angle: 90, position: 'insideRight' }} />
              <Tooltip 
                labelFormatter={(label) => new Date(label).toLocaleString()}
                formatter={tooltipFormatter}
              />
              <Legend />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="bitrate_kbps"
                stroke="#8884d8"
                activeDot={{ r: 8 }}
                name="Bitrate"
                strokeWidth={2}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="fps"
                stroke="#82ca9d"
                name="FPS"
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};
