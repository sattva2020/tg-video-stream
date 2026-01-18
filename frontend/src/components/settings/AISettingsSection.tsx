/**
 * Компонент настроек AI/LLM для SuperAdmin.
 * 
 * Позволяет настраивать и переключать AI-провайдеры
 * для ChatOps бота и Anomaly Detection.
 * 
 * Автор: Jarvis
 * Дата: 2025-12-29
 */
import React, { useState, useEffect, useCallback } from 'react';
import { 
  Bot, 
  Sparkles, 
  Check, 
  X, 
  Loader2, 
  RefreshCw,
  Eye,
  EyeOff,
  ChevronDown,
  ChevronUp,
  Zap,
  Brain,
  AlertTriangle
} from 'lucide-react';
import { client as api } from '../../api/client';

// ============================================
// ТИПЫ
// ============================================

interface AIProvider {
  id: string;
  name: string;
  enabled: boolean;
  api_key: string | null;
  base_url: string | null;
  model: string;
  description: string | null;
}

interface AISettings {
  active_provider: string;
  providers: AIProvider[];
  chatops_enabled: boolean;
  anomaly_detection_enabled: boolean;
}

interface ModelOption {
  id: string;
  name: string;
}

// ============================================
// ИКОНКИ ПРОВАЙДЕРОВ
// ============================================

const ProviderIcons: Record<string, React.ReactNode> = {
  openai: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
      <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.8956zm16.0993 3.8558L12.6 8.3829l2.02-1.1638a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z"/>
    </svg>
  ),
  anthropic: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
      <path d="M17.304 3.541h-3.672l6.696 16.918h3.672L17.304 3.541zm-10.608 0L0 20.459h3.744l1.368-3.6h7.056l1.368 3.6h3.744L10.608 3.541H6.696zm.456 10.284l2.496-6.576 2.496 6.576H7.152z"/>
    </svg>
  ),
  gemini: (
    <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor">
      <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm0 4.8c3.979 0 7.2 3.221 7.2 7.2s-3.221 7.2-7.2 7.2-7.2-3.221-7.2-7.2S8.021 4.8 12 4.8z"/>
    </svg>
  ),
  openrouter: <Zap className="w-5 h-5" />,
  deepseek: <Brain className="w-5 h-5" />,
  qwen: <Sparkles className="w-5 h-5" />,
  zai: <Bot className="w-5 h-5" />,
};

// ============================================
// КОМПОНЕНТ
// ============================================

