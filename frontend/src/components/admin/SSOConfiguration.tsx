import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { adminApi, SAMLConfig, SAMLConfigCreate } from '@/api/admin';
import { useToast } from '@/hooks/useToast';
import { Shield, Plus, Trash2, Power, PowerOff, RefreshCw, Key, Globe, Settings } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

interface SSOConfigurationProps {
  className?: string;
}

export const SSOConfiguration: React.FC<SSOConfigurationProps> = ({ className }) => {
  const toast = useToast();
  const queryClient = useQueryClient();

  // Form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [configName, setConfigName] = useState('');
  const [idpEntityId, setIdpEntityId] = useState('');
  const [idpSsoUrl, setIdpSsoUrl] = useState('');
  const [idpX509Cert, setIdpX509Cert] = useState('');
  const [idpSloUrl, setIdpSLoUrl] = useState('');
  const [idpMetadataUrl, setIdpMetadataUrl] = useState('');
  const [spEntityId, setSpEntityId] = useState('');
  const [spAcsUrl, setSpAcsUrl] = useState('');
  const [spSloUrl, setSpSloUrl] = useState('');
  const [nameIdFormat, setNameIdFormat] = useState('urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified');
  const [isAdding, setIsAdding] = useState(false);

  // Fetch SAML configurations
  // Fetch SAML configurations
  const { data: configs = [], isLoading, refetch } = useQuery({
    queryKey: ['saml-configs'],
    queryFn: () => adminApi.getSAMLConfigs(),
  });

  // Create config mutation
  const createMutation = useMutation({
    mutationFn: (data: SAMLConfigCreate) => adminApi.createSAMLConfig(data),
    onSuccess: () => {
      toast.success('SAML configuration created successfully');
      handleFormReset();
      setShowAddForm(false);
      queryClient.invalidateQueries({ queryKey: ['saml-configs'] });
      queryClient.invalidateQueries({ queryKey: ['security-config-summary'] });
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || 'Failed to create SAML configuration';
      toast.error(message);
    },
  });

  // Delete config mutation
  const deleteMutation = useMutation({
    mutationFn: (configId: string) => adminApi.deleteSAMLConfig(configId),
    onSuccess: () => {
      toast.success('SAML configuration deleted');
      queryClient.invalidateQueries({ queryKey: ['saml-configs'] });
      queryClient.invalidateQueries({ queryKey: ['security-config-summary'] });
    },
    onError: () => {
      toast.error('Failed to delete SAML configuration');
    },
  });

  // Toggle enabled mutation
  const toggleMutation = useMutation({
    mutationFn: ({ configId, enabled }: { configId: string; enabled: boolean }) =>
      enabled
        ? adminApi.disableSAMLConfig(configId)
        : adminApi.enableSAMLConfig(configId),
    onSuccess: () => {
      toast.success('SAML configuration updated');
      queryClient.invalidateQueries({ queryKey: ['saml-configs'] });
      queryClient.invalidateQueries({ queryKey: ['security-config-summary'] });
    },
    onError: () => {
      toast.error('Failed to update SAML configuration');
    },
  });

  const handleAddConfig = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!configName.trim()) {
      toast.error('Configuration name is required');
      return;
    }

    if (!idpEntityId.trim() || !idpSsoUrl.trim() || !idpX509Cert.trim()) {
      toast.error('Identity Provider settings are required');
      return;
    }

    if (!spEntityId.trim() || !spAcsUrl.trim()) {
      toast.error('Service Provider settings are required');
      return;
    }

    setIsAdding(true);
    try {
      await createMutation.mutateAsync({
        name: configName.trim(),
        enabled: false,
        idp_entity_id: idpEntityId.trim(),
        idp_sso_url: idpSsoUrl.trim(),
        idp_x509_cert: idpX509Cert.trim(),
        idp_slo_url: idpSloUrl.trim() || undefined,
        idp_metadata_url: idpMetadataUrl.trim() || undefined,
        sp_entity_id: spEntityId.trim(),
        sp_acs_url: spAcsUrl.trim(),
        sp_slo_url: spSloUrl.trim() || undefined,
        name_id_format: nameIdFormat,
      });
    } finally {
      setIsAdding(false);
    }
  };

  const handleDeleteConfig = (configId: string) => {
    if (!confirm('Are you sure you want to delete this SAML configuration?')) {
      return;
    }
    deleteMutation.mutate(configId);
  };

  const handleToggleEnabled = (config: SAMLConfig) => {
    toggleMutation.mutate({
      configId: config.id,
      enabled: config.enabled,
    });
  };

  const handleFormReset = () => {
    setConfigName('');
    setIdpEntityId('');
    setIdpSsoUrl('');
    setIdpX509Cert('');
    setIdpSloUrl('');
    setIdpMetadataUrl('');
    setSpEntityId('');
    setSpAcsUrl('');
    setSpSloUrl('');
    setNameIdFormat('urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified');
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Main Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>SSO/SAML Configuration</CardTitle>
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
                Add Configuration
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Add Configuration Form */}
          {showAddForm && (
            <form onSubmit={handleAddConfig} className="space-y-6 p-4 border rounded-lg bg-muted/50">
              <div className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  Identity Provider (IdP) Settings
                </h3>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Configuration Name</label>
                  <Input
                    placeholder="e.g., Okta Production"
                    value={configName}
                    onChange={(e) => setConfigName(e.target.value)}
                    disabled={isAdding}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">IdP Entity ID</label>
                  <Input
                    placeholder="https://idp.example.com/entityid"
                    value={idpEntityId}
                    onChange={(e) => setIdpEntityId(e.target.value)}
                    disabled={isAdding}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">IdP Single Sign-On URL</label>
                  <Input
                    placeholder="https://idp.example.com/sso"
                    value={idpSsoUrl}
                    onChange={(e) => setIdpSsoUrl(e.target.value)}
                    disabled={isAdding}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">IdP X.509 Certificate</label>
                  <textarea
                    className="flex min-h-[100px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                    placeholder="-----BEGIN CERTIFICATE-----&#10;...certificate content...&#10;-----END CERTIFICATE-----"
                    value={idpX509Cert}
                    onChange={(e) => setIdpX509Cert(e.target.value)}
                    disabled={isAdding}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">IdP Single Logout URL (Optional)</label>
                  <Input
                    placeholder="https://idp.example.com/slo"
                    value={idpSloUrl}
                    onChange={(e) => setIdpSloUrl(e.target.value)}
                    disabled={isAdding}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">IdP Metadata URL (Optional)</label>
                  <Input
                    placeholder="https://idp.example.com/metadata"
                    value={idpMetadataUrl}
                    onChange={(e) => setIdpMetadataUrl(e.target.value)}
                    disabled={isAdding}
                  />
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Globe className="h-5 w-5" />
                  Service Provider (SP) Settings
                </h3>

                <div className="space-y-2">
                  <label className="text-sm font-medium">SP Entity ID</label>
                  <Input
                    placeholder="https://yourapp.com/saml/metadata"
                    value={spEntityId}
                    onChange={(e) => setSpEntityId(e.target.value)}
                    disabled={isAdding}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">SP Assertion Consumer Service URL</label>
                  <Input
                    placeholder="https://yourapp.com/auth/saml/acs"
                    value={spAcsUrl}
                    onChange={(e) => setSpAcsUrl(e.target.value)}
                    disabled={isAdding}
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">SP Single Logout URL (Optional)</label>
                  <Input
                    placeholder="https://yourapp.com/auth/saml/slo"
                    value={spSloUrl}
                    onChange={(e) => setSpSloUrl(e.target.value)}
                    disabled={isAdding}
                  />
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Key className="h-5 w-5" />
                  Advanced Settings
                </h3>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Name ID Format</label>
                  <select
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                    value={nameIdFormat}
                    onChange={(e) => setNameIdFormat(e.target.value)}
                    disabled={isAdding}
                  >
                    <option value="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified">Unspecified</option>
                    <option value="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">Email Address</option>
                    <option value="urn:oasis:names:tc:SAML:1.1:nameid-format:X509SubjectName">X.509 Subject Name</option>
                    <option value="urn:oasis:names:tc:SAML:2.0:nameid-format:persistent">Persistent</option>
                    <option value="urn:oasis:names:tc:SAML:2.0:nameid-format:transient">Transient</option>
                  </select>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  type="submit"
                  size="sm"
                  disabled={isAdding || !configName.trim() || !idpEntityId.trim() || !idpSsoUrl.trim() || !idpX509Cert.trim() || !spEntityId.trim() || !spAcsUrl.trim()}
                >
                  {isAdding ? 'Creating...' : 'Create Configuration'}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setShowAddForm(false);
                    handleFormReset();
                  }}
                  disabled={isAdding}
                >
                  Cancel
                </Button>
              </div>
            </form>
          )}

          {/* Configs List */}
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading SAML configurations...
            </div>
          ) : configs.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Shield className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No SAML configurations found</p>
              <p className="text-sm mt-2">Add a configuration to enable Single Sign-On</p>
            </div>
          ) : (
            <div className="space-y-4">
              {configs.map((config) => (
                <div
                  key={config.id}
                  className={`p-4 border rounded-lg ${
                    !config.enabled ? 'opacity-60 bg-muted/30' : ''
                  }`}
                >
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <h4 className="text-base font-semibold">{config.name}</h4>
                        {config.enabled ? (
                          <span className="text-xs px-2 py-1 rounded-full bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                            Enabled
                          </span>
                        ) : (
                          <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200">
                            Disabled
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {config.idp_entity_id}
                      </p>
 </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleToggleEnabled(config)}
                        disabled={toggleMutation.isPending}
                        title={config.enabled ? 'Disable' : 'Enable'}
                      >
                        {config.enabled ? (
                          <Power className="h-4 w-4 text-green-600" />
                        ) : (
                          <PowerOff className="h-4 w-4 text-gray-600" />
                        )}
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleDeleteConfig(config.id)}
                        disabled={deleteMutation.isPending}
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="grid md:grid-cols-2 gap-4 text-sm">
                    <div className="space-y-2">
                      <p className="font-medium">Identity Provider</p>
                      <div className="space-y-1 text-muted-foreground">
                        <p>SSO URL: <code className="bg-muted px-1 rounded">{config.idp_sso_url}</code></p>
                        {config.idp_slo_url && <p>SLO URL: <code className="bg-muted px-1 rounded">{config.idp_slo_url}</code></p>}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <p className="font-medium">Service Provider</p>
                      <div className="space-y-1 text-muted-foreground">
                        <p>Entity ID: <code className="bg-muted px-1 rounded">{config.sp_entity_id}</code></p>
 <p>ACS URL: <code className="bg-muted px-1 rounded">{config.sp_acs_url}</code></p>
                      </div>
                    </div>
                  </div>

                  {(config.attribute_mapping || config.role_mapping) && (
                    <div className="mt-4 pt-4 border-t">
                      <p className="font-medium text-sm mb-2">Advanced Configuration</p>
                      <div className="flex flex-wrap gap-2">
                        {config.attribute_mapping && (
                          <span className="text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                            Attribute Mapping
                          </span>
                        )}
                        {config.role_mapping && (
                          <span className="text-xs px-2 py-1 rounded-full bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200">
                            Role Mapping
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
