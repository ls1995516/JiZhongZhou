import type { SceneObject } from "../types";

/** Recursively renders a SceneObject tree as R3F elements. */
export function SceneObjectRenderer({ obj }: { obj: SceneObject }) {
  const { position, rotation, scale } = obj.transform;

  if (obj.type === "group") {
    return (
      <group position={position} rotation={rotation} scale={scale}>
        {obj.children.map((child) => (
          <SceneObjectRenderer key={child.id} obj={child} />
        ))}
      </group>
    );
  }

  // Mesh
  const geo = obj.geometry;
  const mat = obj.material;

  return (
    <mesh position={position} rotation={rotation} scale={scale}>
      {geo ? <PrimitiveGeometry geo={geo} /> : <boxGeometry args={[1, 1, 1]} />}
      <meshStandardMaterial
        color={mat?.color ?? "#cccccc"}
        opacity={mat?.opacity ?? 1}
        transparent={(mat?.opacity ?? 1) < 1}
        metalness={mat?.metalness ?? 0}
        roughness={mat?.roughness ?? 0.8}
      />
    </mesh>
  );
}

function PrimitiveGeometry({ geo }: { geo: NonNullable<SceneObject["geometry"]> }) {
  const p = geo.params;

  switch (geo.primitive) {
    case "box":
      return (
        <boxGeometry args={[p.width ?? 1, p.height ?? 1, p.depth ?? 1]} />
      );
    case "cylinder":
      return (
        <cylinderGeometry
          args={[
            p.radiusTop ?? p.radius ?? 0.5,
            p.radiusBottom ?? p.radius ?? 0.5,
            p.height ?? 1,
            p.segments ?? 16,
          ]}
        />
      );
    default:
      // extrusion / custom — fallback to unit box
      return <boxGeometry args={[1, 1, 1]} />;
  }
}
