import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import AuthCard from '../../src/components/auth/AuthCard';
import '../../src/i18n';

/**
 * AuthCard currently implements only login flow.
 * This test verifies that a server-provided error banner is displayed.
 */

vi.mock('../../src/context/AuthContext', () => ({
  useAuth: () => ({
    login: vi.fn().mockResolvedValue(undefined),
    isPendingApproval: false,
  }),
}));

describe('AuthCard register error handling', () => {
  it('displays server error banner when register fails with auth error', async () => {
    const serverMessage = 'Пользователь с таким email уже существует';

    render(
      <MemoryRouter>
        <AuthCard initialBanner={{ tone: 'error', message: serverMessage }} />
      </MemoryRouter>
    );

    const banner = await screen.findByText(serverMessage);
    expect(banner).toBeInTheDocument();
  });
});
