import { Canvas } from "@react-three/fiber";
import { OrbitControls, Grid } from "@react-three/drei";
import { useAppStore } from "../stores/appStore";
import { SceneObjectRenderer } from "./SceneObjectRenderer";

export function Viewer3D() {
  const scene = useAppStore((s) => s.scene);
  const sceneData = scene?.scene;

  return (
    <div className="viewer-panel">
      <Canvas
        camera={{
          position: sceneData?.camera?.position ?? [20, 20, 20],
          fov: sceneData?.camera?.fov ?? 50,
        }}
      >
        {/* Lights — from scene data or defaults */}
        {sceneData?.lights?.map((light, i) => {
          switch (light.type) {
            case "ambient":
              return (
                <ambientLight
                  key={i}
                  color={light.color}
                  intensity={light.intensity}
                />
              );
            case "directional":
              return (
                <directionalLight
                  key={i}
                  color={light.color}
                  intensity={light.intensity}
                  position={light.position ?? [10, 20, 10]}
                />
              );
            case "point":
              return (
                <pointLight
                  key={i}
                  color={light.color}
                  intensity={light.intensity}
                  position={light.position ?? [0, 10, 0]}
                />
              );
          }
        }) ?? (
          <>
            <ambientLight intensity={0.4} />
            <directionalLight position={[10, 20, 10]} intensity={0.8} />
          </>
        )}

        {/* Ground grid */}
        <Grid
          args={[100, 100]}
          cellSize={1}
          cellThickness={0.5}
          cellColor="#6e6e6e"
          sectionSize={5}
          sectionThickness={1}
          sectionColor="#9d4b4b"
          fadeDistance={50}
          infiniteGrid
          position={[0, -0.01, 0]}
        />

        {/* Scene objects from backend */}
        {sceneData?.objects?.map((obj) => (
          <SceneObjectRenderer key={obj.id} obj={obj} />
        ))}

        {/* Placeholder when no scene loaded */}
        {!sceneData && (
          <mesh position={[0, 1.5, 0]}>
            <boxGeometry args={[3, 3, 3]} />
            <meshStandardMaterial color="#4a90d9" wireframe />
          </mesh>
        )}

        <OrbitControls
          target={sceneData?.camera?.target ?? [0, 0, 0]}
          makeDefault
        />
      </Canvas>
    </div>
  );
}
