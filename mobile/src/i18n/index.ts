import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { I18nManager } from 'react-native';
import * as Localization from 'expo-localization';

// Import locale files
import en from './locales/en.json';
import ru from './locales/ru.json';
import uk from './locales/uk.json';
import de from './locales/de.json';
import es from './locales/es.json';
import ja from './locales/ja.json';
import zh from './locales/zh.json';

// Get device language
const getDeviceLanguage = (): string => {
  const locale = Localization.locale;
  if (locale) {
    // Extract language code from locale (e.g., 'en-US' -> 'en')
    const languageCode = locale.split('-')[0];
    // Map device language to supported languages
    const supportedLanguages = ['en', 'ru', 'uk', 'de', 'es', 'ja', 'zh'];
    if (supportedLanguages.includes(languageCode)) {
      return languageCode;
    }
  }
  return 'en'; // Default fallback
};

// Initialize i18next
i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      ru: { translation: ru },
      uk: { translation: uk },
      de: { translation: de },
      es: { translation: es },
      ja: { translation: ja },
      zh: { translation: zh },
    },
    lng: getDeviceLanguage(),
    fallbackLng: 'en',
    supportedLngs: ['en', 'ru', 'uk', 'de', 'es', 'ja', 'zh'],
    compatibilityJSON: 'v3',
    interpolation: {
      escapeValue: false, // React Native already escapes values
    },
    react: {
      useSuspense: false, // Disable suspense for React Native
    },
  });

// Export helper functions
export const changeLanguage = async (language: string): Promise<void> => {
  await i18n.changeLanguage(language);

  // Handle RTL languages if needed in the future
  // For example, Arabic, Hebrew, etc.
  const isRTL = language === 'ar' || language === 'he';
  I18nManager.allowRTL(isRTL);
  I18nManager.forceRTL(isRTL);
};

export const getCurrentLanguage = (): string => {
  return i18n.language;
};

export const getSupportedLanguages = (): Array<{ code: string; name: string }> => {
  return [
    { code: 'en', name: 'English' },
    { code: 'ru', name: 'Русский' },
    { code: 'uk', name: 'Українська' },
    { code: 'de', name: 'Deutsch' },
    { code: 'es', name: 'Español' },
    { code: 'ja', name: '日本語' },
    { code: 'zh', name: '中文' },
  ];
};

export default i18n;
