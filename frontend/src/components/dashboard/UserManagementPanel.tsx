import React, { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Filter,
  UserCheck,
  UserX,
  Users,
  Clock,
  Shield,
  ChevronDown,
  Mail,
  Calendar,
  Check,
  X,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Button,
  Skeleton,
} from '@heroui/react';
import { usePaginatedUsers, useApproveUser, useRejectUser } from '../../hooks/useUsersQuery';
import { useToast } from '../../hooks/useToast';
import { Pagination } from '../ui/Pagination';

type UserStatus = 'all' | 'pending' | 'approved' | 'rejected';

interface UserCardProps {
  user: {
    id: string;
    email: string;
    full_name?: string;
    status: string;
    created_at?: string;
    role?: string;
  };
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  isLoading?: boolean;
}

const UserCard: React.FC<UserCardProps> = ({ user, onApprove, onReject, isLoading }) => {
  const { t } = useTranslation();
  
  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'approved':
        return { color: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20', label: t('admin.approved', 'Активен') };
      case 'pending':
        return { color: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20', label: t('admin.pending', 'Ожидает') };
      case 'rejected':
        return { color: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20', label: t('admin.rejected', 'Отклонён') };
      default:
        return { color: 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20', label: status };
    }
  };

  const statusConfig = getStatusConfig(user.status);
  const initials = user.full_name 
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : user.email.slice(0, 2).toUpperCase();

  const createdDate = user.created_at 
    ? new Date(user.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' })
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      layout
      className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] hover:border-[color:var(--color-border-hover)] transition-all duration-200"
    >
      <div className="flex items-start gap-4">
        {/* Avatar */}
        <div className="shrink-0">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center text-white font-semibold text-sm shadow-lg shadow-violet-500/20">
            {initials}
          </div>
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h4 className="font-semibold text-[color:var(--color-text)] truncate">
                {user.full_name || user.email.split('@')[0]}
              </h4>
              <div className="flex items-center gap-1.5 text-sm text-[color:var(--color-text-muted)]">
                <Mail className="w-3.5 h-3.5" />
                <span className="truncate">{user.email}</span>
              </div>
            </div>
            
            {/* Status Badge */}
            <span className={`shrink-0 px-2.5 py-1 text-xs font-medium rounded-lg border ${statusConfig.color}`}>
              {statusConfig.label}
            </span>
          </div>

          {/* Meta info */}
          <div className="flex items-center gap-4 mt-3 text-xs text-[color:var(--color-text-muted)]">
            {createdDate && (
              <div className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                <span>{createdDate}</span>
              </div>
            )}
            {user.role && (
              <div className="flex items-center gap-1">
                <Shield className="w-3.5 h-3.5" />
                <span>{user.role}</span>
              </div>
            )}
          </div>

          {/* Actions for pending users */}
          {user.status === 'pending' && (
            <div className="flex gap-2 mt-4">
              <Button
                size="sm"
                onPress={() => onApprove(user.id)}
                isDisabled={isLoading}
                className="flex-1 bg-gradient-to-r from-emerald-500 to-green-600 text-white font-medium rounded-lg hover:shadow-lg hover:shadow-emerald-500/25 transition-all"
                startContent={<Check className="w-4 h-4" />}
              >
                {t('admin.approve', 'Одобрить')}
              </Button>
              <Button
                size="sm"
                onPress={() => onReject(user.id)}
                isDisabled={isLoading}
                className="flex-1 bg-gradient-to-r from-rose-500 to-red-600 text-white font-medium rounded-lg hover:shadow-lg hover:shadow-rose-500/25 transition-all"
                startContent={<X className="w-4 h-4" />}
              >
                {t('admin.reject', 'Отклонить')}
              </Button>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

const UserCardSkeleton: React.FC = () => (
  <div className="p-4 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
    <div className="flex items-start gap-4">
      <Skeleton className="w-12 h-12 rounded-xl" />
      <div className="flex-1 space-y-3">
        <div className="flex justify-between">
          <div className="space-y-2">
            <Skeleton className="h-4 w-32 rounded-lg" />
            <Skeleton className="h-3 w-48 rounded-lg" />
          </div>
          <Skeleton className="h-6 w-16 rounded-lg" />
        </div>
        <Skeleton className="h-3 w-24 rounded-lg" />
      </div>
    </div>
  </div>
);

export const UserManagementPanel: React.FC = () => {
  const { t } = useTranslation();
  const toast = useToast();
  
  // State
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<UserStatus>('all');
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);

  // Data hooks
  const {
    data,
    pagination,
    isLoading,
    isFetching,
    goToPage,
    setPageSize,
    setStatus,
    setSearch: setSearchQuery,
  } = usePaginatedUsers({ page_size: 12 });

  const users = data?.items || [];
  
  const approveMutation = useApproveUser();
  const rejectMutation = useRejectUser();

  // Handlers
  const handleSearch = useCallback((value: string) => {
    setSearch(value);
    // Debounced search would be better here
    setSearchQuery(value);
  }, [setSearchQuery]);

  const handleStatusFilterChange = useCallback((status: UserStatus) => {
    setStatusFilter(status);
    setStatus(status === 'all' ? undefined : status);
  }, [setStatus]);

  const handleApprove = useCallback(async (userId: string) => {
    try {
      await approveMutation.mutateAsync(userId);
      toast.success(t('admin.userApproved', 'Пользователь одобрен'));
    } catch (error) {
      toast.error(t('admin.approveError', 'Ошибка при одобрении'));
    }
  }, [approveMutation, toast, t]);

  const handleReject = useCallback(async (userId: string) => {
    try {
      await rejectMutation.mutateAsync(userId);
      toast.success(t('admin.userRejected', 'Пользователь отклонён'));
    } catch (error) {
      toast.error(t('admin.rejectError', 'Ошибка при отклонении'));
    }
  }, [rejectMutation, toast, t]);

  // Filter tabs
  const filterTabs = useMemo(() => [
    { key: 'all', label: t('admin.allUsers', 'Все'), icon: Users, count: null },
    { key: 'pending', label: t('admin.pending', 'Ожидают'), icon: Clock, count: null },
    { key: 'approved', label: t('admin.approved', 'Активные'), icon: UserCheck, count: null },
    { key: 'rejected', label: t('admin.rejected', 'Отклонённые'), icon: UserX, count: null },
  ], [t]);

  return (
    <div className="space-y-5">
      {/* Header with Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[color:var(--color-text-muted)]" />
          <input
            type="text"
            value={search}
            onChange={(e) => handleSearch(e.target.value)}
            placeholder={t('admin.searchUsers', 'Поиск пользователей...')}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] text-[color:var(--color-text)] placeholder:text-[color:var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-violet-500/50 focus:border-violet-500 transition-all"
          />
        </div>

        {/* Mobile Filter Toggle */}
        <button
          onClick={() => setIsFiltersOpen(!isFiltersOpen)}
          className="sm:hidden flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] text-[color:var(--color-text)]"
        >
          <Filter className="w-4 h-4" />
          <span>{t('admin.filters', 'Фильтры')}</span>
          <ChevronDown className={`w-4 h-4 transition-transform ${isFiltersOpen ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Filter Tabs */}
      <AnimatePresence>
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className={`flex flex-wrap gap-2 ${!isFiltersOpen ? 'hidden sm:flex' : ''}`}
        >
          {filterTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = statusFilter === tab.key;
            
            return (
              <button
                key={tab.key}
                onClick={() => handleStatusFilterChange(tab.key as UserStatus)}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium
                  transition-all duration-200
                  ${isActive 
                    ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white shadow-lg shadow-violet-500/25' 
                    : 'bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-muted)] hover:bg-[color:var(--color-surface-hover)] border border-[color:var(--color-border)]'}
                `}
              >
                <Icon className="w-4 h-4" />
                <span>{tab.label}</span>
                {tab.count !== null && (
                  <span className={`px-1.5 py-0.5 text-xs rounded-md ${isActive ? 'bg-white/20' : 'bg-[color:var(--color-surface)]'}`}>
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </motion.div>
      </AnimatePresence>

      {/* Users Grid */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          // Skeleton loading
          Array.from({ length: 6 }).map((_, i) => (
            <UserCardSkeleton key={i} />
          ))
        ) : users.length === 0 ? (
          // Empty state
          <div className="col-span-full py-12 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-[color:var(--color-surface-muted)] flex items-center justify-center">
              <Users className="w-8 h-8 text-[color:var(--color-text-muted)]" />
            </div>
            <h3 className="text-lg font-semibold text-[color:var(--color-text)]">
              {t('admin.noUsersFound', 'Пользователи не найдены')}
            </h3>
            <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
              {search 
                ? t('admin.tryDifferentSearch', 'Попробуйте другой поисковый запрос')
                : t('admin.noUsersInCategory', 'В этой категории пока нет пользователей')}
            </p>
          </div>
        ) : (
          // User cards
          <AnimatePresence mode="popLayout">
            {users.map((user: { id: string; email: string; full_name?: string; status: string; created_at?: string; role?: string }) => (
              <UserCard
                key={user.id}
                user={user}
                onApprove={handleApprove}
                onReject={handleReject}
                isLoading={approveMutation.isPending || rejectMutation.isPending}
              />
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* Pagination */}
      {pagination && pagination.total > 0 && (
        <div className="pt-4 border-t border-[color:var(--color-border)]">
          <Pagination
            page={pagination.page}
            totalPages={pagination.totalPages}
            total={pagination.total}
            pageSize={pagination.pageSize}
            hasNext={pagination.hasNext}
            hasPrev={pagination.hasPrev}
            onPageChange={goToPage}
            onPageSizeChange={setPageSize}
            isLoading={isFetching}
          />
        </div>
      )}
    </div>
  );
};
