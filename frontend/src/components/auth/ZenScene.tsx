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
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (forceStatic) {
      setWebGLReady(false);
      // Показываем fallback сразу с анимацией
      requestAnimationFrame(() => setIsVisible(true));
      return;
    }

    if (typeof window === 'undefined') {
      return;
    }

    // Проверяем WebGL сразу, без задержки
    const hasWebGL = checkWebGLAvailability();
    setWebGLReady(hasWebGL);
    
    // Плавное появление
    requestAnimationFrame(() => {
      requestAnimationFrame(() => setIsVisible(true));
    });
  }, [forceStatic]);

  return (
    <div 
      className={`pointer-events-none absolute inset-0 transition-opacity duration-1000 ${isVisible ? 'opacity-100' : 'opacity-0'}`} 
      aria-hidden="true"
    >
      {webGLReady ? (
        <Suspense fallback={<div className="h-full w-full bg-[#0c0a09]" />}>
          <LazyZenCanvas scrollY={scrollY} />
        </Suspense>
      ) : (
        <div className="h-full w-full bg-[#0c0a09]" />
      )}
    </div>
  );
};

export default AuthZenScene;
