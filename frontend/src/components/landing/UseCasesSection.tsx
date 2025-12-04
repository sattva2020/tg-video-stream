import { useTranslation } from 'react-i18next';
import { landingUseCases } from '../../lib/landing/sections';

const accentMap: Record<string, string> = {
  sky: 'from-[#1B7CFF]/40 via-transparent to-transparent',
  violet: 'from-[#7C3AED]/35 via-transparent to-transparent',
  amber: 'from-[#FFB347]/35 via-transparent to-transparent',
};

const UseCasesSection = () => {
  const { t } = useTranslation();

  return (
    <section
      className="space-y-6 rounded-[36px] border border-white/10 bg-brand-midnight/80 p-6 shadow-2xl shadow-black/30 backdrop-blur-lg xs:p-8"
      aria-labelledby="landing-usecases-title"
    >
      <div className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.4em] text-brand-glow/70">
          {t('landing_usecases_overline')}
        </p>
        <div className="space-y-2">
          <h2 id="landing-usecases-title" className="text-2xl font-semibold sm:text-3xl">
            {t('landing_usecases_title')}
          </h2>
          <p className="text-base text-white/80 sm:text-lg">{t('landing_usecases_subtitle')}</p>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {landingUseCases.map((useCase) => (
          <article
            key={useCase.id}
            className="relative overflow-hidden rounded-4xl border border-white/10 bg-white/5 p-5 text-left shadow-xl shadow-black/20"
          >
            <div
              className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${accentMap[useCase.accent] ?? accentMap.sky}`}
              aria-hidden
            />
            <div className="relative space-y-3">
              <h3 className="text-xl font-semibold text-white">{t(useCase.titleKey)}</h3>
              <p className="text-sm text-white/85">{t(useCase.descriptionKey)}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
};

export default UseCasesSection;
