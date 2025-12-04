/**
 * LanguageSwitcher Component
 * Переключатель языков интерфейса
 * 
 * Features:
 * - Support for 4 languages: Russian, English, Ukrainian, Spanish
 * - Persists selection in localStorage
 * - Auto-detect browser language
 * - Dropdown or inline button options
 * - Flag icons for visual identification
 * - Accessibility support (ARIA labels)
 * 
 * User Story: US10 - Interface Localization
 * Related Tasks: T068-T073
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe, ChevronDown, Check } from 'lucide-react';
import axios from 'axios';

interface LanguageSwitcherProps {
  /** Style variant: dropdown, inline, or compact */
  variant?: 'dropdown' | 'inline' | 'compact';
  /** Callback when language changes */
  onLanguageChange?: (lang: string) => void;
  /** API base URL */
  apiBaseUrl?: string;
  /** Whether component is disabled */
  disabled?: boolean;
  /** Show flag emoji */
  showFlags?: boolean;
  /** Storage key for persistence */
  storageKey?: string;
}

interface Language {
  code: string;
  name: string;
  nativeName: string;
  flag?: string;
}

const SUPPORTED_LANGUAGES: Language[] = [
  { code: 'ru', name: 'Russian', nativeName: 'Русский', flag: '🇷🇺' },
  { code: 'en', name: 'English', nativeName: 'English', flag: '🇬🇧' },
  { code: 'uk', name: 'Ukrainian', nativeName: 'Українська', flag: '🇺🇦' },
  { code: 'es', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸' },
];

const STORAGE_KEY = 'i18n_language';
const DEFAULT_LANGUAGE = 'ru';

/**
 * Detect browser language
 */
const detectBrowserLanguage = (): string => {
  const browserLang = navigator.language.split('-')[0];
  const supported = SUPPORTED_LANGUAGES.find((lang) => lang.code === browserLang);
  return supported ? supported.code : DEFAULT_LANGUAGE;
};

/**
 * Dropdown variant
 */
const DropdownVariant: React.FC<{
  currentLang: string;
  onSelect: (lang: string) => void;
  disabled: boolean;
  showFlags: boolean;
}> = ({ currentLang, onSelect, disabled, showFlags }) => {
  const [isOpen, setIsOpen] = useState(false);
  const currentLanguage = SUPPORTED_LANGUAGES.find((l) => l.code === currentLang);

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        className="flex items-center gap-2 rounded-lg bg-gray-700 px-3 py-2 text-sm text-gray-200 transition-all hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
        aria-label="Language selector"
        aria-expanded={isOpen}
      >
        <Globe className="h-4 w-4" />
        {showFlags && currentLanguage?.flag && (
          <span className="text-lg">{currentLanguage.flag}</span>
        )}
        <span className="hidden sm:inline">{currentLanguage?.nativeName}</span>
        <ChevronDown className="h-4 w-4" />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 rounded-lg bg-gray-800 py-1 shadow-lg z-50">
          {SUPPORTED_LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => {
                onSelect(lang.code);
                setIsOpen(false);
              }}
              className={`w-full px-4 py-2 text-left text-sm transition-all ${
                currentLang === lang.code
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-200 hover:bg-gray-700'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {showFlags && lang.flag && (
                    <span className="text-lg">{lang.flag}</span>
                  )}
                  <div>
                    <div className="font-medium">{lang.nativeName}</div>
                    <div className="text-xs text-gray-400">{lang.name}</div>
                  </div>
                </div>
                {currentLang === lang.code && (
                  <Check className="h-4 w-4" />
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * Inline variant (buttons in a row)
 */
const InlineVariant: React.FC<{
  currentLang: string;
  onSelect: (lang: string) => void;
  disabled: boolean;
  showFlags: boolean;
}> = ({ currentLang, onSelect, disabled, showFlags }) => {
  return (
    <div className="flex gap-1 rounded-lg bg-gray-800 p-1">
      {SUPPORTED_LANGUAGES.map((lang) => (
        <button
          key={lang.code}
          onClick={() => onSelect(lang.code)}
          disabled={disabled}
          className={`px-3 py-1 text-sm font-medium rounded transition-all ${
            currentLang === lang.code
              ? 'bg-blue-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          } disabled:cursor-not-allowed disabled:opacity-50`}
          title={lang.nativeName}
          aria-label={`Select ${lang.nativeName}`}
          aria-pressed={currentLang === lang.code}
        >
          {showFlags && lang.flag && <span>{lang.flag}</span>}
          <span className="hidden sm:inline">{lang.code.toUpperCase()}</span>
        </button>
      ))}
    </div>
  );
};

