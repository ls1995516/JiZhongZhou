/** Project JSON types — mirrors backend models/project.py */

export interface Vector2 {
  x: number;
  y: number;
}

export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

export interface Polygon {
  points: Vector2[];
}

export type OpeningType = "door" | "window";

export interface Opening {
  id: string;
  type: OpeningType;
  position: number;
  width: number;
  height: number;
  sill_height: number;
}

export interface Wall {
  id: string;
  start: Vector2;
  end: Vector2;
  thickness: number;
  openings: Opening[];
}

export interface Room {
  id: string;
  label: string;
  outline: Polygon;
  function?: string;
}

export type RoofType = "flat" | "gable" | "hip";

export interface Floor {
  id: string;
  label?: string;
  elevation: number;
  height: number;
  outline: Polygon;
  walls: Wall[];
  rooms: Room[];
}

export interface ProjectMetadata {
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface BuildingInfo {
  floors: Floor[];
  roof_type: RoofType;
}

export interface SiteInfo {
  dimensions: Vector2;
  elevation: number;
}

export interface ProjectJSON {
  version: string;
  id: string;
  metadata: ProjectMetadata;
  site: SiteInfo;
  building: BuildingInfo;
}
