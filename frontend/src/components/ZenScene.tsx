import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Stars, useTexture } from '@react-three/drei';
import { Group, Mesh, AdditiveBlending, DoubleSide, BackSide, FrontSide, Vector2 } from 'three';

const ZenScene: React.FC<{ scrollY: number }> = ({ scrollY: _scrollY }) => {
  return (
    <>
      <color attach="background" args={['#000008']} />
      <Stars radius={300} depth={60} count={6000} factor={5} saturation={0} fade speed={0.8} />
      
      {/* Основной солнечный свет — имитация Солнца справа сверху */}
      <directionalLight 
        position={[8, 4, 6]} 
        intensity={2.5} 
        color="#fffaf0"
        castShadow
      />
      
      {/* Мягкий fill-свет с противоположной стороны (отражённый свет) */}
      <directionalLight 
        position={[-5, -2, -3]} 
        intensity={0.3} 
        color="#4a6fa5"
      />
      
      {/* Ambient для мягкой заливки теней */}
      <ambientLight intensity={0.15} color="#1a1a2e" />
      
      {/* Rim light — подсветка края для объёма */}
      <pointLight position={[-6, 2, -4]} intensity={0.8} color="#6ba3ff" distance={20} />

      <Earth />
    </>
  );
};

const Earth = () => {
  const spinRef = useRef<Group>(null);
  const cloudsRef = useRef<Mesh>(null);
  const atmosphereRef = useRef<Mesh>(null);

  // Load high-res textures
  const [colorMap, normalMap, specularMap, cloudsMap] = useTexture([
    '/textures/earth_atmos_2048.webp',
    '/textures/earth_normal_2048.webp',
    '/textures/earth_specular_2048.webp',
    '/textures/earth_clouds_1024.webp'
  ]);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    // Earth rotates from West to East (Counter-Clockwise viewed from North Pole)
    if (spinRef.current) {
      spinRef.current.rotation.y = t * 0.03; // Более медленное реалистичное вращение
    }
    if (cloudsRef.current) {
      // Clouds move slightly faster than the surface (weather systems)
      cloudsRef.current.rotation.y = t * 0.035; 
    }
    if (atmosphereRef.current) {
      // Subtle atmosphere shimmer
      atmosphereRef.current.rotation.y = t * 0.01;
    }
  });

  return (
    // Axial Tilt: Earth is tilted ~23.4 degrees relative to its orbital plane.
    <group rotation={[0, 0, 23.4 * Math.PI / 180]}>
      <group ref={spinRef}>
        {/* Earth Surface — использует MeshStandardMaterial для PBR-реализма */}
        <mesh>
          <sphereGeometry args={[2.5, 128, 128]} />
          <meshStandardMaterial
            map={colorMap}
            normalMap={normalMap}
            normalScale={new Vector2(0.8, 0.8)}
            roughnessMap={specularMap}
            roughness={0.7}
            metalness={0.1}
            envMapIntensity={0.3}
          />
        </mesh>

        {/* Clouds Layer — полупрозрачный слой облаков */}
        <mesh ref={cloudsRef} scale={[1.008, 1.008, 1.008]}>
          <sphereGeometry args={[2.5, 64, 64]} />
          <meshStandardMaterial
            map={cloudsMap}
            transparent
            opacity={0.45}
            alphaMap={cloudsMap}
            blending={AdditiveBlending}
            side={DoubleSide}
            depthWrite={false}
          />
        </mesh>

        {/* Atmosphere Glow — внутреннее свечение атмосферы */}
        <mesh ref={atmosphereRef} scale={[1.015, 1.015, 1.015]}>
          <sphereGeometry args={[2.5, 64, 64]} />
          <meshBasicMaterial
            color="#4a90d9"
            transparent
            opacity={0.08}
            side={FrontSide}
            depthWrite={false}
          />
        </mesh>
      </group>

      {/* Outer Atmosphere — свечение вокруг планеты (Fresnel-эффект) */}
      <mesh scale={[1.12, 1.12, 1.12]}>
        <sphereGeometry args={[2.5, 64, 64]} />
        <shaderMaterial
          transparent
          depthWrite={false}
          side={BackSide}
          uniforms={{
            glowColor: { value: [0.3, 0.6, 1.0] },
            intensity: { value: 0.6 },
          }}
          vertexShader={`
            varying vec3 vNormal;
            void main() {
              vNormal = normalize(normalMatrix * normal);
              gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
            }
          `}
          fragmentShader={`
            uniform vec3 glowColor;
            uniform float intensity;
            varying vec3 vNormal;
            void main() {
              float glow = pow(0.65 - dot(vNormal, vec3(0.0, 0.0, 1.0)), 3.0);
              gl_FragColor = vec4(glowColor, glow * intensity);
            }
          `}
        />
      </mesh>
    </group>
  );
};

export default ZenScene;
