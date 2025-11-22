import { HeroSection, LandingLayout, LanguageSwitcher } from '../components/landing';
import VisualBackground from '../components/landing/VisualBackground';
import heroContent from '../lib/landing/content';
import { useLandingLocale } from '../lib/landing/useLandingLocale';

const LandingPage = () => {
  const { locale, setLocale, supportedLocales, needsFallbackHint, autoDetectedLocale } = useLandingLocale();

  return (
    <LandingLayout
      background={<VisualBackground />}
      nav={(
        <nav
          className="flex w-full flex-col gap-3 xs:flex-row xs:items-center xs:justify-between"
          aria-label="Навигация лендинга"
        >
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
        </nav>
      )}
      hero={<HeroSection content={heroContent} locale={locale} />}
    />
  );
};

export default LandingPage;
