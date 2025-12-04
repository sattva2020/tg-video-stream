import { useEffect, useState } from 'react';
import clsx from 'clsx';
import styles from './visual-background.module.css';

export type VisualBackgroundProps = {
  className?: string;
};

// Статический массив частиц
const PARTICLES = Array.from({ length: 30 }, (_, i) => ({
  id: i,
  left: (i * 37 + 13) % 100,
  top: (i * 23 + 7) % 100,
  delay: (i * 0.17) % 5,
  duration: 3 + (i % 4),
}));

/**
 * VisualBackground — визуальный фон для лендинга
 * Космический стиль с Telegram стилистикой
 */
type VisualMode = 'particles' | 'minimal';

type VisualWindow = Window & {
  __VISUAL_BACKGROUND_MODE__?: VisualMode;
};

const usePrefersReducedMotion = () => {
  const [prefers, setPrefers] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return undefined;
    }
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const handleChange = (event: MediaQueryListEvent) => setPrefers(event.matches);
    setPrefers(media.matches);
    media.addEventListener('change', handleChange);
    return () => media.removeEventListener('change', handleChange);
  }, []);

  return prefers;
};

const VisualBackground = ({ className }: VisualBackgroundProps) => {
  const prefersReducedMotion = usePrefersReducedMotion();
  const overrideMode =
    typeof window !== 'undefined' ? (window as VisualWindow).__VISUAL_BACKGROUND_MODE__ : undefined;
  const mode: VisualMode = overrideMode ?? (prefersReducedMotion ? 'minimal' : 'particles');
  const shouldRenderParticles = mode === 'particles';

  return (
    <div
      className={clsx(styles.root, className)}
      data-testid="visual-background"
      data-visual-mode={mode}
      data-reduced-motion={prefersReducedMotion}
      data-particle-count={shouldRenderParticles ? PARTICLES.length : 0}
      aria-hidden
    >
      {/* Базовый градиент неба */}
      <div className={styles.skyGradient} />

      {shouldRenderParticles ? (
        <div className={styles.particles}>
          {PARTICLES.map((p) => (
            <div
              key={p.id}
              data-testid="visual-particle"
              className={styles.particle}
              style={{
                left: `${p.left}%`,
                top: `${p.top}%`,
                animationDelay: `${p.delay}s`,
                animationDuration: `${p.duration}s`,
              }}
            />
          ))}
        </div>
      ) : (
        <div className={styles.minimalOverlay} />
      )}
    </div>
  );
};

export default VisualBackground;
