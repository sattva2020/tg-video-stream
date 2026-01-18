/**
 * IncidentsPage - страница управления инцидентами для админов
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { 
  Incident, 
  IncidentStatus, 
  IncidentPriority, 
  IncidentCategory 
} from '../../types/incident';
import { AppLayout } from '../../components/layout';

// API functions
const fetchIncidents = async (params: {
  status?: IncidentStatus;
  priority?: IncidentPriority;
  search?: string;
  page?: number;
}) => {
  const searchParams = new URLSearchParams();
  if (params.status) searchParams.set('status', params.status);
  if (params.priority) searchParams.set('priority', params.priority);
  if (params.search) searchParams.set('search', params.search);
  if (params.page) searchParams.set('page', params.page.toString());
  
  const response = await fetch(`/api/incidents?${searchParams}`);
  if (!response.ok) throw new Error('Failed to fetch incidents');
  return response.json();
};

const updateIncident = async ({ id, ...data }: { id: string } & Partial<Incident>) => {
  const response = await fetch(`/api/incidents/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to update incident');
  return response.json();
};

// Status badge component
const StatusBadge = ({ status }: { status: IncidentStatus }) => {
  const colors = {
    new: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
    in_progress: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
    waiting_user: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
    resolved: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
    closed: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
    duplicate: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
  };
  
  const labels = {
    new: 'Новый',
    in_progress: 'В работе',
    waiting_user: 'Ожидает ответа',
    resolved: 'Решён',
    closed: 'Закрыт',
    duplicate: 'Дубликат',
  };
  
  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[status]}`}>
      {labels[status]}
    </span>
  );
};

// Priority badge
const PriorityBadge = ({ priority }: { priority: IncidentPriority }) => {
  const colors = {
    low: 'text-gray-500',
    medium: 'text-blue-500',
    high: 'text-orange-500',
    critical: 'text-red-500',
  };
  
  const icons = {
    low: '○',
    medium: '◐',
    high: '●',
    critical: '🔥',
  };
  
  return (
    <span className={`font-medium ${colors[priority]}`} title={priority}>
      {icons[priority]}
    </span>
  );
};

// Category badge
const CategoryBadge = ({ category }: { category?: IncidentCategory }) => {
  if (!category) return null;
  
  const labels: Record<IncidentCategory, string> = {
    bug: '🐛 Баг',
    feature: '✨ Фича',
    question: '❓ Вопрос',
    performance: '⚡ Производительность',
    security: '🔒 Безопасность',
    ui_ux: '🎨 UI/UX',
    other: '📋 Прочее',
  };
  
  return (
    <span className="text-xs text-gray-500 dark:text-gray-400">
      {labels[category]}
    </span>
  );
};

export function IncidentsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  
  const [filters, setFilters] = useState({
    status: undefined as IncidentStatus | undefined,
    priority: undefined as IncidentPriority | undefined,
    search: '',
    page: 1,
  });
  
  const [selectedIncident, setSelectedIncident] = useState<string | null>(null);
  
  // Fetch incidents
  const { data, isLoading, error } = useQuery({
    queryKey: ['incidents', filters],
    queryFn: () => fetchIncidents(filters),
  });
  
  // Update mutation
  const updateMutation = useMutation({
    mutationFn: updateIncident,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
  
  // Handle status change
  const handleStatusChange = (id: string, status: IncidentStatus) => {
    updateMutation.mutate({ id, status });
  };
  
  if (error) {
    return (
      <div className="p-6 text-center text-red-500">
        Ошибка загрузки инцидентов: {(error as Error).message}
      </div>
    );
  }
  
  return (
    <AppLayout>
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          🎫 Инциденты и обращения
        </h1>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span>Всего: {data?.total || 0}</span>
        </div>
      </div>
      
      {/* Filters */}
      <div className="flex flex-wrap gap-4 p-4 bg-white dark:bg-gray-800 rounded-lg shadow">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <input
            type="text"
            placeholder="Поиск по заголовку или описанию..."
            value={filters.search}
            onChange={(e) => setFilters(f => ({ ...f, search: e.target.value, page: 1 }))}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                     bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          />
        </div>
        
        {/* Status filter */}
        <select
          value={filters.status || ''}
          onChange={(e) => setFilters(f => ({ 
            ...f, 
            status: e.target.value as IncidentStatus || undefined, 
            page: 1 
          }))}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                   bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="">Все статусы</option>
          <option value="new">Новые</option>
          <option value="in_progress">В работе</option>
          <option value="waiting_user">Ожидают ответа</option>
          <option value="resolved">Решённые</option>
          <option value="closed">Закрытые</option>
        </select>
        
        {/* Priority filter */}
        <select
          value={filters.priority || ''}
          onChange={(e) => setFilters(f => ({ 
            ...f, 
            priority: e.target.value as IncidentPriority || undefined, 
            page: 1 
          }))}
          className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                   bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
        >
          <option value="">Все приоритеты</option>
          <option value="critical">🔥 Критический</option>
          <option value="high">● Высокий</option>
          <option value="medium">◐ Средний</option>
          <option value="low">○ Низкий</option>
        </select>
      </div>
      
      {/* Incidents table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">
            <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-2" />
            Загрузка...
          </div>
        ) : data?.items?.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            Инциденты не найдены
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Приоритет
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Заголовок
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Категория
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Статус
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Создан
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Логи
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Действия
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {data?.items?.map((incident: any) => (
                <tr 
                  key={incident.id}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer"
                  onClick={() => setSelectedIncident(incident.id)}
                >
                  <td className="px-4 py-3 text-center">
                    <PriorityBadge priority={incident.priority} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900 dark:text-white">
                      {incident.title}
                    </div>
                    {incident.assignedToName && (
                      <div className="text-xs text-gray-500">
                        → {incident.assignedToName}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <CategoryBadge category={incident.category} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={incident.status} />
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {new Date(incident.createdAt).toLocaleDateString('ru-RU', {
                      day: 'numeric',
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {incident.logsCount > 0 && (
                      <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                        {incident.logsCount}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <select
                      value={incident.status}
                      onChange={(e) => {
                        e.stopPropagation();
                        handleStatusChange(incident.id, e.target.value as IncidentStatus);
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 rounded
                               bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                    >
                      <option value="new">Новый</option>
                      <option value="in_progress">В работе</option>
                      <option value="waiting_user">Ожидает ответа</option>
                      <option value="resolved">Решён</option>
                      <option value="closed">Закрыт</option>
                      <option value="duplicate">Дубликат</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        
        {/* Pagination */}
        {data && data.totalPages > 1 && (
          <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <div className="text-sm text-gray-500">
              Страница {data.page} из {data.totalPages}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setFilters(f => ({ ...f, page: f.page - 1 }))}
                disabled={filters.page <= 1}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded
                         disabled:opacity-50 disabled:cursor-not-allowed
                         hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                ←
              </button>
              <button
                onClick={() => setFilters(f => ({ ...f, page: f.page + 1 }))}
                disabled={filters.page >= data.totalPages}
                className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded
                         disabled:opacity-50 disabled:cursor-not-allowed
                         hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
    </AppLayout>
  );
}

export default IncidentsPage;
