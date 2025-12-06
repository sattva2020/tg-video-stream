import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

export const I18N_RESOURCES = {
  ru: {
    translation: {
      'auth.email_registered': 'Пользователь с таким email уже существует',
      'auth.google_account_exists': 'Аккаунт уже зарегистрирован через Google — свяжите учётные записи.',
      'auth.account_pending': 'Аккаунт ожидает одобрения администратора',
      'auth.account_rejected': 'Аккаунт отклонён администрацией',
      'auth.server_error': 'Что-то пошло не так. Попробуйте позже',
    },
  },
  en: {
    translation: {
      'auth.email_registered': 'An account with this email already exists',
      'auth.google_account_exists': 'An account is already registered via Google — please link your accounts.',
      'auth.account_pending': "Your account is awaiting administrator approval",
      'auth.account_rejected': "Your account has been rejected by administrators",
      'auth.server_error': 'Something went wrong. Please try again later',
    },
  },
};

i18n
  .use(initReactI18next)
  .use(LanguageDetector)
  .init({
    resources: I18N_RESOURCES,
    fallbackLng: 'ru',
    debug: false,
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
