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
          className="flex w-full flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
          aria-label="Навигация лендинга"
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-6">
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
          <PrimaryCTA
            label={t('cta_enter')}
            cta={heroContent.cta}
            className="shadow-brand-glow/40 sm:w-auto"
          />
        </nav>
      )}
      hero={<HeroSection content={heroContent} locale={locale} hideCta />}
    />
  );
};

export default LandingPage;
