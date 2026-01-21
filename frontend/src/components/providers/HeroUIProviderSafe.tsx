import React, { type ReactNode, useEffect, useState } from 'react';
import { useThemePreference } from '../../hooks/useThemePreference';

type HeroUIProviderComponent = React.ComponentType<{
  className?: string;
  children: ReactNode;
}>;

/**
 * Безопасная обёртка для HeroUIProvider.
 * Если загрузка библиотеки падает, приложение продолжит работать без провайдера.
 */
const HeroUIProviderSafe: React.FC<{ children: ReactNode }> = ({ children }) => {
  const { theme } = useThemePreference();
  const [Provider, setProvider] = useState<HeroUIProviderComponent | null>(null);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    let isMounted = true;

    import('@heroui/react')
      .then((module) => {
        if (!isMounted) {
          return;
        }
        setProvider(() => module.HeroUIProvider as HeroUIProviderComponent);
      })
      .catch((error) => {
        console.error('HeroUIProvider failed to load:', error);
        if (isMounted) {
          setHasError(true);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  if (!Provider || hasError) {
    return <>{children}</>;
  }

  return <Provider className={theme}>{children}</Provider>;
};

export default HeroUIProviderSafe;
