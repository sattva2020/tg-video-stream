/**
 * Страница настроек приложения.
 * 
 * Позволяет администраторам управлять:
 * - API ключами AI провайдеров
 * - Другими настройками приложения
 */

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Settings, 
  Eye, 
  EyeOff, 
  Save, 
  Trash2, 
  CheckCircle, 
  XCircle,
  RefreshCw,
  Cpu,
  Plug,
  Bell,
  Shield,
  Send,
  ExternalLink,
  AlertTriangle,
  Info
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { AppLayout } from '../../components/layout';
import { client as api } from '../../api/client';

// === Types ===

interface SettingMetadata {
  icon?: string;
  provider?: string;
  docs_url?: string;
  options?: Array<{ value: string; label: string }>;
}

interface AppSetting {
  id: string;
  key: string;
  display_name: string;
  description: string | null;
  category: string;
  value_type: string;
  is_secret: boolean;
  is_editable: boolean;
  has_value: boolean;
  value: string | null;
  from_env?: boolean;
  default_value: string | null;
  validation_pattern: string | null;
  validation_message: string | null;
  metadata: SettingMetadata | null;
  updated_at: string | null;
}

interface SettingsCategory {
  key: string;
  name: string;
  icon: string;
  settings: AppSetting[];
}

interface AIStatus {
  active_provider: string | null;
  providers: Record<string, { configured: boolean; is_active: boolean }>;
}

interface TestResult {
  success: boolean;
  provider?: string;
  models_available?: number;
  message?: string;
  error?: string;
}

// === Component ===

