import { Moon, Sun } from 'lucide-react';
import clsx from 'clsx';
import { useThemePreference } from '../../hooks/useThemePreference';

const themes = [
  { id: 'light', icon: Sun, label: 'Светлая' },
  { id: 'dark', icon: Moon, label: 'Тёмная' },
] as const;

const ThemeToggle = () => {
  const { theme, toggleTheme } = useThemePreference();

  return (
    <div className="theme-toggle-shell" role="group" aria-label="Переключатель темы">
      {themes.map(({ id, icon: Icon, label }) => (
        <button
          key={id}
          type="button"
          className={clsx('theme-toggle-btn', theme === id && 'is-active')}
          aria-pressed={theme === id}
          aria-label={label}
          onClick={() => {
            if (theme !== id) {
              toggleTheme();
            }
          }}
        >
          <Icon aria-hidden />
        </button>
      ))}
    </div>
  );
};

export default ThemeToggle;
