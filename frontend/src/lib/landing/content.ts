import type { HeroContent } from '../../components/landing';

const heroContent: HeroContent = {
  labelKey: 'hero_label',
  titleKey: 'hero_title',
  subtitleKey: 'hero_subtitle',
  benefits: [
    { id: 'no-lag', labelKey: 'hero_benefit_no_lag', metricKey: 'hero_metric_no_lag' },
    { id: '24-7', labelKey: 'hero_benefit_247', metricKey: 'hero_metric_streams' },
    { id: 'youtube-playlists', labelKey: 'hero_benefit_playlist', metricKey: 'hero_metric_playlist' },
  ],
  cta: {
    labelKey: 'cta_enter',
    href: '/login',
    trackingId: 'landing_enter_click',
    styleVariant: 'glass',
  },
};

export const validateHeroContent = (content: HeroContent): HeroContent => {
  if (content.cta.href !== '/login') {
    throw new Error('HeroContent.cta.href обязан указывать на /login согласно спецификации');
  }

  const benefitCount = content.benefits.length;
  if (benefitCount < 3 || benefitCount > 4) {
    throw new Error('HeroContent.benefits должен содержать от 3 до 4 записей.');
  }

  return content;
};

export default validateHeroContent(heroContent);
