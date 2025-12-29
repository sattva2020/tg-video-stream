import React, { useMemo } from 'react';

/**
 * StaticZenFallback - звёздное небо как CSS fallback для 3D сцены
 * 
 * Имитирует @react-three/drei Stars компонент чистым CSS
 * для устройств без WebGL
 */

interface StaticZenFallbackProps {
  animate?: boolean;
  className?: string;
}

// Генератор звёзд с фиксированным seed для консистентности
const generateStars = (count: number, seed: number = 42) => {
  const stars = [];
  let random = seed;
  
  // Simple seeded random
  const nextRandom = () => {
    random = (random * 16807) % 2147483647;
    return (random - 1) / 2147483646;
  };
  
  for (let i = 0; i < count; i++) {
    stars.push({
      x: nextRandom() * 100,
      y: nextRandom() * 100,
      size: nextRandom() * 2 + 0.5,
      opacity: nextRandom() * 0.7 + 0.3,
      delay: nextRandom() * 8,
      duration: nextRandom() * 4 + 2,
      // Некоторые звёзды ярче
      bright: nextRandom() > 0.92,
    });
  }
  return stars;
};

const StaticZenFallback: React.FC<StaticZenFallbackProps> = ({ 
  animate = true,
  className = '' 
}) => {
  // Мемоизируем звёзды чтобы не пересоздавать при ререндере
  const stars = useMemo(() => generateStars(200), []);
  const farStars = useMemo(() => generateStars(100, 123), []);

  return (
    <div 
      className={`absolute inset-0 overflow-hidden ${className}`}
      aria-hidden="true"
      data-testid="static-zen-fallback"
    >
      {/* Deep space background - как в 3D сцене #000008 */}
      <div 
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse at 50% 50%, #0a0a15 0%, #000008 50%, #000005 100%)',
        }}
      />
      
      {/* Дальний слой звёзд (мелкие, тусклые) */}
      <div className="absolute inset-0">
        {farStars.map((star, i) => (
          <div
            key={`far-${i}`}
            className="absolute rounded-full"
            style={{
              width: star.size * 0.6 + 'px',
              height: star.size * 0.6 + 'px',
              left: star.x + '%',
              top: star.y + '%',
              backgroundColor: 'rgba(180, 190, 220, ' + star.opacity * 0.5 + ')',
            }}
          />
        ))}
      </div>

      {/* Основной слой звёзд */}
      <div className="absolute inset-0">
        {stars.map((star, i) => (
          <div
            key={`star-${i}`}
            className={`absolute rounded-full ${animate && star.bright ? 'animate-twinkle' : ''}`}
            style={{
              width: star.size + 'px',
              height: star.size + 'px',
              left: star.x + '%',
              top: star.y + '%',
              backgroundColor: star.bright 
                ? 'rgba(255, 255, 255, ' + (star.opacity + 0.2) + ')'
                : 'rgba(200, 210, 255, ' + star.opacity + ')',
              boxShadow: star.bright 
                ? '0 0 ' + (star.size * 2) + 'px rgba(255, 255, 255, 0.5)' 
                : 'none',
              animationDelay: star.delay + 's',
              animationDuration: star.duration + 's',
            }}
          />
        ))}
      </div>

      {/* Несколько крупных ярких звёзд с лучами */}
      <div className="absolute inset-0 pointer-events-none">
        {[
          { x: 15, y: 20, size: 3 },
          { x: 85, y: 15, size: 2.5 },
          { x: 75, y: 70, size: 2 },
          { x: 10, y: 80, size: 2.5 },
          { x: 50, y: 8, size: 2 },
        ].map((star, i) => (
          <div
            key={`bright-${i}`}
            className={`absolute ${animate ? 'animate-glow' : ''}`}
            style={{
              left: star.x + '%',
              top: star.y + '%',
              width: star.size + 'px',
              height: star.size + 'px',
              backgroundColor: '#fff',
              borderRadius: '50%',
              boxShadow: `
                0 0 ${star.size * 4}px rgba(255, 255, 255, 0.8),
                0 0 ${star.size * 8}px rgba(200, 220, 255, 0.5),
                0 0 ${star.size * 15}px rgba(150, 180, 255, 0.3)
              `,
              animationDelay: i * 1.5 + 's',
            }}
          />
        ))}
      </div>

      {/* Тонкая туманность/Млечный путь */}
      <div 
        className="absolute inset-0 pointer-events-none opacity-30"
        style={{
          background: `
            linear-gradient(135deg, 
              transparent 0%, 
              rgba(100, 120, 180, 0.03) 30%, 
              rgba(80, 100, 150, 0.05) 50%, 
              rgba(100, 120, 180, 0.03) 70%, 
              transparent 100%
            )
          `,
        }}
      />

      {/* Мягкое виньетирование */}
      <div 
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at center, transparent 40%, rgba(0, 0, 8, 0.4) 80%, rgba(0, 0, 5, 0.7) 100%)',
        }}
      />
    </div>
  );
};

export default StaticZenFallback;
