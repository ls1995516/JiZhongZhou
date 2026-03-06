/** Render scene types — mirrors backend models/scene.py */

export type GeometryPrimitive = "box" | "cylinder" | "extrusion" | "custom";

export interface Geometry {
  primitive: GeometryPrimitive;
  params: Record<string, number>;
  vertices?: number[][];
  indices?: number[];
}

export interface Material {
  color: string;
  opacity: number;
  metalness: number;
  roughness: number;
}

export type Transform = {
  position: [number, number, number];
  rotation: [number, number, number];
  scale: [number, number, number];
};

export type SceneObjectType = "mesh" | "group";

export interface ObjectMetadata {
  semantic_type?: string;
  label?: string;
}

export interface SceneObject {
  id: string;
  source_id?: string;
  type: SceneObjectType;
  geometry?: Geometry;
  material?: Material;
  transform: Transform;
  children: SceneObject[];
  metadata: ObjectMetadata;
}

export type LightType = "ambient" | "directional" | "point";

export interface SceneLight {
  type: LightType;
  color: string;
  intensity: number;
  position?: [number, number, number];
}

export interface SceneCamera {
  position: [number, number, number];
  target: [number, number, number];
  fov: number;
}

export interface SceneData {
  objects: SceneObject[];
  lights: SceneLight[];
  camera: SceneCamera;
}

export interface SceneJSON {
  version: string;
  metadata: Record<string, string>;
  scene: SceneData;
}
