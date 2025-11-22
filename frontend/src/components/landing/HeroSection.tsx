import { useId, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import clsx from 'clsx';
import PrimaryCTA from './PrimaryCTA';
import type { HeroContent, LocaleKey } from './types';

export type HeroSectionProps = {
  content: HeroContent;
  locale: LocaleKey;
  onCtaClick?: () => void;
};

const BenefitList = ({
  content,
  locale,
  listId,
}: {
  content: HeroContent['benefits'];
  locale: LocaleKey;
  listId: string;
}) => {
  const { t, i18n } = useTranslation();

  const benefits = useMemo(
    () =>
      content.map((benefit) => {
        const hasTranslation = i18n.exists(benefit.labelKey, { lng: locale });
        const label = t(benefit.labelKey);
        const metric = benefit.metricKey ? t(benefit.metricKey) : undefined;
        return {
          ...benefit,
          label,
          metric,
          isFallback: !hasTranslation,
        };
      }),
    [content, i18n, locale, t],
  );

  return (
    <ul
      id={listId}
      data-testid="hero-benefits"
      className="space-y-4 4xl:space-y-6"
      aria-label={t('hero_benefits_label', 'Key benefits')}
      aria-live="polite"
    >
      {benefits.map((benefit) => (
        <li
          key={benefit.id}
          className="rounded-3xl border border-white/20 bg-white/10 p-4 shadow-lg shadow-black/20 backdrop-blur-md 3xl:p-5"
        >
          <p
            className={clsx('text-base font-semibold text-white 3xl:text-lg', {
              'italic text-white/80': benefit.isFallback,
            })}
          >
            <span lang={benefit.isFallback ? 'en' : undefined}>{benefit.label}</span>
            {benefit.isFallback ? (
              <span className="sr-only">{t('landing_benefit_fallback_notice')}</span>
            ) : null}
          </p>
          {benefit.metric ? (
            <p className="text-sm font-semibold uppercase tracking-wide text-brand-glow/90 3xl:text-base">
              {benefit.metric}
            </p>
          ) : null}
        </li>
      ))}
    </ul>
  );
};

const HeroSection = ({ content, locale, onCtaClick }: HeroSectionProps) => {
  const { t } = useTranslation();
  const headingId = useId();
  const subtitleId = useId();
  const ctaDescriptionId = useId();
  const benefitListId = useId();

  return (
    <section
      className="grid gap-10 xs:gap-12 md:grid-cols-[minmax(0,1fr)_minmax(240px,320px)]"
      aria-labelledby={headingId}
      aria-describedby={subtitleId}
      data-landing-hero
    >
      <div className="space-y-6">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.25em] text-brand-glow xs:text-xs xs:tracking-[0.4em]">
          {t(content.labelKey)}
        </p>
        <h1
          id={headingId}
          className="text-[clamp(2.25rem,8vw,3rem)] font-semibold leading-tight text-white sm:text-5xl 3xl:text-6xl 4xl:text-7xl"
        >
          {t(content.titleKey)}
        </h1>
        <p id={subtitleId} className="text-base leading-relaxed text-white/85 sm:text-lg 3xl:text-xl">
          {t(content.subtitleKey)}
        </p>
        <div className="flex flex-col gap-3 xs:flex-row xs:items-center">
          <PrimaryCTA
            label={t(content.cta.labelKey)}
            cta={content.cta}
            onClick={onCtaClick}
            ariaDescribedBy={ctaDescriptionId}
            className="shadow-brand-glow/40"
          />
          <p
            id={ctaDescriptionId}
            className="text-xs text-white/70"
            aria-live="polite"
            role="status"
          >
            {t('cta_support_copy', 'Single entry point to /login with full WCAG AA compliance.')}
          </p>
        </div>
      </div>
      <BenefitList content={content.benefits} locale={locale} listId={benefitListId} />
    </section>
  );
};

export default HeroSection;
