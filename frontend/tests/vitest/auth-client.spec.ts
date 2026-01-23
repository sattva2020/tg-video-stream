import { describe, it, expect, vi } from 'vitest';
import { authClient } from '../../src/lib/api/authClient';
import { client } from '../../src/api/client';
import i18n from '../../src/i18n';

describe('authClient error normalization', () => {
  it('resolves message_key via i18next when server returns message_key', async () => {
    const axiosErr = {
      isAxiosError: true,
      response: {
        status: 409,
        data: { code: 'conflict', message_key: 'auth.email_registered', hint: 'email_exists' },
      },
    } as any;

    const spy = vi.spyOn(client, 'post').mockRejectedValue(axiosErr);

    try {
      await authClient.register({ email: 'a@b.com', password: 'Password123!' });
    } catch (err: any) {
      expect(err).toBeDefined();
      expect(err.payload).toBeDefined();
      expect(err.payload.code).toBe('conflict');
      // message should be resolved from message_key via i18next
      expect(err.payload.message).toBe(i18n.t('auth.email_registered'));
    }

    spy.mockRestore();
  });
});
