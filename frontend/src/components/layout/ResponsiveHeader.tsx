import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { LanguageSwitcher } from '../auth/LanguageSwitcher';
import { ThemeToggle } from '../auth/ThemeToggle';
import UserBadge from '../UserBadge';
import { MobileNav } from './MobileNav';
import { DesktopNav } from './DesktopNav';
import { DEFAULT_LOGO, getUserLogo, subscribeLogoChanges } from '../../utils/branding';

export const ResponsiveHeader: React.FC = () => {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [userLogo, setUserLogo] = useState<string | undefined>(() => getUserLogo(user?.id));

  useEffect(() => {
    setUserLogo(getUserLogo(user?.id));
  }, [user?.id]);

  useEffect(() => {
    const unsub = subscribeLogoChanges((userId, logo) => {
      if (userId === user?.id) {
        setUserLogo(logo);
      }
    });
    return unsub;
  }, [user?.id]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const logoSrc = useMemo(() => userLogo || DEFAULT_LOGO, [userLogo]);

  return (
    <header className="sticky top-0 z-40 bg-[color:var(--color-surface)] border-b border-[color:var(--color-border)]">
      <div className="max-w-screen-2xl mx-auto px-3 sm:px-4 lg:px-6">
        <div className="flex items-center justify-between h-14 sm:h-16">
          {/* Mobile: Hamburger + Logo */}
          <div className="flex items-center gap-3">
            <MobileNav />
            
            {/* Logo - visible on all screens */}
            <a 
              href="/dashboard" 
              className="flex items-center gap-2 text-lg font-semibold text-[color:var(--color-text)]"
            >
              <img 
                src={logoSrc}
                alt="Sattva" 
                className="w-9 h-9"
              />
            </a>
          </div>

          {/* Desktop Navigation - center */}
          <div className="hidden lg:flex flex-1 justify-center">
            <DesktopNav />
          </div>

          {/* Right side: User info + Badge + Language + Theme + Logout */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* User info - hidden on small screens */}
            {user && (
              <div className="hidden sm:flex items-center gap-2 text-sm text-[color:var(--color-text-muted)]">
                <UserIcon className="w-4 h-4" />
                <span className="hidden md:inline truncate max-w-[120px]">
                  {user.full_name || user.email}
                </span>
              </div>
            )}

            {/* User Role Badge */}
            {user && <UserBadge role={user.role} />}

            {/* Language Switcher */}
            <LanguageSwitcher className="text-[color:var(--color-text)]" />

            {/* Theme Toggle */}
            <ThemeToggle className="text-[color:var(--color-text)]" />

            {/* Logout button */}
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-2 sm:px-3 py-2 text-sm rounded-lg text-[color:var(--color-text-muted)] hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
              title={t('auth.logout', 'Выйти')}
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">{t('auth.logout', 'Выйти')}</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
