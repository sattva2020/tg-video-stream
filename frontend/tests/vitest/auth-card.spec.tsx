import { describe, expect, it, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import AuthCard, { type AuthMode } from '../../src/components/auth/AuthCard';
import '../../src/i18n';

vi.mock('../../src/context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    login: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn(),
  }),
}));

vi.mock('../../src/lib/api/authClient', () => ({
  authClient: {
    login: vi.fn().mockResolvedValue({ access_token: 'mock-token', token_type: 'bearer' }),
    register: vi.fn().mockResolvedValue({ status: 'pending' }),
  },
  isAuthClientError: () => false,
}));

const renderCard = (mode: AuthMode = 'login') =>
  render(
    <AuthCard mode={mode} onModeChange={() => {}} />
  );

describe('AuthCard visual fidelity', () => {
  it('matches snapshot in login mode', () => {
    const { container } = renderCard('login');
    expect(container.firstChild).toMatchSnapshot();
  });

  it('matches snapshot in register mode', () => {
    const { container, getByLabelText } = renderCard('register');
    expect(container.firstChild).toMatchSnapshot();
    expect(getByLabelText(/confirm password|подтвердите пароль/i)).toBeInTheDocument();
  });

  it('toggles mode when link is clicked', () => {
    const onModeChange = vi.fn();
    const { getByText } = render(
      <AuthCard mode="login" onModeChange={onModeChange} />
    );
    
    // In 'en' locale: "Don't have an account? Sign up"
    const toggleLink = getByText(/Don't have an account\? Sign up/i);
    fireEvent.click(toggleLink);
    
    expect(onModeChange).toHaveBeenCalledWith('register');
  });
});
