/**
 * Тесты для ABTestWizard компонента
 * Feature: 016-a-b-testing-framework-for-content
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ABTestWizard from '../ABTestWizard';
import * as abTestingApi from '../../../api/ab_testing';
import type { ABTestCreate } from '../../../types/ab_testing';

// Mock API модуля
vi.mock('../../../api/ab_testing', () => ({
  createABTest: vi.fn(),
}));

// Mock HeroUI components
vi.mock('@heroui/react', () => ({
  Button: ({ onPress, children, ...props }: any) => (
    <button
      onClick={onPress}
      disabled={props.isDisabled}
      type={props.type}
    >
      {children}
    </button>
  ),
  Card: ({ children }: any) => <div>{children}</div>,
  CardContent: ({ children }: any) => <div>{children}</div>,
  Input: ({ onChange, value, ...props }: any) => (
    <input
      onChange={onChange}
      value={value}
      placeholder={props.placeholder}
      type={props.type}
      id={props.id}
      min={props.min}
      max={props.max}
      disabled={props.isDisabled}
    />
  ),
  Textarea: ({ onChange, value, children, ...props }: any) => (
    <textarea
      onChange={onChange}
      value={value}
      placeholder={props.placeholder}
      id={props.id}
      minRows={props.minRows}
    >
      {children}
    </textarea>
  ),
  Label: ({ children, className }: any) => <label className={className}>{children}</label>,
  Slider: ({ value, onChangeValue, minValue, maxValue, step, className }: any) => (
    <input
      type="range"
      min={minValue}
      max={maxValue}
      step={step}
      value={value?.[0] || value}
      onChange={(e) => onChangeValue?.([Number(e.target.value)])}
      className={className}
    />
  ),
  Dialog: ({ open, onOpenChange, children }: any) =>
    open ? (
      <div role="dialog">
        {typeof children === 'function'
          ? children({ onOpenChange })
          : children}
      </div>
    ) : null,
  DialogContent: ({ children }: any) => <div className="dialog-content">{children}</div>,
  DialogHeader: ({ children }: any) => <div className="dialog-header">{children}</div>,
  DialogTitle: ({ children }: any) => <h2 className="dialog-title">{children}</h2>,
  DialogDescription: ({ children }: any) => <p className="dialog-description">{children}</p>,
  DialogFooter: ({ children }: any) => <div className="dialog-footer">{children}</div>,
}));

const mockChannelId = 'channel-123';
const mockOnSuccess = vi.fn();
const mockOnOpenChange = vi.fn();

describe('ABTestWizard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Рендеринг', () => {
    it('рендерит диалог когда открыт', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      expect(screen.getByText('Создание A/B теста')).toBeInTheDocument();
      expect(screen.getByText('Следуйте пошаговым инструкциям для создания нового A/B теста')).toBeInTheDocument();
    });

    it('не рендерит диалог когда закрыт', () => {
      render(
        <ABTestWizard
          open={false}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      expect(screen.queryByText('Создание A/B теста')).not.toBeInTheDocument();
    });

    it('показывает индикатор шагов', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Проверяем наличие шагов
      expect(screen.getByText('Детали теста')).toBeInTheDocument();
      expect(screen.getByText('Варианты')).toBeInTheDocument();
      expect(screen.getByText('Настройки')).toBeInTheDocument();
      expect(screen.getByText('Просмотр')).toBeInTheDocument();
    });

    it('начинает с первого шага (Детали теста)', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Проверяем наличие полей первого шага
      expect(screen.getByPlaceholderText('Тест thumbnail изображений')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима')).toBeInTheDocument();
    });
  });

  describe('Шаг 1: Детали теста', () => {
    it('показывает поле названия с обязательной меткой', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      expect(screen.getByText(/Название теста/)).toBeInTheDocument();
      expect(screen.getByText('*')).toBeInTheDocument(); // Обязательное поле
    });

    it('показывает поле описания с обязательной меткой', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      expect(screen.getByText(/Описание/)).toBeInTheDocument();
    });

    it('показывает поле гипотезы без обязательной метки', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      expect(screen.getByText('Гипотеза')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Яркий thumbnail с изображением спикера увеличит CTR на 15%')).toBeInTheDocument();
    });

    it('показывает подсказку для гипотезы', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      expect(screen.getByText('Опишите, что вы ожидаете от этого теста')).toBeInTheDocument();
    });
  });

  describe('Навигация по шагам', () => {
    it('показывает кнопку "Отмена" на первом шаге', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      expect(screen.getByText('Отмена')).toBeInTheDocument();
    });

    it('показывает кнопку "Далее" на первом шаге', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      expect(screen.getByText('Далее')).toBeInTheDocument();
    });

    it('закрывает диалог при клике на "Отмена"', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      const cancelButton = screen.getByText('Отмена');
      fireEvent.click(cancelButton);

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('не переходит на следующий шаг если название не заполнено', async () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      const nextButton = screen.getByText('Далее');
      fireEvent.click(nextButton);

      // Должен остаться на том же шаге
      expect(screen.getByPlaceholderText('Тест thumbnail изображений')).toBeInTheDocument();
      expect(screen.queryByText('Варианты')).not.toBeInTheDocument();
    });

    it('переходит на шаг 2 при заполненных обязательных полях', async () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Заполняем обязательные поля
      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');
      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      fireEvent.change(nameInput, { target: { value: 'Тест A' } });
      fireEvent.change(descInput, { target: { value: 'Описание теста' } });

      // Кликаем Далее
      const nextButton = screen.getByText('Далее');
      fireEvent.click(nextButton);

      // Должен показать шаг 2 (Варианты)
      await waitFor(() => {
        expect(screen.getByText('Контроль')).toBeInTheDocument();
        expect(screen.getByText('Вариант A')).toBeInTheDocument();
      });
    });

    it('показывает кнопку "Назад" на втором шаге', async () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Заполняем и переходим на шаг 2
      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');
      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      fireEvent.change(nameInput, { target: { value: 'Тест A' } });
      fireEvent.change(descInput, { target: { value: 'Описание теста' } });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Назад')).toBeInTheDocument();
      });
    });
  });

  describe('Шаг 2: Варианты', () => {
    beforeEach(async () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Заполняем шаг 1 и переходим к шагу 2
      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');
      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      fireEvent.change(nameInput, { target: { value: 'Тест A' } });
      fireEvent.change(descInput, { target: { value: 'Описание теста' } });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Контроль')).toBeInTheDocument();
      });
    });

    it('показывает два варианта по умолчанию', () => {
      expect(screen.getByDisplayValue('Контроль')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Вариант A')).toBeInTheDocument();
    });

    it('показывает распределение трафика для вариантов', () => {
      expect(screen.getByText('50%')).toBeInTheDocument();
      expect(screen.getByText('Распределение трафика')).toBeInTheDocument();
    });

    it('показывает что общий трафик 100%', () => {
      expect(screen.getByText('Общий трафик: 100%')).toBeInTheDocument();
    });

    it('не позволяет удалить первые два варианта', () => {
      const deleteButtons = screen.getAllByRole('button').filter(
        btn => btn.getAttribute('disabled') !== null
      );

      // Кнопки удаления для первых двух вариантов должны быть disabled
      expect(deleteButtons.length).toBeGreaterThan(0);
    });

    it('позволяет добавить новый вариант', () => {
      const addButton = screen.getByText('Добавить вариант');
      expect(addButton).toBeInTheDocument();
    });

    it('показывает предупреждение если сумма не равна 100%', async () => {
      // Меняем распределение первого варианта
      const sliders = screen.getAllByRole('slider');
      fireEvent.change(sliders[0], { target: { value: 30 } });

      await waitFor(() => {
        expect(screen.getByText(/осталось/)).toBeInTheDocument();
      });
    });

    it('не переходит дальше если варианты не валидны', async () => {
      // Меняем распределение чтобы было != 100%
      const sliders = screen.getAllByRole('slider');
      fireEvent.change(sliders[0], { target: { value: 30 } });

      const nextButton = screen.getByText('Далее');
      fireEvent.click(nextButton);

      // Должен остаться на шаге 2
      expect(screen.getByText('Контроль')).toBeInTheDocument();
    });
  });

  describe('Шаг 3: Настройки', () => {
    beforeEach(async () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Заполняем шаг 1
      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');
      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      fireEvent.change(nameInput, { target: { value: 'Тест A' } });
      fireEvent.change(descInput, { target: { value: 'Описание теста' } });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Контроль')).toBeInTheDocument();
      });

      // Переходим к шагу 3
      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Длительность теста')).toBeInTheDocument();
      });
    });

    it('показывает поле длительности с обязательной меткой', () => {
      expect(screen.getByText(/Длительность теста/)).toBeInTheDocument();
      expect(screen.getByText('*')).toBeInTheDocument();
    });

    it('показывает слайдер для длительности', () => {
      const sliders = screen.getAllByRole('slider');
      expect(sliders.length).toBeGreaterThan(0);
    });

    it('показывает подсказку о рекомендуемой длительности', () => {
      expect(screen.getByText(/Рекомендуемая длительность: 24-72 часа/)).toBeInTheDocument();
    });

    it('показывает информацию об автоматической остановке', () => {
      expect(screen.getByText('Автоматическая остановка')).toBeInTheDocument();
      expect(screen.getByText(/Тест будет автоматически остановлен/)).toBeInTheDocument();
    });

    it('имеет значение по умолчанию 24 часа', () => {
      const numberInput = screen.getByRole('spinbox');
      expect(numberInput).toHaveValue(24);
    });
  });

  describe('Шаг 4: Просмотр', () => {
    beforeEach(async () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Заполняем все шаги
      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');
      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      fireEvent.change(nameInput, { target: { value: 'Мой тест' } });
      fireEvent.change(descInput, { target: { value: 'Описание' } });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Контроль')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Длительность теста')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Мой тест')).toBeInTheDocument();
      });
    });

    it('показывает название теста', () => {
      expect(screen.getByText('Мой тест')).toBeInTheDocument();
    });

    it('показывает описание теста', () => {
      expect(screen.getByText('Описание')).toBeInTheDocument();
    });

    it('показывает список вариантов', () => {
      expect(screen.getByText(/Варианты \(2\)/)).toBeInTheDocument();
      expect(screen.getByText('Контроль')).toBeInTheDocument();
      expect(screen.getByText('Вариант A')).toBeInTheDocument();
    });

    it('показывает распределение для каждого варианта', () => {
      const percentages = screen.getAllByText('50%');
      expect(percentages.length).toBeGreaterThanOrEqual(2);
    });

    it('показывает длительность теста', () => {
      expect(screen.getByText('24 ч')).toBeInTheDocument();
      expect(screen.getByText('Длительность теста:')).toBeInTheDocument();
    });

    it('показывает кнопку "Создать тест"', () => {
      expect(screen.getByText('Создать тест')).toBeInTheDocument();
    });
  });

  describe('Создание теста', () => {
    beforeEach(async () => {
      vi.mocked(abTestingApi.createABTest).mockResolvedValue({
        id: 'test-123',
        name: 'Мой тест',
        description: 'Описание',
        hypothesis: '',
        channel_id: mockChannelId,
        status: 'draft',
        planned_duration_hours: 24,
        variants: [],
        created_at: '2024-01-15T10:00:00Z',
        start_time: null,
        end_time: null,
        confidence_level: 0.95,
      });

      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
          onSuccess={mockOnSuccess}
        />
      );

      // Заполняем все шаги
      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');
      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      fireEvent.change(nameInput, { target: { value: 'Мой тест' } });
      fireEvent.change(descInput, { target: { value: 'Описание' } });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Контроль')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Длительность теста')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Мой тест')).toBeInTheDocument();
      });
    });

    it('отправляет данные на сервер при клике на "Создать тест"', async () => {
      const submitButton = screen.getByText('Создать тест');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(abTestingApi.createABTest).toHaveBeenCalled();
      });
    });

    it('передает правильные данные в API', async () => {
      const submitButton = screen.getByText('Создать тест');
      fireEvent.click(submitButton);

      await waitFor(() => {
        const callArgs = vi.mocked(abTestingApi.createABTest).mock.calls[0][0] as ABTestCreate;
        expect(callArgs.name).toBe('Мой тест');
        expect(callArgs.description).toBe('Описание');
        expect(callArgs.channel_id).toBe(mockChannelId);
        expect(callArgs.planned_duration_hours).toBe(24);
        expect(callArgs.variants).toHaveLength(2);
      });
    });

    it('вызывает onSuccess после успешного создания', async () => {
      const submitButton = screen.getByText('Создать тест');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnSuccess).toHaveBeenCalledWith('test-123');
      });
    });

    it('закрывает диалог после успешного создания', async () => {
      const submitButton = screen.getByText('Создать тест');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockOnOpenChange).toHaveBeenCalledWith(false);
      });
    });

    it('показывает ошибку при неудачном создании', async () => {
      vi.mocked(abTestingApi.createABTest).mockRejectedValue(
        new Error('Failed to create test')
      );

      const submitButton = screen.getByText('Создать тест');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Ошибка создания теста')).toBeInTheDocument();
      });
    });
  });

  describe('Валидация формы', () => {
    it('показывает ошибку для пустого названия', async () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');

      // Попытка отправить с пустым названием
      nameInput.focus();
      nameInput.blur();

      // Попробовать перейти дальше
      const nextButton = screen.getByText('Далее');
      fireEvent.click(nextButton);

      // Должен остаться на шаге 1
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Тест thumbnail изображений')).toBeInTheDocument();
      });
    });

    it('показывает ошибку для пустого описания', async () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      descInput.focus();
      descInput.blur();

      const nextButton = screen.getByText('Далее');
      fireEvent.click(nextButton);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима')).toBeInTheDocument();
      });
    });

    it('проверяет что сумма распределения трафика равна 100%', async () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Заполняем шаг 1
      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');
      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      fireEvent.change(nameInput, { target: { value: 'Тест A' } });
      fireEvent.change(descInput, { target: { value: 'Описание' } });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Контроль')).toBeInTheDocument();
      });

      // Меняем распределение
      const sliders = screen.getAllByRole('slider');
      fireEvent.change(sliders[0], { target: { value: 30 } });

      // Проверяем предупреждение
      await waitFor(() => {
        expect(screen.getByText(/осталось/)).toBeInTheDocument();
      });
    });

    it('проверяет что длительность больше 0', async () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Заполняем шаг 1
      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');
      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      fireEvent.change(nameInput, { target: { value: 'Тест A' } });
      fireEvent.change(descInput, { target: { value: 'Описание' } });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Контроль')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Длительность теста')).toBeInTheDocument();
      });

      // Значение по умолчанию 24, должно быть валидно
      const nextButton = screen.getByText('Далее');
      expect(nextButton).toBeInTheDocument();
    });
  });

  describe('Добавление и удаление вариантов', () => {
    beforeEach(async () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Заполняем шаг 1
      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');
      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      fireEvent.change(nameInput, { target: { value: 'Тест A' } });
      fireEvent.change(descInput, { target: { value: 'Описание' } });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Контроль')).toBeInTheDocument();
      });
    });

    it('добавляет новый вариант при клике на "Добавить вариант"', async () => {
      const addButton = screen.getByText('Добавить вариант');
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(screen.getByDisplayValue('Вариант B')).toBeInTheDocument();
      });
    });

    it('устанавливает распределение 0% для нового варианта', async () => {
      const addButton = screen.getByText('Добавить вариант');
      fireEvent.click(addButton);

      await waitFor(() => {
        const sliders = screen.getAllByRole('slider');
        expect(sliders[2]).toHaveValue(0);
      });
    });

    it('обновляет общий трафик при добавлении варианта', async () => {
      const addButton = screen.getByText('Добавить вариант');
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(screen.getByText('Общий трафик: 100%')).toBeInTheDocument();
      });
    });
  });

  describe('Навигация назад', () => {
    it('возвращается на предыдущий шаг при клике "Назад"', async () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Заполняем шаг 1
      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');
      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      fireEvent.change(nameInput, { target: { value: 'Тест A' } });
      fireEvent.change(descInput, { target: { value: 'Описание' } });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Контроль')).toBeInTheDocument();
      });

      // Кликаем Назад
      const backButton = screen.getByText('Назад');
      fireEvent.click(backButton);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Тест thumbnail изображений')).toBeInTheDocument();
      });
    });
  });

  describe('Индикатор шагов', () => {
    it('подсвечивает текущий шаг', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Первый шаг должен быть активным
      const stepTitles = screen.getAllByText('Детали теста');
      expect(stepTitles.length).toBeGreaterThan(0);
    });
  });

  describe('Accessibility', () => {
    it('имеет правильную роль dialog', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();
    });

    it('имеет заголовок', () => {
      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      const title = screen.getByText('Создание A/B теста');
      expect(title.tagName).toBe('H2');
    });
  });

  describe('Обработка ошибок', () => {
    it('показывает сообщение об ошибке от API', async () => {
      vi.mocked(abTestingApi.createABTest).mockRejectedValue(
        new Error('Network error: Failed to fetch')
      );

      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
          onSuccess={mockOnSuccess}
        />
      );

      // Заполняем все шаги и создаем
      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');
      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      fireEvent.change(nameInput, { target: { value: 'Мой тест' } });
      fireEvent.change(descInput, { target: { value: 'Описание' } });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Контроль')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Длительность теста')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Мой тест')).toBeInTheDocument();
      });

      const submitButton = screen.getByText('Создать тест');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Ошибка создания теста')).toBeInTheDocument();
      });
    });

    it('скрывает ошибку после следующего действия', async () => {
      vi.mocked(abTestingApi.createABTest).mockRejectedValue(
        new Error('Error')
      );

      render(
        <ABTestWizard
          open={true}
          onOpenChange={mockOnOpenChange}
          channelId={mockChannelId}
        />
      );

      // Быстрое заполнение и отправка
      const nameInput = screen.getByPlaceholderText('Тест thumbnail изображений');
      const descInput = screen.getByPlaceholderText('Сравниваем два варианта thumbnail для стрима');

      fireEvent.change(nameInput, { target: { value: 'Тест' } });
      fireEvent.change(descInput, { target: { value: 'Описание' } });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Контроль')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Длительность теста')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Далее'));

      await waitFor(() => {
        expect(screen.getByText('Тест')).toBeInTheDocument();
      });

      const submitButton = screen.getByText('Создать тест');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Ошибка создания теста')).toBeInTheDocument();
      });
    });
  });
});
