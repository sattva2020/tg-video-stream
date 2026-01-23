import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Stars, useTexture } from '@react-three/drei';
import { Group, Mesh, AdditiveBlending, DoubleSide } from 'three';

const ZenScene: React.FC<{ scrollY: number }> = ({ scrollY: _scrollY }) => {
  return (
    <>
      <color attach="background" args={['#000005']} />
      <Stars radius={300} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
      
      {/* Stronger light to make textures visible */}
      <directionalLight position={[5, 3, 5]} intensity={4.0} color="#ffffff" />
      <ambientLight intensity={1.5} />

      <Earth />
    </>
  );
};

const Earth = () => {
  const spinRef = useRef<Group>(null);
  const cloudsRef = useRef<Mesh>(null);

  // Load high-res textures
  const [colorMap, normalMap, specularMap, cloudsMap] = useTexture([
    'https://raw.githubusercontent.com/mrdoob/three.js/master/examples/textures/planets/earth_atmos_2048.jpg',
    'https://raw.githubusercontent.com/mrdoob/three.js/master/examples/textures/planets/earth_normal_2048.jpg',
    'https://raw.githubusercontent.com/mrdoob/three.js/master/examples/textures/planets/earth_specular_2048.jpg',
    'https://raw.githubusercontent.com/mrdoob/three.js/master/examples/textures/planets/earth_clouds_1024.png'
  ]);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    // Earth rotates from West to East (Counter-Clockwise viewed from North Pole)
    // In Three.js (Right-Hand Rule), positive Y rotation is Counter-Clockwise.
    if (spinRef.current) {
      spinRef.current.rotation.y = t * 0.05; 
    }
    if (cloudsRef.current) {
      // Clouds move slightly faster than the surface (weather systems)
      cloudsRef.current.rotation.y = t * 0.055; 
    }
  });

  return (
    // Axial Tilt: Earth is tilted ~23.4 degrees relative to its orbital plane.
    // We apply this tilt to the container group so the planet spins around the tilted axis.
    <group rotation={[0, 0, 23.4 * Math.PI / 180]}>
      <group ref={spinRef}>
        {/* Earth Surface */}
        <mesh>
          <sphereGeometry args={[2.5, 64, 64]} />
          <meshPhongMaterial
            map={colorMap}
            normalMap={normalMap}
            specularMap={specularMap}
            shininess={5}
          />
        </mesh>

        {/* Clouds Layer - Separate mesh to allow independent rotation */}
        <mesh ref={cloudsRef} scale={[1.01, 1.01, 1.01]}>
          <sphereGeometry args={[2.5, 64, 64]} />
          <meshStandardMaterial
            map={cloudsMap}
            transparent
            opacity={0.8}
            blending={AdditiveBlending}
            side={DoubleSide}
            depthWrite={false}
          />
        </mesh>
      </group>
    </group>
  );
};

export default ZenScene;
