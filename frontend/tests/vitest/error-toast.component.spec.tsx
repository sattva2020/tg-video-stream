import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import ErrorToast from '../../src/components/auth/ErrorToast';

describe('ErrorToast component', () => {
  it('renders message and has role=alert', () => {
    render(<ErrorToast message="Пример ошибки" tone="error" data-testid="et" />);
    const el = screen.getByTestId('et');
    expect(el).toBeInTheDocument();
    expect(el).toHaveAttribute('role', 'alert');
    expect(el).toHaveTextContent('Пример ошибки');
  });
});
