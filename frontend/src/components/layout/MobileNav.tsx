import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { 
  Menu, 
  X, 
  Home, 
  Tv, 
  ListMusic, 
  Users, 
  Settings,
  LogOut,
  CalendarDays,
  Activity,
  BarChart3,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { filterNavItems } from '../../utils/navigationHelpers';
import { isAdminLike } from '../../utils';
import { NavItem } from '../../types/navigation';

export const MobileNav: React.FC = () => {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);

  const navItems: NavItem[] = [
    { 
      path: '/dashboard', 
      label: '🏠 ' + t('nav.dashboard', 'Дашборд'), 
      icon: <Home className="w-5 h-5" /> 
    },
    { 
      path: '/channels', 
      label: '📺 ' + t('nav.channels', 'Каналы'), 
      icon: <Tv className="w-5 h-5" /> 
    },
    { 
      path: '/playlist', 
      label: '🎵 ' + t('nav.playlist', 'Плейлист'), 
      icon: <ListMusic className="w-5 h-5" /> 
    },
    { 
      path: '/schedule', 
      label: '📅 ' + t('nav.schedule', 'Расписание'), 
      icon: <CalendarDays className="w-5 h-5" /> 
    },
    { 
      path: '/admin/pending', 
      label: '👥 ' + t('nav.pendingUsers', 'Ожидающие'), 
      icon: <Users className="w-5 h-5" />,
      adminOnly: true 
    },
    { 
      path: '/admin/monitoring', 
      label: '📊 ' + t('nav.monitoring', 'Мониторинг'), 
      icon: <Activity className="w-5 h-5" />,
      adminOnly: true,
      moderatorAllowed: true,
    },
    { 
      path: '/admin/analytics', 
      label: '📈 ' + t('nav.analytics', 'Аналитика'), 
      icon: <BarChart3 className="w-5 h-5" />,
      adminOnly: true,
      moderatorAllowed: true,
    },
    { 
      path: '/admin', 
      label: '⚙️ ' + t('nav.admin', 'Админ'), 
      icon: <Settings className="w-5 h-5" />,
      adminOnly: true 
    },
  ];

  const filteredNavItems = filterNavItems(navItems, user?.role);

  const isActive = (path: string) => location.pathname === path;

  return (
    <>
      {/* Hamburger Button - visible on mobile */}
      <button
        onClick={() => setIsOpen(true)}
        className="lg:hidden p-2 rounded-lg hover:bg-[color:var(--color-surface-muted)] transition-colors"
        aria-label={t('nav.openMenu', 'Открыть меню')}
      >
        <Menu className="w-6 h-6" />
      </button>

      {/* Mobile Drawer Overlay */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={() => setIsOpen(false)}
              className="lg:hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-[60]"
            />

            {/* Drawer */}
            <motion.div
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="lg:hidden fixed inset-y-0 left-0 w-72 bg-[color:var(--color-panel)] border-r border-[color:var(--color-outline)] z-[70] flex flex-col shadow-xl"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-[color:var(--color-outline)]">
                <h2 className="font-landing-serif text-xl font-bold text-[color:var(--color-text)]">
                  Sattva
                </h2>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 rounded-lg hover:bg-[color:var(--color-surface-muted)] transition-colors"
                  aria-label={t('nav.closeMenu', 'Закрыть меню')}
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* User info */}
              {user && (
                <div className="p-4 border-b border-[color:var(--color-outline)]">
                  <div className="text-sm text-[color:var(--color-text-muted)]">
                    {t('nav.loggedInAs', 'Вы вошли как')}
                  </div>
                  <div className="font-medium text-[color:var(--color-text)] truncate">
                    {user.email}
                  </div>
                  <div className="mt-1">
                    <span
                      className={`inline-flex px-2 py-0.5 text-xs rounded-full ${
                        isAdminLike(user.role)
                          ? 'bg-purple-500/20 text-purple-400'
                          : 'bg-blue-500/20 text-blue-400'
                      }`}
                    >
                      {user.role}
                    </span>
                  </div>
                </div>
              )}

              {/* Navigation Links */}
              <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                {filteredNavItems.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setIsOpen(false)}
                    data-testid={`nav-${item.path.replace(/\//g, '')}`}
                    className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                      isActive(item.path)
                        ? 'bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)]'
                        : 'text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] hover:text-[color:var(--color-text)]'
                    }`}
                  >
                    {item.icon}
                    <span className="font-medium">{item.label}</span>
                  </Link>
                ))}
              </nav>

              {/* Footer / Logout */}
              <div className="p-4 border-t border-[color:var(--color-outline)]">
                <button
                  onClick={() => {
                    setIsOpen(false);
                    logout();
                  }}
                  className="flex items-center gap-3 w-full px-4 py-3 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors"
                >
                  <LogOut className="w-5 h-5" />
                  <span className="font-medium">{t('nav.logout', 'Выйти')}</span>
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
};
