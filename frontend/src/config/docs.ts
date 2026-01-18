/**
 * Конфигурация документации.
 * 
 * URL документации можно переопределить через переменную окружения
 * VITE_DOCS_URL, иначе используется дефолтный docs.sattva.app
 */

// URL документации (wiki)
export const DOCS_URL = import.meta.env.VITE_DOCS_URL || 'https://docs.sattva.app';

// URL разделов документации по ролям
export const DOCS_SECTIONS = {
  // Общие разделы
  home: DOCS_URL,
  quickStart: `${DOCS_URL}/quick-start`,
  faq: `${DOCS_URL}/faq`,
  
  // По ролям
  user: `${DOCS_URL}/user-guide`,
  operator: `${DOCS_URL}/operator-guide`,
  moderator: `${DOCS_URL}/moderator-guide`,
  admin: `${DOCS_URL}/admin-guide`,
  superadmin: `${DOCS_URL}/superadmin-guide`,
  
  // Функциональные разделы
  playlist: `${DOCS_URL}/features/playlist`,
  schedule: `${DOCS_URL}/features/schedule`,
  streaming: `${DOCS_URL}/features/streaming`,
  notifications: `${DOCS_URL}/features/notifications`,
  monitoring: `${DOCS_URL}/features/monitoring`,
  analytics: `${DOCS_URL}/features/analytics`,
  
  // Технические разделы
  api: `${DOCS_URL}/api`,
  deployment: `${DOCS_URL}/deployment`,
  troubleshooting: `${DOCS_URL}/troubleshooting`,
  changelog: `${DOCS_URL}/changelog`,
} as const;

// Функция для получения URL документации по роли
export function getDocsUrlForRole(role: string | undefined): string {
  const roleMap: Record<string, string> = {
    'SUPERADMIN': DOCS_SECTIONS.superadmin,
    'ADMIN': DOCS_SECTIONS.admin,
    'MODERATOR': DOCS_SECTIONS.moderator,
    'OPERATOR': DOCS_SECTIONS.operator,
    'USER': DOCS_SECTIONS.user,
  };
  
  return roleMap[role?.toUpperCase() || ''] || DOCS_SECTIONS.user;
}
