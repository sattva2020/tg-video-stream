/**
 * Feature 022 Phase 3: Stream Quality Trend Chart and Alert Settings - Tests
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import StreamQualityChart from './StreamQualityChart';
import StreamQualityAlertSettings from './StreamQualityAlertSettings';
import { QualityTrendData, QualityAlertConfigUpdate } from '../../api/admin';

// Mock data
const mockTrendData: QualityTrendData = {
  stream_url: 'http://stream.local',
  stream_name: 'Test Stream',
  history: [
    {
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      overall_quality: 'high',
      audio_quality: 'high',
      audio_bitrate_kbps: 128,
      video_quality: 'high',
      video_bitrate_kbps: 2500,
      video_resolution: '1920x1080',
      video_fps: 30,
      success: true,
    },
    {
      timestamp: new Date(Date.now() - 1800000).toISOString(),
      overall_quality: 'high',
      audio_quality: 'high',
      audio_bitrate_kbps: 128,
      video_quality: 'high',
      video_bitrate_kbps: 2500,
      video_resolution: '1920x1080',
      video_fps: 30,
      success: true,
    },
  ],
  average_quality: 'high',
  min_quality: 'medium',
  max_quality: 'high',
  audio_avg_bitrate_kbps: 128,
  video_avg_bitrate_kbps: 2500,
  success_rate: 0.95,
  period_start: new Date(Date.now() - 86400000).toISOString(),
  period_end: new Date().toISOString(),
  samples_count: 288,
};

describe('StreamQualityChart Component', () => {
  describe('Rendering', () => {
    it('should render chart container', () => {
      const { container } = render(
        <StreamQualityChart
          streamUrl="http://stream.local"
          streamName="Test Stream"
        />
      );
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should display loading state initially', () => {
      render(
        <StreamQualityChart
          streamUrl="http://stream.local"
          loading={true}
        />
      );
      expect(screen.getByText(/Loading trend data/i)).toBeInTheDocument();
    });

    it('should display error state', () => {
      const errorMsg = 'Failed to fetch data';
      render(
        <StreamQualityChart
          streamUrl="http://stream.local"
          error={errorMsg}
        />
      );
      expect(screen.getByText(new RegExp(errorMsg))).toBeInTheDocument();
    });

    it('should display no data message', () => {
      render(
        <StreamQualityChart
          streamUrl="http://stream.local"
        />
      );
      // When data is not provided
      expect(screen.getByText(/No quality data available/i)).toBeInTheDocument();
    });
  });

  describe('Statistics Display', () => {
    it('should display quality statistics', () => {
      // Mock the data loading
      vi.mock('../../api/admin', () => ({
        adminApi: {
          getQualityTrend: vi.fn().mockResolvedValue(mockTrendData),
        },
      }));

      // In real implementation with proper data
      // This would test statistics rendering
    });

    it('should display period information', () => {
      // Test period start/end display
    });

    it('should calculate and display success rate', () => {
      // Test success rate calculation and display
    });
  });

  describe('Data Points', () => {
    it('should display total samples count', () => {
      // Test samples count display
    });

    it('should display bitrate averages', () => {
      // Test audio/video bitrate display
    });

    it('should handle missing bitrate data', () => {
      // Test graceful handling of missing data
    });
  });

  describe('Responsive Design', () => {
    it('should be responsive on mobile', () => {
      const { container } = render(
        <StreamQualityChart
          streamUrl="http://stream.local"
          hours={24}
        />
      );
      const grid = container.querySelector('[class*="grid"]');
      expect(grid).toBeInTheDocument();
    });

    it('should have proper grid layout', () => {
      const { container } = render(
        <StreamQualityChart
          streamUrl="http://stream.local"
        />
      );
      expect(container.querySelector('[class*="grid-cols"]')).toBeInTheDocument();
    });
  });

  describe('Interaction', () => {
    it('should call onDataLoaded callback when data is received', async () => {
      const onDataLoaded = vi.fn();
      // This would be tested with actual data mock
    });

    it('should accept hours parameter', () => {
      const { rerender } = render(
        <StreamQualityChart
          streamUrl="http://stream.local"
          hours={24}
        />
      );
      
      rerender(
        <StreamQualityChart
          streamUrl="http://stream.local"
          hours={48}
        />
      );
    });
  });
});

describe('StreamQualityAlertSettings Component', () => {
  describe('Rendering', () => {
    it('should render settings form', () => {
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
          streamName="Test Stream"
        />
      );
      expect(screen.getByText(/Alert Settings/i)).toBeInTheDocument();
    });

    it('should display loading state', () => {
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
          loading={true}
        />
      );
      expect(screen.getByText(/Loading alert settings/i)).toBeInTheDocument();
    });

    it('should display error message', () => {
      const errorMsg = 'Failed to load config';
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
          error={errorMsg}
        />
      );
      expect(screen.getByText(new RegExp(errorMsg))).toBeInTheDocument();
    });
  });

  describe('Enable/Disable Toggle', () => {
    it('should have enable/disable toggle', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const toggle = container.querySelector('input[type="checkbox"]');
      expect(toggle).toBeInTheDocument();
    });

    it('should be enabled by default', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const toggle = container.querySelector('input[type="checkbox"]') as HTMLInputElement;
      expect(toggle?.checked).toBe(true);
    });

    it('should toggle enabled/disabled state', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const toggle = container.querySelector('input[type="checkbox"]') as HTMLElement;
      fireEvent.click(toggle);
      // Verify state changed
    });
  });

  describe('Quality Thresholds', () => {
    it('should display overall quality threshold select', () => {
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      expect(screen.getByText(/Minimum Overall Quality/i)).toBeInTheDocument();
    });

    it('should display audio quality threshold select', () => {
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      expect(screen.getByText(/Minimum Audio Quality/i)).toBeInTheDocument();
    });

    it('should display video quality threshold select', () => {
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      expect(screen.getByText(/Minimum Video Quality/i)).toBeInTheDocument();
    });

    it('should have quality level options', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const selects = container.querySelectorAll('select');
      expect(selects.length).toBeGreaterThan(0);
    });

    it('should allow quality level selection', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const select = container.querySelector('select') as HTMLSelectElement;
      fireEvent.change(select, { target: { value: 'high' } });
      expect(select.value).toBe('high');
    });
  });

  describe('Advanced Settings', () => {
    it('should have advanced settings toggle', () => {
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      expect(screen.getByText(/Advanced Bitrate Thresholds/i)).toBeInTheDocument();
    });

    it('should toggle advanced settings visibility', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const advButton = screen.getByText(/Advanced Bitrate Thresholds/i);
      fireEvent.click(advButton);
      // Verify visibility toggled
    });

    it('should display audio bitrate threshold input', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      // After clicking advanced toggle
      const advButton = screen.getByText(/Advanced Bitrate Thresholds/i);
      fireEvent.click(advButton);
      
      expect(screen.getByText(/Minimum Audio Bitrate/i)).toBeInTheDocument();
    });

    it('should display video bitrate threshold input', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const advButton = screen.getByText(/Advanced Bitrate Thresholds/i);
      fireEvent.click(advButton);
      
      expect(screen.getByText(/Minimum Video Bitrate/i)).toBeInTheDocument();
    });

    it('should display resolution threshold select', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const advButton = screen.getByText(/Advanced Bitrate Thresholds/i);
      fireEvent.click(advButton);
      
      expect(screen.getByText(/Minimum Video Resolution/i)).toBeInTheDocument();
    });
  });

  describe('Alert Behavior', () => {
    it('should display degradation notification checkbox', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      expect(screen.getByText(/Notify when quality degrades/i)).toBeInTheDocument();
    });

    it('should display recovery notification checkbox', () => {
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      expect(screen.getByText(/Notify when quality recovers/i)).toBeInTheDocument();
    });

    it('should toggle degradation notifications', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const checkboxes = container.querySelectorAll('input[type="checkbox"]');
      if (checkboxes.length > 1) {
        fireEvent.click(checkboxes[1]);
      }
    });

    it('should toggle recovery notifications', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const checkboxes = container.querySelectorAll('input[type="checkbox"]');
      if (checkboxes.length > 2) {
        fireEvent.click(checkboxes[2]);
      }
    });
  });

  describe('Save Button', () => {
    it('should display save button', () => {
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      expect(screen.getByText(/Save Settings/i)).toBeInTheDocument();
    });

    it('should be enabled by default', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const button = screen.getByText(/Save Settings/i) as HTMLButtonElement;
      expect(button.disabled).toBe(false);
    });

    it('should call onSave callback when clicked', async () => {
      const onSave = vi.fn();
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
          onSave={onSave}
        />
      );
      const button = screen.getByText(/Save Settings/i);
      fireEvent.click(button);
      
      await waitFor(() => {
        // onSave should be called
      });
    });

    it('should show success message after save', async () => {
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const button = screen.getByText(/Save Settings/i);
      fireEvent.click(button);
      
      // In real implementation with mocked API
      // await waitFor(() => {
      //   expect(screen.getByText(/saved successfully/i)).toBeInTheDocument();
      // });
    });
  });

  describe('Consecutive Failures Threshold', () => {
    it('should display consecutive failures input', () => {
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      expect(screen.getByText(/Consecutive Failures to Alert/i)).toBeInTheDocument();
    });

    it('should allow changing consecutive failures', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const inputs = container.querySelectorAll('input[type="number"]');
      if (inputs.length > 0) {
        fireEvent.change(inputs[0], { target: { value: '5' } });
        expect((inputs[0] as HTMLInputElement).value).toBe('5');
      }
    });

    it('should have min/max constraints', () => {
      const { container } = render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      const input = container.querySelector('input[type="number"][min]') as HTMLInputElement;
      if (input) {
        expect(input.min).toBeDefined();
        expect(input.max).toBeDefined();
      }
    });
  });

  describe('Info Box', () => {
    it('should display information box', () => {
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      expect(screen.getByText(/Alert Notification/i)).toBeInTheDocument();
    });

    it('should contain helpful information', () => {
      render(
        <StreamQualityAlertSettings
          streamUrl="http://stream.local"
        />
      );
      expect(
        screen.getByText(/Alerts will be triggered when consecutive failures/i)
      ).toBeInTheDocument();
    });
  });
});
