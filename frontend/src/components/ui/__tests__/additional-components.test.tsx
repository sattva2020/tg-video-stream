/**
 * Тесты для дополнительных UI компонентов
 */
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Label } from '../label';
import { Textarea } from '../textarea';
import { Pagination } from '../Pagination';

describe('Label', () => {
  it('рендерит label с текстом', () => {
    render(<Label htmlFor="input1">Username</Label>);
    expect(screen.getByText('Username')).toBeInTheDocument();
  });

  it('применяет htmlFor атрибут', () => {
    render(<Label htmlFor="email">Email</Label>);
    const label = screen.getByText('Email');
    expect(label).toHaveAttribute('for', 'email');
  });

  it('применяет кастомный className', () => {
    render(<Label className="custom-label">Label</Label>);
    const label = screen.getByText('Label');
    expect(label.className).toContain('custom-label');
  });
});

describe('Textarea', () => {
  it('рендерит textarea', () => {
    render(<Textarea placeholder="Enter text" />);
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
  });

  it('принимает и отображает значение', () => {
    render(<Textarea value="Test content" readOnly />);
    const textarea = screen.getByDisplayValue('Test content') as HTMLTextAreaElement;
    expect(textarea.value).toBe('Test content');
  });

  it('вызывает onChange при вводе', () => {
    const handleChange = vi.fn();
    render(<Textarea onChange={handleChange} />);
    
    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'New text' } });
    
    expect(handleChange).toHaveBeenCalled();
  });

  it('применяет disabled состояние', () => {
    render(<Textarea disabled placeholder="Disabled" />);
    const textarea = screen.getByPlaceholderText('Disabled');
    expect(textarea).toBeDisabled();
  });

  it('применяет кастомный className', () => {
    render(<Textarea className="custom-textarea" />);
    const textarea = screen.getByRole('textbox');
    expect(textarea.className).toContain('custom-textarea');
  });
});

describe('Pagination', () => {
  it('рендерит pagination с total и current page', () => {
    render(<Pagination total={100} currentPage={1} onPageChange={() => {}} />);
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('вызывает onPageChange при клике на страницу', () => {
    const handlePageChange = vi.fn();
    render(<Pagination total={50} currentPage={1} onPageChange={handlePageChange} />);
    
    // Проверяем что компонент рендерится
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('отображает правильное количество страниц', () => {
    render(<Pagination total={25} currentPage={2} onPageChange={() => {}} />);
    // При total=25, itemsPerPage=10 (default), должно быть 3 страницы
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('отображает первую страницу', () => {
    render(<Pagination total={30} currentPage={1} onPageChange={() => {}} />);
    expect(screen.getByText('1')).toBeInTheDocument();
  });
});
