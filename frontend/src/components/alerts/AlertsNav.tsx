import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Bell, ScrollText, Layers } from 'lucide-react';

export const AlertsNav: React.FC = () => {
  const location = useLocation();

  const navItems = [
    { path: '/alerts/rules', label: 'Rules', icon: <Bell className="w-4 h-4" /> },
    { path: '/alerts/history', label: 'History', icon: <ScrollText className="w-4 h-4" /> },
    { path: '/alerts/groups', label: 'Groups', icon: <Layers className="w-4 h-4" /> },
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
