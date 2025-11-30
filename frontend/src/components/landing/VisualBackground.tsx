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
const VisualBackground = ({ className }: VisualBackgroundProps) => (
  <div className={clsx(styles.root, className)} data-testid="visual-background">
    {/* Базовый градиент неба */}
    <div className={styles.skyGradient} />
    
    {/* Звёзды / частицы */}
    <div className={styles.particles}>
      {PARTICLES.map((p) => (
        <div 
          key={p.id} 
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
    
    {/* Telegram самолётик */}
    <div className={styles.telegramPlane}>
      <svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
      </svg>
    </div>
    
    {/* LIVE индикатор */}
    <div className={styles.liveIndicator}>
      <span className={styles.liveDot} />
      <span className={styles.liveText}>24/7</span>
    </div>
  </div>
);

export default VisualBackground;
