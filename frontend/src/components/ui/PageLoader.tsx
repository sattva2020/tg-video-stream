import React, { useEffect, useState } from 'react';

interface PageLoaderProps {
  /** Минимальное время показа лоадера (мс) для плавного UX */
  minDisplayTime?: number;
  /** Коллбек когда лоадер завершен */
  onComplete?: () => void;
  /** Размер лоадера */
  size?: 'sm' | 'md' | 'lg';
}

/**
 * Красивый круговой лоадер с анимацией заполнения.
 * Показывает прогресс загрузки страницы.
 */
export const PageLoader: React.FC<PageLoaderProps> = ({
  minDisplayTime = 800,
  onComplete,
  size = 'md',
}) => {
  const [progress, setProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  const sizeMap = {
    sm: { container: 'w-12 h-12', stroke: 3, text: 'text-xs' },
    md: { container: 'w-20 h-20', stroke: 4, text: 'text-sm' },
    lg: { container: 'w-28 h-28', stroke: 5, text: 'text-base' },
  };

  const { container, stroke, text } = sizeMap[size];
  const radius = 45;
  const circumference = 2 * Math.PI * radius;

  useEffect(() => {
    const startTime = Date.now();
    let animationFrame: number;

    const animate = () => {
      const elapsed = Date.now() - startTime;
      const targetProgress = Math.min(elapsed / minDisplayTime, 1);
      
      // Easing функция для плавности
      const eased = 1 - Math.pow(1 - targetProgress, 3);
      setProgress(eased * 100);

      if (targetProgress < 1) {
        animationFrame = requestAnimationFrame(animate);
      } else {
        setIsComplete(true);
        onComplete?.();
      }
    };

    animationFrame = requestAnimationFrame(animate);

    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [minDisplayTime, onComplete]);

  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div 
      className={`
        fixed inset-0 z-50 flex flex-col items-center justify-center 
        bg-[#0c0a09] transition-opacity duration-500
        ${isComplete ? 'opacity-0 pointer-events-none' : 'opacity-100'}
      `}
      role="progressbar"
      aria-label={`Loading page ${progress}%`}
    >
      {/* Логотип */}
      <div className="mb-8 text-center">
        <p 
          className="text-xs uppercase tracking-[0.45em] text-[#e5d9c7]/70 animate-pulse"
        >
          Sattva studio
        </p>
      </div>

      {/* Круговой прогресс */}
      <div className={`relative ${container}`}>
        <svg 
          className="transform -rotate-90 w-full h-full"
          viewBox="0 0 100 100"
        >
          {/* Фоновый круг */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="rgba(229, 217, 199, 0.1)"
            strokeWidth={stroke}
          />
          
          {/* Прогресс круг с градиентом */}
          <defs>
            <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#e5d9c7" stopOpacity="0.4" />
              <stop offset="50%" stopColor="#F7E2C6" />
              <stop offset="100%" stopColor="#e5d9c7" stopOpacity="0.8" />
            </linearGradient>
          </defs>
          
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            stroke="url(#progressGradient)"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className="transition-all duration-100 ease-out drop-shadow-[0_0_6px_rgba(247,226,198,0.5)]"
          />
          
          {/* Светящаяся точка на конце */}
          <circle
            cx={50 + radius * Math.cos((progress / 100 * 360 - 90) * Math.PI / 180)}
            cy={50 + radius * Math.sin((progress / 100 * 360 - 90) * Math.PI / 180)}
            r={stroke / 1.5}
            fill="#F7E2C6"
            className={`transition-all duration-100 drop-shadow-[0_0_8px_rgba(247,226,198,0.8)] ${progress > 5 ? 'opacity-100' : 'opacity-0'}`}
          />
        </svg>

        {/* Процент в центре */}
        <div 
          className={`
            absolute inset-0 flex items-center justify-center
            ${text} font-medium text-[#e5d9c7]/80
          `}
        >
          {Math.round(progress)}%
        </div>
      </div>

      {/* Подсказка */}
      <p className="mt-6 text-xs text-[#e5d9c7]/50 animate-pulse">
        Loading...
      </p>
    </div>
  );
};

export default PageLoader;
