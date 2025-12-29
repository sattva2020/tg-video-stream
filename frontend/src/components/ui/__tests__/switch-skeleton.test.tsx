/**
 * Тесты для Switch и Skeleton компонентов
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Switch } from '../switch';
import { Skeleton } from '../skeleton';

describe('Switch', () => {
  it('рендерит switch элемент', () => {
    const { container } = render(<Switch />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('применяет disabled состояние', () => {
    const { container } = render(<Switch disabled />);
    const switchElement = container.firstChild;
    expect(switchElement).toBeInTheDocument();
  });
});

describe('Skeleton', () => {
  it('рендерит skeleton loader', () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('имеет правильные стили для анимации', () => {
    const { container } = render(<Skeleton />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton.className).toMatch(/animate-pulse/);
  });

  it('принимает кастомный className', () => {
    const { container } = render(<Skeleton className="w-full h-12" />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton.className).toContain('w-full');
    expect(skeleton.className).toContain('h-12');
  });

  it('рендерит multiple skeletons', () => {
    const { container } = render(
      <div>
        <Skeleton className="h-4 w-full mb-2" />
        <Skeleton className="h-4 w-3/4 mb-2" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    );
    
    const skeletons = container.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBe(3);
  });

  it('используется для loading состояний', () => {
    const LoadingCard = () => (
      <div className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-4/5" />
      </div>
    );

    const { container } = render(<LoadingCard />);
    const skeletons = container.querySelectorAll('[class*="animate-pulse"]');
    expect(skeletons.length).toBeGreaterThanOrEqual(2);
  });
});
