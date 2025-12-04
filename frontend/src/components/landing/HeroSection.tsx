import { useId, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import clsx from 'clsx';
import PrimaryCTA from './PrimaryCTA';
import type { HeroContent, LocaleKey } from './types';

export type HeroSectionProps = {
  content: HeroContent;
  locale: LocaleKey;
  onCtaClick?: () => void;
  hideCta?: boolean;
};

const HeroStatGrid = ({
  content,
  locale,
}: {
  content: HeroContent['benefits'];
  locale: LocaleKey;
}) => {
  const { t, i18n } = useTranslation();

  const stats = useMemo(
    () =>
      content.map((item) => {
        const hasTranslation = i18n.exists(item.labelKey, { lng: locale });
        return {
          ...item,
          label: t(item.labelKey),
          metric: item.metricKey ? t(item.metricKey) : undefined,
          isFallback: !hasTranslation,
        };
      }),
    [content, i18n, locale, t],
  );

  return (
    <div
      className="rounded-[32px] border border-white/10 bg-white/5 p-4 shadow-2xl shadow-black/40 backdrop-blur"
      aria-label={t('hero_benefits_label', 'Key benefits')}
      data-testid="hero-benefits"
    >
      <div className="grid gap-3 sm:grid-cols-2">
        {stats.map((item) => (
          <article
            key={item.id}
            className="rounded-2xl border border-white/10 bg-brand-midnight/40 p-4 text-white/90"
          >
            <p
              className={clsx('text-base font-semibold 3xl:text-lg', {
                'italic text-white/75': item.isFallback,
              })}
            >
              <span lang={item.isFallback ? 'en' : undefined}>{item.label}</span>
              {item.isFallback ? (
                <span className="sr-only">{t('landing_benefit_fallback_notice')}</span>
              ) : null}
            </p>
            {item.metric ? (
              <p className="text-sm font-semibold uppercase tracking-[0.3em] text-brand-glow">
                {item.metric}
              </p>
            ) : null}
          </article>
        ))}
      </div>
    </div>
  );
};

const HeroSection = ({ content, locale, onCtaClick, hideCta }: HeroSectionProps) => {
  const { t } = useTranslation();
  const headingId = useId();
  const subtitleId = useId();

  return (
    <section
      className="grid gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]"
      aria-labelledby={headingId}
      aria-describedby={subtitleId}
      data-landing-hero
    >
      <div className="space-y-6">
        <div className="space-y-4">
          <p className="text-[0.7rem] font-semibold uppercase tracking-[0.4em] text-brand-glow xs:text-xs">
            {t(content.labelKey)}
          </p>
          <h1
            id={headingId}
            className="text-[clamp(2.35rem,6vw,3.65rem)] font-bold leading-tight text-white drop-shadow-[0_25px_60px_rgba(15,185,255,0.35)]"
          >
            {t(content.titleKey)}
          </h1>
          <p id={subtitleId} className="text-base leading-relaxed text-white/85 sm:text-lg">
            {t(content.subtitleKey)}
          </p>
        </div>
        {!hideCta ? (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <PrimaryCTA
              label={t(content.cta.labelKey)}
              cta={content.cta}
              onClick={onCtaClick}
              ariaDescribedBy={subtitleId}
              className="w-full sm:w-auto"
            />
            {content.secondaryCta ? (
              <a
                href={content.secondaryCta.href}
                data-tracking-id={content.secondaryCta.trackingId}
                className="inline-flex min-h-[44px] w-full items-center justify-center rounded-full border border-white/30 px-6 py-3 text-sm font-semibold uppercase tracking-wide text-white transition hover:border-white/60 hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-glow sm:w-auto sm:min-w-[210px] sm:px-8 sm:py-4 sm:text-base"
              >
                {t(content.secondaryCta.labelKey)}
              </a>
            ) : null}
          </div>
        ) : null}
        <div className="rounded-3xl border border-white/10 bg-white/5 p-4 text-sm text-white/80 shadow-inner shadow-black/20">
          <p>{t('landing_features_thesis')}</p>
        </div>
      </div>
      <HeroStatGrid content={content.benefits} locale={locale} />
    </section>
  );
};

export default HeroSection;
