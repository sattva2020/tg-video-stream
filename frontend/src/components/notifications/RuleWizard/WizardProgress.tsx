import React from 'react';
import { Check } from 'lucide-react';

export interface WizardStep {
  id: number;
  title: string;
  description?: string;
}

interface WizardProgressProps {
  steps: WizardStep[];
  currentStep: number;
  onStepClick?: (step: number) => void;
  /** Разрешить клик только на пройденные шаги */
  allowClickOnCompleted?: boolean;
}

/**
 * Компонент индикатора прогресса wizard.
 * Показывает текущий шаг и позволяет навигацию по пройденным шагам.
 */
export const WizardProgress: React.FC<WizardProgressProps> = ({
  steps,
  currentStep,
  onStepClick,
  allowClickOnCompleted = true,
}) => {
  const handleStepClick = (stepId: number) => {
    if (!onStepClick) return;
    if (allowClickOnCompleted && stepId < currentStep) {
      onStepClick(stepId);
    }
  };

  return (
    <div className="w-full">
      {/* Desktop view - горизонтальный */}
      <div className="hidden sm:flex items-center justify-between">
        {steps.map((step, index) => {
          const isCompleted = step.id < currentStep;
          const isCurrent = step.id === currentStep;
          const isClickable = allowClickOnCompleted && isCompleted && onStepClick;

          return (
            <React.Fragment key={step.id}>
              {/* Step indicator */}
              <div className="flex flex-col items-center">
                <button
                  type="button"
                  onClick={() => handleStepClick(step.id)}
                  disabled={!isClickable}
                  className={`
                    w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold
                    transition-all duration-200
                    ${isCompleted
                      ? 'bg-green-500 text-white cursor-pointer hover:bg-green-600'
                      : isCurrent
                        ? 'bg-[color:var(--color-accent)] text-white ring-4 ring-[color:var(--color-accent)]/20'
                        : 'bg-[color:var(--color-surface-muted)] text-[color:var(--color-text-secondary)] border-2 border-[color:var(--color-border)]'
                    }
                    ${isClickable ? 'cursor-pointer' : 'cursor-default'}
                  `}
                  aria-current={isCurrent ? 'step' : undefined}
                >
                  {isCompleted ? <Check className="w-5 h-5" /> : step.id}
                </button>
                <span className={`
                  mt-2 text-sm font-medium
                  ${isCurrent ? 'text-[color:var(--color-accent)]' : 'text-[color:var(--color-text-secondary)]'}
                `}>
                  {step.title}
                </span>
                {step.description && (
                  <span className="text-xs text-[color:var(--color-text-secondary)] mt-0.5">
                    {step.description}
                  </span>
                )}
              </div>

              {/* Connector line */}
              {index < steps.length - 1 && (
                <div className={`
                  flex-1 h-0.5 mx-4
                  ${step.id < currentStep ? 'bg-green-500' : 'bg-[color:var(--color-border)]'}
                `} />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Mobile view - вертикальный компактный */}
      <div className="sm:hidden">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-[color:var(--color-accent)]">
            Шаг {currentStep} из {steps.length}
          </span>
          <span className="text-sm text-[color:var(--color-text-secondary)]">
            {steps.find(s => s.id === currentStep)?.title}
          </span>
        </div>
        <div className="flex gap-1">
          {steps.map((step) => (
            <div
              key={step.id}
              className={`
                h-1 flex-1 rounded-full transition-colors
                ${step.id < currentStep
                  ? 'bg-green-500'
                  : step.id === currentStep
                    ? 'bg-[color:var(--color-accent)]'
                    : 'bg-[color:var(--color-border)]'
                }
              `}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default WizardProgress;
