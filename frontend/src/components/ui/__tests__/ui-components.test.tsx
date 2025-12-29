/**
 * Тесты для UI компонентов Button и Input
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '../button';
import { Input } from '../input';

describe('Button', () => {
  it('рендерит с текстом', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('вызывает onClick при клике', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click</Button>);
    
    fireEvent.click(screen.getByText('Click'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('disabled состояние блокирует клики', () => {
    const handleClick = vi.fn();
    render(<Button disabled onClick={handleClick}>Disabled</Button>);
    
    const button = screen.getByText('Disabled');
    expect(button).toBeDisabled();
    
    fireEvent.click(button);
    expect(handleClick).not.toHaveBeenCalled();
  });

  it('применяет variant классы', () => {
    const { rerender } = render(<Button variant="destructive">Delete</Button>);
    let button = screen.getByText('Delete');
    expect(button.className).toMatch(/destructive/);
    
    rerender(<Button variant="outline">Cancel</Button>);
    button = screen.getByText('Cancel');
    expect(button.className).toMatch(/outline/);
  });

  it('применяет size классы', () => {
    render(<Button size="sm">Small</Button>);
    const button = screen.getByText('Small');
    expect(button.className).toContain('h-9');
  });
});

describe('Input', () => {
  it('рендерит input элемент', () => {
    render(<Input placeholder="Enter text" />);
    expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument();
  });

  it('принимает и отображает значение', () => {
    render(<Input value="test value" readOnly />);
    const input = screen.getByDisplayValue('test value') as HTMLInputElement;
    expect(input.value).toBe('test value');
  });

  it('вызывает onChange при изменении', () => {
    const handleChange = vi.fn();
    render(<Input onChange={handleChange} />);
    
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'new value' } });
    
    expect(handleChange).toHaveBeenCalled();
  });

  it('disabled состояние работает', () => {
    render(<Input disabled placeholder="Disabled" />);
    const input = screen.getByPlaceholderText('Disabled');
    expect(input).toBeDisabled();
  });

  it('type по умолчанию text', () => {
    render(<Input />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('type', 'text');
  });

  it('принимает разные типы', () => {
    const { rerender } = render(<Input type="email" />);
    let input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('type', 'email');
    
    rerender(<Input type="password" />);
    input = document.querySelector('input[type="password"]')!;
    expect(input).toHaveAttribute('type', 'password');
  });

  it('применяет кастомный className', () => {
    render(<Input className="custom-class" />);
    const input = screen.getByRole('textbox');
    expect(input.className).toContain('custom-class');
  });
});
