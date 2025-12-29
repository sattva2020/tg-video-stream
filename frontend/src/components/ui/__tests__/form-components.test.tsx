/**
 * Тесты для форм компонентов
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import PasswordInput from '../PasswordInput';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '../select';
import { ScrollArea } from '../scroll-area';

describe('PasswordInput', () => {
  it('рендерит password input', () => {
    render(<PasswordInput placeholder="Enter password" />);
    expect(screen.getByPlaceholderText('Enter password')).toBeInTheDocument();
  });

  it('скрывает пароль по умолчанию', () => {
    render(<PasswordInput value="secret123" readOnly />);
    const input = screen.getByDisplayValue('secret123') as HTMLInputElement;
    expect(input.type).toBe('password');
  });

  it('показывает/скрывает пароль при клике на иконку', () => {
    render(<PasswordInput value="secret123" readOnly />);
    
    const toggleButton = screen.getByRole('button');
    const input = screen.getByDisplayValue('secret123') as HTMLInputElement;
    
    expect(input.type).toBe('password');
    
    fireEvent.click(toggleButton);
    expect(input.type).toBe('text');
    
    fireEvent.click(toggleButton);
    expect(input.type).toBe('password');
  });

  it('принимает ввод пароля', () => {
    render(<PasswordInput placeholder="password" />);
    const input = screen.getByPlaceholderText('password');
    expect(input).toBeInTheDocument();
  });

  it('рендерится с disabled', () => {
    render(<PasswordInput disabled placeholder="disabled" />);
    expect(screen.getByPlaceholderText('disabled')).toBeInTheDocument();
  });
});

describe('Select', () => {
  it('рендерит select component', () => {
    render(
      <Select>
        <SelectTrigger>
          <SelectValue placeholder="Select option" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="1">Option 1</SelectItem>
        </SelectContent>
      </Select>
    );
    
    expect(screen.getByText('Select option')).toBeInTheDocument();
  });

  it('применяет кастомный className на trigger', () => {
    const { container } = render(
      <Select>
        <SelectTrigger className="custom-trigger">
          <SelectValue />
        </SelectTrigger>
      </Select>
    );
    
    expect(container.querySelector('.custom-trigger')).toBeInTheDocument();
  });
});

describe('ScrollArea', () => {
  it('рендерит scroll area с контентом', () => {
    render(
      <ScrollArea>
        <div>Scrollable content</div>
      </ScrollArea>
    );
    
    expect(screen.getByText('Scrollable content')).toBeInTheDocument();
  });

  it('применяет кастомный className', () => {
    const { container } = render(
      <ScrollArea className="custom-scroll">
        <div>Content</div>
      </ScrollArea>
    );
    
    const scrollArea = container.firstChild as HTMLElement;
    expect(scrollArea?.className).toContain('custom-scroll');
  });

  it('рендерит children правильно', () => {
    render(
      <ScrollArea>
        <div data-testid="child1">Child 1</div>
        <div data-testid="child2">Child 2</div>
      </ScrollArea>
    );
    
    expect(screen.getByTestId('child1')).toBeInTheDocument();
    expect(screen.getByTestId('child2')).toBeInTheDocument();
  });
});