const SettingsPage: React.FC = () => {
  const { user } = useAuth();
  
  // State
  const [categories, setCategories] = useState<SettingsCategory[]>([]);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>('ai_providers');
  
  // Edit state
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  
  // Success/error messages
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // === Data fetching ===
  
  const fetchSettings = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/admin/settings');
      setCategories(response.data.categories || []);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка загрузки настроек');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAiStatus = useCallback(async () => {
    try {
      const response = await api.get('/api/admin/settings/ai/status');
      setAiStatus(response.data);
    } catch (err) {
      console.error('Failed to fetch AI status:', err);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
    fetchAiStatus();
  }, [fetchSettings, fetchAiStatus]);

  // === Actions ===

  const handleEdit = (setting: AppSetting) => {
    setEditingKey(setting.key);
    setEditValue(setting.is_secret ? '' : (setting.value || ''));
  };

  const handleSave = async (key: string) => {
    if (!editValue.trim()) {
      setError('Значение не может быть пустым');
      return;
    }

    try {
      setSaving(key);
      await api.put(`/api/admin/settings/${key}`, { value: editValue });
      setEditingKey(null);
      setEditValue('');
      setSuccessMessage(`Настройка ${key} успешно сохранена`);
      setTimeout(() => setSuccessMessage(null), 3000);
      await fetchSettings();
      await fetchAiStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка сохранения');
    } finally {
      setSaving(null);
    }
  };

  const handleDelete = async (key: string) => {
    if (!confirm('Удалить значение? Будет использоваться значение из .env (если есть)')) {
      return;
    }

    try {
      setSaving(key);
      await api.delete(`/api/admin/settings/${key}`);
      setSuccessMessage(`Значение ${key} удалено`);
      setTimeout(() => setSuccessMessage(null), 3000);
      await fetchSettings();
      await fetchAiStatus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка удаления');
    } finally {
      setSaving(null);
    }
  };

  const handleTestKey = async (setting: AppSetting) => {
    const provider = setting.metadata?.provider;
    if (!provider) return;

    // Используем введённое значение или текущее
    const keyToTest = editingKey === setting.key ? editValue : null;
    
    if (!keyToTest && !setting.has_value) {
      setError('Сначала введите API ключ');
      return;
    }

    try {
      setTesting(setting.key);
      const response = await api.post('/api/admin/settings/test-api-key', {
        provider,
        api_key: keyToTest || 'use_stored' // Backend должен использовать сохранённый ключ
      });
      setTestResults(prev => ({ ...prev, [setting.key]: response.data }));
    } catch (err: any) {
      setTestResults(prev => ({
        ...prev,
        [setting.key]: {
          success: false,
          error: err.response?.data?.detail || 'Ошибка проверки'
        }
      }));
    } finally {
      setTesting(null);
    }
  };

  const handleInitialize = async () => {
    try {
      setLoading(true);
      await api.post('/api/admin/settings/initialize');
      await fetchSettings();
      setSuccessMessage('Настройки инициализированы');
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка инициализации');
    } finally {
      setLoading(false);
    }
  };

  // === Helpers ===

  const getCategoryIcon = (iconName: string) => {
    const icons: Record<string, React.ReactNode> = {
      cpu: <Cpu className="w-5 h-5" />,
      plug: <Plug className="w-5 h-5" />,
      bell: <Bell className="w-5 h-5" />,
      shield: <Shield className="w-5 h-5" />,
      settings: <Settings className="w-5 h-5" />,
      send: <Send className="w-5 h-5" />,
    };
    return icons[iconName] || <Settings className="w-5 h-5" />;
  };

  const toggleSecretVisibility = (key: string) => {
    setShowSecrets(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // === Render ===

  if (loading && categories.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  const currentCategory = categories.find(c => c.key === activeCategory);

  return (
    <AppLayout>
    <div className="container mx-auto max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Settings className="w-8 h-8 text-blue-500" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Настройки приложения
          </h1>
        </div>
        <button
          onClick={handleInitialize}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Инициализировать
        </button>
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-700 dark:text-red-400">
          <XCircle className="w-5 h-5 flex-shrink-0" />
          {error}
          <button onClick={() => setError(null)} className="ml-auto text-red-500 hover:text-red-700">×</button>
        </div>
      )}

      {successMessage && (
        <div className="mb-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-center gap-2 text-green-700 dark:text-green-400">
          <CheckCircle className="w-5 h-5 flex-shrink-0" />
          {successMessage}
        </div>
      )}

      {/* AI Status Banner */}
      {aiStatus && activeCategory === 'ai_providers' && (
        <div className="mb-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
          <div className="flex items-center gap-2 mb-2">
            <Cpu className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            <span className="font-medium text-purple-900 dark:text-purple-100">
              Статус AI
            </span>
          </div>
          <div className="flex flex-wrap gap-3">
            {Object.entries(aiStatus.providers).map(([provider, status]) => (
              <div
                key={provider}
                className={`px-3 py-1.5 rounded-full text-sm flex items-center gap-2 ${
                  status.is_active
                    ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                    : status.configured
                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400'
                }`}
              >
                {status.is_active && <CheckCircle className="w-4 h-4" />}
                {status.configured && !status.is_active && <Info className="w-4 h-4" />}
                {!status.configured && <XCircle className="w-4 h-4" />}
                <span className="capitalize">{provider}</span>
              </div>
            ))}
          </div>
          {aiStatus.active_provider && (
            <p className="mt-2 text-sm text-purple-700 dark:text-purple-300">
              Активный провайдер: <strong className="capitalize">{aiStatus.active_provider}</strong>
            </p>
          )}
        </div>
      )}

      {/* Layout */}
      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-56 flex-shrink-0">
          <nav className="space-y-1">
            {categories.map(category => (
              <button
                key={category.key}
                onClick={() => setActiveCategory(category.key)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-colors ${
                  activeCategory === category.key
                    ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
              >
                {getCategoryIcon(category.icon)}
                <span className="font-medium">{category.name}</span>
                <span className="ml-auto text-xs bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded-full">
                  {category.settings.length}
                </span>
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {currentCategory && (
            <div className="space-y-4">
              {currentCategory.settings.map(setting => (
                <div
                  key={setting.id}
                  className="p-5 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm"
                >
                  {/* Setting Header */}
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                        {setting.display_name}
                        {setting.is_secret && (
                          <span className="text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 px-2 py-0.5 rounded">
                            Секрет
                          </span>
                        )}
                        {setting.from_env && (
                          <span className="text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded">
                            из .env
                          </span>
                        )}
                      </h3>
                      {setting.description && (
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          {setting.description}
                        </p>
                      )}
                    </div>
                    
                    {setting.metadata?.docs_url && (
                      <a
                        href={setting.metadata.docs_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-gray-400 hover:text-blue-500 transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                  </div>

                  {/* Setting Value */}
                  {editingKey === setting.key ? (
                    <div className="space-y-3">
                      <div className="relative">
                        <input
                          type={setting.is_secret && !showSecrets[setting.key] ? 'password' : 'text'}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          placeholder={setting.default_value || `Введите ${setting.display_name}`}
                          className="w-full px-4 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                        {setting.is_secret && (
                          <button
                            type="button"
                            onClick={() => toggleSecretVisibility(setting.key)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                          >
                            {showSecrets[setting.key] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                        )}
                      </div>
                      
                      {setting.validation_message && (
                        <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" />
                          {setting.validation_message}
                        </p>
                      )}

                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleSave(setting.key)}
                          disabled={saving === setting.key}
                          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                        >
                          {saving === setting.key ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          ) : (
                            <Save className="w-4 h-4" />
                          )}
                          Сохранить
                        </button>
                        <button
                          onClick={() => { setEditingKey(null); setEditValue(''); }}
                          className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        >
                          Отмена
                        </button>
                        
                        {setting.metadata?.provider && editValue && (
                          <button
                            onClick={() => handleTestKey(setting)}
                            disabled={testing === setting.key}
                            className="flex items-center gap-2 px-4 py-2 ml-auto bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded-lg hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors"
                          >
                            {testing === setting.key ? (
                              <RefreshCw className="w-4 h-4 animate-spin" />
                            ) : (
                              <CheckCircle className="w-4 h-4" />
                            )}
                            Проверить
                          </button>
                        )}
                      </div>
                    </div>
                  ) : setting.value_type === 'select' && setting.metadata?.options ? (
                    <select
                      value={setting.value || setting.default_value || ''}
                      onChange={(e) => {
                        setEditingKey(setting.key);
                        setEditValue(e.target.value);
                        // Auto-save for selects
                        api.put(`/api/admin/settings/${setting.key}`, { value: e.target.value })
                          .then(() => {
                            setEditingKey(null);
                            fetchSettings();
                            fetchAiStatus();
                          });
                      }}
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                    >
                      {setting.metadata.options.map(opt => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {setting.has_value ? (
                          <>
                            <CheckCircle className="w-5 h-5 text-green-500" />
                            <span className="text-gray-600 dark:text-gray-400">
                              {setting.is_secret ? '••••••••' : setting.value}
                            </span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-5 h-5 text-gray-400" />
                            <span className="text-gray-400 italic">Не задано</span>
                          </>
                        )}
                      </div>
                      
                      <div className="flex items-center gap-2">
                        {setting.is_editable && (
                          <button
                            onClick={() => handleEdit(setting)}
                            className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                          >
                            {setting.has_value ? 'Изменить' : 'Добавить'}
                          </button>
                        )}
                        
                        {setting.has_value && !setting.from_env && (
                          <button
                            onClick={() => handleDelete(setting.key)}
                            disabled={saving === setting.key}
                            className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                            title="Удалить значение"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Test Result */}
                  {testResults[setting.key] && (
                    <div className={`mt-3 p-3 rounded-lg ${
                      testResults[setting.key].success
                        ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400'
                        : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
                    }`}>
                      {testResults[setting.key].success ? (
                        <div className="flex items-center gap-2">
                          <CheckCircle className="w-4 h-4" />
                          {testResults[setting.key].message}
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <XCircle className="w-4 h-4" />
                          {testResults[setting.key].error}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}

              {currentCategory.settings.length === 0 && (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Нет настроек в этой категории</p>
                  <button
                    onClick={handleInitialize}
                    className="mt-4 text-blue-500 hover:underline"
                  >
                    Инициализировать настройки
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
    </AppLayout>
  );
};

export default SettingsPage;
