import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeToggle } from '../../src/components/auth/ThemeToggle';
import * as ThemeHooks from '../../src/hooks/useThemePreference';

// Mock the hook
vi.mock('../../src/hooks/useThemePreference', () => ({
  useThemePreference: vi.fn(),
}));

describe('ThemeToggle', () => {
  it('renders correctly', () => {
    (ThemeHooks.useThemePreference as any).mockReturnValue({
      theme: 'light',
      toggleTheme: vi.fn(),
    });

    render(<ThemeToggle />);
    expect(screen.getByTestId('theme-toggle')).toBeInTheDocument();
  });

  it('calls toggleTheme on click', () => {
    const toggleThemeMock = vi.fn();
    (ThemeHooks.useThemePreference as any).mockReturnValue({
      theme: 'light',
      toggleTheme: toggleThemeMock,
    });

    render(<ThemeToggle />);
    const button = screen.getByTestId('theme-toggle');
    fireEvent.click(button);

    expect(toggleThemeMock).toHaveBeenCalledTimes(1);
  });

  it('displays correct icon for light mode', () => {
    (ThemeHooks.useThemePreference as any).mockReturnValue({
      theme: 'light',
      toggleTheme: vi.fn(),
    });

    render(<ThemeToggle />);
    expect(screen.getByLabelText(/switch to dark mode/i)).toBeInTheDocument();
  });

  it('displays correct icon for dark mode', () => {
    (ThemeHooks.useThemePreference as any).mockReturnValue({
      theme: 'dark',
      toggleTheme: vi.fn(),
    });

    render(<ThemeToggle />);
    expect(screen.getByLabelText(/switch to light mode/i)).toBeInTheDocument();
  });
});
