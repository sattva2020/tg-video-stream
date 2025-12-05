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
      className={clsx('relative min-h-dvh text-[color:var(--landing-text)]', className)}
      data-landing-surface="hero"
    >
      {background ? (
        <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
          {background}
        </div>
      ) : null}
      {/* Sticky header вынесен на уровень выше, чтобы работал корректно */}
      {nav ? (
        <header
          className="sticky top-0 z-50 px-4 py-4 backdrop-blur sm:px-8 sm:py-6"
          data-testid="landing-nav"
          style={{
            backgroundColor: 'var(--landing-nav-bg)',
            borderBottom: '1px solid var(--landing-nav-border)',
            boxShadow: 'var(--landing-nav-shadow)',
          }}
        >
          <SectionShell className="px-0">{nav}</SectionShell>
        </header>
      ) : null}
      <div className="relative z-10 flex min-h-[calc(100dvh-80px)] flex-col">
        <main className="flex flex-1 flex-col justify-start pb-10 pt-4 xs:pb-12 xs:pt-6" role="main">
          <SectionShell>{hero}</SectionShell>
        </main>
        {footer ? (
          <footer className="px-4 pb-6 sm:px-8" data-testid="landing-footer">
            <SectionShell className="px-0 text-sm text-[color:var(--landing-text-muted)]">{footer}</SectionShell>
          </footer>
        ) : null}
      </div>
    </div>
  );
};

export default LandingLayout;
