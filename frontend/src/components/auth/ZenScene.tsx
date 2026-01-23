import React, { lazy, Suspense, useEffect, useState } from 'react';

const LazyZenCanvas = lazy(() => import('./ZenCanvas'));

interface AuthZenSceneProps {
  scrollY: number;
  forceStatic?: boolean;
}

const checkWebGLAvailability = () => {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
  } catch {
    return false;
  }
};

const AuthZenScene: React.FC<AuthZenSceneProps> = ({ scrollY, forceStatic = false }) => {
  const [webGLReady, setWebGLReady] = useState(false);
  const [shouldLoad, setShouldLoad] = useState(false);

  useEffect(() => {
    if (forceStatic) {
      setWebGLReady(false);
      return;
    }

    if (typeof window === 'undefined') {
      return;
    }

    // Defer loading to prioritize LCP and TBT
    const timer = setTimeout(() => {
      setShouldLoad(true);
    }, 2500);

    return () => clearTimeout(timer);
  }, [forceStatic]);

  useEffect(() => {
    if (shouldLoad && !forceStatic) {
      setWebGLReady(checkWebGLAvailability());
    }
  }, [shouldLoad, forceStatic]);

  return (
    <div className="pointer-events-none absolute inset-0" aria-hidden="true">
      {webGLReady ? (
        <Suspense fallback={null}>
          <LazyZenCanvas scrollY={scrollY} />
        </Suspense>
      ) : (
        <picture data-testid="auth-zen-fallback" className="block h-full w-full">
          <source srcSet="/fallback/zen-scene.svg" type="image/svg+xml" />
          <img src="/fallback/zen-scene.svg" alt="ZenScene static background" className="h-full w-full object-cover" loading="lazy" />
        </picture>
      )}
    </div>
  );
};

export default AuthZenScene;
