import React, { useCallback, useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { adminApi, Organization } from '../../api/admin';
import { useToast } from '../../hooks/useToast';
import { Skeleton } from '../../components/ui/Skeleton';
import { AppLayout } from '../../components/layout';
import { useTranslation } from 'react-i18next';
import { Building2, Users, Globe, CheckCircle, XCircle, RefreshCw, Clock, Settings } from 'lucide-react';

const SkeletonOrgItem: React.FC = () => (
  <div className="bg-[color:var(--color-surface)] rounded-xl border border-[color:var(--color-border)] p-4 sm:p-6">
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div className="flex items-center gap-4">
        <Skeleton className="h-12 w-12 rounded-xl" />
        <div>
          <Skeleton className="h-5 w-40 mb-2" />
          <Skeleton className="h-4 w-32" />
        </div>
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-10 w-28 rounded-lg" />
        <Skeleton className="h-10 w-28 rounded-lg" />
      </div>
    </div>
  </div>
);

const Organizations: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.listOrganizations();
      setOrganizations(data?.items || []);
    } catch (err) {
      toastRef.current.error(t('organizations.loadError', 'Не удалось загрузить список организаций'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  const onToggleStatus = async (org: Organization) => {
    if (!window.confirm(t('organizations.toggleConfirm', {
      name: org.name,
      action: org.is_active ? t('organizations.deactivate', 'деактивировать') : t('organizations.activate', 'активировать'),
      defaultValue: `Вы уверены, что хотите ${org.is_active ? 'деактивировать' : 'активировать'} организацию ${org.name}?`
    }))) {
      return;
    }
    setActionLoading(org.id + '_toggle');
    try {
      if (org.is_active) {
        await adminApi.deactivateOrganization(org.id);
        toast.success(t('organizations.deactivateSuccess', { name: org.name, defaultValue: `Организация ${org.name} деактивирована` }));
      } else {
        await adminApi.updateOrganization(org.id, { is_active: true });
        toast.success(t('organizations.activateSuccess', { name: org.name, defaultValue: `Организация ${org.name} активирована` }));
      }
      load();
    } catch (err) {
      toast.error(t('organizations.toggleError', { name: org.name, defaultValue: `Не удалось изменить статус организации ${org.name}` }));
    } finally {
      setActionLoading(null);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '';
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

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-blue-100 dark:bg-blue-900/30 rounded-xl">
              <Building2 className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-[color:var(--color-text)]">
                {t('organizations.title', 'Организации')}
              </h1>
              <p className="text-sm text-[color:var(--color-text-secondary)]">
                {t('organizations.subtitle', 'Управление организациями и их настройками')}
              </p>
            </div>
          </div>

          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[color:var(--color-bg)] border border-[color:var(--color-border)] text-[color:var(--color-text)] hover:bg-[color:var(--color-border)] transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            {t('common.refresh', 'Обновить')}
          </button>
        </div>

        {/* Stats Badge */}
        {!loading && organizations.length > 0 && (
          <div className="mb-6 inline-flex items-center gap-2 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium">
            <Building2 className="w-4 h-4" />
            {t('organizations.count', { count: organizations.length, defaultValue: `${organizations.length} организаций` })}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="space-y-4">
            <SkeletonOrgItem />
            <SkeletonOrgItem />
            <SkeletonOrgItem />
          </div>
        )}

        {/* Empty State */}
        {!loading && organizations.length === 0 && (
          <div className="text-center py-16 px-4">
            <div className="w-20 h-20 mx-auto mb-6 bg-gray-100 dark:bg-gray-900/30 rounded-full flex items-center justify-center">
              <Building2 className="w-10 h-10 text-gray-400 dark:text-gray-600" />
            </div>
            <h3 className="text-xl font-semibold text-[color:var(--color-text)] mb-2">
              {t('organizations.empty.title', 'Нет организаций')}
            </h3>
            <p className="text-[color:var(--color-text-secondary)] max-w-md mx-auto">
              {t('organizations.empty.description', 'Организации пока не созданы. Создайте первую организацию для начала работы.')}
            </p>
          </div>
        )}

        {/* Organizations List */}
        {!loading && organizations.length > 0 && (
          <div className="space-y-4">
            {organizations.map((org) => (
              <div
                key={org.id}
                className="bg-[color:var(--color-bg)] rounded-xl border border-[color:var(--color-border)] p-4 sm:p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  {/* Org Info */}
                  <div className="flex items-center gap-4">
                    <div
                      className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-lg"
                      style={{
                        background: org.primary_color
                          ? `linear-gradient(135deg, ${org.primary_color}, ${org.secondary_color || org.primary_color})`
                          : 'linear-gradient(135deg, #3b82f6, #1d4ed8)'
                      }}
                    >
                      <Building2 className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-[color:var(--color-text)]">
                          {org.name}
                        </span>
                        {org.is_active ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-500" />
                        )}
                      </div>
                      {org.slug && (
                        <div className="flex items-center gap-1.5 text-sm text-[color:var(--color-text-secondary)]">
                          <Globe className="w-3.5 h-3.5" />
                          {org.slug}
                        </div>
                      )}
                      {org.created_at && (
                        <div className="flex items-center gap-1.5 text-xs text-[color:var(--color-text-secondary)] mt-1">
                          <Clock className="w-3 h-3" />
                          {t('organizations.createdAt', 'Создана')}: {formatDate(org.created_at)}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 sm:gap-3">
                    <button
                      onClick={() => onToggleStatus(org)}
                      disabled={actionLoading !== null}
                      className={`flex-1 sm:flex-none flex items-center justify-center gap-2 ${
                        org.is_active
                          ? 'bg-orange-500 hover:bg-orange-600 disabled:bg-orange-400'
                          : 'bg-green-500 hover:bg-green-600 disabled:bg-green-400'
                      } text-white px-4 py-2.5 rounded-lg font-medium transition-colors`}
                    >
                      {actionLoading === org.id + '_toggle' ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : org.is_active ? (
                        <XCircle className="w-4 h-4" />
                      ) : (
                        <CheckCircle className="w-4 h-4" />
                      )}
                      {org.is_active
                        ? t('organizations.deactivate', 'Деактивировать')
                        : t('organizations.activate', 'Активировать')}
                    </button>
                    <button
                      onClick={() => navigate(`/admin/organizations/${org.id}`)}
                      disabled={actionLoading !== null}
                      className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-[color:var(--color-bg)] border border-[color:var(--color-border)] text-[color:var(--color-text)] hover:bg-[color:var(--color-border)] px-4 py-2.5 rounded-lg font-medium transition-colors disabled:opacity-50"
                    >
                      <Settings className="w-4 h-4" />
                      {t('organizations.settings', 'Настройки')}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        </div>
      </div>
    </AppLayout>
  );
};

export default Organizations;
