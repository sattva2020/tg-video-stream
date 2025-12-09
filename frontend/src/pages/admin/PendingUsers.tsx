import React, { useCallback, useEffect, useState, useRef } from 'react';
import { adminApi } from '../../api/admin';
import { useToast } from '../../hooks/useToast';
import { Skeleton } from '../../components/ui/Skeleton';

type PendingUser = { id: string; email: string; status: string };

const SkeletonUserItem: React.FC = () => (
  <li className="p-3 border rounded flex items-center justify-between">
    <div className="flex-1">
      <Skeleton className="h-5 w-48 mb-2" />
      <Skeleton className="h-4 w-24" />
    </div>
    <div className="flex gap-2">
      <Skeleton className="h-8 w-24 rounded" />
      <Skeleton className="h-8 w-24 rounded" />
    </div>
  </li>
);

const PendingUsers: React.FC = () => {
  const [users, setUsers] = useState<PendingUser[]>([]);
  const [loading, setLoading] = useState(false);
  const toast = useToast();
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.listUsers({ status: 'pending' });
      setUsers(data?.items || []);
    } catch (err) {
      toastRef.current.error('Не удалось загрузить список пользователей');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onApprove = async (id: string, email: string) => {
    try {
      await adminApi.approveUser(id);
      toast.success(`Пользователь ${email} успешно одобрен`);
      load();
    } catch (err) {
      toast.error(`Не удалось одобрить пользователя ${email}`);
    }
  };

  const onReject = async (id: string, email: string) => {
    try {
      await adminApi.rejectUser(id);
      toast.success(`Заявка пользователя ${email} отклонена`);
      load();
    } catch (err) {
      toast.error(`Не удалось отклонить заявку ${email}`);
    }
  };

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Ожидающие подтверждения</h1>

      {loading && (
        <ul className="space-y-2">
          <SkeletonUserItem />
          <SkeletonUserItem />
          <SkeletonUserItem />
        </ul>
      )}

      {!loading && users.length === 0 && <p>Нет ожидающих пользователей.</p>}

      <ul className="space-y-2">
        {users.map((u) => (
          <li key={u.id} className="p-3 border rounded flex items-center justify-between">
            <div>
              <div className="font-medium">{u.email}</div>
              <div className="text-sm text-gray-500">Статус: {u.status}</div>
            </div>
            <div className="space-x-2">
              <button onClick={() => onApprove(u.id, u.email)} className="bg-green-500 text-white px-3 py-1 rounded">Утвердить</button>
              <button onClick={() => onReject(u.id, u.email)} className="bg-red-500 text-white px-3 py-1 rounded">Отклонить</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default PendingUsers;
