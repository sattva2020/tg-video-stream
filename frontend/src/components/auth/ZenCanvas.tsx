import React, { lazy, Suspense, useEffect, useState } from 'react';

const LazyZenScene = lazy(() => import('../ZenScene'));

interface ZenCanvasProps {
  scrollY: number;
}

const ZenCanvas: React.FC<ZenCanvasProps> = ({ scrollY }) => {
  const [CanvasComp, setCanvasComp] = useState<any>(null);

  useEffect(() => {
    let mounted = true;
    // Dynamically import @react-three/fiber only when component mounts
    import('@react-three/fiber').then((m) => {
      if (mounted) setCanvasComp(() => m.Canvas);
    });
    return () => {
      mounted = false;
    };
  }, []);
  return (
    <div data-testid="auth-zen-canvas" className="h-full w-full">
      <Suspense fallback={null}>
        {CanvasComp ? (
          <CanvasComp camera={{ position: [0, 0, 8], fov: 45 }} gl={{ alpha: true }}>
            <LazyZenScene scrollY={scrollY} />
          </CanvasComp>
        ) : null}
      </Suspense>
    </div>
  );
};

export default ZenCanvas;
