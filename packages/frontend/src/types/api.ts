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

export interface ProjectResponse {
  project: ProjectJSON;
}

export interface SceneResponse {
  scene: SceneJSON;
}

export interface TurnResponse {
  assistant_message: string;
  project: ProjectJSON;
  scene: SceneJSON;
}
