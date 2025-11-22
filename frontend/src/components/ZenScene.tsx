import React, { useRef, useMemo, useState, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import { MeshReflectorMaterial, Float, Sparkles, Text, Stars as DreiStars } from '@react-three/drei';
import * as THREE from 'three';

const ZenScene: React.FC<{ scrollY: number }> = ({ scrollY }) => {
  const groupRef = useRef<THREE.Group>(null);
  const [mouse, setMouse] = useState({ x: 0, y: 0 });

  // Track mouse movement
  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      setMouse({
        x: (event.clientX / window.innerWidth) * 2 - 1,
        y: -(event.clientY / window.innerHeight) * 2 + 1,
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useFrame((state) => {
    if (groupRef.current) {
      // Smooth rotation based on time
      groupRef.current.rotation.y = state.clock.getElapsedTime() * 0.05;
      groupRef.current.rotation.z = scrollY * 0.0002;

      // Interactive parallax effect - follow mouse
      groupRef.current.rotation.x = THREE.MathUtils.lerp(
        groupRef.current.rotation.x,
        mouse.y * 0.1,
        0.05
      );
      groupRef.current.rotation.y = THREE.MathUtils.lerp(
        groupRef.current.rotation.y,
        mouse.x * 0.1 + state.clock.getElapsedTime() * 0.05,
        0.05
      );
    }
  });

  return (
    <>
      {/* Uniform Starry Sky Background */}
      <color attach="background" args={['#000000']} />
      <DreiStars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />

      <ambientLight intensity={0.5} color="#ffffff" />
      <InteractiveLights mouse={mouse} />

      <group ref={groupRef}>
        {/* Central Text Object */}
        <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
          <SattvaText />
        </Float>

        {/* Orbital Rings - Mandalas */}
        <OrbitalRings />

        {/* Energy Particles */}
        <Sparkles count={100} scale={12} size={4} speed={0.4} opacity={0.5} color="#ffd700" />
        <Sparkles count={50} scale={10} size={6} speed={0.3} opacity={0.3} color="#4a90e2" />

        {/* Floating Lotus Petals */}
        <LotusPetals />
      </group>

      {/* Cosmic Floor with Real-time Reflections */}
      <CosmicFloor />
    </>
  );
};

const InteractiveLights: React.FC<{ mouse: { x: number; y: number } }> = ({ mouse }) => {
  const light1Ref = useRef<THREE.PointLight>(null);
  const light2Ref = useRef<THREE.PointLight>(null);
  const light3Ref = useRef<THREE.PointLight>(null);

  useFrame(() => {
    if (light1Ref.current) {
      light1Ref.current.position.x = THREE.MathUtils.lerp(
        light1Ref.current.position.x,
        10 + mouse.x * 5,
        0.1
      );
      light1Ref.current.position.y = THREE.MathUtils.lerp(
        light1Ref.current.position.y,
        10 + mouse.y * 5,
        0.1
      );
    }
    if (light2Ref.current) {
      light2Ref.current.position.x = THREE.MathUtils.lerp(
        light2Ref.current.position.x,
        -10 - mouse.x * 3,
        0.1
      );
      light2Ref.current.position.y = THREE.MathUtils.lerp(
        light2Ref.current.position.y,
        -5 - mouse.y * 3,
        0.1
      );
    }
    if (light3Ref.current) {
      light3Ref.current.position.x = THREE.MathUtils.lerp(
        light3Ref.current.position.x,
        mouse.x * 4,
        0.1
      );
    }
  });

  return (
    <>
      <pointLight ref={light1Ref} position={[10, 10, 10]} intensity={2} color="#ffd700" distance={20} />
      <pointLight ref={light2Ref} position={[-10, -5, -10]} intensity={1.2} color="#ff6b35" distance={15} />
      <pointLight ref={light3Ref} position={[0, -10, 5]} intensity={0.8} color="#4a90e2" distance={12} />
    </>
  );
};

const SattvaText = () => {
  return (
    <Text
      fontSize={1}
      color="#ffd700"
      anchorX="center"
      anchorY="middle"
      outlineWidth={0.02}
      outlineColor="#d4af37"
    >
      SATTVA-TETTREY
      <meshPhysicalMaterial
        attach="material"
        color="#ffd700"
        emissive="#d4af37"
        emissiveIntensity={0.2}
        roughness={0}
        metalness={0.8}
        transmission={0.2}
        thickness={1}
      />
    </Text>
  );
};

const OrbitalRings = () => {
  const ring1Ref = useRef<THREE.Mesh>(null);
  const ring2Ref = useRef<THREE.Mesh>(null);
  const ring3Ref = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (ring1Ref.current) {
      ring1Ref.current.rotation.x = Math.sin(t * 0.2) * 0.5 + Math.PI / 2;
      ring1Ref.current.rotation.z = t * 0.1;
    }
    if (ring2Ref.current) {
      ring2Ref.current.rotation.y = t * 0.15;
      ring2Ref.current.rotation.x = Math.cos(t * 0.15) * 0.3;
    }
    if (ring3Ref.current) {
      ring3Ref.current.rotation.x = Math.PI / 3;
      ring3Ref.current.rotation.z = -t * 0.05;
    }
  });

  return (
    <group>
      <mesh ref={ring1Ref}>
        <torusGeometry args={[3.5, 0.02, 16, 100]} />
        <meshStandardMaterial
          color="#d4af37"
          roughness={0.2}
          metalness={1}
          emissive="#d4af37"
          emissiveIntensity={0.2}
        />
      </mesh>

      <mesh ref={ring2Ref}>
        <torusGeometry args={[4.2, 0.01, 16, 100]} />
        <meshStandardMaterial
          color="#c0c0c0"
          roughness={0.1}
          metalness={1}
          emissive="#ffffff"
          emissiveIntensity={0.1}
        />
      </mesh>

      <mesh ref={ring3Ref}>
        <torusGeometry args={[4.9, 0.01, 16, 100]} />
        <meshStandardMaterial
          color="#cd7f32"
          roughness={0.3}
          metalness={1}
          emissive="#cd7f32"
          emissiveIntensity={0.1}
        />
      </mesh>
    </group>
  );
};

const LotusPetals = () => {
  const petals = useMemo(() => {
    return Array.from({ length: 8 }, (_, i) => ({
      angle: (i / 8) * Math.PI * 2,
      radius: 4.0,
      height: Math.random() * 0.5 - 0.25,
    }));
  }, []);

  return (
    <group>
      {petals.map((petal, i) => (
        <mesh
          key={i}
          position={[
            Math.cos(petal.angle) * petal.radius,
            petal.height,
            Math.sin(petal.angle) * petal.radius,
          ]}
          rotation={[0, petal.angle, 0]}
        >
          <boxGeometry args={[0.4, 0.05, 1.2]} />
          <meshStandardMaterial
            color="#ff69b4"
            emissive="#ff1493"
            emissiveIntensity={0.3}
            transparent
            opacity={0.4}
          />
        </mesh>
      ))}
    </group>
  );
};

const CosmicFloor = () => {
  return (
    <mesh position={[0, -4, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[50, 50]} />
      <MeshReflectorMaterial
        blur={[300, 100]}
        resolution={1024}
        mixBlur={1}
        mixStrength={50}
        roughness={1}
        depthScale={1.2}
        minDepthThreshold={0.4}
        maxDepthThreshold={1.4}
        color="#151515"
        metalness={0.5}
        mirror={0.5}
      />
    </mesh>
  );
};

export default ZenScene;
