import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Bell, Radio, FileText, Users, ScrollText } from 'lucide-react';

export const NotificationsNav: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { path: '/notifications/rules', label: 'Правила', icon: <Bell className="w-4 h-4" /> },
    { path: '/notifications/channels', label: 'Каналы', icon: <Radio className="w-4 h-4" /> },
    { path: '/notifications/templates', label: 'Шаблоны', icon: <FileText className="w-4 h-4" /> },
    { path: '/notifications/recipients', label: 'Получатели', icon: <Users className="w-4 h-4" /> },
    { path: '/notifications/logs', label: 'Журнал', icon: <ScrollText className="w-4 h-4" /> },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="mb-6 border-b border-[color:var(--color-border)]">
      <nav className="-mb-px flex space-x-4 overflow-x-auto" aria-label="Tabs">
        {navItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`
              group inline-flex items-center gap-2 border-b-2 px-1 py-4 text-sm font-medium whitespace-nowrap
              ${
                isActive(item.path)
                  ? 'border-[color:var(--color-accent)] text-[color:var(--color-accent)]'
                  : 'border-transparent text-[color:var(--color-text-secondary)] hover:border-[color:var(--color-border-hover)] hover:text-[color:var(--color-text)]'
              }
            `}
          >
            {item.icon}
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
};
