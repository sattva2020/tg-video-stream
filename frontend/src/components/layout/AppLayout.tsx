import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Menu } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { MobileNav } from './MobileNav';
import { LanguageSwitcher } from '../auth/LanguageSwitcher';
import { ThemeToggle } from '../auth/ThemeToggle';
import UserBadge from '../UserBadge';
import { useAuth } from '../../context/AuthContext';
import OfflineBanner from '../pwa/OfflineBanner';
import PWAInstallPrompt from '../pwa/PWAInstallPrompt';
import InstallButton from '../pwa/InstallButton';

interface AppLayoutProps {
  children: React.ReactNode;
  /** Заголовок страницы для мобильного header */
  title?: string;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children, title }) => {
  const { t } = useTranslation();
  const { user } = useAuth();
  
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebar_collapsed');
    return saved === 'true';
  });

  // Sync with sidebar state
  useEffect(() => {
    const handleStorage = () => {
      const saved = localStorage.getItem('sidebar_collapsed');
      setIsSidebarCollapsed(saved === 'true');
    };
    
    window.addEventListener('storage', handleStorage);
    
    // Also poll for changes (for same-tab updates)
    const interval = setInterval(() => {
      const saved = localStorage.getItem('sidebar_collapsed');
      setIsSidebarCollapsed(saved === 'true');
    }, 100);
    
    return () => {
      window.removeEventListener('storage', handleStorage);
      clearInterval(interval);
    };
  }, []);

  return (
    <div className="min-h-screen bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
      {/* PWA Components */}
      <OfflineBanner />
      <PWAInstallPrompt />

      {/* Desktop Sidebar */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* Mobile Header */}
      <header className="lg:hidden sticky top-0 z-30 bg-[color:var(--color-surface)] border-b border-[color:var(--color-border)]">
        <div className="flex items-center justify-between h-14 px-4">
          <div className="flex items-center gap-3">
            <MobileNav />
            {title && (
              <h1 className="text-lg font-semibold text-[color:var(--color-text)] truncate">
                {title}
              </h1>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            {user && <UserBadge role={user.role} />}
            <InstallButton variant="ghost" size="sm" />
            <LanguageSwitcher className="text-[color:var(--color-text)]" />
            <ThemeToggle className="text-[color:var(--color-text)]" />
          </div>
        </div>
      </header>

      {/* Main content */}
      <main 
        className={`transition-all duration-300 ${
          isSidebarCollapsed ? 'lg:ml-16' : 'lg:ml-64'
        }`}
      >
        {/* Desktop top bar with user info */}
        <div className="hidden lg:flex items-center justify-end gap-3 h-16 px-6 border-b border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
          {user && <UserBadge role={user.role} />}
          <InstallButton variant="ghost" size="sm" />
          <LanguageSwitcher className="text-[color:var(--color-text)]" />
          <ThemeToggle className="text-[color:var(--color-text)]" />
        </div>

        {/* Page content */}
        <div className="p-4 sm:p-6 lg:p-8">
          {children}
        </div>
      </main>
    </div>
  );
};

export default AppLayout;
