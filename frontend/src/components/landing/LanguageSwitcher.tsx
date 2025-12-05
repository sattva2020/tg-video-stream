import { useId, useMemo } from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { ChevronDown, Check } from 'lucide-react';
import clsx from 'clsx';
import { useTranslation } from 'react-i18next';
import type { LocaleKey } from './types';

export type LanguageSwitcherProps = {
  value: LocaleKey;
  options: LocaleKey[];
  onChange: (locale: LocaleKey) => void;
  autoDetectedLocale?: LocaleKey;
  needsFallbackHint?: boolean;
  className?: string;
};

const LanguageSwitcher = ({
  value,
  options,
  onChange,
  autoDetectedLocale,
  needsFallbackHint,
  className,
}: LanguageSwitcherProps) => {
  const { t } = useTranslation();
  const fallbackHintId = useId();

  const mappedOptions = useMemo(
    () =>
      options.map((code) => ({
        code,
        label: t(`language_name_${code}` as const, code.toUpperCase()),
        isAutoDetected: code === autoDetectedLocale,
      })),
    [options, autoDetectedLocale, t],
  );

  const current = mappedOptions.find((option) => option.code === value) ?? mappedOptions[0];
  const availableList = mappedOptions.map((option) => option.label).join(', ');

  const describedBy = needsFallbackHint ? fallbackHintId : undefined;

  return (
    <div
      className={clsx('flex w-full flex-col items-stretch gap-2 text-sm xs:w-auto xs:items-end', className)}
      data-testid="language-switcher"
    >
      <DropdownMenu.Root modal={false}>
        <DropdownMenu.Trigger
          className="inline-flex w-full items-center justify-between gap-2 rounded-full border px-4 py-2 text-sm font-semibold uppercase tracking-wide backdrop-blur transition hover:bg-[color:var(--landing-pill-bg)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[var(--landing-accent-glow)] xs:w-auto xs:justify-start"
          aria-label={t('language_switcher_label', 'Change landing language')}
          data-testid="language-switcher-trigger"
          aria-describedby={describedBy}
          style={{
            backgroundColor: 'var(--landing-secondary-cta-bg)',
            borderColor: 'var(--landing-secondary-cta-border)',
            color: 'var(--landing-secondary-cta-text)',
          }}
        >
          <span>{current?.label ?? value.toUpperCase()}</span>
          {value === autoDetectedLocale ? (
            <span
              className="text-xs font-medium uppercase"
              aria-label={t('language_switcher_auto_badge', 'Auto')}
              style={{ color: 'var(--landing-accent-glow)' }}
            >
              {t('language_switcher_auto_badge', 'Auto')}
            </span>
          ) : null}
          <ChevronDown className="h-4 w-4" aria-hidden style={{ color: 'var(--landing-secondary-cta-text)' }} />
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content
            sideOffset={8}
            align="end"
            className="z-50 w-[min(90vw,280px)] max-w-sm rounded-2xl border p-2 text-sm shadow-2xl backdrop-blur"
            style={{
              background: 'var(--landing-card-strong-bg)',
              borderColor: 'var(--landing-card-border-strong)',
              color: 'var(--landing-text)',
              boxShadow: 'var(--landing-card-shadow-strong)',
            }}
          >
            <DropdownMenu.RadioGroup value={value} onValueChange={(next) => onChange(next as LocaleKey)}>
              {mappedOptions.map((option) => (
                <DropdownMenu.RadioItem
                  key={option.code}
                  value={option.code}
                  data-testid={`language-option-${option.code}`}
                  data-locale={option.code}
                  className="group flex cursor-pointer items-center justify-between rounded-xl px-3 py-2 outline-none transition hover:bg-[color:var(--landing-pill-bg)] focus:bg-[color:var(--landing-pill-bg)]"
                >
                  <span className="flex flex-col">
                    <span className="font-semibold" style={{ color: 'var(--landing-text)' }}>
                      {option.label}
                    </span>
                    {option.isAutoDetected ? (
                      <span
                        className="text-xs uppercase"
                        style={{ color: 'var(--landing-accent-glow)' }}
                      >
                        {t('language_switcher_auto_badge', 'Auto')}
                      </span>
                    ) : null}
                  </span>
                  <DropdownMenu.ItemIndicator>
                    <Check className="h-4 w-4" style={{ color: 'var(--landing-accent-glow)' }} />
                  </DropdownMenu.ItemIndicator>
                </DropdownMenu.RadioItem>
              ))}
            </DropdownMenu.RadioGroup>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
      {needsFallbackHint ? (
        <p
          id={fallbackHintId}
          className="text-left text-xs xs:max-w-xs xs:text-right"
          style={{ color: 'var(--landing-amber)' }}
          data-testid="language-fallback-hint"
          aria-live="polite"
        >
          {t('language_switcher_fallback_hint', {
            fallback: current?.label ?? t('language_name_en', 'English'),
            available: availableList,
          })}
        </p>
      ) : null}
    </div>
  );
};

export default LanguageSwitcher;
