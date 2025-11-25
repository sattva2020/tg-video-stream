import React, { lazy, Suspense } from 'react';
import { Canvas } from '@react-three/fiber';

const LazyZenScene = lazy(() => import('../ZenScene'));

interface ZenCanvasProps {
  scrollY: number;
}

const ZenCanvas: React.FC<ZenCanvasProps> = ({ scrollY }) => {
  return (
    <div data-testid="auth-zen-canvas" className="h-full w-full">
      <Suspense fallback={null}>
        <Canvas camera={{ position: [0, 0, 8], fov: 45 }} gl={{ alpha: true }}>
          <LazyZenScene scrollY={scrollY} />
        </Canvas>
      </Suspense>
    </div>
  );
};

export default ZenCanvas;
