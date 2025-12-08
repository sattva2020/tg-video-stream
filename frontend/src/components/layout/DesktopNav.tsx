import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Home, Tv, ListMusic, Users, Settings, CalendarDays, Activity, BarChart3 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { filterNavItems } from '../../utils/navigationHelpers';
import { NavItem } from '../../types/navigation';

export const DesktopNav: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const location = useLocation();

  const navItems: NavItem[] = [
    { 
      path: '/dashboard', 
      label: '🏠 ' + t('nav.dashboard', 'Дашборд'), 
      icon: <Home className="w-4 h-4" /> 
    },
    { 
      path: '/channels', 
      label: '📺 ' + t('nav.channels', 'Каналы'), 
      icon: <Tv className="w-4 h-4" /> 
    },
    { 
      path: '/playlist', 
      label: '🎵 ' + t('nav.playlist', 'Плейлист'), 
      icon: <ListMusic className="w-4 h-4" /> 
    },
    { 
      path: '/schedule', 
      label: '📅 ' + t('nav.schedule', 'Расписание'), 
      icon: <CalendarDays className="w-4 h-4" /> 
    },
    { 
      path: '/admin/pending', 
      label: '👥 ' + t('nav.pendingUsers', 'Ожидающие'), 
      icon: <Users className="w-4 h-4" />,
      adminOnly: true 
    },
    { 
      path: '/admin/monitoring', 
      label: '📊 ' + t('nav.monitoring', 'Мониторинг'), 
      icon: <Activity className="w-4 h-4" />,
      adminOnly: true,
      moderatorAllowed: true,
    },
    { 
      path: '/admin/analytics', 
      label: '📈 ' + t('nav.analytics', 'Аналитика'), 
      icon: <BarChart3 className="w-4 h-4" />,
      adminOnly: true,
      moderatorAllowed: true,
    },
    { 
      path: '/admin', 
      label: '⚙️ ' + t('nav.admin', 'Админ'), 
      icon: <Settings className="w-4 h-4" />,
      adminOnly: true 
    },
  ];

  const filteredNavItems = filterNavItems(navItems, user?.role);

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="hidden lg:flex items-center gap-1">
      {filteredNavItems.map((item) => (
        <Link
          key={item.path}
          to={item.path}
          data-testid={`nav-${item.path.replace(/\//g, '')}`}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            isActive(item.path)
              ? 'bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)]'
              : 'text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] hover:text-[color:var(--color-text)]'
          }`}
        >
          {item.icon}
          <span className="hidden xl:inline">{item.label}</span>
        </Link>
      ))}
    </nav>
  );
};
