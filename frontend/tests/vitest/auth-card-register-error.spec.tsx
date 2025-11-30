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
import { AuthProvider } from '../../src/context/AuthContext';

describe('AuthCard register error handling', () => {
  it('displays server error banner when register fails with auth error', async () => {
    render(
      <AuthProvider>
        <AuthCard mode="register" onModeChange={() => {}} />
      </AuthProvider>
    );

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'exist@example.com' } });
    fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'ValidPass123!' } });
    fireEvent.change(screen.getByLabelText('Confirm Password'), { target: { value: 'ValidPass123!' } });

    fireEvent.click(screen.getByTestId('register-button'));

    const banner = await screen.findByText('Пользователь с таким email уже существует');
    expect(banner).toBeInTheDocument();
  });
});
