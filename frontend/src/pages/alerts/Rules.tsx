import React, { useMemo, useState } from 'react';
import { AppLayout } from '../../components/layout';
import { AlertsNav, AlertRuleList, AlertRuleDetail, AlertRuleWizard } from '../../components/alerts';
import {
  useAlertRules,
  useCreateAlertRule,
  useUpdateAlertRule,
  useDeleteAlertRule,
  useTestAlert,
} from '../../hooks/useAlerts';
import type { AlertRule, AlertRuleCreate } from '../../api/alerts';
import { useToast } from '../../hooks/useToast';
import { Plus } from 'lucide-react';

// View modes
type ViewMode = 'list' | 'detail' | 'wizard';

const RulesPage: React.FC = () => {
  const toast = useToast();

  const { data: rules = [], isLoading: rulesLoading } = useAlertRules();
  const createRule = useCreateAlertRule();
  const updateRule = useUpdateAlertRule();
  const deleteRule = useDeleteAlertRule();
  const testAlert = useTestAlert();

  // View mode
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [selectedRuleId, setSelectedRuleId] = useState<string | null>(null);
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);

  const busy = createRule.isPending || updateRule.isPending || deleteRule.isPending || testAlert.isPending;

  // Open detail view
  const openDetail = (ruleId: string) => {
    setSelectedRuleId(ruleId);
    setViewMode('detail');
  };

  // Close detail
  const closeDetail = () => {
    setSelectedRuleId(null);
    setViewMode('list');
  };

  // Open wizard for creating
  const openCreateWizard = () => {
    setEditingRule(null);
    setViewMode('wizard');
  };

  // Open wizard for editing
  const openEditWizard = (rule: AlertRule) => {
    setEditingRule(rule);
    setViewMode('wizard');
  };

  // Close wizard
  const closeWizard = () => {
    setEditingRule(null);
    setViewMode('list');
  };

  // Handle save from wizard
  const handleWizardSave = async (data: AlertRuleCreate) => {
    try {
      if (editingRule) {
        await updateRule.mutateAsync({ id: editingRule.id, data });
        toast.success('Alert rule updated');
      } else {
        await createRule.mutateAsync(data);
        toast.success('Alert rule created');
      }
      closeWizard();
    } catch (err) {
      toast.error(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Handle toggle enabled
  const handleToggleEnabled = async (rule: AlertRule) => {
    try {
      await updateRule.mutateAsync({ id: rule.id, data: { enabled: !rule.enabled } });
      toast.success(rule.enabled ? 'Alert rule disabled' : 'Alert rule enabled');
    } catch (err) {
      toast.error(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Handle delete
  const handleDelete = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this alert rule?')) return;
    try {
      await deleteRule.mutateAsync(ruleId);
      toast.success('Alert rule deleted');
      if (selectedRuleId === ruleId) {
        closeDetail();
      }
    } catch (err) {
      toast.error(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Handle test
  const handleTest = async (ruleId: string) => {
    try {
      await testAlert.mutateAsync(ruleId);
      toast.success('Test alert sent');
    } catch (err) {
      toast.error(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // ===============================================
  // DETAIL MODE
  // ===============================================
  if (viewMode === 'detail' && selectedRuleId) {
    return (
      <AppLayout>
        <div className="mx-auto max-w-7xl">
          <AlertRuleDetail
            ruleId={selectedRuleId}
            onBack={closeDetail}
            onEdit={(rule) => openEditWizard(rule)}
            onDelete={handleDelete}
            onTest={handleTest}
          />
        </div>
      </AppLayout>
    );
  }

  // ===============================================
  // WIZARD MODE
  // ===============================================
  if (viewMode === 'wizard') {
    return (
      <AppLayout>
        <div className="mx-auto max-w-7xl">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-semibold">
                {editingRule ? 'Edit Alert Rule' : 'New Alert Rule'}
              </h1>
              <p className="text-sm text-[color:var(--color-text-secondary)]">
                Configure alert conditions and notification settings
              </p>
            </div>
            <button
              onClick={closeWizard}
              className="inline-flex items-center gap-2 rounded-lg border border-[color:var(--color-border)] px-3 py-2 text-sm hover:bg-white/5"
            >
              Close
            </button>
          </div>

          <div className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] shadow-sm overflow-hidden min-h-[600px]">
            <AlertRuleWizard
              initialData={editingRule || undefined}
              onSave={handleWizardSave}
              onCancel={closeWizard}
              loading={busy}
            />
          </div>
        </div>
      </AppLayout>
    );
  }

  // ===============================================
  // LIST MODE
  // ===============================================
  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl">
        <AlertsNav />
        <div className="flex flex-col gap-2 mb-6">
          <h1 className="text-2xl font-semibold">Alerts: Rules</h1>
          <p className="text-sm text-[color:var(--color-text-secondary)]">
            Configure alert rules for stream failures, low viewer count, API rate limits, and system resources.
          </p>
        </div>

        <section className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-panel)] p-4 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Alert Rules</h2>
            <button
              className="inline-flex items-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-3 py-2 text-sm text-white hover:opacity-90"
              onClick={openCreateWizard}
              disabled={busy}
            >
              <Plus className="w-4 h-4" /> New Rule
            </button>
          </div>

          <AlertRuleList
            rules={rules}
            loading={rulesLoading}
            onRuleClick={openDetail}
            onToggleEnabled={handleToggleEnabled}
            onEdit={openEditWizard}
            onDelete={handleDelete}
            onTest={handleTest}
          />
        </section>
      </div>
    </AppLayout>
  );
};

export default RulesPage;
