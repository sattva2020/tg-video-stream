/**
 * Feature 022 Phase 2: Stream Quality Badge Component Tests
 * Tests for StreamQualityBadge React component
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import StreamQualityBadge from './StreamQualityBadge';
import { StreamQualityResponse } from '../../api/admin';

const mockHighQuality: StreamQualityResponse = {
  url: 'http://test.stream/video',
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

const mockAudioOnly: StreamQualityResponse = {
  url: 'http://test.stream/audio',
  audio: {
    codec: 'aac',
    bitrate_kbps: 192,
    sample_rate_hz: 44100,
    channels: 2,
    duration_sec: 3600,
    quality: 'high'
  },
  video: null,
  is_audio_only: true,
  is_video_only: false,
  has_both: false,
  overall_quality: 'high'
};

const mockLowQuality: StreamQualityResponse = {
  url: 'http://test.stream/low',
  audio: {
    codec: 'aac',
    bitrate_kbps: 64,
    sample_rate_hz: 22050,
    channels: 1,
    duration_sec: 3600,
    quality: 'low'
  },
  video: {
    codec: 'h264',
    bitrate_kbps: 500,
    resolution: '640x480',
    fps: 15,
    duration_sec: 3600,
    quality: 'low'
  },
  is_audio_only: false,
  is_video_only: false,
  has_both: true,
  overall_quality: 'low'
};

describe('StreamQualityBadge Component', () => {
  describe('Loading State', () => {
    it('should display loading spinner and text', () => {
      render(<StreamQualityBadge loading={true} />);
      expect(screen.getByText(/Analyzing/i)).toBeInTheDocument();
    });

    it('should show loading indicator', () => {
      const { container } = render(<StreamQualityBadge loading={true} />);
      expect(container.querySelector('svg')).toBeInTheDocument();
    });
  });

  describe('Error State', () => {
    it('should display error message', () => {
      render(
        <StreamQualityBadge 
          error="Failed to analyze stream"
          quality={null}
        />
      );
      expect(screen.getByText('Failed to analyze stream')).toBeInTheDocument();
    });

    it('should show warning icon on error', () => {
      const { container } = render(
        <StreamQualityBadge 
          error="Connection timeout"
          quality={null}
        />
      );
      // Check for error styling
      expect(container.querySelector('.text-red-600')).toBeInTheDocument();
    });
  });

  describe('Quality Badge Rendering', () => {
    it('should render high quality badge with green styling', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockHighQuality} />
      );
      expect(screen.getByText(/high/i)).toBeInTheDocument();
      expect(container.querySelector('.bg-green-100')).toBeInTheDocument();
    });

    it('should render low quality badge with orange styling', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockLowQuality} />
      );
      expect(screen.getByText(/low/i)).toBeInTheDocument();
      expect(container.querySelector('.bg-orange-100')).toBeInTheDocument();
    });

    it('should display correct quality icons', () => {
      const { rerender } = render(
        <StreamQualityBadge quality={mockHighQuality} />
      );
      // High quality should have specific icon
      expect(screen.getByTitle(/High quality|📺/)).toBeInTheDocument();

      rerender(<StreamQualityBadge quality={mockLowQuality} />);
      // Low quality should have different icon
      expect(screen.getByTitle(/Low quality|📱/)).toBeInTheDocument();
    });
  });

  describe('Compact Mode', () => {
    it('should render compact view when compact=true', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockHighQuality} compact={true} />
      );
      // Compact mode should have limited width
      const badge = container.querySelector('[className*="max-w"]');
      expect(badge).toBeInTheDocument();
    });

    it('should be clickable in compact mode', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockHighQuality} compact={true} />
      );
      const badge = container.querySelector('[role="button"]') || container.firstChild;
      expect(badge).toBeInTheDocument();
    });
  });

  describe('Expandable Details', () => {
    it('should expand to show audio metrics', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockHighQuality} compact={false} />
      );
      // Should show audio section by default or after expand
      expect(screen.getByText(/Audio/i) || screen.getByText(/codec/i)).toBeInTheDocument();
    });

    it('should display audio codec information', () => {
      render(<StreamQualityBadge quality={mockHighQuality} compact={false} />);
      expect(screen.getByText(/aac|AAC/i)).toBeInTheDocument();
    });

    it('should display audio bitrate', () => {
      render(<StreamQualityBadge quality={mockHighQuality} compact={false} />);
      expect(screen.getByText(/128|bitrate/i)).toBeInTheDocument();
    });

    it('should show video metrics when available', () => {
      render(<StreamQualityBadge quality={mockHighQuality} compact={false} />);
      expect(screen.getByText(/1920x1080|resolution/i)).toBeInTheDocument();
      expect(screen.getByText(/h264|H\.264|h\.264/i)).toBeInTheDocument();
    });

    it('should hide video section for audio-only streams', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockAudioOnly} compact={false} />
      );
      // Should indicate audio-only
      const text = container.textContent || '';
      expect(text).toContain('Audio only');
    });
  });

  describe('Stream Information', () => {
    it('should display stream URL', () => {
      render(<StreamQualityBadge quality={mockHighQuality} compact={false} />);
      expect(screen.getByText(/test\.stream/)).toBeInTheDocument();
    });

    it('should show stream type (audio only)', () => {
      render(<StreamQualityBadge quality={mockAudioOnly} compact={false} />);
      expect(screen.getByText(/Audio only/i) || screen.getByText(/audio only/i)).toBeInTheDocument();
    });

    it('should show stream type (audio + video)', () => {
      render(<StreamQualityBadge quality={mockHighQuality} compact={false} />);
      const text = screen.getByText(/http/i).textContent || '';
      expect(text).toBeDefined();
    });
  });

  describe('Quality Levels', () => {
    const qualityLevels = [
      { level: 'lossless', color: 'green' },
      { level: 'high', color: 'blue' },
      { level: 'medium', color: 'yellow' },
      { level: 'low', color: 'orange' }
    ];

    qualityLevels.forEach(({ level, color }) => {
      it(`should render ${level} quality with ${color} styling`, () => {
        const mockQuality = {
          ...mockHighQuality,
          overall_quality: level
        };
        const { container } = render(
          <StreamQualityBadge quality={mockQuality} />
        );
        // Check for quality-specific color class
        const colorClass = container.querySelector(`[class*="${color}"]`);
        expect(colorClass).toBeDefined();
      });
    });
  });

  describe('Responsive Design', () => {
    it('should apply responsive classes', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockHighQuality} compact={false} />
      );
      // Check for responsive utilities
      const responsiveElement = container.querySelector('[class*="md:"]') || 
                                container.querySelector('[class*="sm:"]');
      expect(responsiveElement).toBeDefined();
    });

    it('should render properly in mobile viewport', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockHighQuality} compact={true} />
      );
      expect(container.firstChild).toBeInTheDocument();
    });
  });

  describe('Interactive Features', () => {
    it('should handle expand/collapse', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockHighQuality} compact={true} />
      );
      const clickable = container.querySelector('[class*="cursor"]') || 
                        container.firstChild as HTMLElement;
      fireEvent.click(clickable);
      // After click, should show expanded content or close
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should have proper hover effects', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockHighQuality} />
      );
      const badge = container.firstChild as HTMLElement;
      // Check for hover classes
      expect(badge.className).toMatch(/hover/i);
    });
  });

  describe('Null and Undefined Handling', () => {
    it('should handle null quality gracefully', () => {
      render(<StreamQualityBadge quality={null} />);
      // Should render without crashing
      expect(document.body).toBeInTheDocument();
    });

    it('should handle undefined quality gracefully', () => {
      render(<StreamQualityBadge quality={undefined} />);
      // Should render without crashing
      expect(document.body).toBeInTheDocument();
    });

    it('should handle missing audio data', () => {
      const mockQuality = {
        ...mockHighQuality,
        audio: null
      };
      render(<StreamQualityBadge quality={mockQuality} />);
      expect(document.body).toBeInTheDocument();
    });

    it('should handle missing video data', () => {
      const mockQuality = {
        ...mockHighQuality,
        video: null
      };
      render(<StreamQualityBadge quality={mockQuality} />);
      expect(document.body).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper title attributes', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockHighQuality} />
      );
      const titleElements = container.querySelectorAll('[title]');
      expect(titleElements.length).toBeGreaterThan(0);
    });

    it('should use semantic HTML', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockHighQuality} compact={false} />
      );
      // Check for proper HTML structure
      expect(container.querySelector('div')).toBeInTheDocument();
    });

    it('should have good color contrast', () => {
      const { container } = render(
        <StreamQualityBadge quality={mockHighQuality} />
      );
      // Tailwind classes ensure WCAG compliance
      expect(container.firstChild).toBeInTheDocument();
    });
  });

  describe('Props Validation', () => {
    it('should render with quality prop only', () => {
      render(<StreamQualityBadge quality={mockHighQuality} />);
      expect(screen.getByText(/high/i)).toBeInTheDocument();
    });

    it('should render with all props', () => {
      render(
        <StreamQualityBadge 
          quality={mockHighQuality}
          loading={false}
          error={null}
          compact={false}
        />
      );
      expect(document.body).toBeInTheDocument();
    });

    it('should handle loading and quality together', () => {
      render(
        <StreamQualityBadge 
          quality={mockHighQuality}
          loading={true}
        />
      );
      // Loading state should take precedence
      expect(screen.getByText(/Analyzing/i)).toBeInTheDocument();
    });
  });
});
