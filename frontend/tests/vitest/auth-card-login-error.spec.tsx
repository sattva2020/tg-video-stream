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

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: 'exist@example.com' } });
    fireEvent.change(screen.getByLabelText(/пароль|password/i), { target: { value: 'ValidPass123!' } });

    fireEvent.click(screen.getByTestId('login-button'));

    const errorBanner = await screen.findByText('Неверный email или пароль.');
    expect(errorBanner).toBeInTheDocument();
  });
});
