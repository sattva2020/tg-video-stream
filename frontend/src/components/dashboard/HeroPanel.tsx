import React from 'react';
import clsx from 'clsx';
import { useThemePreference } from '../../hooks/useThemePreference';

const metricBars = [72, 58, 91, 64];

const HeroPanel: React.FC = () => {
  const { theme } = useThemePreference();

  return (
    <div
      data-testid="dashboard-preview"
      aria-hidden="true"
      className={clsx(
        'rounded-[36px] border px-8 py-7 shadow-[0_25px_120px_rgba(12,10,9,0.25)] transition-colors duration-300',
        'backdrop-blur-2xl ring-1 ring-black/5',
        theme === 'dark'
          ? 'border-white/10 bg-[rgba(12,10,9,0.85)] text-[var(--color-ink-dark)]'
          : 'border-black/5 bg-[rgba(255,255,255,0.72)] text-[var(--color-ink-light)]'
      )}
    >
      <div className="flex items-center justify-between text-xs uppercase tracking-[0.45em] text-[color:var(--color-text-muted)]">
        <span>Zen dashboard</span>
        <span className="rounded-full border border-current px-3 py-1 text-[10px] font-semibold tracking-[0.5em]">
          Live
        </span>
      </div>

      <h3 className="mt-6 font-landing-serif text-4xl leading-tight" data-testid="dashboard-headline">
        Calm Broadcast
      </h3>
      <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
        45 820 зрителей сейчас · +12% удержание
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <div className="rounded-3xl border border-white/10 bg-white/5 p-4 text-sm text-[color:var(--color-text)]">
          <p className="uppercase text-[11px] tracking-[0.4em] text-[color:var(--color-text-muted)]">Следующий гость</p>
          <p className="mt-2 font-landing-serif text-2xl">Кира Мишина</p>
          <p className="text-xs text-[color:var(--color-text-muted)]">00:42 до выхода</p>
        </div>
        <div className="rounded-3xl border border-white/10 bg-white/5 p-4 text-sm text-[color:var(--color-text)]">
          <p className="uppercase text-[11px] tracking-[0.4em] text-[color:var(--color-text-muted)]">Нагруженность</p>
          <p className="mt-2 font-landing-serif text-2xl">92%</p>
          <p className="text-xs text-[color:var(--color-text-muted)]">Цели недели выполнены</p>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        {metricBars.map((value, index) => (
          <div key={index} className="space-y-2">
            <div className="flex items-center justify-between text-xs uppercase tracking-[0.35em] text-[color:var(--color-text-muted)]">
              <span>{index === 0 ? 'engagement' : index === 1 ? 'retention' : index === 2 ? 'zen score' : 'watch time'}</span>
              <span>{value}%</span>
            </div>
            <div className={clsx('h-2 rounded-full', theme === 'dark' ? 'bg-white/15' : 'bg-black/10')}>
              <div
                className="h-full rounded-full bg-gradient-to-r from-[#b8845f] via-[#d9a065] to-[#f7e2c6]"
                style={{ width: `${value}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default HeroPanel;
