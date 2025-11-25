import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import AuthCard from '../../src/components/auth/AuthCard';
import { AuthProvider } from '../../src/context/AuthContext';

describe('AuthCard error display', () => {
  it('shows banner when provided initialBanner', () => {
    render(
      <AuthProvider>
        <AuthCard mode="login" onModeChange={() => {}} initialBanner={{ tone: 'error', message: 'Test error' }} />
      </AuthProvider>
    );
    expect(screen.getByText('Test error')).toBeInTheDocument();
  });
});
