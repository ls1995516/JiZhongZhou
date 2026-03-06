/** Global app state using Zustand. */

import { create } from "zustand";
import type { ProjectJSON, SceneJSON } from "../types";
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

  // Chat
  messages: ChatMessage[];
  isSending: boolean;

  // Inspector
  showInspector: boolean;

  // Actions
  createProject: (name: string) => Promise<void>;
  loadProject: (id: string) => Promise<void>;
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
  messages: [],
  isSending: false,
  showInspector: false,

  createProject: async (name: string) => {
    const { project } = await api.createProject({ name });
    const { scene } = await api.compileScene(project.id);
    set({
      projectId: project.id,
      project,
      scene,
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
    const { project } = await api.getProject(id);
    const { scene } = await api.compileScene(project.id);
    set({ projectId: id, project, scene });
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
        isSending: false,
      }));
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