const AISettingsSection: React.FC = () => {
  // Состояние
  const [settings, setSettings] = useState<AISettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // UI состояние
  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);
  const [showApiKeys, setShowApiKeys] = useState<Record<string, boolean>>({});
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<Record<string, { success: boolean; message: string } | null>>({});
  
  // Локальные изменения (до сохранения)
  const [localProviders, setLocalProviders] = useState<AIProvider[]>([]);
  const [availableModels, setAvailableModels] = useState<Record<string, ModelOption[]>>({});

  // ============================================
  // ЗАГРУЗКА ДАННЫХ
  // ============================================

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/api/admin/ai-settings');
      setSettings(response.data);
      setLocalProviders(response.data.providers);
    } catch (err: any) {
      console.error('Failed to load AI settings:', err);
      if (err.response?.status === 403) {
        setError('Доступ запрещён. Только SUPERADMIN может управлять AI настройками.');
      } else {
        setError('Не удалось загрузить настройки AI');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // ============================================
  // ЗАГРУЗКА МОДЕЛЕЙ
  // ============================================

  const loadModels = useCallback(async (providerId: string) => {
    if (availableModels[providerId]) return; // Уже загружено
    
    try {
      const response = await api.get(`/api/admin/ai-settings/available-models/${providerId}`);
      setAvailableModels(prev => ({
        ...prev,
        [providerId]: response.data
      }));
    } catch (err) {
      console.error(`Failed to load models for ${providerId}:`, err);
    }
  }, [availableModels]);

  // ============================================
  // СОХРАНЕНИЕ
  // ============================================

  const saveSettings = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    
    try {
      const response = await api.put('/api/admin/ai-settings', {
        active_provider: settings?.active_provider,
        providers: localProviders,
        chatops_enabled: settings?.chatops_enabled,
        anomaly_detection_enabled: settings?.anomaly_detection_enabled,
      });
      
      setSettings(response.data);
      setLocalProviders(response.data.providers);
      setSuccess('Настройки AI сохранены!');
      
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      console.error('Failed to save AI settings:', err);
      setError(err.response?.data?.detail || 'Не удалось сохранить настройки');
    } finally {
      setSaving(false);
    }
  };

  // ============================================
  // ТЕСТ ПОДКЛЮЧЕНИЯ
  // ============================================

  const testConnection = async (provider: AIProvider) => {
    setTestingProvider(provider.id);
    setTestResult(prev => ({ ...prev, [provider.id]: null }));
    
    try {
      const response = await api.post('/api/admin/ai-settings/test-connection', {
        provider_id: provider.id,
        api_key: localProviders.find(p => p.id === provider.id)?.api_key || '',
        base_url: provider.base_url,
        model: provider.model,
      });
      
      setTestResult(prev => ({
        ...prev,
        [provider.id]: response.data
      }));
    } catch (err: any) {
      setTestResult(prev => ({
        ...prev,
        [provider.id]: {
          success: false,
          message: err.response?.data?.detail || 'Ошибка подключения'
        }
      }));
    } finally {
      setTestingProvider(null);
    }
  };

  // ============================================
  // ОБРАБОТЧИКИ
  // ============================================

  const updateProvider = (providerId: string, updates: Partial<AIProvider>) => {
    setLocalProviders(prev => 
      prev.map(p => p.id === providerId ? { ...p, ...updates } : p)
    );
  };

  const toggleProvider = (providerId: string) => {
    if (expandedProvider === providerId) {
      setExpandedProvider(null);
    } else {
      setExpandedProvider(providerId);
      loadModels(providerId);
    }
  };

  const setActiveProvider = (providerId: string) => {
    setSettings(prev => prev ? { ...prev, active_provider: providerId } : null);
  };

  // ============================================
  // РЕНДЕР
  // ============================================

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-6 h-6 animate-spin text-[color:var(--color-accent)]" />
        <span className="ml-2">Загрузка настроек AI...</span>
      </div>
    );
  }

  if (error && !settings) {
    return (
      <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
        <AlertTriangle className="w-5 h-5 inline mr-2" />
        {error}
      </div>
    );
  }

  return (
    <section className="mb-8">
      <h2 className="text-lg font-semibold mb-4 border-b border-[color:var(--color-border)] pb-2 flex items-center gap-2">
        <Bot className="w-5 h-5 text-[color:var(--color-accent)]" />
        AI / LLM Настройки
        <span className="text-xs font-normal text-[color:var(--color-text-secondary)] ml-2">
          (только SUPERADMIN)
        </span>
      </h2>

      {/* Уведомления */}
      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
          {error}
        </div>
      )}
      {success && (
        <div className="mb-4 p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400">
          {success}
        </div>
      )}

      {/* Глобальные переключатели */}
      <div className="grid gap-4 sm:grid-cols-2 mb-6">
        <div className="p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Bot className="w-5 h-5 text-blue-400" />
              <div>
                <p className="font-medium">ChatOps Bot</p>
                <p className="text-xs text-[color:var(--color-text-secondary)]">
                  Telegram бот для мониторинга
                </p>
              </div>
            </div>
            <button
              onClick={() => setSettings(prev => prev ? { ...prev, chatops_enabled: !prev.chatops_enabled } : null)}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                settings?.chatops_enabled 
                  ? 'bg-green-500' 
                  : 'bg-gray-600'
              }`}
            >
              <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                settings?.chatops_enabled ? 'left-7' : 'left-1'
              }`} />
            </button>
          </div>
        </div>

        <div className="p-4 rounded-lg bg-[color:var(--color-panel)] border border-[color:var(--color-border)]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Brain className="w-5 h-5 text-purple-400" />
              <div>
                <p className="font-medium">Anomaly Detection</p>
                <p className="text-xs text-[color:var(--color-text-secondary)]">
                  ML для предсказания проблем
                </p>
              </div>
            </div>
            <button
              onClick={() => setSettings(prev => prev ? { ...prev, anomaly_detection_enabled: !prev.anomaly_detection_enabled } : null)}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                settings?.anomaly_detection_enabled 
                  ? 'bg-green-500' 
                  : 'bg-gray-600'
              }`}
            >
              <span className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                settings?.anomaly_detection_enabled ? 'left-7' : 'left-1'
              }`} />
            </button>
          </div>
        </div>
      </div>

      {/* Список провайдеров */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-[color:var(--color-text-secondary)]">
          AI Провайдеры
        </h3>

        {localProviders.map(provider => {
          const isExpanded = expandedProvider === provider.id;
          const isActive = settings?.active_provider === provider.id;
          const test = testResult[provider.id];
          const hasKey = provider.api_key && !provider.api_key.includes('***') || localProviders.find(p => p.id === provider.id)?.api_key;

          return (
            <div 
              key={provider.id}
              className={`rounded-lg border transition-colors ${
                isActive 
                  ? 'border-[color:var(--color-accent)] bg-[color:var(--color-accent)]/5' 
                  : 'border-[color:var(--color-border)] bg-[color:var(--color-panel)]'
              }`}
            >
              {/* Заголовок провайдера */}
              <div 
                className="flex items-center justify-between p-4 cursor-pointer"
                onClick={() => toggleProvider(provider.id)}
              >
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    isActive ? 'bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)]' : 'bg-white/5'
                  }`}>
                    {ProviderIcons[provider.id] || <Bot className="w-5 h-5" />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{provider.name}</p>
                      {isActive && (
                        <span className="text-xs px-2 py-0.5 rounded-full bg-[color:var(--color-accent)] text-white">
                          Активный
                        </span>
                      )}
                      {hasKey && (
                        <Check className="w-4 h-4 text-green-400" />
                      )}
                    </div>
                    <p className="text-xs text-[color:var(--color-text-secondary)]">
                      {provider.model}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {!isActive && hasKey && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveProvider(provider.id);
                      }}
                      className="px-3 py-1 text-xs rounded-lg bg-[color:var(--color-accent)]/20 text-[color:var(--color-accent)] hover:bg-[color:var(--color-accent)]/30"
                    >
                      Сделать активным
                    </button>
                  )}
                  {isExpanded ? (
                    <ChevronUp className="w-5 h-5 text-[color:var(--color-text-secondary)]" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-[color:var(--color-text-secondary)]" />
                  )}
                </div>
              </div>

              {/* Развёрнутые настройки */}
              {isExpanded && (
                <div className="px-4 pb-4 space-y-4 border-t border-[color:var(--color-border)]">
                  <p className="text-sm text-[color:var(--color-text-secondary)] pt-3">
                    {provider.description}
                  </p>

                  {/* API Key */}
                  <div>
                    <label className="text-sm font-medium block mb-1">API Key</label>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <input
                          type={showApiKeys[provider.id] ? 'text' : 'password'}
                          value={localProviders.find(p => p.id === provider.id)?.api_key || ''}
                          onChange={(e) => updateProvider(provider.id, { api_key: e.target.value })}
                          placeholder="sk-..."
                          className="w-full px-3 py-2 pr-10 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-sm"
                        />
                        <button
                          type="button"
                          onClick={() => setShowApiKeys(prev => ({ ...prev, [provider.id]: !prev[provider.id] }))}
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-[color:var(--color-text-secondary)] hover:text-[color:var(--color-text)]"
                        >
                          {showApiKeys[provider.id] ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Model */}
                  <div>
                    <label className="text-sm font-medium block mb-1">Модель</label>
                    <select
                      value={localProviders.find(p => p.id === provider.id)?.model || provider.model}
                      onChange={(e) => updateProvider(provider.id, { model: e.target.value })}
                      className="w-full px-3 py-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-sm"
                    >
                      {(availableModels[provider.id] || [{ id: provider.model, name: provider.model }]).map(m => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                  </div>

                  {/* Base URL (для кастомных) */}
                  {provider.base_url && (
                    <div>
                      <label className="text-sm font-medium block mb-1">Base URL</label>
                      <input
                        type="text"
                        value={localProviders.find(p => p.id === provider.id)?.base_url || ''}
                        onChange={(e) => updateProvider(provider.id, { base_url: e.target.value })}
                        className="w-full px-3 py-2 rounded-lg border border-[color:var(--color-border)] bg-[color:var(--color-surface)] text-sm"
                      />
                    </div>
                  )}

                  {/* Тест подключения */}
                  <div className="flex items-center gap-3 pt-2">
                    <button
                      onClick={() => testConnection(localProviders.find(p => p.id === provider.id)!)}
                      disabled={testingProvider === provider.id || !localProviders.find(p => p.id === provider.id)?.api_key}
                      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] text-sm hover:border-[color:var(--color-accent)] disabled:opacity-50"
                    >
                      {testingProvider === provider.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4" />
                      )}
                      Тест подключения
                    </button>

                    {test && (
                      <div className={`flex items-center gap-2 text-sm ${test.success ? 'text-green-400' : 'text-red-400'}`}>
                        {test.success ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
                        {test.message}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Кнопка сохранения */}
      <div className="mt-6 flex justify-end">
        <button
          onClick={saveSettings}
          disabled={saving}
          className="flex items-center gap-2 px-6 py-2 rounded-lg bg-[color:var(--color-accent)] text-white font-medium hover:opacity-90 disabled:opacity-50"
        >
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Check className="w-4 h-4" />
          )}
          Сохранить настройки
        </button>
      </div>
    </section>
  );
};

export default AISettingsSection;