/**
 * Compact variant (just flags/codes)
 */
const CompactVariant: React.FC<{
  currentLang: string;
  onSelect: (lang: string) => void;
  disabled: boolean;
  showFlags: boolean;
}> = ({ currentLang, onSelect, disabled, showFlags }) => {
  return (
    <div className="flex gap-2">
      {SUPPORTED_LANGUAGES.map((lang) => (
        <button
          key={lang.code}
          onClick={() => onSelect(lang.code)}
          disabled={disabled}
          className={`p-1.5 rounded transition-all ${
            currentLang === lang.code
              ? 'bg-blue-600 text-white'
              : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          } disabled:cursor-not-allowed disabled:opacity-50`}
          title={lang.nativeName}
          aria-label={`Select ${lang.nativeName}`}
          aria-pressed={currentLang === lang.code}
        >
          {showFlags ? (
            lang.flag && <span className="text-lg">{lang.flag}</span>
          ) : (
            <span className="text-xs font-bold">{lang.code.toUpperCase()}</span>
          )}
        </button>
      ))}
    </div>
  );
};

/**
 * LanguageSwitcher Component
 * 
 * Allows users to select between supported languages with local persistence
 * and automatic detection.
 */
export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  variant = 'dropdown',
  onLanguageChange,
  apiBaseUrl = '/api',
  disabled = false,
  showFlags = true,
  storageKey = STORAGE_KEY,
}) => {
  const { i18n } = useTranslation();
  const [currentLang, setCurrentLang] = useState<string>(DEFAULT_LANGUAGE);
  const [isInitialized, setIsInitialized] = useState(false);

  /**
   * Initialize language on mount
   */
  useEffect(() => {
    const initializeLanguage = async () => {
      // Check localStorage first
      const stored = localStorage.getItem(storageKey);
      if (stored && SUPPORTED_LANGUAGES.some((l) => l.code === stored)) {
        setCurrentLang(stored);
        await i18n.changeLanguage(stored);
        setIsInitialized(true);
        return;
      }

      // Try to detect browser language
      const detected = detectBrowserLanguage();
      setCurrentLang(detected);
      await i18n.changeLanguage(detected);
      localStorage.setItem(storageKey, detected);
      setIsInitialized(true);
    };

    initializeLanguage();
  }, [i18n, storageKey]);

  /**
   * Handle language selection
   */
  const handleLanguageChange = useCallback(
    async (newLang: string) => {
      try {
        // Update i18next
        await i18n.changeLanguage(newLang);

        // Persist to localStorage
        localStorage.setItem(storageKey, newLang);

        // Update state
        setCurrentLang(newLang);

        // Notify backend (if API available)
        try {
          await axios.post(`${apiBaseUrl}/i18n/language`, {
            language: newLang,
          });
        } catch (err) {
          console.warn('Failed to update language on backend:', err);
        }

        // Call callback
        onLanguageChange?.(newLang);
      } catch (err) {
        console.error('Failed to change language:', err);
      }
    },
    [i18n, apiBaseUrl, storageKey, onLanguageChange]
  );

  // Don't render until initialized to prevent hydration mismatch
  if (!isInitialized) {
    return null;
  }

  // Render based on variant
  switch (variant) {
    case 'inline':
      return (
        <InlineVariant
          currentLang={currentLang}
          onSelect={handleLanguageChange}
          disabled={disabled}
          showFlags={showFlags}
        />
      );
    case 'compact':
      return (
        <CompactVariant
          currentLang={currentLang}
          onSelect={handleLanguageChange}
          disabled={disabled}
          showFlags={showFlags}
        />
      );
    case 'dropdown':
    default:
      return (
        <DropdownVariant
          currentLang={currentLang}
          onSelect={handleLanguageChange}
          disabled={disabled}
          showFlags={showFlags}
        />
      );
  }
};

export default LanguageSwitcher;
