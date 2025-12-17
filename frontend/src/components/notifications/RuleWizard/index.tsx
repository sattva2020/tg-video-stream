import React from 'react';
import { ChevronLeft, ChevronRight, Check, AlertTriangle } from 'lucide-react';
import { WizardProgress } from './WizardProgress';
import { StepBasic } from './StepBasic';
import { StepFilters } from './StepFilters';
import { StepDelivery } from './StepDelivery';
import {
  emptyRuleFormState,
  WIZARD_STEPS,
  type RuleFormState,
  type WizardStep,
} from './types';
import type {
  NotificationChannel,
  NotificationRecipient,
  NotificationTemplate,
} from '../../../api/notifications';

export interface RuleWizardProps {
  /** Начальные данные (для редактирования) */
  initialData?: Partial<RuleFormState>;
  /** Callback при сохранении */
  onSave: (data: RuleFormState) => void;
  /** Callback при отмене */
  onCancel: () => void;
  /** Загрузка (сохранение) */
  loading?: boolean;
  /** Доступные каналы */
  channels: NotificationChannel[];
  /** Доступные получатели */
  recipients: NotificationRecipient[];
  /** Доступные шаблоны */
  templates: NotificationTemplate[];
}

/**
 * Wizard для создания/редактирования правила уведомлений.
 * 3 шага: Основные → Фильтры → Доставка
 */
export const RuleWizard: React.FC<RuleWizardProps> = ({
  initialData,
  onSave,
  onCancel,
  loading = false,
  channels,
  recipients,
  templates,
}) => {
  // Состояние формы
  const [form, setForm] = React.useState<RuleFormState>(() => ({
    ...emptyRuleFormState,
    ...initialData,
  }));

  // Текущий шаг
  const [currentStep, setCurrentStep] = React.useState<WizardStep>(1);

  // Пройденные шаги (для навигации назад)
  const [completedSteps, setCompletedSteps] = React.useState<Set<WizardStep>>(new Set());

  // Обновление формы
  const updateForm = (updates: Partial<RuleFormState>) => {
    setForm((prev) => ({ ...prev, ...updates }));
  };

  // Валидация шагов
  const validateStep = (step: WizardStep): { valid: boolean; errors: string[] } => {
    const errors: string[] = [];

    switch (step) {
      case 1:
        if (!form.name.trim()) {
          errors.push('Название правила обязательно');
        }
        break;

      case 2:
        // Фильтры опциональны, но предупреждаем если пусто
        break;

      case 3:
        if (form.recipientIds.length === 0) {
          errors.push('Выберите хотя бы одного получателя');
        }
        if (form.channelIds.length === 0) {
          errors.push('Добавьте хотя бы один канал доставки');
        }
        break;
    }

    return { valid: errors.length === 0, errors };
  };

  // Переход на следующий шаг
  const goNext = () => {
    const validation = validateStep(currentStep);
    if (!validation.valid) {
      // TODO: показать ошибки
      return;
    }

    setCompletedSteps((prev) => new Set(prev).add(currentStep));

    if (currentStep < 3) {
      setCurrentStep((currentStep + 1) as WizardStep);
    }
  };

  // Переход на предыдущий шаг
  const goBack = () => {
    if (currentStep > 1) {
      setCurrentStep((currentStep - 1) as WizardStep);
    }
  };

  // Переход к конкретному шагу (только назад или к пройденным)
  const goToStep = (step: WizardStep) => {
    if (step < currentStep || completedSteps.has(step)) {
      setCurrentStep(step);
    }
  };

  // Сохранение
  const handleSave = () => {
    const validation = validateStep(3);
    if (!validation.valid) {
      return;
    }
    onSave(form);
  };

  // Проверка всех шагов для финальной валидации
  const canSave =
    form.name.trim() !== '' &&
    form.recipientIds.length > 0 &&
    form.channelIds.length > 0;

  // Предупреждения (не блокируют, но показываем)
  const warnings: string[] = [];
  if (
    form.severityLevels.length === 0 &&
    form.tagConditions.length === 0 &&
    form.hostConditions.length === 0
  ) {
    warnings.push('Нет фильтров — правило будет срабатывать на все события');
  }

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      {/* Прогресс */}
      <div className="px-6 py-4 border-b border-[color:var(--color-border)]">
        <WizardProgress
          steps={WIZARD_STEPS.map(s => ({ id: s.step, title: s.title, description: s.description }))}
          currentStep={currentStep}
          onStepClick={(step) => goToStep(step as WizardStep)}
          allowClickOnCompleted={true}
        />
      </div>

      {/* Контент шага */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {currentStep === 1 && (
          <StepBasic form={form} onChange={updateForm} disabled={loading} />
        )}

        {currentStep === 2 && (
          <StepFilters form={form} onChange={updateForm} disabled={loading} />
        )}

        {currentStep === 3 && (
          <StepDelivery
            form={form}
            onChange={updateForm}
            disabled={loading}
            channels={channels}
            recipients={recipients}
            templates={templates}
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
              className="inline-flex items-center gap-2 rounded-lg border border-[color:var(--color-border)] px-4 py-2 text-sm hover:bg-white/5"
            >
              <ChevronLeft className="w-4 h-4" />
              Назад
            </button>
          ) : (
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg border border-[color:var(--color-border)] px-4 py-2 text-sm hover:bg-white/5"
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
              disabled={loading || (currentStep === 1 && !form.name.trim())}
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
                  Сохранить правило
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default RuleWizard;

// Реэкспорт типов
export * from './types';
