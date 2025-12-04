import type { HeroContent } from '../../components/landing';

const heroContent: HeroContent = {
  labelKey: 'hero_label',
  titleKey: 'hero_title',
  subtitleKey: 'hero_subtitle',
  benefits: [
    { id: '24-7', labelKey: 'hero_benefit_247', metricKey: 'hero_metric_streams' },
    { id: 'youtube-playlists', labelKey: 'hero_benefit_playlist', metricKey: 'hero_metric_playlist' },
    { id: 'no-lag', labelKey: 'hero_benefit_no_lag', metricKey: 'hero_metric_no_lag' },
    { id: 'failover', labelKey: 'hero_benefit_failover', metricKey: 'hero_metric_failover' },
  ],
  audienceTags: [
    { id: 'owners', labelKey: 'hero_audience_channel_owners' },
    { id: 'streamers', labelKey: 'hero_audience_streamers' },
    { id: 'admins', labelKey: 'hero_audience_admins' },
    { id: 'newsrooms', labelKey: 'hero_audience_newsrooms' },
  ],
  valueProps: [
    { id: 'always-on', labelKey: 'hero_value_always_on' },
    { id: 'rotation', labelKey: 'hero_value_rotation' },
    { id: 'failsafe', labelKey: 'hero_value_failsafe' },
    { id: 'speed', labelKey: 'hero_value_speed' },
  ],
  clarityList: [
    { id: 'clarity-obs', labelKey: 'hero_clarity_obs_free' },
    { id: 'clarity-switch', labelKey: 'hero_clarity_switching' },
    { id: 'clarity-mix', labelKey: 'hero_clarity_mix' },
    { id: 'clarity-recover', labelKey: 'hero_clarity_recover' },
    { id: 'clarity-schedule', labelKey: 'hero_clarity_schedule' },
  ],
  cta: {
    labelKey: 'cta_enter',
    href: '/login',
    trackingId: 'landing_enter_click',
    styleVariant: 'solid',
  },
  secondaryCta: {
    labelKey: 'hero_secondary_cta',
    href: '#landing-workflow',
    trackingId: 'landing_secondary_cta',
  },
  checklist: [
    { id: 'signal', labelKey: 'hero_checklist_signal' },
    { id: 'failover', labelKey: 'hero_checklist_failover' },
    { id: 'security', labelKey: 'hero_checklist_security' },
  ],
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
