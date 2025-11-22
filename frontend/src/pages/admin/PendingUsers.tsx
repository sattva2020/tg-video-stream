import React, { useEffect, useState } from 'react';
import { adminApi } from '../../api/admin';

type PendingUser = { id: string; email: string; status: string };

const PendingUsers: React.FC = () => {
  const [users, setUsers] = useState<PendingUser[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await adminApi.listUsers('pending');
      setUsers(data || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onApprove = async (id: string) => {
    await adminApi.approveUser(id);
    load();
  };

  const onReject = async (id: string) => {
    await adminApi.rejectUser(id);
    load();
  };

  return (
    <div className="p-4">
      <h1 className="text-xl font-bold mb-4">Ожидающие подтверждения</h1>

      {loading && <p>Загрузка...</p>}

      {!loading && users.length === 0 && <p>Нет ожидающих пользователей.</p>}

      <ul className="space-y-2">
        {users.map((u) => (
          <li key={u.id} className="p-3 border rounded flex items-center justify-between">
            <div>
              <div className="font-medium">{u.email}</div>
              <div className="text-sm text-gray-500">Статус: {u.status}</div>
            </div>
            <div className="space-x-2">
              <button onClick={() => onApprove(u.id)} className="bg-green-500 text-white px-3 py-1 rounded">Утвердить</button>
              <button onClick={() => onReject(u.id)} className="bg-red-500 text-white px-3 py-1 rounded">Отклонить</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default PendingUsers;
