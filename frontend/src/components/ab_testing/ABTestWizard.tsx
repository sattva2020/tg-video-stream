/**
 * ABTestWizard — Мастер создания A/B тестов.
 *
 * Функции:
 * - Пошаговое создание A/B тестов
 * - Управление вариантами теста
 * - Настройка распределения трафика
 * - Предпросмотр перед созданием
 */

import React, { useState } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  ChevronLeft,
  Plus,
  Trash2,
  TestTube,
  Target,
  Settings,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  Input,
  Textarea,
  Label,
  Slider,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@heroui/react';
import { createABTest } from '../../api/ab_testing';
import type { ABTestCreate, ABTestVariantCreate } from '../../types/ab_testing';

// ==================== Types ====================

interface ABTestWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  channelId: string;
  onSuccess?: (testId: string) => void;
}

type WizardStep = 'details' | 'variants' | 'config' | 'review';

interface VariantFormData {
  id: string;
  name: string;
  description: string;
  traffic_allocation: number;
  configuration: Record<string, unknown>;
}

interface FormData {
  name: string;
  description: string;
  hypothesis: string;
  planned_duration_hours: number;
  variants: VariantFormData[];
}

// ==================== Constants ====================

const STEP_TITLES: Record<WizardStep, string> = {
  details: 'Детали теста',
  variants: 'Варианты',
  config: 'Настройки',
  review: 'Просмотр',
};

const STEP_ICONS: Record<WizardStep, React.ElementType> = {
  details: TestTube,
  variants: Target,
  config: Settings,
  review: CheckCircle,
};

// ==================== Helper Components ====================

