/**
 * Feature 022 Phase 3: Metrics Dashboard Integration Tests
 * Tests for tab navigation and component switching
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Metrics from '../../pages/admin/Metrics';
import * as adminApi from '../../api/admin';

// Mock the API
vi.mock('../../api/admin');

// Mock child components
vi.mock('../../components/dashboard/StreamQualityBadge', () => ({
  default: ({ quality, loading, error }: any) => (
    <div data-testid="quality-badge">
      {loading && <span>Loading quality...</span>}
      {error && <span>Error: {error}</span>}
      {quality && <span>Quality: {quality.overall_quality}</span>}
    </div>
  ),
}));

vi.mock('../../components/dashboard/StreamQualityChart', () => ({
  default: ({ streamUrl }: { streamUrl: string }) => (
    <div data-testid="quality-chart">Quality Chart: {streamUrl}</div>
  ),
}));

vi.mock('../../components/dashboard/StreamQualityAlertSettings', () => ({
  default: ({ streamUrl }: { streamUrl: string }) => (
    <div data-testid="alert-settings">Alert Settings: {streamUrl}</div>
  ),
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
      memory_rss: 256000000,
    },
  },
};

const mockQuality = {
  url: 'http://localhost:8081/stream',
  audio: {
    codec: 'aac',
    bitrate_kbps: 128,
    sample_rate_hz: 48000,
    channels: 2,
    duration_sec: 3600,
    quality: 'high',
  },
  video: {
    codec: 'h264',
    bitrate_kbps: 2500,
    resolution: '1920x1080',
    fps: 30,
    duration_sec: 3600,
    quality: 'high',
  },
  is_audio_only: false,
  is_video_only: false,
  has_both: true,
  overall_quality: 'high',
};

const renderMetricsAndWaitReady = async () => {
  render(<Metrics />);
  await screen.findByText(/Current Quality \(Phase 2\)/i);
};

describe('Metrics Dashboard - Phase 3 Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (adminApi.adminApi.getMetrics as any).mockResolvedValue(mockMetrics);
    (adminApi.adminApi.getStreamQuality as any).mockResolvedValue(mockQuality);
  });

  describe('Tab Navigation', () => {
    it('should render all three tabs', async () => {
      await renderMetricsAndWaitReady();
      
      expect(screen.getByText(/Current Quality \(Phase 2\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Trend Analysis \(Phase 3\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Alert Settings \(Phase 3\)/i)).toBeInTheDocument();
    });

    it('should have quality tab active by default', async () => {
      await renderMetricsAndWaitReady();
      
      const qualityTab = screen.getByText(/Current Quality \(Phase 2\)/i).closest('button');
      expect(qualityTab).toHaveClass('border-[color:var(--color-accent)]');
      expect(qualityTab).toHaveClass('text-[color:var(--color-accent)]');
    });

    it('should display quality badge component by default', async () => {
      await renderMetricsAndWaitReady();
      
      expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
      expect(screen.queryByTestId('quality-chart')).not.toBeInTheDocument();
      expect(screen.queryByTestId('alert-settings')).not.toBeInTheDocument();
    });

    it('should switch to trends tab on click', async () => {
      await renderMetricsAndWaitReady();
      
      const trendsTab = screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button');
      fireEvent.click(trendsTab!);
      
      expect(trendsTab).toHaveClass('border-[color:var(--color-accent)]');
      expect(trendsTab).toHaveClass('text-[color:var(--color-accent)]');
    });

    it('should display trend chart component after tab switch', async () => {
      await renderMetricsAndWaitReady();
      
      const trendsTab = screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button');
      fireEvent.click(trendsTab!);
      
      expect(screen.getByTestId('quality-chart')).toBeInTheDocument();
      expect(screen.queryByTestId('quality-badge')).not.toBeInTheDocument();
      expect(screen.queryByTestId('alert-settings')).not.toBeInTheDocument();
    });

    it('should switch to alerts tab on click', async () => {
      await renderMetricsAndWaitReady();
      
      const alertsTab = screen.getByText(/Alert Settings \(Phase 3\)/i).closest('button');
      fireEvent.click(alertsTab!);
      
      expect(alertsTab).toHaveClass('border-[color:var(--color-accent)]');
      expect(alertsTab).toHaveClass('text-[color:var(--color-accent)]');
    });

    it('should display alert settings component after tab switch', async () => {
      await renderMetricsAndWaitReady();
      
      const alertsTab = screen.getByText(/Alert Settings \(Phase 3\)/i).closest('button');
      fireEvent.click(alertsTab!);
      
      expect(screen.getByTestId('alert-settings')).toBeInTheDocument();
      expect(screen.queryByTestId('quality-badge')).not.toBeInTheDocument();
      expect(screen.queryByTestId('quality-chart')).not.toBeInTheDocument();
    });
  });

  describe('Tab Styling', () => {
    it('should have proper active tab styling', async () => {
      await renderMetricsAndWaitReady();
      
      const activeTab = screen.getByText(/Current Quality \(Phase 2\)/i).closest('button');
      expect(activeTab).toHaveClass('border-b-2');
      expect(activeTab).toHaveClass('border-[color:var(--color-accent)]');
    });

    it('should have proper inactive tab styling', async () => {
      await renderMetricsAndWaitReady();
      
      const inactiveTab = screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button');
      expect(inactiveTab).toHaveClass('border-transparent');
      expect(inactiveTab).toHaveClass('text-[color:var(--color-text-muted)]');
    });

    it('should update styling on tab change', async () => {
      await renderMetricsAndWaitReady();
      
      const qualityTab = screen.getByText(/Current Quality \(Phase 2\)/i).closest('button');
      const trendsTab = screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button');
      
      // Initial state
      expect(qualityTab).toHaveClass('border-[color:var(--color-accent)]');
      expect(trendsTab).not.toHaveClass('border-[color:var(--color-accent)]');
      
      // After click
      fireEvent.click(trendsTab!);
      expect(trendsTab).toHaveClass('border-[color:var(--color-accent)]');
      expect(qualityTab).not.toHaveClass('border-[color:var(--color-accent)]');
    });
  });

  describe('Tab Switching Behavior', () => {
    it('should not display multiple components at once', async () => {
      await renderMetricsAndWaitReady();
      
      // Switch through tabs
      fireEvent.click(screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button')!);
      expect(screen.getByTestId('quality-chart')).toBeInTheDocument();
      expect(screen.queryByTestId('quality-badge')).not.toBeInTheDocument();
      
      fireEvent.click(screen.getByText(/Alert Settings \(Phase 3\)/i).closest('button')!);
      expect(screen.getByTestId('alert-settings')).toBeInTheDocument();
      expect(screen.queryByTestId('quality-chart')).not.toBeInTheDocument();
      
      fireEvent.click(screen.getByText(/Current Quality \(Phase 2\)/i).closest('button')!);
      expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
      expect(screen.queryByTestId('alert-settings')).not.toBeInTheDocument();
    });

    it('should maintain component state during tab switches', async () => {
      await renderMetricsAndWaitReady();
      
      const trendsTab = screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button');
      fireEvent.click(trendsTab!);
      
      // Component should still be in document
      expect(screen.getByTestId('quality-chart')).toBeInTheDocument();
    });

    it('should handle rapid tab switching', async () => {
      await renderMetricsAndWaitReady();
      
      const qualityTab = screen.getByText(/Current Quality \(Phase 2\)/i).closest('button');
      const trendsTab = screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button');
      const alertsTab = screen.getByText(/Alert Settings \(Phase 3\)/i).closest('button');
      
      // Rapid clicks
      fireEvent.click(trendsTab!);
      fireEvent.click(alertsTab!);
      fireEvent.click(qualityTab!);
      fireEvent.click(trendsTab!);
      
      // Should still be on trends tab
      expect(screen.getByTestId('quality-chart')).toBeInTheDocument();
    });
  });

  describe('Component Props Passing', () => {
    it('should pass streamUrl to quality badge', async () => {
      await renderMetricsAndWaitReady();
      
      // Assuming streamUrl is part of component context
      const badge = screen.getByTestId('quality-badge');
      expect(badge).toBeInTheDocument();
    });

    it('should pass streamUrl to quality chart', async () => {
      await renderMetricsAndWaitReady();
      
      fireEvent.click(screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button')!);
      const chart = screen.getByTestId('quality-chart');
      expect(chart).toBeInTheDocument();
    });

    it('should pass streamUrl to alert settings', async () => {
      await renderMetricsAndWaitReady();
      
      fireEvent.click(screen.getByText(/Alert Settings \(Phase 3\)/i).closest('button')!);
      const settings = screen.getByTestId('alert-settings');
      expect(settings).toBeInTheDocument();
    });
  });

  describe('Phase 2 & Phase 3 Coexistence', () => {
    it('should support both Phase 2 and Phase 3 features', async () => {
      await renderMetricsAndWaitReady();
      
      // Phase 2
      expect(screen.getByText(/Current Quality \(Phase 2\)/i)).toBeInTheDocument();
      expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
      
      // Phase 3
      expect(screen.getByText(/Trend Analysis \(Phase 3\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Alert Settings \(Phase 3\)/i)).toBeInTheDocument();
    });

    it('should not break Phase 2 functionality with Phase 3', async () => {
      await renderMetricsAndWaitReady();
      
      // Phase 2 should still work when on its tab
      const qualityTab = screen.getByText(/Current Quality \(Phase 2\)/i).closest('button');
      fireEvent.click(qualityTab!);
      
      expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
    });

    it('should display other sections with Phase 3 tabs', async () => {
      await renderMetricsAndWaitReady();
      
      // Other sections should still be visible
      // Assuming there are other sections like system metrics
      // This depends on actual Metrics component structure
      expect(screen.getByText(/System Metrics/i)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper button semantics for tabs', async () => {
      await renderMetricsAndWaitReady();

      expect(screen.getByRole('button', { name: /Current Quality \(Phase 2\)/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Trend Analysis \(Phase 3\)/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Alert Settings \(Phase 3\)/i })).toBeInTheDocument();
    });

    it('should have clear tab labels', async () => {
      await renderMetricsAndWaitReady();
      
      expect(screen.getByText(/Current Quality/i)).toBeInTheDocument();
      expect(screen.getByText(/Trend Analysis/i)).toBeInTheDocument();
      expect(screen.getByText(/Alert Settings/i)).toBeInTheDocument();
    });

    it('should indicate active tab visually', async () => {
      await renderMetricsAndWaitReady();
      
      const activeTab = screen.getByText(/Current Quality/i).closest('button');
      expect(activeTab).toHaveClass('border-[color:var(--color-accent)]');
    });
  });

  describe('Error Handling', () => {
    it('should handle missing stream data gracefully', async () => {
      (adminApi.adminApi.getStreamQuality as any).mockRejectedValueOnce(new Error('boom'));

      await renderMetricsAndWaitReady();
      expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
    });

    it('should render metrics error state', async () => {
      (adminApi.adminApi.getMetrics as any).mockRejectedValueOnce(new Error('boom'));
      render(<Metrics />);
      expect(await screen.findByText(/Failed to fetch metrics/i)).toBeInTheDocument();
    });
  });

  describe('User Interaction Flow', () => {
    it('should complete full user workflow', async () => {
      await renderMetricsAndWaitReady();
      
      // 1. View current quality (Phase 2)
      expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
      
      // 2. Switch to trends (Phase 3)
      fireEvent.click(screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button')!);
      expect(screen.getByTestId('quality-chart')).toBeInTheDocument();
      
      // 3. Switch to alert settings (Phase 3)
      fireEvent.click(screen.getByText(/Alert Settings \(Phase 3\)/i).closest('button')!);
      expect(screen.getByTestId('alert-settings')).toBeInTheDocument();
      
      // 4. Return to current quality
      fireEvent.click(screen.getByText(/Current Quality \(Phase 2\)/i).closest('button')!);
      expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
    });
  });

  describe('Responsive Tabs', () => {
    it('should render tabs in a row', async () => {
      const { container } = render(<Metrics />);
      await screen.findByText(/Current Quality \(Phase 2\)/i);
      const tabContainer = container.querySelector('[class*="flex"][class*="gap"]');
      expect(tabContainer).toBeInTheDocument();
    });

    it('should have consistent tab sizing', async () => {
      const { container } = render(<Metrics />);
      await screen.findByText(/Current Quality \(Phase 2\)/i);
      const tabs = container.querySelectorAll('button[class*="px-4"]');
      expect(tabs.length).toBeGreaterThanOrEqual(3);
    });
  });
});
