import React, { lazy, Suspense, useEffect, useState } from 'react';
import StaticZenFallback from './StaticZenFallback';

const LazyZenCanvas = lazy(() => import('./ZenCanvas'));

interface AuthZenSceneProps {
  scrollY: number;
  forceStatic?: boolean;
}

/**
 * Проверка доступности WebGL
 */
const checkWebGLAvailability = () => {
  try {
    const canvas = document.createElement('canvas');
    return Boolean(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
  } catch {
    return false;
  }
};

/**
 * Определение слабого устройства:
 * - Мобильные устройства с малым количеством ядер
 * - Устройства с предпочтением reduced motion
 * - Устройства с режимом экономии данных
 */
const isLowEndDevice = (): boolean => {
  if (typeof window === 'undefined') return true;
  
  // Проверяем prefers-reduced-motion
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReducedMotion) return true;
  
  // Проверяем режим экономии данных
  const saveData = (navigator as any).connection?.saveData;
  if (saveData) return true;
  
  // Проверяем количество логических ядер (менее 4 = слабое устройство)
  const cores = navigator.hardwareConcurrency || 1;
  if (cores < 4) return true;
  
  // Проверяем размер устройства (мобильные < 768px могут быть слабыми)
  const isMobile = window.matchMedia('(max-width: 768px)').matches;
  const isTouch = 'ontouchstart' in window;
  
  // Мобильные с touch - скорее всего слабые
  if (isMobile && isTouch && cores < 6) return true;
  
  return false;
};

const AuthZenScene: React.FC<AuthZenSceneProps> = ({ scrollY, forceStatic = false }) => {
  const [webGLReady, setWebGLReady] = useState(false);
  const [isLowEnd, setIsLowEnd] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (forceStatic) {
      setWebGLReady(false);
      setIsLowEnd(true);
      // Показываем fallback сразу с анимацией
      requestAnimationFrame(() => setIsVisible(true));
      return;
    }

    if (typeof window === 'undefined') {
      return;
    }

    // Проверяем WebGL и производительность устройства
    const hasWebGL = checkWebGLAvailability();
    const lowEnd = isLowEndDevice();
    
    setWebGLReady(hasWebGL && !lowEnd);
    setIsLowEnd(lowEnd);
    
    // Плавное появление
    requestAnimationFrame(() => {
      requestAnimationFrame(() => setIsVisible(true));
    });
  }, [forceStatic]);

  // Логируем для отладки в dev режиме
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('[ZenScene] WebGL ready:', webGLReady, '| Low-end device:', isLowEnd);
    }
  }, [webGLReady, isLowEnd]);

  return (
    <div 
      className={`pointer-events-none absolute inset-0 transition-opacity duration-1000 ${isVisible ? 'opacity-100' : 'opacity-0'}`} 
      aria-hidden="true"
    >
      {webGLReady && !isLowEnd ? (
        <Suspense fallback={<StaticZenFallback animate={false} />}>
          <LazyZenCanvas scrollY={scrollY} />
        </Suspense>
      ) : (
        <StaticZenFallback animate={!isLowEnd} />
      )}
    </div>
  );
};

export default AuthZenScene;
