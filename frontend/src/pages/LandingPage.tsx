import { useTranslation } from 'react-i18next';
import {
  FeatureSection,
  HeroSection,
  LandingLayout,
  LanguageSwitcher,
  WorkflowSection,
  UseCasesSection,
} from '../components/landing';
import PrimaryCTA from '../components/landing/PrimaryCTA';
import VisualBackground from '../components/landing/VisualBackground';
import heroContent from '../lib/landing/content';
import { useLandingLocale } from '../lib/landing/useLandingLocale';

const LandingPage = () => {
  const { locale, setLocale, supportedLocales, needsFallbackHint, autoDetectedLocale } = useLandingLocale();
  const { t } = useTranslation();

  return (
    <LandingLayout
      background={<VisualBackground />}
      nav={(
        <nav
          className="flex w-full flex-col gap-4 xs:flex-row xs:items-center xs:justify-between"
          aria-label="Навигация лендинга"
        >
          <div className="flex items-center gap-4 sm:gap-6">
            <div className="text-[0.65rem] font-semibold uppercase tracking-[0.4em] text-brand-glow xs:text-xs">
              TELEGRAM STREAMER
            </div>
            <LanguageSwitcher
              value={locale}
              options={supportedLocales}
              onChange={setLocale}
              autoDetectedLocale={autoDetectedLocale}
              needsFallbackHint={needsFallbackHint}
            />
          </div>
          <div className="flex w-full justify-start xs:w-auto xs:justify-end">
            <PrimaryCTA
              label={t(heroContent.cta.labelKey)}
              cta={heroContent.cta}
              className="w-full min-w-[150px] justify-center px-5 py-2 text-xs font-semibold uppercase shadow-brand-glow/50 xs:w-auto"
            />
          </div>
        </nav>
      )}
      hero={(
        <div className="space-y-6 pb-8">
          <HeroSection content={heroContent} locale={locale} />
          <FeatureSection />
          <WorkflowSection />
          <UseCasesSection />
        </div>
      )}
    />
  );
};

export default LandingPage;
