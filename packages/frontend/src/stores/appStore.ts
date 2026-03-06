/** Global app state using Zustand. */

import { create } from "zustand";
import type { ProjectJSON, SavedProjectMetadata, SceneJSON } from "../types";
import * as api from "../api/client";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface AppState {
  // Project
  projectId: string | null;
  project: ProjectJSON | null;

  // Scene
  scene: SceneJSON | null;
  savedProjects: SavedProjectMetadata[];

  // Chat
  messages: ChatMessage[];
  isSending: boolean;
  isSaving: boolean;

  // Inspector
  showInspector: boolean;

  // Actions
  createProject: (name: string) => Promise<void>;
  loadProject: (id: string) => Promise<void>;
  saveProject: () => Promise<void>;
  refreshProjects: () => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
  compileScene: () => Promise<void>;
  toggleInspector: () => void;
}

let msgCounter = 0;
function makeId(): string {
  return `msg-${++msgCounter}-${Date.now()}`;
}

export const useAppStore = create<AppState>((set, get) => ({
  projectId: null,
  project: null,
  scene: null,
  savedProjects: [],
  messages: [],
  isSending: false,
  isSaving: false,
  showInspector: false,

  createProject: async (name: string) => {
    const { project } = await api.createProject({ name });
    const { scene } = await api.compileScene(project.id);
    const savedProjects = await api.listProjects();
    set({
      projectId: project.id,
      project,
      scene,
      savedProjects,
      messages: [
        {
          id: makeId(),
          role: "assistant",
          content: `Project "${name}" created. You have a default 10×10m single-floor building. Tell me what you'd like to build.`,
        },
      ],
    });
  },

  loadProject: async (id: string) => {
    const saved = await api.getProject(id);
    const scene =
      saved.scene ?? (await api.compileScene(saved.project.id)).scene;
    set({
      projectId: id,
      project: saved.project,
      scene,
    });
  },

  saveProject: async () => {
    const { projectId, project, scene } = get();
    if (!projectId || !project) return;

    set({ isSaving: true });
    try {
      const saved = await api.saveProject(projectId, {
        project,
        scene,
      });
      const savedProjects = await api.listProjects();
      set({
        project: saved.project,
        scene: saved.scene ?? scene,
        savedProjects,
        isSaving: false,
      });
    } catch (err) {
      const errorMsg: ChatMessage = {
        id: makeId(),
        role: "assistant",
        content: `Save failed: ${err instanceof Error ? err.message : String(err)}`,
      };
      set((s) => ({
        messages: [...s.messages, errorMsg],
        isSaving: false,
      }));
    }
  },

  refreshProjects: async () => {
    const savedProjects = await api.listProjects();
    set({ savedProjects });
  },

  sendMessage: async (text: string) => {
    const { projectId } = get();
    if (!projectId) return;

    const userMsg: ChatMessage = { id: makeId(), role: "user", content: text };
    set((s) => ({ messages: [...s.messages, userMsg], isSending: true }));

    try {
      const turn = await api.sendTurn(projectId, { prompt: text });
      const assistantMsg: ChatMessage = {
        id: makeId(),
        role: "assistant",
        content: turn.assistant_message,
      };
      set((s) => ({
        messages: [...s.messages, assistantMsg],
        project: turn.project,
        scene: turn.scene,
        savedProjects: s.savedProjects,
        isSending: false,
      }));
      const savedProjects = await api.listProjects();
      set({ savedProjects });
    } catch (err) {
      const errorMsg: ChatMessage = {
        id: makeId(),
        role: "assistant",
        content: `Error: ${err instanceof Error ? err.message : String(err)}`,
      };
      set((s) => ({
        messages: [...s.messages, errorMsg],
        isSending: false,
      }));
    }
  },

  compileScene: async () => {
    const { projectId } = get();
    if (!projectId) return;
    const { scene } = await api.compileScene(projectId);
    set({ scene });
  },

  toggleInspector: () => set((s) => ({ showInspector: !s.showInspector })),
}));
