import React, { useState } from 'react';
import { adminApi, User } from '../../api/admin';
import { 
  Card, 
  CardBody, 
  CardHeader, 
  Button, 
  Table, 
  TableHeader, 
  TableColumn, 
  TableBody, 
  TableRow, 
  TableCell, 
  Chip, 
  Tabs, 
  Tab,
  Input
} from '@heroui/react';
import { useToast } from '../../hooks/useToast';
import { StreamStatusCard } from './StreamStatusCard';
import { SkeletonStatCard, SkeletonTableRow } from '../ui/Skeleton';
import { Pagination } from '../ui/Pagination';
import { usePaginatedUsers, useUserStats, useApproveUser, useRejectUser } from '../../hooks/useUsersQuery';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../lib/queryClient';
import { Check, X, RefreshCw, Search } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export const AdminDashboard: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  
  // Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  
  // React Query hooks with pagination
  const { 
    data, 
    isLoading: loading, 
    refetch: refetchUsers,
    pagination,
    goToPage,
    setPageSize,
    setStatus,
    setSearch,
    isFetching
  } = usePaginatedUsers({ page_size: 10 });
  
  const users = data?.items || [];
  const { stats } = useUserStats();
  const approveUser = useApproveUser();
  const rejectUser = useRejectUser();

  // Handle search with debounce
  const handleSearchChange = (value: string) => {
    setSearchTerm(value);
    // Debounce the actual search
    const timeoutId = setTimeout(() => {
      setSearch(value || undefined);
    }, 300);
    return () => clearTimeout(timeoutId);
  };

  // Handle status filter
  const handleStatusFilter = (status: string) => {
    const newStatus = status === statusFilter ? undefined : status;
    setStatusFilter(newStatus);
    setStatus(newStatus);
  };

  const handleApprove = (id: string) => {
    approveUser.mutate(id);
  };

  const handleReject = (id: string) => {
    if (!confirm('Вы уверены, что хотите отклонить этого пользователя?')) return;
    rejectUser.mutate(id);
  };

  const handleRestartStream = async () => {
    if (!confirm('Вы уверены? Это прервёт текущую трансляцию.')) return;
    try {
      await adminApi.restartStream();
      toast.success('Перезапуск трансляции инициирован');
      queryClient.invalidateQueries({ queryKey: queryKeys.stream.all });
    } catch (error) {
      console.error('Failed to restart stream', error);
      toast.error('Не удалось перезапустить трансляцию');
    }
  };
  
  const handleStartStream = async () => {
    try {
      await adminApi.startStream();
      toast.success('Трансляция запущена');
      queryClient.invalidateQueries({ queryKey: queryKeys.stream.all });
    } catch (error) {
      console.error('Failed to start stream', error);
      toast.error('Не удалось запустить трансляцию');
    }
  };
  
  const handleStopStream = async () => {
    if (!confirm('Вы уверены, что хотите остановить трансляцию?')) return;
    try {
      await adminApi.stopStream();
      toast.success('Трансляция остановлена');
      queryClient.invalidateQueries({ queryKey: queryKeys.stream.all });
    } catch (error) {
      console.error('Failed to stop stream', error);
      toast.error('Не удалось остановить трансляцию');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved': return 'success';
      case 'pending': return 'warning';
      case 'rejected': return 'danger';
      default: return 'default';
    }
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Stats Overview */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4">
        {loading ? (
          <>
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
          </>
        ) : (
          <>
            <Card className="col-span-1">
              <CardBody className="gap-1 p-3 sm:p-4 sm:gap-2">
                <div className="text-xs sm:text-sm text-default-500">Всего пользователей</div>
                <div className="text-xl sm:text-2xl font-semibold">{stats.total}</div>
              </CardBody>
            </Card>
            <Card className="col-span-1">
              <CardBody className="gap-1 p-3 sm:p-4 sm:gap-2">
                <div className="text-xs sm:text-sm text-default-500">Ожидают одобрения</div>
                <div className="text-xl sm:text-2xl font-semibold text-warning">{stats.pending}</div>
              </CardBody>
            </Card>
            {/* Stream Status Card - Real-time */}
            <div className="col-span-2 sm:col-span-1">
              <StreamStatusCard refreshInterval={15000} useWebSocket={true} />
            </div>
          </>
        )}
      </div>

      {/* Tabs */}
      <div className="flex w-full flex-col">
        <Tabs 
          aria-label="Admin Options" 
          classNames={{
            tabList: "gap-2 flex-wrap sm:flex-nowrap",
            tab: "text-xs sm:text-sm px-2 sm:px-4"
          }}
        >
          <Tab key="overview" title="Обзор">
            <Card>
              <CardBody className="p-4 sm:p-6">
                <h3 className="text-base sm:text-lg font-medium mb-3 sm:mb-4">Обзор системы</h3>
                <p className="text-sm text-default-500">
                  Добро пожаловать в панель управления. Используйте вкладки выше для управления пользователями и настройками трансляции.
                </p>
              </CardBody>
            </Card>
          </Tab>
          
          <Tab key="users" title={t('admin.users', 'Пользователи')}>
            <Card>
              <CardHeader className="flex flex-col gap-3 px-4 sm:px-6 py-3 sm:py-4">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 w-full">
                  <h3 className="text-base sm:text-lg font-medium">
                    {t('admin.userManagement', 'Управление пользователями')}
                  </h3>
                  <Button 
                    size="sm" 
                    color="primary" 
                    variant="flat" 
                    onPress={() => refetchUsers()}
                    isLoading={isFetching}
                    startContent={<RefreshCw className="w-4 h-4" />}
                  >
                    <span className="hidden sm:inline">{t('common.refresh', 'Обновить')}</span>
                  </Button>
                </div>
                
                {/* Filters */}
                <div className="flex flex-col sm:flex-row gap-2 w-full">
                  <Input
                    size="sm"
                    placeholder={t('admin.searchByEmail', 'Поиск по email...')}
                    value={searchTerm}
                    onValueChange={handleSearchChange}
                    startContent={<Search className="w-4 h-4 text-default-400" />}
                    className="w-full sm:max-w-xs"
                    isClearable
                    onClear={() => handleSearchChange('')}
                  />
                  <div className="flex gap-1 flex-wrap">
                    <Chip
                      size="sm"
                      variant={statusFilter === undefined ? 'solid' : 'flat'}
                      color="default"
                      className="cursor-pointer"
                      onClick={() => handleStatusFilter('')}
                    >
                      {t('admin.all', 'Все')}
                    </Chip>
                    <Chip
                      size="sm"
                      variant={statusFilter === 'pending' ? 'solid' : 'flat'}
                      color="warning"
                      className="cursor-pointer"
                      onClick={() => handleStatusFilter('pending')}
                    >
                      {t('admin.pending', 'Ожидающие')}
                    </Chip>
                    <Chip
                      size="sm"
                      variant={statusFilter === 'approved' ? 'solid' : 'flat'}
                      color="success"
                      className="cursor-pointer"
                      onClick={() => handleStatusFilter('approved')}
                    >
                      {t('admin.approved', 'Одобренные')}
                    </Chip>
                    <Chip
                      size="sm"
                      variant={statusFilter === 'rejected' ? 'solid' : 'flat'}
                      color="danger"
                      className="cursor-pointer"
                      onClick={() => handleStatusFilter('rejected')}
                    >
                      {t('admin.rejected', 'Отклонённые')}
                    </Chip>
                  </div>
                </div>
              </CardHeader>
              <CardBody className="p-0 sm:p-4">
                {/* Desktop Table */}
                <div className="hidden sm:block overflow-x-auto">
                  <Table aria-label="Users table" removeWrapper>
                    <TableHeader>
                      <TableColumn>EMAIL</TableColumn>
                      <TableColumn>{t('admin.status', 'СТАТУС')}</TableColumn>
                      <TableColumn align="end">{t('admin.actions', 'ДЕЙСТВИЯ')}</TableColumn>
                    </TableHeader>
                    <TableBody 
                      items={users} 
                      emptyContent={loading ? (
                        <div className="space-y-2 py-4">
                          <SkeletonTableRow columns={3} />
                          <SkeletonTableRow columns={3} />
                          <SkeletonTableRow columns={3} />
                        </div>
                      ) : t('admin.noUsers', 'Пользователи не найдены')}
                      isLoading={loading}
                    >
                      {(user: User) => (
                        <TableRow key={user.id}>
                          <TableCell>
                            <div>
                              <div className="font-medium">{user.email}</div>
                              {user.full_name && (
                                <div className="text-xs text-default-500">{user.full_name}</div>
                              )}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Chip color={getStatusColor(user.status) as any} size="sm" variant="flat">
                              {user.status}
                            </Chip>
                          </TableCell>
                          <TableCell>
                            <div className="flex justify-end gap-2">
                              {user.status === 'pending' && (
                                <>
                                  <Button
                                    size="sm"
                                    color="success"
                                    variant="flat"
                                    onPress={() => handleApprove(user.id)}
                                  >
                                    {t('admin.approve', 'Одобрить')}
                                  </Button>
                                  <Button
                                    size="sm"
                                    color="danger"
                                    variant="flat"
                                    onPress={() => handleReject(user.id)}
                                  >
                                    {t('admin.reject', 'Отклонить')}
                                  </Button>
                                </>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>

                {/* Mobile Card List */}
                <div className="sm:hidden divide-y divide-[color:var(--color-border)]">
                  {loading ? (
                    <div className="space-y-3 p-4">
                      <SkeletonTableRow columns={1} />
                      <SkeletonTableRow columns={1} />
                      <SkeletonTableRow columns={1} />
                    </div>
                  ) : users.length === 0 ? (
                    <div className="p-6 text-center text-default-500 text-sm">
                      {t('admin.noUsers', 'Пользователи не найдены')}
                    </div>
                  ) : (
                    users.map((user: User) => (
                      <div key={user.id} className="p-4 flex flex-col gap-3">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <span className="text-sm font-medium truncate block text-[color:var(--color-text)]">
                              {user.email}
                            </span>
                            {user.full_name && (
                              <span className="text-xs text-default-500 truncate block">
                                {user.full_name}
                              </span>
                            )}
                          </div>
                          <Chip color={getStatusColor(user.status) as any} size="sm" variant="flat">
                            {user.status}
                          </Chip>
                        </div>
                        {user.status === 'pending' && (
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              color="success"
                              variant="flat"
                              onPress={() => handleApprove(user.id)}
                              className="flex-1"
                              startContent={<Check className="w-4 h-4" />}
                            >
                              {t('admin.approve', 'Одобрить')}
                            </Button>
                            <Button
                              size="sm"
                              color="danger"
                              variant="flat"
                              onPress={() => handleReject(user.id)}
                              className="flex-1"
                              startContent={<X className="w-4 h-4" />}
                            >
                              {t('admin.reject', 'Отклонить')}
                            </Button>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>

                {/* Pagination */}
                {pagination && pagination.total > 0 && (
                  <div className="p-4 border-t border-[color:var(--color-border)]">
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
              </CardBody>
            </Card>
          </Tab>

          <Tab key="stream" title="Трансляция">
            <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
              {/* Stream Status */}
              <StreamStatusCard refreshInterval={5000} useWebSocket={true} />
              
              {/* Stream Controls */}
              <Card>
                <CardBody className="p-4 sm:p-6">
                  <h3 className="text-base sm:text-lg font-medium mb-4 sm:mb-6">Управление трансляцией</h3>
                  
                  <div className="space-y-3 sm:space-y-4">
                    <div className="p-3 sm:p-4 rounded-xl bg-default-50 border border-default-200">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                          <h4 className="font-medium text-sm sm:text-base">Запустить</h4>
                          <p className="text-xs sm:text-sm text-default-500">
                            Запустить видеотрансляцию
                          </p>
                        </div>
                        <Button
                          color="success"
                          onPress={handleStartStream}
                          size="sm"
                          className="w-full sm:w-auto"
                        >
                          Запустить
                        </Button>
                      </div>
                    </div>

                    <div className="p-3 sm:p-4 rounded-xl bg-default-50 border border-default-200">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                          <h4 className="font-medium text-sm sm:text-base">Перезапуск</h4>
                          <p className="text-xs sm:text-sm text-default-500">
                            Перезапустить сервис. Будет кратковременный перерыв.
                          </p>
                        </div>
                        <Button
                          color="primary"
                          onPress={handleRestartStream}
                          className="shadow-lg shadow-blue-600/20 w-full sm:w-auto"
                          size="sm"
                        >
                          Перезапустить
                        </Button>
                      </div>
                    </div>

                    <div className="p-3 sm:p-4 rounded-xl bg-default-50 border border-default-200">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div>
                          <h4 className="font-medium text-sm sm:text-base">Экстренная остановка</h4>
                          <p className="text-xs sm:text-sm text-default-500">
                            Немедленно остановить трансляцию.
                          </p>
                        </div>
                        <Button 
                          color="danger"
                          onPress={handleStopStream}
                          size="sm"
                          className="w-full sm:w-auto"
                        >
                          Остановить
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardBody>
              </Card>
            </div>
          </Tab>
        </Tabs>
      </div>
    </div>
  );
};
