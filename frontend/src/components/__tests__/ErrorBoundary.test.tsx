/**
 * Тесты для компонента ErrorBoundary
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import ErrorBoundary from '../ErrorBoundary';

// Компонент который выбрасывает ошибку
const ThrowError = () => {
  throw new Error('Test error');
};

// Нормальный компонент
const NormalComponent = () => <div>Normal Content</div>;

describe('ErrorBoundary', () => {
  // Подавляем console.error для чистоты вывода
  const originalError = console.error;
  beforeAll(() => {
    console.error = vi.fn();
  });
  afterAll(() => {
    console.error = originalError;
  });

  it('рендерит children когда нет ошибки', () => {
    render(
      <ErrorBoundary>
        <NormalComponent />
      </ErrorBoundary>
    );

    expect(screen.getByText('Normal Content')).toBeInTheDocument();
  });

  it('показывает fallback UI при ошибке', () => {
    render(
      <ErrorBoundary>
        <ThrowError />
      </ErrorBoundary>
    );

    expect(screen.getByText(/sorry.*there was an error/i)).toBeInTheDocument();
  });
});
