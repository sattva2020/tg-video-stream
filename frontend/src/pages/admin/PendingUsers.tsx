import React, { useCallback, useEffect, useState, useRef } from 'react';
import { adminApi } from '../../api/admin';
import { useToast } from '../../hooks/useToast';
import { Skeleton } from '../../components/ui/Skeleton';
import { ResponsiveHeader } from '../../components/layout/ResponsiveHeader';
import { useTranslation } from 'react-i18next';
import { UserPlus, UserCheck, UserX, Clock, Mail, RefreshCw } from 'lucide-react';

type PendingUser = { id: string; email: string; full_name?: string; status: string; created_at?: string };

const SkeletonUserItem: React.FC = () => (
  <div className="bg-[color:var(--color-surface)] rounded-xl border border-[color:var(--color-border)] p-4 sm:p-6">
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div className="flex items-center gap-4">
        <Skeleton className="h-12 w-12 rounded-full" />
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

const PendingUsers: React.FC = () => {
  const { t } = useTranslation();
  const [users, setUsers] = useState<PendingUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.listUsers({ status: 'pending' });
      setUsers(data?.items || []);
    } catch (err) {
      toastRef.current.error(t('pending.loadError', 'Не удалось загрузить список пользователей'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    load();
  }, [load]);

  const onApprove = async (id: string, email: string) => {
    setActionLoading(id + '_approve');
    try {
      await adminApi.approveUser(id);
      toast.success(t('pending.approveSuccess', { email, defaultValue: `Пользователь ${email} успешно одобрен` }));
      load();
    } catch (err) {
      toast.error(t('pending.approveError', { email, defaultValue: `Не удалось одобрить пользователя ${email}` }));
    } finally {
      setActionLoading(null);
    }
  };

  const onReject = async (id: string, email: string) => {
    if (!window.confirm(t('pending.rejectConfirm', { email, defaultValue: `Вы уверены, что хотите отклонить заявку ${email}?` }))) {
      return;
    }
    setActionLoading(id + '_reject');
    try {
      await adminApi.rejectUser(id);
      toast.success(t('pending.rejectSuccess', { email, defaultValue: `Заявка пользователя ${email} отклонена` }));
      load();
    } catch (err) {
      toast.error(t('pending.rejectError', { email, defaultValue: `Не удалось отклонить заявку ${email}` }));
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
    <div className="min-h-screen bg-[color:var(--color-surface)]">
      <ResponsiveHeader />
      
      <main className="max-w-4xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-100 dark:bg-amber-900/30 rounded-xl">
              <UserPlus className="w-6 h-6 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-[color:var(--color-text)]">
                {t('pending.title', 'Ожидающие подтверждения')}
              </h1>
              <p className="text-sm text-[color:var(--color-text-secondary)]">
                {t('pending.subtitle', 'Новые пользователи, ожидающие одобрения')}
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
        {!loading && users.length > 0 && (
          <div className="mb-6 inline-flex items-center gap-2 px-3 py-1.5 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 rounded-full text-sm font-medium">
            <Clock className="w-4 h-4" />
            {t('pending.count', { count: users.length, defaultValue: `${users.length} заявок ожидают рассмотрения` })}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="space-y-4">
            <SkeletonUserItem />
            <SkeletonUserItem />
            <SkeletonUserItem />
          </div>
        )}

        {/* Empty State */}
        {!loading && users.length === 0 && (
          <div className="text-center py-16 px-4">
            <div className="w-20 h-20 mx-auto mb-6 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center">
              <UserCheck className="w-10 h-10 text-green-600 dark:text-green-400" />
            </div>
            <h3 className="text-xl font-semibold text-[color:var(--color-text)] mb-2">
              {t('pending.empty.title', 'Нет ожидающих пользователей')}
            </h3>
            <p className="text-[color:var(--color-text-secondary)] max-w-md mx-auto">
              {t('pending.empty.description', 'Все заявки на регистрацию обработаны. Новые заявки будут появляться здесь автоматически.')}
            </p>
          </div>
        )}

        {/* Users List */}
        {!loading && users.length > 0 && (
          <div className="space-y-4">
            {users.map((u) => (
              <div 
                key={u.id} 
                className="bg-[color:var(--color-bg)] rounded-xl border border-[color:var(--color-border)] p-4 sm:p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  {/* User Info */}
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-white font-bold text-lg">
                      {(u.full_name || u.email)?.[0]?.toUpperCase() || '?'}
                    </div>
                    <div>
                      <div className="font-semibold text-[color:var(--color-text)]">
                        {u.full_name || u.email.split('@')[0]}
                      </div>
                      <div className="flex items-center gap-1.5 text-sm text-[color:var(--color-text-secondary)]">
                        <Mail className="w-3.5 h-3.5" />
                        {u.email}
                      </div>
                      {u.created_at && (
                        <div className="flex items-center gap-1.5 text-xs text-[color:var(--color-text-secondary)] mt-1">
                          <Clock className="w-3 h-3" />
                          {t('pending.registeredAt', 'Зарегистрирован')}: {formatDate(u.created_at)}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 sm:gap-3">
                    <button 
                      onClick={() => onApprove(u.id, u.email)} 
                      disabled={actionLoading !== null}
                      className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 disabled:bg-green-400 text-white px-4 py-2.5 rounded-lg font-medium transition-colors"
                    >
                      {actionLoading === u.id + '_approve' ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <UserCheck className="w-4 h-4" />
                      )}
                      {t('pending.approve', 'Утвердить')}
                    </button>
                    <button 
                      onClick={() => onReject(u.id, u.email)} 
                      disabled={actionLoading !== null}
                      className="flex-1 sm:flex-none flex items-center justify-center gap-2 bg-red-500 hover:bg-red-600 disabled:bg-red-400 text-white px-4 py-2.5 rounded-lg font-medium transition-colors"
                    >
                      {actionLoading === u.id + '_reject' ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <UserX className="w-4 h-4" />
                      )}
                      {t('pending.reject', 'Отклонить')}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default PendingUsers;
