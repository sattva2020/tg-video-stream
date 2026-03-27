import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import {
  Home,
  Tv,
  Users,
  Settings,
  LogOut,
  CalendarDays,
  Activity,
  BarChart3,
  Bell,
  Signal,
  Library,
  BookOpen,
  ExternalLink,
  MessageSquareWarning,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Key,
  Gauge,
  FileText,
  LayoutDashboard,
  AlertCircle,
} from 'lucide-react';
import { DOCS_URL } from '../../config/docs';
import { useAuth } from '../../context/AuthContext';
import { filterNavItems } from '../../utils/navigationHelpers';
import { NavItem } from '../../types/navigation';
import { UserRole } from '../../types/user';
import { DEFAULT_LOGO, getUserLogo, subscribeLogoChanges } from '../../utils/branding';

const OPERATOR_AND_ABOVE = [UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR, UserRole.OPERATOR];

interface NavGroup {
  id: string;
  label: string;
  icon: React.ReactNode;
  items: NavItem[];
}

export const Sidebar: React.FC = () => {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  
  const [isCollapsed, setIsCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebar_collapsed');
    return saved === 'true';
  });
  
  const [expandedGroups, setExpandedGroups] = useState<string[]>(() => {
    const saved = localStorage.getItem('sidebar_expanded_groups');
    return saved ? JSON.parse(saved) : ['main', 'monitoring', 'admin'];
  });

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

  useEffect(() => {
    localStorage.setItem('sidebar_collapsed', String(isCollapsed));
  }, [isCollapsed]);

  useEffect(() => {
    localStorage.setItem('sidebar_expanded_groups', JSON.stringify(expandedGroups));
  }, [expandedGroups]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => 
      prev.includes(groupId) 
        ? prev.filter(id => id !== groupId)
        : [...prev, groupId]
    );
  };

  const navGroups: NavGroup[] = [
    {
      id: 'main',
      label: t('nav.group.main', 'Основное'),
      icon: <LayoutDashboard className="w-4 h-4" />,
      items: [
        { 
          path: '/dashboard', 
          label: t('nav.dashboard', 'Главная'), 
          icon: <Home className="w-5 h-5" /> 
        },
        { 
          path: '/user-playlists', 
          label: t('nav.myPlaylists', 'Мои треки'), 
          icon: <Library className="w-5 h-5" /> 
        },
      ]
    },
    {
      id: 'content',
      label: t('nav.group.content', 'Контент'),
      icon: <Tv className="w-4 h-4" />,
      items: [
        { 
          path: '/channels', 
          label: t('nav.channels', 'Каналы'), 
          icon: <Tv className="w-5 h-5" />,
          allowedRoles: OPERATOR_AND_ABOVE
        },
        { 
          path: '/schedule', 
          label: t('nav.schedule', 'График'), 
          icon: <CalendarDays className="w-5 h-5" />,
          allowedRoles: OPERATOR_AND_ABOVE
        },
      ]
    },
    {
      id: 'monitoring',
      label: t('nav.group.monitoring', 'Мониторинг'),
      icon: <Activity className="w-4 h-4" />,
      items: [
        { 
          path: '/admin/monitoring', 
          label: t('nav.monitoring', 'Монитор'), 
          icon: <Activity className="w-5 h-5" />,
          adminOnly: true,
          moderatorAllowed: true,
        },
        { 
          path: '/admin/analytics', 
          label: t('nav.analytics', 'Статистика'), 
          icon: <BarChart3 className="w-5 h-5" />,
          adminOnly: true,
          moderatorAllowed: true,
        },
        { 
          path: '/admin/stream-quality', 
          label: t('nav.streamQuality', 'Качество'), 
          icon: <Signal className="w-5 h-5" />,
          adminOnly: true,
        },
        { 
          path: '/admin/incidents', 
          label: t('nav.incidents', 'Инциденты'), 
          icon: <MessageSquareWarning className="w-5 h-5" />,
          adminOnly: true,
          moderatorAllowed: true,
        },
      ]
    },
    {
      id: 'admin',
      label: t('nav.group.admin', 'Администрирование'),
      icon: <Settings className="w-4 h-4" />,
      items: [
        {
          path: '/users',
          label: t('nav.users', 'Юзеры'),
          icon: <Users className="w-5 h-5" />,
          adminOnly: true
        },
        {
          path: '/notifications/rules',
          label: t('nav.notifications', 'Уведомления'),
          icon: <Bell className="w-5 h-5" />,
          adminOnly: true
        },
        {
          path: '/alerts/rules',
          label: t('nav.alerts', 'Алерты'),
          icon: <AlertCircle className="w-5 h-5" />,
          adminOnly: true
        },
        {
          path: '/admin/settings',
          label: t('nav.appSettings', 'API ключи'),
          icon: <Key className="w-5 h-5" />,
          adminOnly: true
        },
        {
          path: '/settings',
          label: t('nav.settings', 'Настройки'),
          icon: <Settings className="w-5 h-5" />,
        },
      ]
    },
  ];

  const isActive = (path: string) => location.pathname === path;

  const logoSrc = userLogo || DEFAULT_LOGO;

  // Filter items in each group
  const filteredGroups = navGroups.map(group => ({
    ...group,
    items: filterNavItems(group.items, user?.role)
  })).filter(group => group.items.length > 0);

  return (
    <aside 
      className={`fixed left-0 top-0 h-full bg-[color:var(--color-panel)] border-r border-[color:var(--color-border)] z-40 flex flex-col transition-all duration-300 ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Logo */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-[color:var(--color-border)]">
        <Link to="/dashboard" className="flex items-center gap-3">
          <img 
            src={logoSrc}
            alt="Sattva" 
            className="w-8 h-8 shrink-0"
          />
          <AnimatePresence>
            {!isCollapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="font-semibold text-lg text-[color:var(--color-text)] whitespace-nowrap overflow-hidden"
              >
                Sattva
              </motion.span>
            )}
          </AnimatePresence>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2">
        {filteredGroups.map((group) => (
          <div key={group.id} className="mb-2">
            {/* Group header */}
            {!isCollapsed && (
              <button
                onClick={() => toggleGroup(group.id)}
                className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold uppercase tracking-wider text-[color:var(--color-text-muted)] hover:text-[color:var(--color-text)] transition-colors"
              >
                <span className="flex items-center gap-2">
                  {group.icon}
                  {group.label}
                </span>
                <ChevronDown 
                  className={`w-4 h-4 transition-transform ${
                    expandedGroups.includes(group.id) ? 'rotate-180' : ''
                  }`} 
                />
              </button>
            )}

            {/* Group items */}
            <AnimatePresence initial={false}>
              {(isCollapsed || expandedGroups.includes(group.id)) && (
                <motion.div
                  initial={isCollapsed ? false : { height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  {group.items.map((item) => (
                    <Link
                      key={item.path}
                      to={item.path}
                      title={isCollapsed ? item.label : undefined}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                        isActive(item.path)
                          ? 'bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] shadow-sm'
                          : 'text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] hover:text-[color:var(--color-text)]'
                      } ${isCollapsed ? 'justify-center' : ''}`}
                    >
                      <span className="shrink-0">{item.icon}</span>
                      <AnimatePresence>
                        {!isCollapsed && (
                          <motion.span
                            initial={{ opacity: 0, width: 0 }}
                            animate={{ opacity: 1, width: 'auto' }}
                            exit={{ opacity: 0, width: 0 }}
                            className="whitespace-nowrap overflow-hidden"
                          >
                            {item.label}
                          </motion.span>
                        )}
                      </AnimatePresence>
                    </Link>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ))}

        {/* Documentation link */}
        <div className="mt-4 pt-4 border-t border-[color:var(--color-border)]">
          <a
            href={DOCS_URL}
            target="_blank"
            rel="noopener noreferrer"
            title={isCollapsed ? t('nav.docs', 'Документация') : undefined}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] hover:text-[color:var(--color-text)] transition-all group ${
              isCollapsed ? 'justify-center' : ''
            }`}
          >
            <BookOpen className="w-5 h-5 shrink-0" />
            <AnimatePresence>
              {!isCollapsed && (
                <motion.span
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: 'auto' }}
                  exit={{ opacity: 0, width: 0 }}
                  className="flex items-center gap-2 whitespace-nowrap overflow-hidden"
                >
                  {t('nav.docs', 'Документация')}
                  <ExternalLink className="w-3 h-3 opacity-50 group-hover:opacity-100" />
                </motion.span>
              )}
            </AnimatePresence>
          </a>
        </div>
      </nav>

      {/* Bottom section: User + Logout + Collapse toggle */}
      <div className="border-t border-[color:var(--color-border)] p-2">
        {/* User info */}
        {user && !isCollapsed && (
          <div className="px-3 py-2 mb-2">
            <div className="text-sm font-medium text-[color:var(--color-text)] truncate">
              {user.full_name || user.email}
            </div>
            <div className="text-xs text-[color:var(--color-text-muted)] capitalize">
              {user.role}
            </div>
          </div>
        )}

        {/* Logout */}
        <button
          onClick={handleLogout}
          title={isCollapsed ? t('auth.logout', 'Выйти') : undefined}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-[color:var(--color-text-muted)] hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors ${
            isCollapsed ? 'justify-center' : ''
          }`}
        >
          <LogOut className="w-5 h-5 shrink-0" />
          <AnimatePresence>
            {!isCollapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                {t('auth.logout', 'Выйти')}
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {/* Collapse toggle */}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 mt-2 rounded-lg text-sm text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-muted)] hover:text-[color:var(--color-text)] transition-colors"
          title={isCollapsed ? t('nav.expand', 'Развернуть') : t('nav.collapse', 'Свернуть')}
        >
          {isCollapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <>
              <ChevronLeft className="w-5 h-5" />
              <span>{t('nav.collapse', 'Свернуть')}</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
};
