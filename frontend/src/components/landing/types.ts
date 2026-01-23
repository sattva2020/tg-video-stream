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

export type HeroContent = {
  labelKey: string;
  titleKey: string;
  subtitleKey: string;
  benefits: BenefitItem[];
  cta: CTAConfig;
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
