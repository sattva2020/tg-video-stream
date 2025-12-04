import { useTranslation } from 'react-i18next';
import { Shield, Sparkles, Timer } from 'lucide-react';
import PrimaryCTA from './PrimaryCTA';
import heroContent from '../../lib/landing/content';

const trustMetrics = [
  { id: 'uptime', valueKey: 'landing_trust_metric_uptime_value', labelKey: 'landing_trust_metric_uptime_label' },
  { id: 'streams', valueKey: 'landing_trust_metric_streams_value', labelKey: 'landing_trust_metric_streams_label' },
  { id: 'sla', valueKey: 'landing_trust_metric_sla_value', labelKey: 'landing_trust_metric_sla_label' },
] as const;

const trustGuarantees = [
  'landing_trust_guarantee_case',
  'landing_trust_guarantee_sla',
  'landing_trust_guarantee_runner',
] as const;

const trustSecurity = [
  'landing_trust_security_mfa',
  'landing_trust_security_audit',
  'landing_trust_security_alerting',
] as const;

const TrustSection = () => {
  const { t } = useTranslation();

  return (
    <section
      className="space-y-6 rounded-4xl border border-white/10 bg-brand-midnight/60 p-6 shadow-2xl shadow-black/30 backdrop-blur-xl xs:p-8"
      aria-labelledby="landing-trust-title"
      data-testid="landing-trust-section"
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-4">
          <p className="text-xs font-semibold uppercase tracking-[0.4em] text-brand-glow/80">
            {t('landing_trust_overline')}
          </p>
          <h2 id="landing-trust-title" className="text-2xl font-semibold sm:text-3xl">
            {t('landing_trust_title')}
          </h2>
          <p className="text-base text-white/85">{t('landing_trust_subtitle')}</p>
          <div className="grid gap-3 sm:grid-cols-3" aria-live="polite">
            {trustMetrics.map((metric) => (
              <div key={metric.id} className="rounded-3xl border border-white/10 bg-white/5 p-3 text-center">
                <p className="text-2xl font-semibold text-white">{t(metric.valueKey)}</p>
                <p className="text-xs uppercase tracking-[0.3em] text-white/60">{t(metric.labelKey)}</p>
              </div>
            ))}
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-3 rounded-3xl border border-white/10 bg-white/5 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.3em] text-white/70">
                <Sparkles className="h-4 w-4 text-brand-glow" aria-hidden />
                <span>{t('landing_trust_guarantee_label')}</span>
              </div>
              <ul className="space-y-2 text-sm text-white/85">
                {trustGuarantees.map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <span className="mt-1 h-1.5 w-1.5 rounded-full bg-brand-glow" aria-hidden />
                    <span>{t(item)}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="space-y-3 rounded-3xl border border-white/10 bg-white/5 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.3em] text-white/70">
                <Shield className="h-4 w-4 text-brand-glow" aria-hidden />
                <span>{t('landing_trust_security_label')}</span>
              </div>
              <ul className="space-y-2 text-sm text-white/85">
                {trustSecurity.map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <span className="mt-1 h-1.5 w-1.5 rounded-full bg-brand-sky" aria-hidden />
                    <span>{t(item)}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <PrimaryCTA
              label={t(heroContent.cta.labelKey)}
              cta={heroContent.cta}
              className="min-w-[200px]"
            />
            <div className="flex items-center gap-2 text-sm text-white/80">
              <Timer className="h-4 w-4 text-brand-glow" aria-hidden />
              <span>{t('landing_trust_callout')}</span>
            </div>
          </div>
        </div>
        <figure className="rounded-4xl border border-white/10 bg-white/5 p-4 shadow-lg shadow-black/20">
          <img
            src="/assets/landing/landing-poster.webp"
            alt={t('landing_trust_poster_alt')}
            className="h-full w-full rounded-2xl object-cover"
            loading="lazy"
          />
          <figcaption className="mt-3 text-sm text-white/70">
            {t('landing_trust_poster_caption')}
          </figcaption>
        </figure>
      </div>
    </section>
  );
};

export default TrustSection;
