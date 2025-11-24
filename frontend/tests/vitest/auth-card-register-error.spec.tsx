import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

vi.mock('../../src/lib/api/authClient', () => {
  return {
    authClient: {
      register: vi.fn().mockRejectedValue({ payload: { code: 'conflict', message: 'Пользователь с таким email уже существует', hint: 'email_exists' } }),
    },
    isAuthClientError: (e: unknown) => true,
  };
});

import AuthCard from '../../src/components/auth/AuthCard';

describe('AuthCard register error handling', () => {
  it('displays server error banner when register fails with auth error', async () => {
    render(<AuthCard mode="register" onModeChange={() => {}} />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'exist@example.com' } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: 'ValidPass123!' } });
    fireEvent.change(screen.getByLabelText(/confirm_password/i), { target: { value: 'ValidPass123!' } });

    fireEvent.click(screen.getByTestId('auth-primary-action'));

    const banner = await screen.findByText('Пользователь с таким email уже существует');
    expect(banner).toBeInTheDocument();
  });
});
