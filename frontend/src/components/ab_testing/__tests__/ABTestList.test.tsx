/**
 * Тесты для ABTestList компонента
 * Feature: 016-a-b-testing-framework-for-content
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ABTestList from '../ABTestList';
import * as abTestingApi from '../../../api/ab_testing';
import type { ABTestListResponse, ABTestStatus } from '../../../types/ab_testing';

// Mock API модуля
vi.mock('../../../api/ab_testing', () => ({
  listABTests: vi.fn(),
  startABTest: vi.fn(),
  stopABTest: vi.fn(),
  deleteABTest: vi.fn(),
}));

const mockTests: ABTestListResponse[] = [
  {
    id: '1',
    name: 'Тест thumbnail изображений',
    channel_id: 'channel-1',
    status: 'draft',
    variant_count: 2,
    created_at: '2024-01-15T10:00:00Z',
    start_time: undefined,
    end_time: undefined,
    is_significant: undefined,
    winner_variant_id: undefined,
  },
  {
    id: '2',
    name: 'Тест расписания стримов',
    channel_id: 'channel-1',
    status: 'running',
    variant_count: 3,
    created_at: '2024-01-14T10:00:00Z',
    start_time: '2024-01-14T12:00:00Z',
    end_time: undefined,
    is_significant: false,
    winner_variant_id: undefined,
  },
  {
    id: '3',
    name: 'Тест качества видео',
    channel_id: 'channel-1',
    status: 'completed',
    variant_count: 2,
    created_at: '2024-01-10T10:00:00Z',
    start_time: '2024-01-10T12:00:00Z',
    end_time: '2024-01-12T12:00:00Z',
    is_significant: true,
    winner_variant_id: 'variant-1',
  },
];

describe('ABTestList Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.confirm
    global.confirm = vi.fn(() => true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Рендеринг компонента', () => {
    it('рендерит заголовок с количеством тестов', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      render(<ABTestList />);

      await waitFor(() => {
        expect(screen.getByText('A/B Тесты')).toBeInTheDocument();
        expect(screen.getByText('(3)')).toBeInTheDocument();
      });
    });

    it('рендерит иконку колбы в заголовке', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      render(<ABTestList />);

      await waitFor(() => {
        const container = screen.getByText('A/B Тесты').parentElement;
        expect(container).toBeInTheDocument();
      });
    });
  });

  describe('Состояние загрузки', () => {
    it('показывает скелетоны во время загрузки', () => {
      vi.mocked(abTestingApi.listABTests).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<ABTestList />);

      // Проверяем наличие скелетонов (animate-pulse элементы)
      const { container } = render(<ABTestList />);
      expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
    });

    it('показывает 3 скелетона-заглушки', () => {
      vi.mocked(abTestingApi.listABTests).mockImplementation(
        () => new Promise(() => {})
      );

      const { container } = render(<ABTestList />);
      const skeletons = container.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe('Пустое состояние', () => {
    it('показывает сообщение когда нет тестов', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [],
        total: 0,
      });

      render(<ABTestList />);

      await waitFor(() => {
        expect(screen.getByText('Нет A/B тестов')).toBeInTheDocument();
        expect(
          screen.getByText('Создайте первый A/B тест, чтобы начать эксперимент')
        ).toBeInTheDocument();
      });
    });

    it('показывает иконку колбы в пустом состоянии', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [],
        total: 0,
      });

      render(<ABTestList />);

      await waitFor(() => {
        const container = screen.getByText('Нет A/B тестов').parentElement;
        expect(container).toBeInTheDocument();
      });
    });
  });

  describe('Состояние ошибки', () => {
    it('показывает сообщение об ошибке при неудачном запросе', async () => {
      vi.mocked(abTestingApi.listABTests).mockRejectedValue(
        new Error('Network error')
      );

      render(<ABTestList />);

      await waitFor(() => {
        expect(
          screen.getByText('Не удалось загрузить список A/B тестов')
        ).toBeInTheDocument();
      });
    });

    it('применяет правильные стили для ошибки', async () => {
      vi.mocked(abTestingApi.listABTests).mockRejectedValue(
        new Error('API Error')
      );

      const { container } = render(<ABTestList />);

      await waitFor(() => {
        const errorDiv = container.querySelector('.bg-red-500\\/10');
        expect(errorDiv).toBeInTheDocument();
      });
    });
  });

  describe('Карточки тестов', () => {
    it('рендерит все тесты из списка', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      render(<ABTestList />);

      await waitFor(() => {
        expect(screen.getByText('Тест thumbnail изображений')).toBeInTheDocument();
        expect(screen.getByText('Тест расписания стримов')).toBeInTheDocument();
        expect(screen.getByText('Тест качества видео')).toBeInTheDocument();
      });
    });

    it('показывает правильный статус для каждого теста', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      render(<ABTestList />);

      await waitFor(() => {
        expect(screen.getByText('Черновик')).toBeInTheDocument();
        expect(screen.getByText('Запущен')).toBeInTheDocument();
        expect(screen.getByText('Завершён')).toBeInTheDocument();
      });
    });

    it('показывает количество вариантов', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      render(<ABTestList />);

      await waitFor(() => {
        expect(screen.getByText(/2 вариант/)).toBeInTheDocument();
        expect(screen.getByText(/3 вариант/)).toBeInTheDocument();
      });
    });

    it('показывает дату создания', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      render(<ABTestList />);

      await waitFor(() => {
        expect(screen.getByText(/Создан:/)).toBeInTheDocument();
      });
    });

    it('показывает длительность для запущенного теста', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[1]], // running test
        total: 1,
      });

      render(<ABTestList />);

      await waitFor(() => {
        expect(screen.getByText(/Длится:/)).toBeInTheDocument();
      });
    });

    it('показывает длину для завершенного теста', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[2]], // completed test
        total: 1,
      });

      render(<ABTestList />);

      await waitFor(() => {
        expect(screen.getByText(/Длина:/)).toBeInTheDocument();
      });
    });

    it('показывает статистическую значимость', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[1], mockTests[2]],
        total: 2,
      });

      render(<ABTestList />);

      await waitFor(() => {
        expect(screen.getByText('Требуется больше данных')).toBeInTheDocument();
        expect(screen.getByText('Статистически значимый')).toBeInTheDocument();
      });
    });

    it('показывает победителя для завершенного теста', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[2]],
        total: 1,
      });

      render(<ABTestList />);

      await waitFor(() => {
        expect(screen.getByText('Победитель определён')).toBeInTheDocument();
      });
    });

    it('показывает подсказку "Нажмите для деталей"', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      render(<ABTestList />);

      await waitFor(() => {
        expect(screen.getByText('Нажмите для деталей')).toBeInTheDocument();
      });
    });
  });

  describe('Действия с тестами', () => {
    it('показывает кнопку запуска для черновиков', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[0]], // draft test
        total: 1,
      });

      render(<ABTestList onStartTest={vi.fn()} />);

      await waitFor(() => {
        const playButtons = screen.getAllByTitle('Запустить тест');
        expect(playButtons.length).toBeGreaterThan(0);
      });
    });

    it('показывает кнопку остановки для запущенных тестов', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[1]], // running test
        total: 1,
      });

      render(<ABTestList onStopTest={vi.fn()} />);

      await waitFor(() => {
        const pauseButtons = screen.getAllByTitle('Остановить тест');
        expect(pauseButtons.length).toBeGreaterThan(0);
      });
    });

    it('показывает кнопку удаления для всех тестов', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      render(<ABTestList onDeleteTest={vi.fn()} />);

      await waitFor(() => {
        const deleteButtons = screen.getAllByTitle('Удалить тест');
        expect(deleteButtons.length).toBe(3);
      });
    });

    it('запускает тест при клике на кнопку запуска', async () => {
      const mockStartTest = vi.fn();
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[0]],
        total: 1,
      });
      vi.mocked(abTestingApi.startABTest).mockResolvedValue({
        success: true,
        message: 'Test started',
      });

      render(<ABTestList onStartTest={mockStartTest} />);

      await waitFor(() => {
        const playButton = screen.getByTitle('Запустить тест');
        fireEvent.click(playButton);
      });

      await waitFor(() => {
        expect(abTestingApi.startABTest).toHaveBeenCalledWith('1');
        expect(mockStartTest).toHaveBeenCalledWith('1');
      });
    });

    it('останавливает тест при клике на кнопку остановки', async () => {
      const mockStopTest = vi.fn();
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[1]],
        total: 1,
      });
      vi.mocked(abTestingApi.stopABTest).mockResolvedValue({
        success: true,
        message: 'Test stopped',
        winner_variant_id: null,
      });

      render(<ABTestList onStopTest={mockStopTest} />);

      await waitFor(() => {
        const pauseButton = screen.getByTitle('Остановить тест');
        fireEvent.click(pauseButton);
      });

      await waitFor(() => {
        expect(abTestingApi.stopABTest).toHaveBeenCalledWith('2', true);
        expect(mockStopTest).toHaveBeenCalledWith('2');
      });
    });

    it('удаляет тест после подтверждения', async () => {
      const mockDeleteTest = vi.fn();
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[0]],
        total: 1,
      });
      vi.mocked(abTestingApi.deleteABTest).mockResolvedValue({
        success: true,
        message: 'Test deleted',
      });

      render(<ABTestList onDeleteTest={mockDeleteTest} />);

      await waitFor(() => {
        const deleteButton = screen.getByTitle('Удалить тест');
        fireEvent.click(deleteButton);
      });

      await waitFor(() => {
        expect(global.confirm).toHaveBeenCalledWith(
          'Вы уверены, что хотите удалить этот тест?'
        );
        expect(abTestingApi.deleteABTest).toHaveBeenCalledWith('1');
        expect(mockDeleteTest).toHaveBeenCalledWith('1');
      });
    });

    it('не удаляет тест при отмене подтверждения', async () => {
      global.confirm = vi.fn(() => false);
      const mockDeleteTest = vi.fn();
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[0]],
        total: 1,
      });

      render(<ABTestList onDeleteTest={mockDeleteTest} />);

      await waitFor(() => {
        const deleteButton = screen.getByTitle('Удалить тест');
        fireEvent.click(deleteButton);
      });

      await waitFor(() => {
        expect(abTestingApi.deleteABTest).not.toHaveBeenCalled();
        expect(mockDeleteTest).not.toHaveBeenCalled();
      });
    });
  });

  describe('Клик по карточке', () => {
    it('вызывает onTestClick при клике на карточку', async () => {
      const mockTestClick = vi.fn();
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[0]],
        total: 1,
      });

      render(<ABTestList onTestClick={mockTestClick} />);

      await waitFor(() => {
        const card = screen.getByText('Тест thumbnail изображений').closest('div');
        fireEvent.click(card!);
      });

      expect(mockTestClick).toHaveBeenCalledWith('1');
    });

    it('не вызывает onTestClick при клике на кнопки действий', async () => {
      const mockTestClick = vi.fn();
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[0]],
        total: 1,
      });
      vi.mocked(abTestingApi.startABTest).mockResolvedValue({
        success: true,
        message: 'Test started',
      });

      render(<ABTestList onTestClick={mockTestClick} onStartTest={vi.fn()} />);

      await waitFor(() => {
        const playButton = screen.getByTitle('Запустить тест');
        fireEvent.click(playButton);
      });

      await waitFor(() => {
        expect(mockTestClick).not.toHaveBeenCalled();
      });
    });
  });

  describe('Фильтрация', () => {
    it('передает параметры фильтрации в API', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [],
        total: 0,
      });

      render(
        <ABTestList
          channelId="channel-123"
          status="running"
          limit={20}
        />
      );

      await waitFor(() => {
        expect(abTestingApi.listABTests).toHaveBeenCalledWith(
          'channel-123',
          'running',
          20,
          0
        );
      });
    });
  });

  describe('Автообновление', () => {
    it('устанавливает интервал обновления когда передан refreshInterval', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      vi.useFakeTimers();

      render(<ABTestList refreshInterval={5000} />);

      await waitFor(() => {
        expect(abTestingApi.listABTests).toHaveBeenCalledTimes(1);
      });

      // Продвигаем время на 5 секунд
      vi.advanceTimersByTime(5000);

      await waitFor(() => {
        expect(abTestingApi.listABTests).toHaveBeenCalledTimes(2);
      });

      vi.useRealTimers();
    });

    it('не устанавливает интервал когда refreshInterval не передан', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      vi.useFakeTimers();

      render(<ABTestList />);

      await waitFor(() => {
        expect(abTestingApi.listABTests).toHaveBeenCalledTimes(1);
      });

      // Продвигаем время на 5 секунд
      vi.advanceTimersByTime(5000);

      // Должен остаться на 1 вызове
      expect(abTestingApi.listABTests).toHaveBeenCalledTimes(1);

      vi.useRealTimers();
    });
  });

  describe('Обработка ошибок API', () => {
    it('обрабатывает ошибку при запуске теста', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[0]],
        total: 1,
      });
      vi.mocked(abTestingApi.startABTest).mockRejectedValue(
        new Error('Failed to start')
      );

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(<ABTestList onStartTest={vi.fn()} />);

      await waitFor(() => {
        const playButton = screen.getByTitle('Запустить тест');
        fireEvent.click(playButton);
      });

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalled();
      });

      consoleSpy.mockRestore();
    });

    it('обрабатывает ошибку при остановке теста', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[1]],
        total: 1,
      });
      vi.mocked(abTestingApi.stopABTest).mockRejectedValue(
        new Error('Failed to stop')
      );

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(<ABTestList onStopTest={vi.fn()} />);

      await waitFor(() => {
        const pauseButton = screen.getByTitle('Остановить тест');
        fireEvent.click(pauseButton);
      });

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalled();
      });

      consoleSpy.mockRestore();
    });

    it('обрабатывает ошибку при удалении теста', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: [mockTests[0]],
        total: 1,
      });
      vi.mocked(abTestingApi.deleteABTest).mockRejectedValue(
        new Error('Failed to delete')
      );

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(<ABTestList onDeleteTest={vi.fn()} />);

      await waitFor(() => {
        const deleteButton = screen.getByTitle('Удалить тест');
        fireEvent.click(deleteButton);
      });

      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalled();
      });

      consoleSpy.mockRestore();
    });
  });

  describe('Анимации', () => {
    it('применяет motion компонент для анимации', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      const { container } = render(<ABTestList />);

      await waitFor(() => {
        expect(container.firstChild).toBeInTheDocument();
      });
    });
  });

  describe('Accessibility', () => {
    it('имеет правильные title атрибуты на кнопках', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      render(<ABTestList />);

      await waitFor(() => {
        expect(screen.getByTitle('Запустить тест')).toBeInTheDocument();
        expect(screen.getByTitle('Остановить тест')).toBeInTheDocument();
        expect(screen.getAllByTitle('Удалить тест').length).toBeGreaterThan(0);
      });
    });

    it('использует семантическую HTML структуру', async () => {
      vi.mocked(abTestingApi.listABTests).mockResolvedValue({
        tests: mockTests,
        total: 3,
      });

      const { container } = render(<ABTestList />);

      await waitFor(() => {
        const headings = screen.getAllByText('A/B Тесты');
        expect(headings.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Статусы тестов', () => {
    const statuses: ABTestStatus[] = ['draft', 'running', 'paused', 'completed', 'stopped'];

    statuses.forEach((status) => {
      it(`правильно рендерит статус ${status}`, async () => {
        const testWithStatus: ABTestListResponse = {
          ...mockTests[0],
          status,
        };

        vi.mocked(abTestingApi.listABTests).mockResolvedValue({
          tests: [testWithStatus],
          total: 1,
        });

        render(<ABTestList />);

        await waitFor(() => {
          expect(screen.getByText(/Черновик|Запущен|Приостановлен|Завершён|Остановлен/)).toBeInTheDocument();
        });
      });
    });
  });
});
