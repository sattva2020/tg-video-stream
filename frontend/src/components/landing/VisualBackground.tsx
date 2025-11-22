import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import clsx from 'clsx';
import { detectVisualSupport, scheduleFallbackTimeout } from '../../lib/landing/visualSupport';
import type { VisualSupportMode, VisualSupportState } from './types';
import ZenScene from './ZenScene';
import styles from './visual-background.module.css';

export type VisualBackgroundProps = {
  className?: string;
};

type LandingVisualMetrics = {
  startedAt: number;
  mode: VisualSupportMode;
  fallbackReason?: VisualSupportState['fallbackReason'];
  fallbackLatencyMs?: number;
  fpsSamples: number;
  averageFps: number;
  lastFrameDurationMs?: number;
};

declare global {
  interface Window {
    __landingMetrics?: LandingVisualMetrics;
    __DISABLE_WEBGL__?: boolean;
  }
}

const now = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());

const VisualBackground = ({ className }: VisualBackgroundProps) => {
  const [state, setState] = useState<VisualSupportState>(() => detectVisualSupport());
  const [webglReady, setWebglReady] = useState(state.mode !== 'webgl');
    useEffect(() => {
      if (state.mode !== 'webgl') {
        setWebglReady(true);
      }
    }, [state.mode]);

  const rafRef = useRef<number>();
  const metricsRef = useRef<LandingVisualMetrics>({
    startedAt: now(),
    mode: state.mode,
    fallbackReason: state.fallbackReason,
    fallbackLatencyMs: state.mode === 'webgl' ? undefined : 0,
    fpsSamples: 0,
    averageFps: 0,
  });

  const commitMetrics = useCallback((patch: Partial<LandingVisualMetrics> = {}) => {
    metricsRef.current = { ...metricsRef.current, ...patch };
    if (typeof window !== 'undefined') {
      window.__landingMetrics = { ...metricsRef.current };
    }
  }, []);

  useEffect(() => {
    commitMetrics();
  }, [commitMetrics]);

  useEffect(() => {
    commitMetrics({ mode: state.mode, fallbackReason: state.fallbackReason });
  }, [state.mode, state.fallbackReason, commitMetrics]);

  useEffect(() => {
    if (state.mode !== 'webgl') {
      return undefined;
    }
    commitMetrics({ fpsSamples: 0, averageFps: 0 });
    let last = now();
    const tick = () => {
      const current = now();
      const delta = current - last;
      last = current;
      if (delta <= 0) {
        rafRef.current = window.requestAnimationFrame(tick);
        return;
      }
      const fps = 1000 / delta;
      const nextSamples = metricsRef.current.fpsSamples + 1;
      const nextAverage = metricsRef.current.averageFps + (fps - metricsRef.current.averageFps) / nextSamples;
      commitMetrics({
        fpsSamples: nextSamples,
        averageFps: Number(nextAverage.toFixed(2)),
        lastFrameDurationMs: Number(delta.toFixed(2)),
      });
      rafRef.current = window.requestAnimationFrame(tick);
    };
    rafRef.current = window.requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) {
        window.cancelAnimationFrame(rafRef.current);
      }
    };
  }, [state.mode, commitMetrics]);

  useEffect(() => {
    if (state.mode !== 'webgl' || webglReady) {
      return undefined;
    }

    const cancel = scheduleFallbackTimeout((fallback) => {
      setState(fallback);
      commitMetrics({
        mode: fallback.mode,
        fallbackReason: fallback.fallbackReason,
        fallbackLatencyMs: now() - metricsRef.current.startedAt,
      });
    });

    return () => cancel?.();
  }, [state.mode, webglReady, commitMetrics]);

  const posterVisible = state.mode === 'poster' || (state.mode === 'webgl' && !webglReady);

  useEffect(() => {
    if (state.mode !== 'webgl' && state.fallbackReason && metricsRef.current.fallbackLatencyMs == null) {
      commitMetrics({ fallbackLatencyMs: now() - metricsRef.current.startedAt });
    }
  }, [state.mode, state.fallbackReason, commitMetrics]);

  const canvas = useMemo(() => {
    if (state.mode !== 'webgl') {
      return null;
    }

    return (
      <Canvas
        className={styles.canvas}
        dpr={[1, 1.5]}
        camera={{ position: [0, 0, 6], fov: 45 }}
        gl={{ alpha: true, antialias: true, powerPreference: 'high-performance' }}
        shadows
      >
        <Suspense fallback={null}>
          <ZenScene onReady={() => setWebglReady(true)} />
        </Suspense>
      </Canvas>
    );
  }, [state.mode]);

  return (
    <div
      className={clsx(styles.root, className)}
      data-testid="visual-background"
      data-visual-mode={state.mode}
      data-fallback-reason={state.fallbackReason ?? ''}
      data-prefers-reduced-motion={state.prefersReducedMotion}
      data-poster-visible={posterVisible ? 'true' : 'false'}
      data-webgl-ready={webglReady ? 'true' : 'false'}
    >
      <div className={styles.gradientLayer} />
      <div className={styles.gradientOverlay} />
      <div
        className={clsx(styles.posterLayer, { [styles.posterVisible]: posterVisible })}
        role="presentation"
        aria-hidden
      />
      {canvas}
      <div className={styles.noiseLayer} />
    </div>
  );
};

export type { LandingVisualMetrics };
export default VisualBackground;
