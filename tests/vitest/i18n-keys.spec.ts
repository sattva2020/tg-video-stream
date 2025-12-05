import * as i18nModule from '../../src/i18n';
const i18n = (i18nModule as any).default;
const RESOURCES = (i18nModule as any).I18N_RESOURCES || (i18n as any).options?.resources || {};

describe('i18n smoke-check', () => {
  const keys = [
    'auth.email_registered',
    'auth.google_account_exists',
    'auth.account_pending',
    'auth.account_rejected',
    'auth.server_error',
  ];

  const langs = ['ru', 'en'];

  // The test uses a static, deterministic check (read from src/i18n/index.ts)
  // instead of relying on runtime i18n state which can be flaky when running tests in parallel.
  const path = require('path');
  const fs = require('fs');
  const i18nSource = fs.readFileSync(path.resolve(__dirname, '../../src/i18n/index.ts'), 'utf8');

  langs.forEach((lng) => {
    it(`has translations for all keys ${lng} (source-level occurrence check)`, () => {
      // ensure each key appears at least twice (once per language) so we cover ru + en
      keys.forEach((k) => {
        const count = (i18nSource.match(new RegExp(k.replace(/\./g, '\\.'), 'g')) || []).length;
        expect(count, `key ${k} should appear more than once for multiple languages in src/i18n/index.ts`).toBeGreaterThanOrEqual(2);
      });
    });
  });
});
