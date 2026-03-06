/** API client for the backend. Vite proxies /api → localhost:8000. */

import type {
  CreateProjectRequest,
  ReferenceMetadata,
  ReferenceResponse,
  SaveProjectRequest,
  SavedProjectMetadata,
  SavedProjectResponse,
  ProjectResponse,
  SceneResponse,
  TurnResponse,
  UpdateProjectRequest,
} from "../types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function createProject(
  req: CreateProjectRequest
): Promise<ProjectResponse> {
  return request<ProjectResponse>("/projects", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function getProject(id: string): Promise<SavedProjectResponse> {
  return request<SavedProjectResponse>(`/projects/${id}`);
}

export async function listReferences(): Promise<ReferenceMetadata[]> {
  return request<ReferenceMetadata[]>("/references");
}

export async function getReference(id: string): Promise<ReferenceResponse> {
  return request<ReferenceResponse>(`/references/${id}`);
}

export async function loadReference(id: string): Promise<ProjectResponse> {
  return request<ProjectResponse>(`/references/${id}/load`, {
    method: "POST",
  });
}

export async function listProjects(): Promise<SavedProjectMetadata[]> {
  return request<SavedProjectMetadata[]>("/projects");
}

export async function saveProject(
  projectId: string,
  req: SaveProjectRequest
): Promise<SavedProjectResponse> {
  return request<SavedProjectResponse>(`/projects/${projectId}/save`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function sendTurn(
  projectId: string,
  req: UpdateProjectRequest
): Promise<TurnResponse> {
  return request<TurnResponse>(`/projects/${projectId}/turn`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function compileScene(projectId: string): Promise<SceneResponse> {
  return request<SceneResponse>(`/projects/${projectId}/compile`, {
    method: "POST",
  });
}
