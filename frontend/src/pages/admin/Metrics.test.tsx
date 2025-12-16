/**
 * Metrics Component Tests with Stream Quality Integration
 * Tests for updated Metrics component with quality monitoring
 */
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Metrics from './Metrics';
import * as adminApi from '../../api/admin';

// Mock the API
vi.mock('../../api/admin');
vi.mock('../../components/dashboard/StreamQualityBadge', () => ({
  default: ({ quality, loading, error }: any) => (
    <div data-testid="quality-badge">
      {loading && <span>Loading quality...</span>}
      {error && <span>Error: {error}</span>}
      {quality && <span>Quality: {quality.overall_quality}</span>}
    </div>
  )
}));

const mockMetrics = {
  online: true,
  current_stream_url: 'http://localhost:8081/stream',
  metrics: {
    system: {
      cpu_percent: 45.5,
      memory_percent: 62.3,
    },
    process: {
      cpu_percent: 12.5,
      memory_rss: 256000000, // ~256 MB
    }
  }
};

const mockQuality = {
  url: 'http://localhost:8081/stream',
  audio: {
    codec: 'aac',
    bitrate_kbps: 128,
    sample_rate_hz: 48000,
    channels: 2,
    duration_sec: 3600,
    quality: 'high'
  },
  video: {
    codec: 'h264',
    bitrate_kbps: 2500,
    resolution: '1920x1080',
    fps: 30,
    duration_sec: 3600,
    quality: 'high'
  },
  is_audio_only: false,
  is_video_only: false,
  has_both: true,
  overall_quality: 'high'
};

describe('Metrics Component with Stream Quality', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Component Rendering', () => {
    it('should render Metrics component', async () => {
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByText(/System Metrics/i)).toBeInTheDocument();
      });
    });

    it('should display loading state initially', () => {
      (adminApi.adminApi.getMetrics as any).mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve(mockMetrics), 100))
      );

      const { container } = render(<Metrics />);
      // Component should be in loading state initially
      expect(container).toBeInTheDocument();
    });
  });

  describe('System Metrics Display', () => {
    it('should display system CPU usage', async () => {
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByText(/System/i)).toBeInTheDocument();
        expect(screen.getByText(/45.5%/)).toBeInTheDocument();
      });
    });

    it('should display system memory usage', async () => {
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByText(/Memory Usage/i)).toBeInTheDocument();
        expect(screen.getByText(/62.3%/)).toBeInTheDocument();
      });
    });

    it('should display process metrics', async () => {
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByText(/Streamer Process/i)).toBeInTheDocument();
        expect(screen.getByText(/12.5%/)).toBeInTheDocument();
        expect(screen.getByText(/256 MB/)).toBeInTheDocument();
      });
    });

    it('should display online status', async () => {
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByText(/ONLINE/i)).toBeInTheDocument();
      });
    });

    it('should display offline status', async () => {
      const offlineMetrics = { ...mockMetrics, online: false };
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(offlineMetrics);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByText(/OFFLINE/i)).toBeInTheDocument();
      });
    });
  });

  describe('Stream Quality Integration', () => {
    it('should display Stream Quality section when online', async () => {
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByText(/Stream Quality/i)).toBeInTheDocument();
      });
    });

    it('should not display Stream Quality section when offline', async () => {
      const offlineMetrics = { ...mockMetrics, online: false };
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(offlineMetrics);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.queryByText(/Stream Quality/i)).not.toBeInTheDocument();
      });
    });

    it('should fetch stream quality data', async () => {
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(adminApi.adminApi.getStreamQuality).toHaveBeenCalledWith(
          'http://localhost:8081/stream',
          10,
          true
        );
      });
    });

    it('should display quality badge component', async () => {
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
        expect(screen.getByText('Quality: high')).toBeInTheDocument();
      });
    });

    it('should handle quality fetch error', async () => {
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockRejectedValue(new Error('API error'));

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
        expect(screen.getByText(/Failed to fetch stream quality/i)).toBeInTheDocument();
      });
    });

    it('should update quality on interval', async () => {
      jest.useFakeTimers();
      
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(adminApi.adminApi.getStreamQuality).toHaveBeenCalledTimes(1);
      });

      // Advance time by 15 seconds (quality polling interval)
      jest.advanceTimersByTime(15000);
      
      await waitFor(() => {
        expect(adminApi.adminApi.getStreamQuality).toHaveBeenCalledTimes(2);
      });

      jest.useRealTimers();
    });
  });

  describe('API Integration', () => {
    it('should call getMetrics on mount', async () => {
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(adminApi.adminApi.getMetrics).toHaveBeenCalled();
      });
    });

    it('should poll metrics every 5 seconds', async () => {
      jest.useFakeTimers();
      
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(adminApi.adminApi.getMetrics).toHaveBeenCalledTimes(1);
      });

      jest.advanceTimersByTime(5000);
      
      await waitFor(() => {
        expect(adminApi.adminApi.getMetrics).toHaveBeenCalledTimes(2);
      });

      jest.useRealTimers();
    });

    it('should handle metrics fetch error', async () => {
      (adminApi.adminApi.getMetrics as any).mockRejectedValue(new Error('API error'));

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByText(/Failed to fetch metrics/i)).toBeInTheDocument();
      });
    });
  });

  describe('Data Formatting', () => {
    it('should format CPU percentage correctly', async () => {
      const customMetrics = {
        ...mockMetrics,
        metrics: {
          ...mockMetrics.metrics,
          system: {
            ...mockMetrics.metrics.system,
            cpu_percent: 99.9
          }
        }
      };
      
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(customMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByText(/99.9%/)).toBeInTheDocument();
      });
    });

    it('should format memory in MB correctly', async () => {
      const customMetrics = {
        ...mockMetrics,
        metrics: {
          ...mockMetrics.metrics,
          process: {
            ...mockMetrics.metrics.process,
            memory_rss: 512000000 // ~512 MB
          }
        }
      };
      
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(customMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByText(/512 MB/)).toBeInTheDocument();
      });
    });

    it('should handle null metrics gracefully', async () => {
      const noMetricsData = { ...mockMetrics, metrics: null };
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(noMetricsData);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByText(/No metrics available/i)).toBeInTheDocument();
      });
    });
  });

  describe('Conditional Rendering', () => {
    it('should show stream quality section only when online', async () => {
      const onlineMetrics = { ...mockMetrics, online: true };
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(onlineMetrics);
      (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.getByText(/Stream Quality/i)).toBeInTheDocument();
      });
    });

    it('should hide stream quality section when offline', async () => {
      const offlineMetrics = { ...mockMetrics, online: false };
      (adminApi.adminApi.getMetrics as any).mockResolvedValue(offlineMetrics);

      render(<Metrics />);
      
      await waitFor(() => {
        expect(screen.queryByText(/Stream Quality/i)).not.toBeInTheDocument();
      });
    });
  });
});
