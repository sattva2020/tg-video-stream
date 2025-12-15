import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import AuthCard from '../../src/components/auth/AuthCard';
import '../../src/i18n';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../src/context/AuthContext', () => ({
  useAuth: () => ({
    login: vi.fn().mockResolvedValue(undefined),
    isPendingApproval: false,
  }),
}));

vi.mock('../../src/api/auth', () => ({
  authApi: {
    login: vi.fn().mockResolvedValue({ access_token: 'mock-token', token_type: 'bearer' }),
  },
}));

const renderCard = () =>
  render(
    <MemoryRouter>
      <AuthCard />
    </MemoryRouter>
  );

describe('AuthCard visual fidelity', () => {
  it('renders the login snapshot', () => {
    const { container } = renderCard();
    expect(container.firstChild).toMatchSnapshot();
  });

  it('renders login inputs and button', () => {
    renderCard();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/пароль|password/i)).toBeInTheDocument();
    expect(screen.getByTestId('login-button')).toBeInTheDocument();
  });
});
