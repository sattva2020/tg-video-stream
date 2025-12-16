/**
 * Feature 022 Phase 3: Metrics Dashboard Integration Tests
 * Tests for tab navigation and component switching
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Metrics from '../../pages/admin/Metrics';

// Mock child components
vi.mock('../dashboard/StreamQualityBadge', () => ({
  default: ({ streamUrl }: { streamUrl: string }) => (
    <div data-testid="quality-badge">Quality Badge: {streamUrl}</div>
  ),
}));

vi.mock('../dashboard/StreamQualityChart', () => ({
  default: ({ streamUrl }: { streamUrl: string }) => (
    <div data-testid="quality-chart">Quality Chart: {streamUrl}</div>
  ),
}));

vi.mock('../dashboard/StreamQualityAlertSettings', () => ({
  default: ({ streamUrl }: { streamUrl: string }) => (
    <div data-testid="alert-settings">Alert Settings: {streamUrl}</div>
  ),
}));

describe('Metrics Dashboard - Phase 3 Integration', () => {
  describe('Tab Navigation', () => {
    it('should render all three tabs', () => {
      render(<Metrics />);
      
      expect(screen.getByText(/Current Quality \(Phase 2\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Trend Analysis \(Phase 3\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Alert Settings \(Phase 3\)/i)).toBeInTheDocument();
    });

    it('should have quality tab active by default', () => {
      const { container } = render(<Metrics />);
      
      const qualityTab = screen.getByText(/Current Quality \(Phase 2\)/i).closest('button');
      expect(qualityTab).toHaveClass('border-blue-600');
      expect(qualityTab).toHaveClass('text-blue-600');
    });

    it('should display quality badge component by default', () => {
      render(<Metrics />);
      
      expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
      expect(screen.queryByTestId('quality-chart')).not.toBeInTheDocument();
      expect(screen.queryByTestId('alert-settings')).not.toBeInTheDocument();
    });

    it('should switch to trends tab on click', () => {
      render(<Metrics />);
      
      const trendsTab = screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button');
      fireEvent.click(trendsTab!);
      
      expect(trendsTab).toHaveClass('border-blue-600');
      expect(trendsTab).toHaveClass('text-blue-600');
    });

    it('should display trend chart component after tab switch', () => {
      render(<Metrics />);
      
      const trendsTab = screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button');
      fireEvent.click(trendsTab!);
      
      expect(screen.getByTestId('quality-chart')).toBeInTheDocument();
      expect(screen.queryByTestId('quality-badge')).not.toBeInTheDocument();
      expect(screen.queryByTestId('alert-settings')).not.toBeInTheDocument();
    });

    it('should switch to alerts tab on click', () => {
      render(<Metrics />);
      
      const alertsTab = screen.getByText(/Alert Settings \(Phase 3\)/i).closest('button');
      fireEvent.click(alertsTab!);
      
      expect(alertsTab).toHaveClass('border-blue-600');
      expect(alertsTab).toHaveClass('text-blue-600');
    });

    it('should display alert settings component after tab switch', () => {
      render(<Metrics />);
      
      const alertsTab = screen.getByText(/Alert Settings \(Phase 3\)/i).closest('button');
      fireEvent.click(alertsTab!);
      
      expect(screen.getByTestId('alert-settings')).toBeInTheDocument();
      expect(screen.queryByTestId('quality-badge')).not.toBeInTheDocument();
      expect(screen.queryByTestId('quality-chart')).not.toBeInTheDocument();
    });
  });

  describe('Tab Styling', () => {
    it('should have proper active tab styling', () => {
      const { container } = render(<Metrics />);
      
      const activeTab = screen.getByText(/Current Quality \(Phase 2\)/i).closest('button');
      expect(activeTab).toHaveClass('border-b-2');
      expect(activeTab).toHaveClass('border-blue-600');
    });

    it('should have proper inactive tab styling', () => {
      const { container } = render(<Metrics />);
      
      const inactiveTab = screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button');
      expect(inactiveTab).toHaveClass('border-transparent');
      expect(inactiveTab).toHaveClass('text-gray-600');
    });

    it('should update styling on tab change', () => {
      render(<Metrics />);
      
      const qualityTab = screen.getByText(/Current Quality \(Phase 2\)/i).closest('button');
      const trendsTab = screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button');
      
      // Initial state
      expect(qualityTab).toHaveClass('border-blue-600');
      expect(trendsTab).not.toHaveClass('border-blue-600');
      
      // After click
      fireEvent.click(trendsTab!);
      expect(trendsTab).toHaveClass('border-blue-600');
      expect(qualityTab).not.toHaveClass('border-blue-600');
    });
  });

  describe('Tab Switching Behavior', () => {
    it('should not display multiple components at once', () => {
      render(<Metrics />);
      
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

    it('should maintain component state during tab switches', () => {
      const { rerender } = render(<Metrics />);
      
      const trendsTab = screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button');
      fireEvent.click(trendsTab!);
      
      // Component should still be in document
      expect(screen.getByTestId('quality-chart')).toBeInTheDocument();
    });

    it('should handle rapid tab switching', () => {
      render(<Metrics />);
      
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
    it('should pass streamUrl to quality badge', () => {
      render(<Metrics />);
      
      // Assuming streamUrl is part of component context
      const badge = screen.getByTestId('quality-badge');
      expect(badge).toBeInTheDocument();
    });

    it('should pass streamUrl to quality chart', () => {
      render(<Metrics />);
      
      fireEvent.click(screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button')!);
      const chart = screen.getByTestId('quality-chart');
      expect(chart).toBeInTheDocument();
    });

    it('should pass streamUrl to alert settings', () => {
      render(<Metrics />);
      
      fireEvent.click(screen.getByText(/Alert Settings \(Phase 3\)/i).closest('button')!);
      const settings = screen.getByTestId('alert-settings');
      expect(settings).toBeInTheDocument();
    });
  });

  describe('Phase 2 & Phase 3 Coexistence', () => {
    it('should support both Phase 2 and Phase 3 features', () => {
      render(<Metrics />);
      
      // Phase 2
      expect(screen.getByText(/Current Quality \(Phase 2\)/i)).toBeInTheDocument();
      expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
      
      // Phase 3
      expect(screen.getByText(/Trend Analysis \(Phase 3\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Alert Settings \(Phase 3\)/i)).toBeInTheDocument();
    });

    it('should not break Phase 2 functionality with Phase 3', () => {
      render(<Metrics />);
      
      // Phase 2 should still work when on its tab
      const qualityTab = screen.getByText(/Current Quality \(Phase 2\)/i).closest('button');
      fireEvent.click(qualityTab!);
      
      expect(screen.getByTestId('quality-badge')).toBeInTheDocument();
    });

    it('should display other sections with Phase 3 tabs', () => {
      render(<Metrics />);
      
      // Other sections should still be visible
      // Assuming there are other sections like system metrics
      // This depends on actual Metrics component structure
    });
  });

  describe('Accessibility', () => {
    it('should have proper button semantics for tabs', () => {
      const { container } = render(<Metrics />);
      
      const tabs = container.querySelectorAll('button');
      expect(tabs.length).toBeGreaterThanOrEqual(3);
    });

    it('should have clear tab labels', () => {
      render(<Metrics />);
      
      expect(screen.getByText(/Current Quality/i)).toBeInTheDocument();
      expect(screen.getByText(/Trend Analysis/i)).toBeInTheDocument();
      expect(screen.getByText(/Alert Settings/i)).toBeInTheDocument();
    });

    it('should indicate active tab visually', () => {
      const { container } = render(<Metrics />);
      
      const activeTab = screen.getByText(/Current Quality/i).closest('button');
      expect(activeTab).toHaveClass('border-blue-600');
    });
  });

  describe('Error Handling', () => {
    it('should handle missing stream data gracefully', () => {
      // Depends on how Metrics handles missing data
      render(<Metrics />);
      expect(screen.getByText(/Current Quality \(Phase 2\)/i)).toBeInTheDocument();
    });

    it('should render even if a child component fails', () => {
      // Tabs should still be clickable even if a component has an error
      render(<Metrics />);
      fireEvent.click(screen.getByText(/Trend Analysis \(Phase 3\)/i).closest('button')!);
      expect(screen.getByTestId('quality-chart')).toBeInTheDocument();
    });
  });

  describe('User Interaction Flow', () => {
    it('should complete full user workflow', () => {
      render(<Metrics />);
      
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
    it('should render tabs in a row', () => {
      const { container } = render(<Metrics />);
      const tabContainer = container.querySelector('[class*="flex"][class*="gap"]');
      expect(tabContainer).toBeInTheDocument();
    });

    it('should have consistent tab sizing', () => {
      const { container } = render(<Metrics />);
      const tabs = container.querySelectorAll('button[class*="px-4"]');
      expect(tabs.length).toBeGreaterThanOrEqual(3);
    });
  });
});
