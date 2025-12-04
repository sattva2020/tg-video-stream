import { forwardRef } from 'react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import type { CTAConfig, CTAStyleVariant } from './types';

export type PrimaryCTAProps = {
  label: string;
  cta: CTAConfig;
  className?: string;
  onClick?: () => void;
  ariaDescribedBy?: string;
};

const variantClasses: Record<CTAStyleVariant, string> = {
  glass: 'backdrop-blur-md bg-white/10 hover:bg-white/20 text-white shadow-[0_0_40px_rgba(14,165,233,0.45)]',
  solid:
    'bg-gradient-to-r from-sky-300 via-sky-400 to-cyan-400 text-brand-midnight hover:from-sky-200 hover:via-sky-300 hover:to-cyan-300 focus-visible:from-sky-200 focus-visible:via-sky-300 focus-visible:to-cyan-300 shadow-[0_20px_60px_rgba(14,165,233,0.45)]',
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
        'inline-flex min-h-[44px] w-full min-w-[160px] items-center justify-center rounded-full px-6 py-3 text-sm font-semibold uppercase tracking-wide transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand-glow xs:w-auto xs:min-w-[190px] xs:px-8 xs:py-4 xs:text-base',
        variantClasses[variant],
        className,
      )}
      aria-label={label}
        aria-describedby={ariaDescribedBy}
    >
      {label}
    </Link>
  );
  },
);

PrimaryCTA.displayName = 'PrimaryCTA';

export default PrimaryCTA;
