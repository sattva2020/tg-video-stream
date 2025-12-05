import { forwardRef } from 'react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import type { CTAConfig, CTAStyleVariant } from './types';
import type { CSSProperties } from 'react';

export type PrimaryCTAProps = {
  label: string;
  cta: CTAConfig;
  className?: string;
  onClick?: () => void;
  ariaDescribedBy?: string;
};

const variantClasses: Record<CTAStyleVariant, string> = {
  glass: 'backdrop-blur-md border transition-colors duration-300 hover:opacity-90',
  solid: 'transition hover:brightness-110 focus-visible:brightness-110',
};

const variantStyles: Record<CTAStyleVariant, CSSProperties> = {
  glass: {
    backgroundColor: 'var(--landing-cta-glass-bg)',
    color: 'var(--landing-cta-glass-text)',
    boxShadow: 'var(--landing-secondary-cta-shadow)',
    borderColor: 'var(--landing-cta-glass-border)',
  },
  solid: {
    backgroundImage: 'var(--landing-cta-gradient)',
    color: 'var(--landing-cta-text)',
    boxShadow: 'var(--landing-cta-shadow)',
  },
};

const PrimaryCTA = forwardRef<HTMLAnchorElement, PrimaryCTAProps>(
  ({ label, cta, className, onClick, ariaDescribedBy }, ref) => {
    const variant = cta.styleVariant ?? 'glass';
    return (
      <Link
        ref={ref}
        to={cta.href}
        onClick={onClick}
        data-tracking-id={cta.trackingId}
        className={clsx(
          'inline-flex min-h-[44px] w-full min-w-[160px] items-center justify-center rounded-full px-6 py-3 text-sm font-semibold uppercase tracking-wide transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--landing-accent-glow)] xs:w-auto xs:min-w-[190px] xs:px-8 xs:py-4 xs:text-base',
          variantClasses[variant],
          className,
        )}
        aria-label={label}
        aria-describedby={ariaDescribedBy}
        style={variantStyles[variant]}
      >
        {label}
      </Link>
    );
  },
);

PrimaryCTA.displayName = 'PrimaryCTA';

export default PrimaryCTA;
