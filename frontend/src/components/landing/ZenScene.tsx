import { useEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Float, Sparkles } from '@react-three/drei';
import * as THREE from 'three';

export type ZenSceneProps = {
  onReady?: () => void;
};

const CameraRig = () => {
  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    const tiltX = Math.sin(t / 4) * THREE.MathUtils.degToRad(8);
    const tiltY = Math.cos(t / 5) * THREE.MathUtils.degToRad(12);
    state.camera.position.set(Math.sin(t / 6) * 0.8, Math.cos(t / 7) * 0.6, 5.5);
    state.camera.rotation.set(tiltX, tiltY, 0);
    state.camera.lookAt(0, 0, 0);
  });
  return null;
};

const AuroraPlane = () => {
  const shader = useMemo(() => new THREE.ShaderMaterial({
    transparent: true,
    uniforms: {
      uTime: { value: 0 },
      uColorStart: { value: new THREE.Color('#0ea5e9') },
      uColorEnd: { value: new THREE.Color('#38bdf8') },
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        vec3 transformed = position;
        transformed.y += sin((uv.x + uv.y) * 8.0) * 0.2;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(transformed, 1.0);
      }
    `,
    fragmentShader: `
      uniform float uTime;
      uniform vec3 uColorStart;
      uniform vec3 uColorEnd;
      varying vec2 vUv;
      void main() {
        float alpha = 0.35 + 0.2 * sin((vUv.x + uTime) * 4.0);
        vec3 color = mix(uColorStart, uColorEnd, vUv.y + 0.05 * sin(uTime + vUv.x * 6.0));
        gl_FragColor = vec4(color, alpha);
      }
    `,
  }), []);

  useEffect(() => () => shader.dispose(), [shader]);

  useFrame((_, delta) => {
    shader.uniforms.uTime.value += delta * 0.5;
  });

  return (
    <mesh rotation={[-Math.PI / 2.5, 0, 0]} position={[0, -0.6, -1]}>
      <planeGeometry args={[10, 8, 64, 64]} />
      <primitive object={shader} attach="material" />
    </mesh>
  );
};

const LightOrbs = () => {
  const ref = useRef<THREE.Group>(null);
  const items = useMemo(
    () =>
      Array.from({ length: 6 }).map((_, index) => ({
        radius: 2.5 + index * 0.25,
        speed: 0.3 + index * 0.05,
        size: 0.15 + index * 0.05,
        phase: Math.random() * Math.PI * 2,
      })),
    [],
  );

  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.getElapsedTime();
    ref.current.children.forEach((child, index) => {
      const orb = items[index];
      const angle = t * orb.speed + orb.phase;
      child.position.set(Math.cos(angle) * orb.radius, Math.sin(angle * 0.6) * 0.6, Math.sin(angle) * orb.radius);
    });
  });

  return (
    <group ref={ref}>
      {items.map((orb, index) => (
        <mesh key={`orb-${index}`}>
          <sphereGeometry args={[orb.size, 32, 32]} />
          <meshStandardMaterial
            color={index % 2 === 0 ? '#7dd3fc' : '#bae6fd'}
            emissive={index % 2 === 0 ? '#0ea5e9' : '#38bdf8'}
            emissiveIntensity={1.2}
            transparent
            opacity={0.85}
          />
        </mesh>
      ))}
    </group>
  );
};

const OrbitalShell = () => {
  const ref = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (!ref.current) return;
    const t = state.clock.getElapsedTime();
    ref.current.rotation.x = Math.sin(t * 0.4) * 0.35 + Math.PI / 3;
    ref.current.rotation.y = Math.cos(t * 0.3) * 0.2;
  });

  return (
    <mesh ref={ref}>
      <torusKnotGeometry args={[2.8, 0.04, 256, 24, 2, 3]} />
      <meshStandardMaterial
        color="#38bdf8"
        metalness={0.9}
        roughness={0.1}
        emissive="#0ea5e9"
        emissiveIntensity={0.3}
      />
    </mesh>
  );
};

const ZenScene = ({ onReady }: ZenSceneProps) => {
  const groupRef = useRef<THREE.Group>(null);
  const notifiedRef = useRef(false);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(t / 3) * 0.25;
      groupRef.current.rotation.x = Math.cos(t / 5) * 0.2;
    }
    if (!notifiedRef.current) {
      notifiedRef.current = true;
      onReady?.();
    }
  });

  const shards = useMemo(() => (
    Array.from({ length: 24 }).map((_, index) => ({
      position: new THREE.Vector3(
        Math.sin((index / 24) * Math.PI * 2) * 3.2,
        THREE.MathUtils.randFloatSpread(1.4),
        Math.cos((index / 24) * Math.PI * 2) * 3.2,
      ),
      rotation: new THREE.Euler(
        THREE.MathUtils.randFloatSpread(0.4),
        THREE.MathUtils.randFloatSpread(0.4),
        THREE.MathUtils.randFloatSpread(0.4),
      ),
    }))
  ), []);

  return (
    <>
      <color attach="background" args={["#050b16"]} />
      <fog attach="fog" args={["#050b16", 8, 22]} />
      <ambientLight intensity={0.4} color="#7dd3fc" />
      <directionalLight position={[6, 6, 5]} intensity={1.1} color="#bae6fd" castShadow />
      <pointLight position={[-6, -4, -2]} intensity={0.8} color="#0ea5e9" distance={18} />
      <CameraRig />
      <group ref={groupRef}>
        <Float speed={1.4} rotationIntensity={0.3} floatIntensity={0.6}>
          <mesh castShadow>
            <icosahedronGeometry args={[1.5, 1]} />
            <meshStandardMaterial color="#38bdf8" emissive="#0ea5e9" metalness={1} roughness={0.15} />
          </mesh>
        </Float>
        <Sparkles count={140} scale={[10, 6, 10]} speed={0.35} color="#bae6fd" opacity={0.6} />
        <Sparkles count={60} scale={[8, 4, 8]} speed={0.2} color="#38bdf8" opacity={0.5} />
        <OrbitalShell />
        <group>
          {shards.map((shard, index) => (
            <mesh key={`shard-${index}`} position={shard.position} rotation={shard.rotation}>
              <boxGeometry args={[0.08, 0.6, 0.18]} />
              <meshStandardMaterial
                color="#7dd3fc"
                emissive="#7dd3fc"
                emissiveIntensity={0.25}
                transparent
                opacity={0.8}
              />
            </mesh>
          ))}
        </group>
      </group>
      <LightOrbs />
      <AuroraPlane />
    </>
  );
};

export default ZenScene;
