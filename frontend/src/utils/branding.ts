const STORAGE_PREFIX = 'user_logo_';
const CUSTOM_EVENT = 'user-logo-updated';
export const DEFAULT_LOGO = '/img/yantra.png?v=2';

export const getUserLogo = (userId?: string | null): string | undefined => {
  if (!userId) return undefined;
  try {
    return localStorage.getItem(`${STORAGE_PREFIX}${userId}`) || undefined;
  } catch {
    return undefined;
  }
};

export const setUserLogo = (userId: string, dataUrl: string): void => {
  localStorage.setItem(`${STORAGE_PREFIX}${userId}`, dataUrl);
  window.dispatchEvent(new CustomEvent(CUSTOM_EVENT, { detail: { userId, logo: dataUrl } }));
};

export const resetUserLogo = (userId: string): void => {
  localStorage.removeItem(`${STORAGE_PREFIX}${userId}`);
  window.dispatchEvent(new CustomEvent(CUSTOM_EVENT, { detail: { userId, logo: undefined } }));
};

export const subscribeLogoChanges = (callback: (userId?: string, logo?: string) => void): (() => void) => {
  const handler = (event: Event) => {
    const custom = event as CustomEvent;
    const detail = custom.detail as { userId?: string; logo?: string } | undefined;
    callback(detail?.userId, detail?.logo);
  };
  window.addEventListener(CUSTOM_EVENT, handler as EventListener);
  return () => window.removeEventListener(CUSTOM_EVENT, handler as EventListener);
};
