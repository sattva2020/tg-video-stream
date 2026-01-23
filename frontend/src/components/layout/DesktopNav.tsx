import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Home, Tv, Users, Settings, CalendarDays, Activity, BarChart3, Bell, Signal, Library, BookOpen, ExternalLink, MessageSquareWarning, Key, Webhook, Globe } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { DOCS_URL } from '../../config/docs';
import { filterNavItems } from '../../utils/navigationHelpers';
import { NavItem } from '../../types/navigation';
import { UserRole } from '../../types/user';

const OPERATOR_AND_ABOVE = [UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR, UserRole.OPERATOR];

export const DesktopNav: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const location = useLocation();

  const navItems: NavItem[] = [
    { 
      path: '/dashboard', 
      label: t('nav.dashboard', 'Головна'), 
      icon: <Home className="w-4 h-4" /> 
    },
    { 
      path: '/channels', 
      label: t('nav.channels', 'Канали'), 
      icon: <Tv className="w-4 h-4" />,
      allowedRoles: OPERATOR_AND_ABOVE
    },
    { 
      path: '/user-playlists', 
      label: t('nav.myPlaylists', 'Мої плейлисти'), 
      icon: <Library className="w-4 h-4" /> 
    },
    { 
      path: '/schedule', 
      label: t('nav.schedule', 'Розклад'), 
      icon: <CalendarDays className="w-4 h-4" />,
      allowedRoles: OPERATOR_AND_ABOVE
    },
    { 
      path: '/users', 
      label: t('nav.users', 'Користувачі'), 
      icon: <Users className="w-4 h-4" />,
      adminOnly: true
    },
    { 
      path: '/notifications/rules', 
      label: t('nav.notifications', 'Сповіщення'), 
      icon: <Bell className="w-4 h-4" />,
      adminOnly: true
    },
    { 
      path: '/admin/monitoring', 
      label: t('nav.monitoring', 'Моніторинг'), 
      icon: <Activity className="w-4 h-4" />,
      adminOnly: true,
      moderatorAllowed: true,
    },
    { 
      path: '/admin/analytics', 
      label: t('nav.analytics', 'Аналітика'), 
      icon: <BarChart3 className="w-4 h-4" />,
      adminOnly: true
    },
    { 
      path: '/admin/stream-quality', 
      label: t('nav.streamQuality', 'Якість'), 
      icon: <Signal className="w-4 h-4" />,
      adminOnly: true
    },
    { 
      path: '/admin/incidents', 
      label: t('nav.incidents', 'Інциденти'), 
      icon: <MessageSquareWarning className="w-4 h-4" />,
      adminOnly: true,
      moderatorAllowed: true,
    },
    { 
      path: '/admin/settings', 
      label: t('nav.appSettings', 'API ключі'), 
      icon: <Settings className="w-4 h-4" />,
      adminOnly: true
    },
    {
      path: '/admin',
      label: t('nav.settings', 'Налаштування'),
      icon: <Settings className="w-4 h-4" />,
      adminOnly: true
    },
    {
      path: '/api-keys',
      label: t('nav.apiKeys', 'API ключі'),
      icon: <Key className="w-4 h-4" />
    },
    {
      path: '/webhooks',
      label: t('nav.webhooks', 'Webhooks'),
      icon: <Webhook className="w-4 h-4" />
    },
    {
      path: '/api-docs',
      label: t('nav.apiDocs', 'API Docs'),
      icon: <BookOpen className="w-4 h-4" />
    },
    {
      path: '/ecosystem',
      label: t('nav.ecosystem', 'Екосистема'),
      icon: <Globe className="w-4 h-4" />
    },
  ];

  const filteredNavItems = filterNavItems(navItems, user?.role);

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="hidden lg:flex items-center gap-0.5">
      {filteredNavItems.map((item) => (
        <Link
          key={item.path}
          to={item.path}
          data-testid={`nav-${item.path.replace(/\//g, '')}`}
          className={`flex items-center gap-1.5 px-2 py-2 rounded-lg text-sm font-medium transition-colors shrink-0 whitespace-nowrap ${
            isActive(item.path)
              ? 'bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)]'
              : 'text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] hover:text-[color:var(--color-text)]'
          }`}
          title={item.label}
        >
          {item.icon}
          <span className="hidden 2xl:inline whitespace-nowrap">{item.label}</span>
        </Link>
      ))}
      
      {/* Ссылка на документацию */}
      <a
        href={DOCS_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1.5 px-2 py-2 rounded-lg text-sm font-medium transition-colors shrink-0 whitespace-nowrap text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] hover:text-[color:var(--color-text)] group"
        title={t('nav.docs', 'Документация')}
      >
        <BookOpen className="w-4 h-4" />
        <span className="hidden 2xl:inline whitespace-nowrap">{t('nav.docs', 'Документация')}</span>
        <ExternalLink className="w-3 h-3 opacity-50 group-hover:opacity-100" />
      </a>
    </nav>
  );
};
