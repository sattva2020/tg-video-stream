import clsx from 'clsx';
import styles from './visual-background.module.css';

export type VisualBackgroundProps = {
  className?: string;
};

const VisualBackground = ({ className }: VisualBackgroundProps) => (
  <div className={clsx(styles.root, className)} data-testid="visual-background">
    <div className={styles.gradientLayer} />
    <div className={styles.glowOrb} />
    <div className={styles.accentRibbon} />
    <div className={styles.spotLight} />
    <div className={styles.noiseLayer} />
  </div>
);

export default VisualBackground;
