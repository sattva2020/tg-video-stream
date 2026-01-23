import React from 'react';
import { ChevronLeft, ChevronRight, Check, AlertTriangle } from 'lucide-react';
import { WizardProgress } from './wizard/WizardProgress';
import { AlertStepBasic } from './wizard/AlertStepBasic';
import { AlertStepConditions } from './wizard/AlertStepConditions';
import { AlertStepNotifications } from './wizard/AlertStepNotifications';
import {
  emptyAlertRuleFormState,
  ALERT_WIZARD_STEPS,
  type AlertRuleFormState,
  type AlertWizardStep,
} from './wizard/types';
import type { AlertRule } from '../../api/alerts';
import type {
  NotificationChannel,
} from '../../api/notifications';

export interface AlertRuleWizardProps {
  /** Начальные данные (для редактирования) */
  initialData?: Partial<AlertRuleFormState>;
  /** Callback при сохранении */
  onSave: (data: AlertRuleFormState) => void;
  /** Callback при отмене */
  onCancel: () => void;
  /** Загрузка (сохранение) */
  loading?: boolean;
  /** Доступные каналы */
  channels: NotificationChannel[];
}

/**
 * Wizard для создания/редактирования правила алертов.
 * 3 шага: Основные → Условия → Уведомления
 */
export const AlertRuleWizard: React.FC<AlertRuleWizardProps> = ({
  initialData,
  onSave,
  onCancel,
  loading = false,
  channels,
}) => {
  // Состояние формы
  const [form, setForm] = React.useState<AlertRuleFormState>(() => ({
    ...emptyAlertRuleFormState,
    ...initialData,
  }));

  // Текущий шаг
  const [currentStep, setCurrentStep] = React.useState<AlertWizardStep>(1);

  // Пройденные шаги (для навигации назад)
  const [completedSteps, setCompletedSteps] = React.useState<Set<AlertWizardStep>>(new Set());

  // Ошибки валидации
  const [validationErrors, setValidationErrors] = React.useState<string[]>([]);

  // Обновление формы
  const updateForm = (updates: Partial<AlertRuleFormState>) => {
    setForm((prev) => ({ ...prev, ...updates }));
    // Очищаем ошибки при изменении формы
    if (validationErrors.length > 0) {
      setValidationErrors([]);
    }
  };

  // Валидация шагов
  const validateStep = (step: AlertWizardStep): { valid: boolean; errors: string[] } => {
    const errors: string[] = [];

    switch (step) {
      case 1:
        if (!form.name.trim()) {
          errors.push('Название правила обязательно');
        }
        if (!form.alert_type) {
          errors.push('Выберите тип алерта');
        }
        if (!form.severity) {
          errors.push('Выберите уровень важности');
        }
        break;

      case 2:
        // Условия могут быть пустыми для некоторых типов алертов
        break;

      case 3:
        if (form.channelIds.length === 0) {
          errors.push('Выберите хотя бы один канал уведомлений');
        }
        break;
    }

    return { valid: errors.length === 0, errors };
  };

  // Переход на следующий шаг
  const goNext = () => {
    const validation = validateStep(currentStep);
    if (!validation.valid) {
      setValidationErrors(validation.errors);
      return;
    }

    setCompletedSteps((prev) => new Set(prev).add(currentStep));

    if (currentStep < 3) {
      setCurrentStep((currentStep + 1) as AlertWizardStep);
    }
  };

  // Переход на предыдущий шаг
  const goBack = () => {
    if (currentStep > 1) {
      setCurrentStep((currentStep - 1) as AlertWizardStep);
      setValidationErrors([]);
    }
  };

  // Переход к конкретному шагу (только назад или к пройденным)
  const goToStep = (step: AlertWizardStep) => {
    if (step < currentStep || completedSteps.has(step)) {
      setCurrentStep(step);
      setValidationErrors([]);
    }
  };

  // Сохранение
  const handleSave = () => {
    const validation = validateStep(3);
    if (!validation.valid) {
      setValidationErrors(validation.errors);
      return;
    }
    onSave(form);
  };

  // Проверка всех шагов для финальной валидации
  const canSave =
    form.name.trim() !== '' &&
    form.alert_type !== '' &&
    form.severity !== '' &&
    form.channelIds.length > 0;

  // Предупреждения (не блокируют, но показываем)
  const warnings: string[] = [];
  if (Object.keys(form.conditions).length === 0) {
    warnings.push('Условия не заданы — алерт может срабатывать некорректно');
  }
  if (form.cooldown_sec === 0 && !form.rate_limit_count) {
    warnings.push('Не задан cooldown или rate limit — возможны частые уведомления');
  }

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      {/* Прогресс */}
      <div className="px-6 py-4 border-b border-[color:var(--color-border)]">
        <WizardProgress
          steps={ALERT_WIZARD_STEPS.map(s => ({ id: s.step, title: s.title, description: s.description }))}
          currentStep={currentStep}
          onStepClick={(step) => goToStep(step as AlertWizardStep)}
          allowClickOnCompleted={true}
        />
      </div>

      {/* Ошибки валидации */}
      {validationErrors.length > 0 && (
        <div className="mx-6 mt-4 rounded-lg border border-red-500/30 bg-red-500/10 p-4">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-400 mb-1">Ошибки валидации:</p>
              {validationErrors.map((err, i) => (
                <p key={i} className="text-sm text-red-300">
                  • {err}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Контент шага */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {currentStep === 1 && (
          <AlertStepBasic form={form} onChange={updateForm} disabled={loading} />
        )}

        {currentStep === 2 && (
          <AlertStepConditions form={form} onChange={updateForm} disabled={loading} />
        )}

        {currentStep === 3 && (
          <AlertStepNotifications
            form={form}
            onChange={updateForm}
            disabled={loading}
            channels={channels}
          />
        )}

        {/* Предупреждения */}
        {currentStep === 3 && warnings.length > 0 && (
          <div className="mt-4 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4">
            <div className="flex items-start gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div>
                {warnings.map((w, i) => (
                  <p key={i} className="text-sm text-yellow-300">
                    {w}
                  </p>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Навигация */}
      <div className="px-6 py-4 border-t border-[color:var(--color-border)] flex items-center justify-between">
        <div>
          {currentStep > 1 ? (
            <button
              type="button"
              onClick={goBack}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg border border-[color:var(--color-border)] px-4 py-2 text-sm hover:bg-white/5 disabled:opacity-50"
            >
              <ChevronLeft className="w-4 h-4" />
              Назад
            </button>
          ) : (
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg border border-[color:var(--color-border)] px-4 py-2 text-sm hover:bg-white/5 disabled:opacity-50"
            >
              Отмена
            </button>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Индикатор шага */}
          <span className="text-sm text-[color:var(--color-text-secondary)]">
            Шаг {currentStep} из 3
          </span>

          {currentStep < 3 ? (
            <button
              type="button"
              onClick={goNext}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-[color:var(--color-accent)] px-4 py-2 text-sm text-white hover:opacity-90 disabled:opacity-50"
            >
              Далее
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSave}
              disabled={loading || !canSave}
              className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <span className="animate-spin">⏳</span>
                  Сохранение...
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  Создать правило
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default AlertRuleWizard;
