import { useTranslation } from 'react-i18next';
import { landingUseCases } from '../../lib/landing/sections';

const accentVarMap: Record<string, string> = {
  sky: '--landing-usecase-cyan',
  violet: '--landing-usecase-violet',
  amber: '--landing-usecase-amber',
};

const UseCasesSection = () => {
  const { t } = useTranslation();

  return (
    <section
      className="space-y-6 rounded-[36px] border p-6 backdrop-blur-lg xs:p-8"
      aria-labelledby="landing-usecases-title"
      style={{
        background: 'var(--landing-usecase-surface)',
        borderColor: 'var(--landing-card-border-strong)',
        boxShadow: 'var(--landing-section-shadow)',
        color: 'var(--landing-text)',
      }}
    >
      <div className="space-y-2">
        <p
          className="text-xs font-semibold uppercase tracking-[0.4em]"
          style={{ color: 'var(--landing-hero-tag-text)' }}
        >
          {t('landing_usecases_overline')}
        </p>
        <div className="space-y-2">
          <h2
            id="landing-usecases-title"
            className="text-2xl font-semibold sm:text-3xl"
            style={{ color: 'var(--landing-heading)' }}
          >
            {t('landing_usecases_title')}
          </h2>
          <p className="text-base sm:text-lg" style={{ color: 'var(--landing-text-muted)' }}>
            {t('landing_usecases_subtitle')}
          </p>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {landingUseCases.map((useCase) => (
          <article
            key={useCase.id}
            className="relative overflow-hidden rounded-4xl border p-5 text-left"
            style={{
              background: 'var(--landing-card-bg)',
              borderColor: 'var(--landing-card-border)',
              boxShadow: 'var(--landing-card-shadow)',
              color: 'var(--landing-text)',
            }}
          >
            <div
              className="pointer-events-none absolute inset-0 mix-blend-overlay"
              aria-hidden
              style={{
                background: `var(${accentVarMap[useCase.accent] ?? '--landing-usecase-cyan'})`,
              }}
            />
            <div className="relative space-y-3">
              <h3 className="text-xl font-semibold" style={{ color: 'var(--landing-text)' }}>
                {t(useCase.titleKey)}
              </h3>
              <p className="text-sm" style={{ color: 'var(--landing-text-muted)' }}>
                {t(useCase.descriptionKey)}
              </p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
};

export default UseCasesSection;
