import React, { useEffect, useState } from 'react';
import { adminApi } from '../../api/admin';
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
  Spinner
} from '@heroui/react';

interface User {
  id: string;
  email: string;
  status: string;
}

export const AdminDashboard: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({ total: 0, pending: 0, approved: 0 });

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await adminApi.listUsers();
      setUsers(data);
      // Calculate stats
      const total = data.length;
      const pending = data.filter((u: User) => u.status === 'pending').length;
      const approved = data.filter((u: User) => u.status === 'approved').length;
      setStats({ total, pending, approved });
    } catch (error) {
      console.error('Failed to fetch users', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleApprove = async (id: string) => {
    try {
      await adminApi.approveUser(id);
      fetchUsers(); // Refresh list
    } catch (error) {
      console.error('Failed to approve user', error);
    }
  };

  const handleReject = async (id: string) => {
    if (!confirm('Are you sure you want to reject this user?')) return;
    try {
      await adminApi.rejectUser(id);
      fetchUsers(); // Refresh list
    } catch (error) {
      console.error('Failed to reject user', error);
    }
  };

  const handleRestartStream = async () => {
    if (!confirm('Are you sure you want to restart the stream? This will interrupt the broadcast.')) return;
    try {
      await adminApi.restartStream();
      alert('Stream restart initiated');
    } catch (error) {
      console.error('Failed to restart stream', error);
      alert('Failed to restart stream');
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
    <div className="space-y-6 p-4">
      {/* Stats Overview */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardBody className="gap-2">
            <div className="text-sm text-default-500">Total Users</div>
            <div className="text-2xl font-semibold">{stats.total}</div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="gap-2">
            <div className="text-sm text-default-500">Pending Approvals</div>
            <div className="text-2xl font-semibold text-warning">{stats.pending}</div>
          </CardBody>
        </Card>
        <Card>
          <CardBody className="gap-2">
            <div className="text-sm text-default-500">Stream Status</div>
            <div className="text-2xl font-semibold text-success">Online</div>
          </CardBody>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex w-full flex-col">
        <Tabs aria-label="Admin Options">
          <Tab key="overview" title="Overview">
            <Card>
              <CardBody className="p-6">
                <h3 className="text-lg font-medium mb-4">System Overview</h3>
                <p className="text-default-500">
                  Welcome to the Admin Control Panel. Use the tabs above to manage users and stream settings.
                </p>
              </CardBody>
            </Card>
          </Tab>
          
          <Tab key="users" title="Users">
            <Card>
              <CardHeader className="flex justify-between items-center px-6 py-4">
                <h3 className="text-lg font-medium">User Management</h3>
                <Button 
                  size="sm" 
                  color="primary" 
                  variant="flat" 
                  onPress={fetchUsers}
                  isLoading={loading}
                >
                  Refresh
                </Button>
              </CardHeader>
              <CardBody>
                <Table aria-label="Users table" removeWrapper>
                  <TableHeader>
                    <TableColumn>EMAIL</TableColumn>
                    <TableColumn>STATUS</TableColumn>
                    <TableColumn align="end">ACTIONS</TableColumn>
                  </TableHeader>
                  <TableBody 
                    items={users} 
                    emptyContent={loading ? <Spinner /> : "No users found"}
                    isLoading={loading}
                  >
                    {(user) => (
                      <TableRow key={user.id}>
                        <TableCell>{user.email}</TableCell>
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
                                  Approve
                                </Button>
                                <Button
                                  size="sm"
                                  color="danger"
                                  variant="flat"
                                  onPress={() => handleReject(user.id)}
                                >
                                  Reject
                                </Button>
                              </>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardBody>
            </Card>
          </Tab>

          <Tab key="stream" title="Stream">
            <Card>
              <CardBody className="p-6">
                <h3 className="text-lg font-medium mb-6">Stream Controls</h3>
                
                <div className="grid gap-6 max-w-xl">
                  <div className="p-4 rounded-xl bg-default-50 border border-default-200">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h4 className="font-medium">Restart Service</h4>
                        <p className="text-sm text-default-500">
                          Restart the video streaming process. This will cause a temporary outage.
                        </p>
                      </div>
                      <Button
                        color="primary"
                        onPress={handleRestartStream}
                        className="shadow-lg shadow-blue-600/20"
                      >
                        Restart Stream
                      </Button>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-default-50 border border-default-200 opacity-50 cursor-not-allowed">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4 className="font-medium">Emergency Stop</h4>
                        <p className="text-sm text-default-500">
                          Immediately stop the broadcast.
                        </p>
                      </div>
                      <Button color="danger" isDisabled>
                        Stop
                      </Button>
                    </div>
                  </div>
                </div>
              </CardBody>
            </Card>
          </Tab>
        </Tabs>
      </div>
    </div>
  );
};
