import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { adminApi, SecurityPolicy, SecurityPolicyInfo } from '@/api/admin';
import { useToast } from '@/hooks/useToast';
import { Shield, Plus, Trash2, Power, PowerOff, RefreshCw, Lock, Clock, Users, AlertTriangle } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

interface TwoFactorPolicyProps {
  className?: string;
}

export const TwoFactorPolicy: React.FC<TwoFactorPolicyProps> = ({ className }) => {
  const toast = useToast();
  const queryClient = useQueryClient();

  // Form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [policyName, setPolicyName] = useState('');
  const [enforcementLevel, setEnforcementLevel] = useState<'optional' | 'mandatory' | 'audit_only'>('optional');
  const [gracePeriodHours, setGracePeriodHours] = useState('0');
  const [affectedRoles, setAffectedRoles] = useState('');
  const [description, setDescription] = useState('');
  const [isAdding, setIsAdding] = useState(false);

  // Fetch 2FA policies
  const { data: policies = [], isLoading, refetch } = useQuery({
    queryKey: ['security-policies', 'two_factor'],
    queryFn: () => adminApi.getSecurityPolicies({ policy_type: 'two_factor_enforcement' }),
  });

  // Fetch policy info
  const { data: info } = useQuery({
    queryKey: ['security-policy-info'],
    queryFn: () => adminApi.getSecurityPolicyInfo(),
  });

  // Create policy mutation
  const createMutation = useMutation({
    mutationFn: (data: {
      name: string;
      enforcement_level: string;
      grace_period_hours: number;
      affected_roles: string[] | null;
      description: string | null;
    }) =>
      adminApi.createSecurityPolicy({
        name: data.name,
        policy_type: 'two_factor_enforcement',
        enabled: false,
        enforcement_level: data.enforcement_level,
        grace_period_hours: data.grace_period_hours,
        affected_roles: data.affected_roles,
        allow_exempt_alternative_auth: false,
        description: data.description,
      }),
    onSuccess: () => {
      toast.success('2FA policy created successfully');
      setPolicyName('');
      setEnforcementLevel('optional');
      setGracePeriodHours('0');
      setAffectedRoles('');
      setDescription('');
      setShowAddForm(false);
      queryClient.invalidateQueries({ queryKey: ['security-policies'] });
      queryClient.invalidateQueries({ queryKey: ['security-policy-info'] });
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || 'Failed to create 2FA policy';
      toast.error(message);
    },
  });

  // Delete policy mutation
  const deleteMutation = useMutation({
    mutationFn: (policyId: string) => adminApi.deleteSecurityPolicy(policyId),
    onSuccess: () => {
      toast.success('2FA policy deleted');
      queryClient.invalidateQueries({ queryKey: ['security-policies'] });
      queryClient.invalidateQueries({ queryKey: ['security-policy-info'] });
    },
    onError: () => {
      toast.error('Failed to delete 2FA policy');
    },
  });

  // Toggle enabled mutation
  const toggleMutation = useMutation({
    mutationFn: ({ policyId, enabled }: { policyId: string; enabled: boolean }) =>
      enabled
        ? adminApi.disableSecurityPolicy(policyId)
        : adminApi.enableSecurityPolicy(policyId),
    onSuccess: () => {
      toast.success('2FA policy updated');
      queryClient.invalidateQueries({ queryKey: ['security-policies'] });
      queryClient.invalidateQueries({ queryKey: ['security-policy-info'] });
    },
    onError: () => {
      toast.error('Failed to update 2FA policy');
    },
  });

  const handleAddPolicy = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!policyName.trim()) {
      toast.error('Policy name is required');
      return;
    }

    const gracePeriod = parseInt(gracePeriodHours, 10);
    if (isNaN(gracePeriod) || gracePeriod < 0) {
      toast.error('Grace period must be a valid number');
      return;
    }

    setIsAdding(true);
    try {
      await createMutation.mutateAsync({
        name: policyName.trim(),
        enforcement_level: enforcementLevel,
        grace_period_hours: gracePeriod,
        affected_roles: affectedRoles.trim()
          ? affectedRoles.split(',').map((r) => r.trim())
          : null,
        description: description.trim() || null,
      });
    } finally {
      setIsAdding(false);
    }
  };

  const handleDeletePolicy = (policyId: string) => {
    if (!confirm('Are you sure you want to delete this 2FA policy?')) {
      return;
    }
    deleteMutation.mutate(policyId);
  };

  const handleToggleEnabled = (policy: SecurityPolicy) => {
    toggleMutation.mutate({
      policyId: policy.id,
      enabled: policy.enabled,
    });
  };

  const getEnforcementLevelBadge = (level: string) => {
    switch (level) {
      case 'mandatory':
        return (
          <span className="text-xs px-2 py-1 rounded-full bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
            Mandatory
          </span>
        );
      case 'optional':
        return (
          <span className="text-xs px-2 py-1 rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
            Optional
          </span>
        );
      case 'audit_only':
        return (
          <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
            Audit Only
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Stats Cards */}
      {info && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Policies</CardTitle>
              <Shield className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{info.total_policies}</div>
              <p className="text-xs text-muted-foreground mt-1">All security policies</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Enabled</CardTitle>
              <Lock className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{info.enabled_policies}</div>
              <p className="text-xs text-muted-foreground mt-1">Currently enforcing</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Mandatory</CardTitle>
              <AlertTriangle className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{info.mandatory_policies}</div>
              <p className="text-xs text-muted-foreground mt-1">Required for all users</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Optional</CardTitle>
              <Users className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{info.optional_policies}</div>
              <p className="text-xs text-muted-foreground mt-1">User-configurable</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>2FA Enforcement Policies</CardTitle>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => refetch()} disabled={isLoading}>
                <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              </Button>
              <Button size="sm" onClick={() => setShowAddForm(!showAddForm)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Policy
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Add Policy Form */}
          {showAddForm && (
            <form onSubmit={handleAddPolicy} className="space-y-4 p-4 border rounded-lg bg-muted/50">
              <div className="space-y-2">
                <label className="text-sm font-medium">Policy Name</label>
                <Input
                  placeholder="e.g., Admin 2FA Requirement"
                  value={policyName}
                  onChange={(e) => setPolicyName(e.target.value)}
                  disabled={isAdding}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Enforcement Level</label>
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  value={enforcementLevel}
                  onChange={(e) => setEnforcementLevel(e.target.value as any)}
                  disabled={isAdding}
                >
                  <option value="optional">Optional - Users can choose</option>
                  <option value="mandatory">Mandatory - Required for all</option>
                  <option value="audit_only">Audit Only - Log without blocking</option>
                </select>
                <p className="text-xs text-muted-foreground">
                  {enforcementLevel === 'mandatory' && 'Users will be required to enable 2FA to access the system'}
                  {enforcementLevel === 'optional' && 'Users will be prompted but can skip 2FA setup'}
                  {enforcementLevel === 'audit_only' && '2FA status will be tracked but not enforced'}
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Grace Period (Hours)</label>
                <Input
                  type="number"
                  min="0"
                  placeholder="0"
                  value={gracePeriodHours}
                  onChange={(e) => setGracePeriodHours(e.target.value)}
                  disabled={isAdding}
                />
                <p className="text-xs text-muted-foreground">
                  Time users have before 2FA is enforced (0 = immediate)
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Affected Roles (Optional)</label>
                <Input
                  placeholder="e.g., admin, moderator (leave empty for all roles)"
                  value={affectedRoles}
                  onChange={(e) => setAffectedRoles(e.target.value)}
                  disabled={isAdding}
                />
                <p className="text-xs text-muted-foreground">
                  Comma-separated list of roles this policy applies to
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Description (Optional)</label>
                <Input
                  placeholder="e.g., Requires 2FA for all admin users"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={isAdding}
                />
              </div>

              <div className="flex gap-2">
                <Button type="submit" size="sm" disabled={isAdding || !policyName.trim()}>
                  {isAdding ? 'Creating...' : 'Create Policy'}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setShowAddForm(false);
                    setPolicyName('');
                    setEnforcementLevel('optional');
                    setGracePeriodHours('0');
                    setAffectedRoles('');
                    setDescription('');
                  }}
                  disabled={isAdding}
                >
                  Cancel
                </Button>
              </div>
            </form>
          )}

          {/* Policies Table */}
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">Loading 2FA policies...</div>
          ) : policies.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No 2FA policies found</p>
              <p className="text-sm mt-2">Create a policy to enforce two-factor authentication</p>
            </div>
          ) : (
            <div className="space-y-2">
              {policies.map((policy) => (
                <div
                  key={policy.id}
                  className={`p-4 border rounded-lg flex items-center justify-between gap-4 ${
                    !policy.enabled ? 'opacity-60 bg-muted/30' : ''
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-sm font-semibold">{policy.name}</span>
                      {getEnforcementLevelBadge(policy.enforcement_level)}
                      {!policy.enabled && (
                        <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200">
                          Disabled
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground mb-1">
                      {policy.grace_period_hours !== null && policy.grace_period_hours > 0 && (
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {policy.grace_period_hours}h grace period
                        </span>
                      )}
                      {policy.affected_roles && policy.affected_roles.length > 0 && (
                        <span className="flex items-center gap-1">
                          <Users className="h-3 w-3" />
                          {policy.affected_roles.join(', ')}
                        </span>
                      )}
                      {policy.affected_roles === null && (
                        <span className="flex items-center gap-1">
                          <Users className="h-3 w-3" />
                          All roles
                        </span>
                      )}
                    </div>
                    {policy.description && (
                      <p className="text-sm text-muted-foreground truncate">{policy.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleToggleEnabled(policy)}
                      disabled={toggleMutation.isPending}
                      title={policy.enabled ? 'Disable' : 'Enable'}
                    >
                      {policy.enabled ? (
                        <Power className="h-4 w-4 text-green-600" />
                      ) : (
                        <PowerOff className="h-4 w-4 text-gray-600" />
                      )}
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleDeletePolicy(policy.id)}
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
