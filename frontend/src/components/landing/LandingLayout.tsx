import type { FC, ReactNode } from 'react';
import clsx from 'clsx';
import type { LandingSectionProps } from './types';

const SectionShell: FC<{ children: ReactNode; className?: string }> = ({ children, className }) => (
  <section
    data-landing-shell
    className={clsx(
      'mx-auto w-full max-w-landing px-4 xs:px-5 sm:px-8 3xl:max-w-landing-wide 4xl:max-w-landing-ultra',
      className,
    )}
  >
    {children}
  </section>
);

const LandingLayout: FC<LandingSectionProps> = ({ hero, nav, footer, background, className }) => {
  return (
    <div
      className={clsx('relative min-h-dvh overflow-hidden bg-brand-midnight text-white', className)}
      data-landing-surface="hero"
    >
      {background ? (
        <div className="pointer-events-none absolute inset-0" aria-hidden>
          {background}
        </div>
      ) : null}
      <div className="relative z-10 flex min-h-dvh flex-col">
        {nav ? (
          <header className="px-4 py-4 sm:px-8 sm:py-6" data-testid="landing-nav">
            <SectionShell className="px-0">{nav}</SectionShell>
          </header>
        ) : null}
        <main className="flex flex-1 flex-col justify-center pb-10 pt-4 xs:pb-12 xs:pt-6" role="main">
          <SectionShell>{hero}</SectionShell>
        </main>
        {footer ? (
          <footer className="px-4 pb-6 sm:px-8" data-testid="landing-footer">
            <SectionShell className="px-0 text-sm text-white/70">{footer}</SectionShell>
          </footer>
        ) : null}
      </div>
    </div>
  );
};

export default LandingLayout;
