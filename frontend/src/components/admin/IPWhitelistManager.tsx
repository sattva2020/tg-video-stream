import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { adminApi, IPWhitelistEntry, IPWhitelistInfo } from '@/api/admin';
import { useToast } from '@/hooks/useToast';
import { Shield, Plus, Trash2, Power, PowerOff, RefreshCw, Globe, Lock } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

interface IPWhitelistManagerProps {
  className?: string;
}

export const IPWhitelistManager: React.FC<IPWhitelistManagerProps> = ({ className }) => {
  const toast = useToast();
  const queryClient = useQueryClient();

  // Form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newCidr, setNewCidr] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  // Fetch IP whitelist entries
  const { data: entries = [], isLoading, refetch } = useQuery({
    queryKey: ['ip-whitelist-entries'],
    queryFn: () => adminApi.getIPWhitelistEntries(),
  });

  // Fetch IP whitelist info
  const { data: info } = useQuery({
    queryKey: ['ip-whitelist-info'],
    queryFn: () => adminApi.getIPWhitelistInfo(),
  });

  // Create entry mutation
  const createMutation = useMutation({
    mutationFn: (data: { cidr: string; description?: string }) =>
      adminApi.createIPWhitelistEntry({
        cidr: data.cidr,
        description: data.description,
        is_active: true,
      }),
    onSuccess: () => {
      toast.success('IP whitelist entry added successfully');
      setNewCidr('');
      setNewDescription('');
      setShowAddForm(false);
      queryClient.invalidateQueries({ queryKey: ['ip-whitelist-entries'] });
      queryClient.invalidateQueries({ queryKey: ['ip-whitelist-info'] });
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || 'Failed to add IP whitelist entry';
      toast.error(message);
    },
  });

  // Delete entry mutation
  const deleteMutation = useMutation({
    mutationFn: (entryId: string) => adminApi.deleteIPWhitelistEntry(entryId),
    onSuccess: () => {
      toast.success('IP whitelist entry deleted');
      queryClient.invalidateQueries({ queryKey: ['ip-whitelist-entries'] });
      queryClient.invalidateQueries({ queryKey: ['ip-whitelist-info'] });
    },
    onError: () => {
      toast.error('Failed to delete IP whitelist entry');
    },
  });

  // Toggle active mutation
  const toggleMutation = useMutation({
    mutationFn: ({ entryId, isActive }: { entryId: string; isActive: boolean }) =>
      isActive
        ? adminApi.deactivateIPWhitelistEntry(entryId)
        : adminApi.activateIPWhitelistEntry(entryId),
    onSuccess: () => {
      toast.success('IP whitelist entry updated');
      queryClient.invalidateQueries({ queryKey: ['ip-whitelist-entries'] });
      queryClient.invalidateQueries({ queryKey: ['ip-whitelist-info'] });
    },
    onError: () => {
      toast.error('Failed to update IP whitelist entry');
    },
  });

  const handleAddEntry = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newCidr.trim()) {
      toast.error('CIDR is required');
      return;
    }

    setIsAdding(true);
    try {
      await createMutation.mutateAsync({
        cidr: newCidr.trim(),
        description: newDescription.trim() || undefined,
      });
    } finally {
      setIsAdding(false);
    }
  };

  const handleDeleteEntry = (entryId: string) => {
    if (!confirm('Are you sure you want to delete this IP whitelist entry?')) {
      return;
    }
    deleteMutation.mutate(entryId);
  };

  const handleToggleActive = (entry: IPWhitelistEntry) => {
    toggleMutation.mutate({
      entryId: entry.id,
      isActive: entry.is_active,
    });
  };

  const validateCIDR = (cidr: string): boolean => {
    // Basic CIDR validation
    const cidrPattern = /^([0-9]{1,3}\.){3}[0-9]{1,3}(\/([0-9]|[1-2][0-9]|3[0-2]))?$|^([0-9a-fA-F:]+:+)([0-9a-fA-F]*)(\/\d{1,3})?$/;
    return cidrPattern.test(cidr);
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Stats Cards */}
      {info && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Entries</CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{info.total_entries}</div>
              <p className="text-xs text-muted-foreground mt-1">
                All whitelist entries
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active</CardTitle>
              <Lock className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{info.active_entries}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Currently enforcing
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">IPv4</CardTitle>
              <Globe className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{info.ipv4_entries}</div>
              <p className="text-xs text-muted-foreground mt-1">
                IPv4 addresses/ranges
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">IPv6</CardTitle>
              <Globe className="h-4 w-4 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-600">{info.ipv6_entries}</div>
              <p className="text-xs text-muted-foreground mt-1">
                IPv6 addresses/ranges
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>IP Whitelist Management</CardTitle>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => refetch()}
                disabled={isLoading}
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              </Button>
              <Button
                size="sm"
                onClick={() => setShowAddForm(!showAddForm)}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Entry
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Add Entry Form */}
          {showAddForm && (
            <form onSubmit={handleAddEntry} className="space-y-4 p-4 border rounded-lg bg-muted/50">
              <div className="space-y-2">
                <label className="text-sm font-medium">CIDR (IP Address or Range)</label>
                <Input
                  placeholder="e.g., 192.168.1.0/24 or 2001:db8::/32"
                  value={newCidr}
                  onChange={(e) => setNewCidr(e.target.value)}
                  disabled={isAdding}
                />
                <p className="text-xs text-muted-foreground">
                  Enter an IP address or CIDR range (e.g., 192.168.1.1 or 192.168.1.0/24)
                </p>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Description (Optional)</label>
                <Input
                  placeholder="e.g., Office Network, VPN, Data Center"
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  disabled={isAdding}
                />
              </div>
              <div className="flex gap-2">
                <Button
                  type="submit"
                  size="sm"
                  disabled={isAdding || !newCidr.trim()}
                >
                  {isAdding ? 'Adding...' : 'Add Entry'}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setShowAddForm(false);
                    setNewCidr('');
                    setNewDescription('');
                  }}
                  disabled={isAdding}
                >
                  Cancel
                </Button>
              </div>
            </form>
          )}

          {/* Entries Table */}
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading IP whitelist entries...
            </div>
          ) : entries.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No IP whitelist entries found</p>
              <p className="text-sm mt-2">Add an entry to start controlling access by IP</p>
            </div>
          ) : (
            <div className="space-y-2">
              {entries.map((entry) => (
                <div
                  key={entry.id}
                  className={`p-4 border rounded-lg flex items-center justify-between gap-4 ${
                    !entry.is_active ? 'opacity-60 bg-muted/30' : ''
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <code className="text-sm font-mono bg-muted px-2 py-1 rounded">
                        {entry.cidr}
                      </code>
                      <span
                        className={`text-xs px-2 py-1 rounded-full ${
                          entry.is_ipv4
                            ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                            : 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
                        }`}
                      >
                        {entry.is_ipv4 ? 'IPv4' : 'IPv6'}
                      </span>
                      {!entry.is_active && (
                        <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200">
                          Inactive
                        </span>
                      )}
                    </div>
                    {entry.description && (
                      <p className="text-sm text-muted-foreground truncate">
                        {entry.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleToggleActive(entry)}
                      disabled={toggleMutation.isPending}
                      title={entry.is_active ? 'Deactivate' : 'Activate'}
                    >
                      {entry.is_active ? (
                        <Power className="h-4 w-4 text-green-600" />
                      ) : (
                        <PowerOff className="h-4 w-4 text-gray-600" />
                      )}
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleDeleteEntry(entry.id)}
                      disabled={deleteMutation.isPending}
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
