/** API request/response types — mirrors backend models/api.py */

import type { ProjectJSON } from "./project";
import type { SceneJSON } from "./scene";

export interface CreateProjectRequest {
  name: string;
  description?: string;
}

export interface UpdateProjectRequest {
  prompt: string;
}

export interface SaveProjectRequest {
  project: ProjectJSON;
  scene?: SceneJSON | null;
}

export interface ProjectResponse {
  project: ProjectJSON;
}

export interface SavedProjectMetadata {
  project_id: string;
  name: string;
  description?: string;
  created_at?: string;
  updated_at?: string;
  last_saved_at?: string;
  has_render_scene: boolean;
}

export interface SavedProjectResponse {
  project: ProjectJSON;
  scene?: SceneJSON | null;
  metadata: SavedProjectMetadata;
  history: Array<Record<string, unknown>>;
}

export interface SceneResponse {
  scene: SceneJSON;
}

export interface TurnResponse {
  assistant_message: string;
  project: ProjectJSON;
  scene: SceneJSON;
}
