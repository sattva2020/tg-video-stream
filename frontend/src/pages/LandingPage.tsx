import { HeroSection, LandingLayout, LanguageSwitcher, PrimaryCTA } from '../components/landing';
import VisualBackground from '../components/landing/VisualBackground';
import heroContent from '../lib/landing/content';
import { useLandingLocale } from '../lib/landing/useLandingLocale';
import { useTranslation } from 'react-i18next';

const LandingPage = () => {
  const { locale, setLocale, supportedLocales, needsFallbackHint, autoDetectedLocale } = useLandingLocale();
  const { t } = useTranslation();

  return (
    <LandingLayout
      background={<VisualBackground />}
      nav={(
        <nav
          className="flex w-full items-center justify-between"
          aria-label="Навигация лендинга"
        >
          {/* Левая часть: логотип и переключатель языка */}
          <div className="flex items-center gap-4 sm:gap-6">
            <div className="text-[0.65rem] font-semibold uppercase tracking-[0.4em] text-brand-glow xs:text-xs">
              SATTVA STREAMER
            </div>
            <LanguageSwitcher
              value={locale}
              options={supportedLocales}
              onChange={setLocale}
              autoDetectedLocale={autoDetectedLocale}
              needsFallbackHint={needsFallbackHint}
            />
          </div>
          
          {/* Правая часть: кнопка Войти */}
          <div className="flex items-center gap-3 sm:gap-4">
            <PrimaryCTA
              label={t('cta_enter')}
              cta={heroContent.cta}
              className="w-auto shadow-brand-glow/40"
            />
          </div>
        </nav>
      )}
      hero={<HeroSection content={heroContent} locale={locale} hideCta />}
    />
  );
};

export default LandingPage;
