import React from 'react';
import { useThemePreference } from '../../hooks/useThemePreference';
import { Sun, Moon } from 'lucide-react';
import { clsx } from 'clsx';

interface ThemeToggleProps {
  className?: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ className }) => {
  const { theme, toggleTheme } = useThemePreference();

  return (
    <button
      onClick={toggleTheme}
      data-testid="theme-toggle"
      aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
      className={clsx(
        "p-2 rounded-full transition-colors hover:bg-black/5 dark:hover:bg-white/10",
        className || "text-[#1E1A19] dark:text-[#F7E2C6]"
      )}
    >
      {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
    </button>
  );
};
