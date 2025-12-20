import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import AuthCard from '../../src/components/auth/AuthCard';
import '../../src/i18n';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../src/context/AuthContext', () => ({
  useAuth: () => ({
    login: vi.fn().mockResolvedValue(undefined),
    isPendingApproval: false,
  }),
}));

vi.mock('../../src/api/auth', () => {
  const loginError = {
    response: {
      status: 401,
    },
  };

  return {
    authApi: {
      login: vi.fn().mockRejectedValue(loginError),
    },
  };
});

describe('AuthCard login error handling', () => {
  it('shows invalid credentials message when login fails', async () => {
    render(
      <MemoryRouter>
        <AuthCard />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByTestId('email-input'), { target: { value: 'exist@example.com' } });
    fireEvent.change(screen.getByTestId('password-input'), { target: { value: 'ValidPass123!' } });

    fireEvent.click(screen.getByTestId('login-button'));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/Неверный email или пароль\.|Invalid email or password\./i);
  });
});
