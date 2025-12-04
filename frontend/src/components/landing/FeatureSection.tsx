import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { featureHighlights } from '../../lib/landing/sections';

const simplifiedFeatureOrder = ['resilience', 'content-sources', 'schedule-engine', 'secure-rbac'] as const;
const simplifiedFeatureIds = new Set<string>(simplifiedFeatureOrder);

const FeatureSection = () => {
  const { t } = useTranslation();
  const featuresToRender = useMemo(
    () => featureHighlights.filter((feature) => simplifiedFeatureIds.has(feature.id)),
    [],
  );

  return (
    <section
      className="space-y-8 rounded-[36px] border border-white/10 bg-brand-midnight/70 p-6 shadow-2xl shadow-black/40 backdrop-blur-lg xs:p-8"
      aria-labelledby="landing-features-title"
      data-testid="landing-feature-section"
    >
      <div className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.4em] text-brand-glow/60">
          {t('landing_features_overline')}
        </p>
        <div className="space-y-2">
          <h2 id="landing-features-title" className="text-2xl font-semibold sm:text-3xl">
            {t('landing_features_title')}
          </h2>
          <p className="text-base text-white/80 sm:text-lg">{t('landing_features_thesis')}</p>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {featuresToRender.map((feature) => (
          <article
            key={feature.id}
            className="rounded-3xl border border-white/10 bg-white/5 p-5 text-left shadow-xl shadow-black/20"
          >
            <p className="text-[0.65rem] font-semibold uppercase tracking-[0.35em] text-brand-glow/80">
              {t(feature.badgeKey)}
            </p>
            <h3 className="mt-3 text-xl font-semibold text-white">{t(feature.titleKey)}</h3>
            <p className="mt-2 text-sm text-white/80">{t(feature.descriptionKey)}</p>
            {feature.pointKeys?.length ? (
              <ul className="mt-4 space-y-2 text-sm text-white/85">
                {feature.pointKeys.slice(0, 2).map((pointKey) => (
                  <li key={pointKey} className="flex items-start gap-2">
                    <span className="mt-1 inline-flex h-1.5 w-1.5 rounded-full bg-brand-glow" aria-hidden />
                    <span>{t(pointKey)}</span>
                  </li>
                ))}
              </ul>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
};

export default FeatureSection;
