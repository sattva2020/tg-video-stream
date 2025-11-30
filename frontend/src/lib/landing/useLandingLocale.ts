import { useCallback, useEffect, useMemo, useState } from 'react';
import i18n from '../../i18n';
import type { LocaleKey } from '../../components/landing';

const SUPPORTED_LOCALES: LocaleKey[] = ['en', 'ru', 'uk', 'de'];
const STORAGE_KEY = 'landing:locale';

const hasWindow = () => typeof window !== 'undefined';
const normalize = (value: string) => value.split('-')[0].toLowerCase();

export const parseAcceptLanguage = (header: string) =>
  header
    .split(',')
    .map((segment, index) => {
      const [rawLang, rawQ] = segment.trim().split(';');
      const q = rawQ ? Number(rawQ.replace('q=', '')) : 1 - index * 0.01;
      return {
        lang: normalize(rawLang),
        q: Number.isFinite(q) ? q : 0,
      };
    })
    .filter((entry) => Boolean(entry.lang))
    .sort((a, b) => b.q - a.q);

const readAcceptLanguage = (): string | undefined => {
  if (!hasWindow()) {
    return undefined;
  }

  const injected = (window as Window & { __ACCEPT_LANGUAGE__?: string }).__ACCEPT_LANGUAGE__;
  if (typeof injected === 'string' && injected.trim().length) {
    return injected;
  }

  if (navigator.languages && navigator.languages.length) {
    return navigator.languages.join(',');
  }

  return navigator.language;
};

const detectFromHeader = (): { locale: LocaleKey; isFallback: boolean } => {
  const raw = readAcceptLanguage();
  if (!raw) {
    return { locale: 'en', isFallback: true };
  }

  const parsed = parseAcceptLanguage(raw);
  for (const candidate of parsed) {
    if (SUPPORTED_LOCALES.includes(candidate.lang as LocaleKey)) {
      return { locale: candidate.lang as LocaleKey, isFallback: false };
    }
  }

  return { locale: 'en', isFallback: true };
};

const readStoredLocale = (): LocaleKey | null => {
  if (!hasWindow()) {
    return null;
  }

  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored && SUPPORTED_LOCALES.includes(stored as LocaleKey)) {
    return stored as LocaleKey;
  }

  return null;
};

const commitLocale = (locale: LocaleKey) => {
  if (!hasWindow()) {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, locale);
};

export const useLandingLocale = () => {
  const fallbackInfo = useMemo(() => detectFromHeader(), []);
  const [locale, setLocale] = useState<LocaleKey>(() => readStoredLocale() ?? fallbackInfo.locale);
  const [needsFallbackHint, setNeedsFallbackHint] = useState(() => !readStoredLocale() && fallbackInfo.isFallback);

  const updateLocale = useCallback((next: LocaleKey) => {
    setLocale(next);
    setNeedsFallbackHint(false);
    commitLocale(next);
  }, []);

  useEffect(() => {
    if (i18n.language !== locale) {
      void i18n.changeLanguage(locale);
    }
    commitLocale(locale);
  }, [locale]);

  return {
    locale,
    setLocale: updateLocale,
    supportedLocales: SUPPORTED_LOCALES,
    needsFallbackHint,
    autoDetectedLocale: fallbackInfo.locale,
  } as const;
};
