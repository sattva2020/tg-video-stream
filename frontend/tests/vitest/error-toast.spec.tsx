import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AuthCard from '../../src/components/auth/AuthCard';
import { MemoryRouter } from 'react-router-dom';
import '../../src/i18n';

vi.mock('../../src/context/AuthContext', () => ({
  useAuth: () => ({
    login: vi.fn().mockResolvedValue(undefined),
    isPendingApproval: false,
  }),
}));

describe('AuthCard error display', () => {
  it('shows banner when provided initialBanner', () => {
    render(
      <MemoryRouter>
        <AuthCard initialBanner={{ tone: 'error', message: 'Test error' }} />
      </MemoryRouter>
    );
    expect(screen.getByText('Test error')).toBeInTheDocument();
  });
});
