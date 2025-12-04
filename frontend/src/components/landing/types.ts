import type { ReactNode } from 'react';

export type LocaleKey = 'en' | 'ru' | 'uk' | 'de';

export type BenefitItem = {
  id: string;
  labelKey: string;
  metricKey?: string;
  icon?: ReactNode | string;
};

export type CTAStyleVariant = 'glass' | 'solid';

export type CTAConfig = {
  labelKey: string;
  href: '/login' | '/register';
  trackingId: string;
  styleVariant?: CTAStyleVariant;
};

export type SecondaryCTAConfig = {
  labelKey: string;
  href: string;
  trackingId?: string;
};

export type HeroChecklistItem = {
  id: string;
  labelKey: string;
};

export type HeroAudienceTag = {
  id: string;
  labelKey: string;
};

export type HeroValuePoint = {
  id: string;
  labelKey: string;
};

export type HeroClarityPoint = {
  id: string;
  labelKey: string;
};

export type HeroContent = {
  labelKey: string;
  titleKey: string;
  subtitleKey: string;
  benefits: BenefitItem[];
  cta: CTAConfig;
  secondaryCta?: SecondaryCTAConfig;
  checklist?: HeroChecklistItem[];
  audienceTags?: HeroAudienceTag[];
  valueProps?: HeroValuePoint[];
  clarityList?: HeroClarityPoint[];
};

export type LanguageOption = {
  code: LocaleKey;
  labelKey: string;
  isDefault?: boolean;
};

export type LandingSectionProps = {
  hero: ReactNode;
  nav?: ReactNode;
  footer?: ReactNode;
  background?: ReactNode;
  className?: string;
};
