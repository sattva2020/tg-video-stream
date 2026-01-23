/**
 * Страница детальной информации об организации.
 *
 * Позволяет администраторам:
 * - Просматривать информацию об организации
 * - Управлять квотами ресурсов
 * - Настраивать лимиты и периоды
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Building2,
  Users,
  Globe,
  CheckCircle,
  XCircle,
  RefreshCw,
  Save,
  Edit,
  X,
  TrendingUp,
  HardDrive,
  Database,
  ArrowLeft,
  Clock,
  AlertTriangle,
  BarChart3,
  RotateCcw,
  Settings
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { AppLayout } from '../../components/layout';
import { client as api } from '../../api/client';
import { useToast } from '../../hooks/useToast';

// === Types ===

interface Organization {
  id: string;
  name: string;
  slug?: string;
  logo_url?: string;
  primary_color?: string;
  secondary_color?: string;
  custom_domain?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

interface Quota {
  quota_type: string;
  limit: number | null;
  current_usage: number;
  remaining: number | null;
  usage_percentage: number;
  is_exceeded: boolean;
  period: string | null;
  reset_at: string | null;
}

interface QuotasResponse {
  organization_id: string;
  quotas: Quota[];
}

// === Icons for quota types ===

const getQuotaIcon = (quotaType: string) => {
  const icons: Record<string, React.ReactNode> = {
    streams: <TrendingUp className="w-5 h-5" />,
    storage_bytes: <HardDrive className="w-5 h-5" />,
    bandwidth_bytes: <Database className="w-5 h-5" />,
    users: <Users className="w-5 h-5" />,
    api_calls: <BarChart3 className="w-5 h-5" />,
    playlists: <Clock className="w-5 h-5" />,
    scheduled_playlists: <Settings className="w-5 h-5" />
  };
  return icons[quotaType] || <Database className="w-5 h-5" />;
};

const getQuotaLabel = (quotaType: string): string => {
  const labels: Record<string, string> = {
    streams: 'Потоки',
    storage_bytes: 'Хранилище (байты)',
    bandwidth_bytes: 'Трафик (байты)',
    users: 'Пользователи',
    api_calls: 'API запросы',
    playlists: 'Плейлисты',
    scheduled_playlists: 'Запланированные плейлисты'
  };
  return labels[quotaType] || quotaType;
};

const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
};

const formatNumber = (num: number): string => {
  return new Intl.NumberFormat('ru-RU').format(num);
};

// === Component ===

const OrganizationDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const toast = useToast();

  // State
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [quotas, setQuotas] = useState<Quota[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit state
  const [editingQuota, setEditingQuota] = useState<string | null>(null);
  const [editLimit, setEditLimit] = useState<string>('');
  const [editPeriod, setEditPeriod] = useState<string>('monthly');
  const [saving, setSaving] = useState<string | null>(null);
  const [resetting, setResetting] = useState<string | null>(null);

  // === Data fetching ===

  const fetchOrganization = useCallback(async () => {
    if (!id) return;

    try {
      const response = await api.get(`/api/organizations/${id}`);
      setOrganization(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки организации');
    }
  }, [id]);

  const fetchQuotas = useCallback(async () => {
    if (!id) return;

    try {
      const response = await api.get(`/api/organizations/${id}/quotas`);
      setQuotas(response.data.quotas || []);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки квот');
    }
  }, [id]);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchOrganization(), fetchQuotas()]);
      setLoading(false);
    };
    loadData();
  }, [fetchOrganization, fetchQuotas]);

  // === Actions ===

  const handleEditQuota = (quota: Quota) => {
    setEditingQuota(quota.quota_type);
    setEditLimit(quota.limit?.toString() || '');
    setEditPeriod(quota.period || 'monthly');
  };

  const handleSaveQuota = async (quotaType: string) => {
    const limit = parseInt(editLimit, 10);
    if (isNaN(limit) || limit < 0) {
      toast.error('Лимит должен быть неотрицательным числом');
      return;
    }

    try {
      setSaving(quotaType);
      await api.put(`/api/organizations/${id}/quotas/${quotaType}`, {
        limit,
        period: editPeriod
      });
      setEditingQuota(null);
      toast.success(`Квота ${getQuotaLabel(quotaType)} обновлена`);
      await fetchQuotas();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Ошибка обновления квоты');
    } finally {
      setSaving(null);
    }
  };

  const handleResetQuota = async (quotaType: string) => {
    if (!confirm(`Сбросить использование квоты ${getQuotaLabel(quotaType)}?`)) {
      return;
    }

    try {
      setResetting(quotaType);
      await api.post(`/api/organizations/${id}/quotas/${quotaType}/reset`);
      toast.success(`Квота ${getQuotaLabel(quotaType)} сброшена`);
      await fetchQuotas();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Ошибка сброса квоты');
    } finally {
      setResetting(null);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  // === Render ===

  if (loading) {
    return (
      <AppLayout>
        <div className="flex items-center justify-center min-h-[400px]">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      </AppLayout>
    );
  }

  if (!organization) {
    return (
      <AppLayout>
        <div className="container mx-auto max-w-6xl">
          <div className="text-center py-16">
            <XCircle className="w-16 h-16 mx-auto mb-4 text-gray-400" />
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
              Организация не найдена
            </h2>
            <button
              onClick={() => navigate('/admin/organizations')}
              className="text-blue-500 hover:text-blue-600"
            >
              Вернуться к списку
            </button>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="container mx-auto max-w-6xl">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => navigate('/admin/organizations')}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </button>
          <div className="flex items-center gap-3 flex-1">
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center text-white"
              style={{
                background: organization.primary_color
                  ? `linear-gradient(135deg, ${organization.primary_color}, ${organization.secondary_color || organization.primary_color})`
                  : 'linear-gradient(135deg, #3b82f6, #1d4ed8)'
              }}
            >
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {organization.name}
              </h1>
              <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                {organization.is_active ? (
                  <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                    <CheckCircle className="w-4 h-4" />
                    Активна
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
                    <XCircle className="w-4 h-4" />
                    Неактивна
                  </span>
                )}
              </div>
            </div>
          </div>
          <button
            onClick={() => {
              fetchOrganization();
              fetchQuotas();
            }}
            className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Обновить
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-700 dark:text-red-400">
            <XCircle className="w-5 h-5 flex-shrink-0" />
            {error}
            <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-700">×</button>
          </div>
        )}

        {/* Organization Info */}
        <div className="mb-8 p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <Building2 className="w-5 h-5" />
            Информация об организации
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-500 dark:text-gray-400">Название</label>
              <p className="font-medium text-gray-900 dark:text-white">{organization.name}</p>
            </div>
            {organization.slug && (
              <div>
                <label className="text-sm text-gray-500 dark:text-gray-400">Slug</label>
                <p className="font-medium text-gray-900 dark:text-white flex items-center gap-1.5">
                  <Globe className="w-4 h-4" />
                  {organization.slug}
                </p>
              </div>
            )}
            {organization.custom_domain && (
              <div>
                <label className="text-sm text-gray-500 dark:text-gray-400">Кастомный домен</label>
                <p className="font-medium text-gray-900 dark:text-white">{organization.custom_domain}</p>
              </div>
            )}
            <div>
              <label className="text-sm text-gray-500 dark:text-gray-400">Создана</label>
              <p className="font-medium text-gray-900 dark:text-white">{formatDate(organization.created_at)}</p>
            </div>
            <div>
              <label className="text-sm text-gray-500 dark:text-gray-400">Обновлена</label>
              <p className="font-medium text-gray-900 dark:text-white">{formatDate(organization.updated_at)}</p>
            </div>
          </div>
        </div>

        {/* Quotas Section */}
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Квоты ресурсов
          </h2>

          {quotas.length === 0 ? (
            <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
              <Database className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              <p className="text-gray-500 dark:text-gray-400">Нет настроенных квот</p>
            </div>
          ) : (
            <div className="space-y-4">
              {quotas.map((quota) => {
                const isStorageOrBandwidth = ['storage_bytes', 'bandwidth_bytes'].includes(quota.quota_type);
                const displayUsage = isStorageOrBandwidth ? formatBytes(quota.current_usage) : formatNumber(quota.current_usage);
                const displayLimit = quota.limit !== null
                  ? (isStorageOrBandwidth ? formatBytes(quota.limit) : formatNumber(quota.limit))
                  : 'Безлимит';
                const displayRemaining = quota.remaining !== null
                  ? (isStorageOrBandwidth ? formatBytes(quota.remaining) : formatNumber(quota.remaining))
                  : '∞';

                return (
                  <div
                    key={quota.quota_type}
                    className="p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm"
                  >
                    {/* Quota Header */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${
                          quota.is_exceeded
                            ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                            : quota.usage_percentage > 80
                            ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400'
                            : 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'
                        }`}>
                          {getQuotaIcon(quota.quota_type)}
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                            {getQuotaLabel(quota.quota_type)}
                            {quota.is_exceeded && (
                              <span className="text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 px-2 py-0.5 rounded flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3" />
                                Превышено
                              </span>
                            )}
                            {quota.period && (
                              <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded">
                                {quota.period}
                              </span>
                            )}
                          </h3>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {displayUsage} из {displayLimit} использовано
                          </p>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2">
                        {editingQuota !== quota.quota_type && (
                          <>
                            <button
                              onClick={() => handleEditQuota(quota)}
                              className="p-2 text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                              title="Изменить лимит"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleResetQuota(quota.quota_type)}
                              disabled={resetting === quota.quota_type}
                              className="p-2 text-gray-400 hover:text-orange-500 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded-lg transition-colors disabled:opacity-50"
                              title="Сбросить использование"
                            >
                              {resetting === quota.quota_type ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                              ) : (
                                <RotateCcw className="w-4 h-4" />
                              )}
                            </button>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Progress Bar */}
                    {quota.limit !== null && (
                      <div className="mb-4">
                        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              quota.is_exceeded
                                ? 'bg-red-500'
                                : quota.usage_percentage > 80
                                ? 'bg-yellow-500'
                                : 'bg-green-500'
                            }`}
                            style={{ width: `${Math.min(quota.usage_percentage, 100)}%` }}
                          />
                        </div>
                        <div className="flex justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
                          <span>{quota.usage_percentage.toFixed(1)}% использовано</span>
                          <span>Осталось: {displayRemaining}</span>
                        </div>
                      </div>
                    )}

                    {/* Edit Form */}
                    {editingQuota === quota.quota_type && (
                      <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg space-y-3">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Новый лимит
                          </label>
                          <input
                            type="number"
                            min="0"
                            value={editLimit}
                            onChange={(e) => setEditLimit(e.target.value)}
                            placeholder="Введите новый лимит"
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Период
                          </label>
                          <select
                            value={editPeriod}
                            onChange={(e) => setEditPeriod(e.target.value)}
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          >
                            <option value="monthly">Ежемесячно</option>
                            <option value="daily">Ежедневно</option>
                            <option value="hourly">Ежечасно</option>
                            <option value="">Пожизненно</option>
                          </select>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleSaveQuota(quota.quota_type)}
                            disabled={saving === quota.quota_type}
                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                          >
                            {saving === quota.quota_type ? (
                              <RefreshCw className="w-4 h-4 animate-spin" />
                            ) : (
                              <Save className="w-4 h-4" />
                            )}
                            Сохранить
                          </button>
                          <button
                            onClick={() => {
                              setEditingQuota(null);
                              setEditLimit('');
                              setEditPeriod('monthly');
                            }}
                            className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors"
                          >
                            <X className="w-4 h-4" />
                            Отмена
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Reset Info */}
                    {quota.reset_at && (
                      <div className="mt-3 text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Сброс: {formatDate(quota.reset_at)}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
};

export default OrganizationDetail;
