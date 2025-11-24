import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import AuthCard from '../../src/components/auth/AuthCard';

describe('AuthCard error display', () => {
  it('shows banner when provided initialBanner', () => {
    render(<AuthCard mode="login" onModeChange={() => {}} initialBanner={{ tone: 'error', message: 'Test error' }} />);
    expect(screen.getByText('Test error')).toBeInTheDocument();
  });
});
