import i18next from '../i18n';

export interface AuthFormError {
  code: string;
  hint?: string;
  message: string;
  severity?: 'error' | 'warning' | 'info';
}

/**
 * Normalize AuthClientError / payload into shape usable by forms/UI
 */
export const normalizeAuthError = (err: unknown): AuthFormError => {
  // defensive defaults
  const fallback: AuthFormError = {
    code: 'server',
    message: 'Что-то пошло не так. Попробуйте позже.',
    severity: 'error',
  };

  // If error is AuthClientError (duck-typing)
  const anyErr = err as any;
  if (!anyErr || typeof anyErr !== 'object') return fallback;

  const payload = anyErr.payload;
  if (!payload || typeof payload !== 'object') return fallback;

  const code = payload.code ?? 'server';
  const hint = payload.hint as string | undefined;

  // Prefer server-provided message, fall back to message_key resolved via i18next
  if (typeof payload.message === 'string' && payload.message.length > 0) {
    return { code, hint, message: payload.message, severity: 'error' };
  }

  if (typeof payload.message_key === 'string' && payload.message_key.length > 0) {
    try {
      const resolved = i18next.t(payload.message_key);
      return { code, hint, message: resolved, severity: 'error' };
    } catch (e) {
      return { code, hint, message: payload.message_key, severity: 'error' };
    }
  }

  return { ...fallback, code, hint };
};

export default { normalizeAuthError };