const StepIndicator: React.FC<{
  steps: WizardStep[];
  currentStep: WizardStep;
}> = ({ steps, currentStep }) => {
  const currentIndex = steps.indexOf(currentStep);

  return (
    <div className="flex items-center justify-between mb-6">
      {steps.map((step, index) => {
        const Icon = STEP_ICONS[step];
        const isCompleted = index < currentIndex;
        const isCurrent = index === currentIndex;

        return (
          <React.Fragment key={step}>
            <div className="flex flex-col items-center">
              <div
                className={`
                  flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all
                  ${isCurrent
                    ? 'border-violet-500 bg-violet-500 text-white'
                    : isCompleted
                    ? 'border-green-500 bg-green-500 text-white'
                    : 'border-[color:var(--color-outline)] text-[color:var(--color-text-muted)]'
                  }
                `}
              >
                {isCompleted ? (
                  <CheckCircle className="w-5 h-5" />
                ) : (
                  <Icon className="w-5 h-5" />
                )}
              </div>
              <span
                className={`
                  mt-2 text-xs font-medium
                  ${isCurrent ? 'text-violet-500' : isCompleted ? 'text-green-500' : 'text-[color:var(--color-text-muted)]'}
                `}
              >
                {STEP_TITLES[step]}
              </span>
            </div>

            {index < steps.length - 1 && (
              <div
                className={`
                  flex-1 h-0.5 mx-2 transition-colors
                  ${index < currentIndex ? 'bg-green-500' : 'bg-[color:var(--color-outline)]'}
                `}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

const VariantCard: React.FC<{
  variant: VariantFormData;
  index: number;
  onUpdate: (index: number, field: keyof VariantFormData, value: string | number) => void;
  onRemove: (index: number) => void;
  totalTraffic: number;
}> = ({ variant, index, onUpdate, onRemove, totalTraffic }) => {
  const colors = ['#8B5CF6', '#3B82F6', '#10B981', '#F59E0B', '#EF4444'];
  const color = colors[index % colors.length];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="p-4 rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-10 rounded-full"
            style={{ backgroundColor: color }}
          />
          <div>
            <Input
              value={variant.name}
              onChange={(e) => onUpdate(index, 'name', e.target.value)}
              placeholder={`Вариант ${String.fromCharCode(65 + index)}`}
              className="font-medium"
              classNames={{
                input: 'text-sm font-semibold',
              }}
            />
          </div>
        </div>

        <Button
          isIconOnly
          size="sm"
          color="danger"
          variant="light"
          onPress={() => onRemove(index)}
          isDisabled={index < 2} // Minimum 2 variants
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>

      <Textarea
        value={variant.description}
        onChange={(e) => onUpdate(index, 'description', e.target.value)}
        placeholder="Описание варианта"
        className="mb-3"
        minRows={1}
      />

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-sm">Распределение трафика</Label>
          <span className="text-sm font-medium text-violet-500">
            {variant.traffic_allocation}%
          </span>
        </div>
        <Slider
          value={variant.traffic_allocation}
          onChangeValue={(value) => onUpdate(index, 'traffic_allocation', value)}
          minValue={0}
          maxValue={100}
          step={5}
          className="w-full"
          classNames={{
            track: 'border-s-secondary-foreground',
            filler: 'bg-gradient-to-r from-violet-500 to-purple-500',
          }}
        />
        <p className="text-xs text-[color:var(--color-text-muted)]">
          Общий трафик: {totalTraffic}%
          {totalTraffic !== 100 && (
            <span className="text-amber-500 ml-1">
              ({totalTraffic < 100 ? `осталось ${100 - totalTraffic}%` : `превышение на ${totalTraffic - 100}%`})
            </span>
          )}
        </p>
      </div>
    </motion.div>
  );
};

// ==================== Main Component ====================

export const ABTestWizard: React.FC<ABTestWizardProps> = ({
  open,
  onOpenChange,
  channelId,
  onSuccess,
}) => {
  const [currentStep, setCurrentStep] = useState<WizardStep>('details');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const steps: WizardStep[] = ['details', 'variants', 'config', 'review'];

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    defaultValues: {
      name: '',
      description: '',
      hypothesis: '',
      planned_duration_hours: 24,
      variants: [
        { id: '1', name: 'Контроль', description: '', traffic_allocation: 50, configuration: {} },
        { id: '2', name: 'Вариант A', description: '', traffic_allocation: 50, configuration: {} },
      ],
    },
  });

  const variants = watch('variants');

  const totalTraffic = variants.reduce((sum, v) => sum + v.traffic_allocation, 0);

  const handleVariantUpdate = (
    index: number,
    field: keyof VariantFormData,
    value: string | number
  ) => {
    setValue(`variants.${index}.${field}` as never, value);
  };

  const handleAddVariant = () => {
    const newVariants = [
      ...variants,
      {
        id: String(variants.length + 1),
        name: `Вариант ${String.fromCharCode(65 + variants.length)}`,
        description: '',
        traffic_allocation: 0,
        configuration: {},
      },
    ];
    setValue('variants', newVariants as never);
  };

  const handleRemoveVariant = (index: number) => {
    const newVariants = variants.filter((_, i) => i !== index);
    setValue('variants', newVariants as never);
  };

  const handleNext = () => {
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex < steps.length - 1) {
      setCurrentStep(steps[currentIndex + 1]);
    }
  };

  const handlePrev = () => {
    const currentIndex = steps.indexOf(currentStep);
    if (currentIndex > 0) {
      setCurrentStep(steps[currentIndex - 1]);
    }
  };

  const validateStep = (step: WizardStep): boolean => {
    if (step === 'details') {
      return !!(watch('name') && watch('description'));
    }
    if (step === 'variants') {
      return totalTraffic === 100 && variants.every(v => v.name && v.traffic_allocation > 0);
    }
    if (step === 'config') {
      return watch('planned_duration_hours') > 0;
    }
    return true;
  };

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    setError(null);

    try {
      const testData: ABTestCreate = {
        name: data.name,
        description: data.description,
        hypothesis: data.hypothesis,
        channel_id: channelId,
        planned_duration_hours: data.planned_duration_hours,
        variants: data.variants.map((v, i) => ({
          name: v.name,
          description: v.description,
          traffic_allocation: v.traffic_allocation,
          position: i,
          configuration: v.configuration,
        })),
      };

      const result = await createABTest(testData);
      onSuccess?.(result.id);
      onOpenChange(false);

      // Reset form
      setValue('name', '');
      setValue('description', '');
      setValue('hypothesis', '');
      setValue('planned_duration_hours', 24);
      setValue('variants', [
        { id: '1', name: 'Контроль', description: '', traffic_allocation: 50, configuration: {} },
        { id: '2', name: 'Вариант A', description: '', traffic_allocation: 50, configuration: {} },
      ]);
      setCurrentStep('details');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Ошибка создания теста';
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const canGoNext = validateStep(currentStep);
  const isLastStep = currentStep === 'review';
  const isFirstStep = currentStep === 'details';

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Создание A/B теста</DialogTitle>
          <DialogDescription>
            Следуйте пошаговым инструкциям для создания нового A/B теста
          </DialogDescription>
        </DialogHeader>

        {/* Step Indicator */}
        <StepIndicator steps={steps} currentStep={currentStep} />

        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
            <p className="text-sm text-red-500">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)}>
          <AnimatePresence mode="wait">
            {/* Step 1: Details */}
            {currentStep === 'details' && (
              <motion.div
                key="details"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label htmlFor="name">
                    Название теста <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="name"
                    {...register('name', { required: 'Название обязательно' })}
                    placeholder="Тест thumbnail изображений"
                  />
                  {errors.name && (
                    <span className="text-sm text-red-500">{errors.name.message}</span>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="description">
                    Описание <span className="text-red-500">*</span>
                  </Label>
                  <Textarea
                    id="description"
                    {...register('description', { required: 'Описание обязательно' })}
                    placeholder="Сравниваем два варианта thumbnail для стрима"
                    minRows={3}
                  />
                  {errors.description && (
                    <span className="text-sm text-red-500">{errors.description.message}</span>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="hypothesis">Гипотеза</Label>
                  <Textarea
                    id="hypothesis"
                    {...register('hypothesis')}
                    placeholder="Яркий thumbnail с изображением спикера увеличит CTR на 15%"
                    minRows={2}
                  />
                  <p className="text-xs text-[color:var(--color-text-muted)]">
                    Опишите, что вы ожидаете от этого теста
                  </p>
                </div>
              </motion.div>
            )}

            {/* Step 2: Variants */}
            {currentStep === 'variants' && (
              <motion.div
                key="variants"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                <div className="space-y-3">
                  <AnimatePresence>
                    {variants.map((variant, index) => (
                      <VariantCard
                        key={variant.id}
                        variant={variant}
                        index={index}
                        onUpdate={handleVariantUpdate}
                        onRemove={handleRemoveVariant}
                        totalTraffic={totalTraffic}
                      />
                    ))}
                  </AnimatePresence>
                </div>

                <Button
                  variant="flat"
                  onPress={handleAddVariant}
                  startContent={<Plus className="w-4 h-4" />}
                  className="w-full"
                >
                  Добавить вариант
                </Button>

                {totalTraffic !== 100 && (
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                    <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0" />
                    <p className="text-sm text-amber-500">
                      Сумма распределения трафика должна быть 100% (текущий: {totalTraffic}%)
                    </p>
                  </div>
                )}
              </motion.div>
            )}

            {/* Step 3: Configuration */}
            {currentStep === 'config' && (
              <motion.div
                key="config"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label htmlFor="duration">
                    Длительность теста (часы) <span className="text-red-500">*</span>
                  </Label>
                  <div className="flex items-center gap-4">
                    <Slider
                      value={[watch('planned_duration_hours')]}
                      onChangeValue={([value]) => setValue('planned_duration_hours', value)}
                      minValue={1}
                      maxValue={168} // 1 week
                      step={1}
                      className="flex-1"
                      classNames={{
                        track: 'border-s-secondary-foreground',
                        filler: 'bg-gradient-to-r from-violet-500 to-purple-500',
                      }}
                    />
                    <Input
                      type="number"
                      {...register('planned_duration_hours', { required: 'Длительность обязательна', min: 1 })}
                      className="w-24"
                      min={1}
                      max={168}
                    />
                  </div>
                  <p className="text-xs text-[color:var(--color-text-muted)]">
                    Рекомендуемая длительность: 24-72 часа для получения статистически значимых результатов
                  </p>
                  {errors.planned_duration_hours && (
                    <span className="text-sm text-red-500">{errors.planned_duration_hours.message}</span>
                  )}
                </div>

                <div className="p-4 rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]">
                  <h4 className="font-semibold text-[color:var(--color-text)] mb-2">Автоматическая остановка</h4>
                  <p className="text-sm text-[color:var(--color-text-muted)]">
                    Тест будет автоматически остановлен после указанного времени или при достижении
                    статистической значимости
                  </p>
                </div>
              </motion.div>
            )}

            {/* Step 4: Review */}
            {currentStep === 'review' && (
              <motion.div
                key="review"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                <div className="p-4 rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)] space-y-3">
                  <div>
                    <h4 className="font-semibold text-[color:var(--color-text)]">{watch('name')}</h4>
                    <p className="text-sm text-[color:var(--color-text-muted)] mt-1">
                      {watch('description')}
                    </p>
                    {watch('hypothesis') && (
                      <p className="text-sm text-violet-500 mt-2 italic">
                        Гипотеза: {watch('hypothesis')}
                      </p>
                    )}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label className="text-sm font-semibold text-[color:var(--color-text)]">
                    Варианты ({variants.length})
                  </Label>
                  <div className="space-y-2">
                    {variants.map((variant, index) => {
                      const colors = ['#8B5CF6', '#3B82F6', '#10B981', '#F59E0B', '#EF4444'];
                      const color = colors[index % colors.length];

                      return (
                        <div
                          key={variant.id}
                          className="flex items-center justify-between p-3 rounded-lg bg-[color:var(--color-surface-muted)] border border-[color:var(--color-border)]"
                        >
                          <div className="flex items-center gap-3">
                            <div
                              className="w-3 h-8 rounded-full"
                              style={{ backgroundColor: color }}
                            />
                            <div>
                              <div className="font-medium text-[color:var(--color-text)]">
                                {variant.name}
                              </div>
                              {variant.description && (
                                <div className="text-xs text-[color:var(--color-text-muted)]">
                                  {variant.description}
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="text-lg font-bold text-violet-500">
                            {variant.traffic_allocation}%
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="p-4 rounded-lg bg-violet-500/10 border border-violet-500/20">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-[color:var(--color-text)]">
                      Длительность теста:
                    </span>
                    <span className="text-lg font-bold text-violet-500">
                      {watch('planned_duration_hours')} ч
                    </span>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <DialogFooter className="mt-6">
            <div className="flex items-center justify-between w-full">
              <Button
                type="button"
                variant="flat"
                onPress={isFirstStep ? () => onOpenChange(false) : handlePrev}
                isDisabled={isSubmitting}
              >
                {isFirstStep ? 'Отмена' : <ChevronLeft className="w-4 h-4" />}
                {!isFirstStep && 'Назад'}
              </Button>

              <Button
                type={isLastStep ? 'submit' : 'button'}
                color="primary"
                onPress={isLastStep ? undefined : handleNext}
                isDisabled={!canGoNext || isSubmitting}
                isLoading={isSubmitting}
                startContent={!isLastStep && <ChevronRight className="w-4 h-4" />}
              >
                {isLastStep ? 'Создать тест' : 'Далее'}
              </Button>
            </div>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default ABTestWizard;
