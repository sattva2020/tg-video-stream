import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import HeroPanel from '../../src/components/dashboard/HeroPanel';
import { useThemePreference } from '../../src/hooks/useThemePreference';

// Mock the hook
vi.mock('../../src/hooks/useThemePreference', () => ({
  useThemePreference: vi.fn(),
}));

describe('HeroPanel', () => {
  it('renders correctly in light mode', () => {
    (useThemePreference as any).mockReturnValue({
      theme: 'light',
    });
    render(<HeroPanel />);
    const panel = screen.getByTestId('dashboard-preview');
    expect(panel).toHaveClass('bg-[rgba(255,255,255,0.72)]');
    expect(screen.getByText(/Calm Broadcast/i)).toBeInTheDocument();
  });

  it('renders correctly in dark mode', () => {
    (useThemePreference as any).mockReturnValue({
      theme: 'dark',
    });
    render(<HeroPanel />);
    const panel = screen.getByTestId('dashboard-preview');
    expect(panel).toHaveClass('bg-[rgba(12,10,9,0.85)]');
  });
});
