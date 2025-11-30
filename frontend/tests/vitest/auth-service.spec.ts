import { describe, it, expect } from 'vitest';
import i18n from '../../src/i18n';
import { normalizeAuthError } from '../../src/services/authService';

describe('authService.normalizeAuthError', () => {
  it('returns message when payload provides message', () => {
    const err = { payload: { code: 'conflict', message: 'Прямой текст', hint: 'email_exists' } } as any;
    const res = normalizeAuthError(err);
    expect(res.code).toBe('conflict');
    expect(res.message).toBe('Прямой текст');
  });

  it('resolves message_key via i18n when message missing', () => {
    const err = { payload: { code: 'conflict', message_key: 'auth.email_registered', hint: 'email_exists' } } as any;
    const res = normalizeAuthError(err);
    expect(res.message).toBe(i18n.t('auth.email_registered'));
  });
});
