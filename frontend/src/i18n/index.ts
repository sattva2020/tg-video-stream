import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

const resources = {
  ru: {
    translation: {
      'auth.email_registered': 'Пользователь с таким email уже существует',
      'auth.google_account_exists': 'Аккаунт уже зарегистрирован через Google — свяжите учётные записи.',
      'auth.account_pending': 'Аккаунт ожидает одобрения администратора',
      'auth.account_rejected': 'Аккаунт отклонён администрацией',
      'auth.server_error': 'Что-то пошло не так. Попробуйте позже',
    },
  },
};

i18n
  .use(initReactI18next)
  .use(LanguageDetector)
  .init({
    resources,
    fallbackLng: 'ru',
    debug: false,
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
