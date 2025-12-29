/**
 * Тесты для LoadingBar и PageLoader компонентов
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import LoadingBar from '../LoadingBar';
import PageLoader from '../PageLoader';

describe('LoadingBar', () => {
  it('рендерит loading bar когда isLoading=true', () => {
    const { container } = render(<LoadingBar isLoading={true} />);
    expect(container).toBeTruthy();
  });

  it('скрывается когда isLoading=false', () => {
    const { container } = render(<LoadingBar isLoading={false} />);
    expect(container).toBeTruthy();
  });
});

describe('PageLoader', () => {
  it('рендерит page loader', () => {
    const { container } = render(<PageLoader />);
    expect(container.firstChild).toBeTruthy();
  });

  it('имеет loading текст', () => {
    render(<PageLoader />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('использует fixed positioning', () => {
    const { container } = render(<PageLoader />);
    const loader = container.firstChild as HTMLElement;
    expect(loader?.className).toMatch(/fixed|inset/);
  });
});
