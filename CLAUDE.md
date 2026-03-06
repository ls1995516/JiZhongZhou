# AI Building Authoring Studio (JiZhongZhou)

## Project Overview
Multi-layer system where coding-agent-style workers generate and transform building descriptions.
User chats → Project JSON (semantic) → Scene JSON (geometry) → 3D render.

## Architecture
- `packages/backend/` — Python (FastAPI + LangGraph)
- `packages/frontend/` — React + TypeScript + Vite + R3F + Zustand
- `packages/shared/` — JSON Schema definitions shared across layers

## Key Conventions
- Python 3.11+, use `uv` for dependency management
- Pydantic v2 for all models
- All dimensions in meters, coordinates relative to building origin
- Project JSON is the semantic source of truth — never render it directly
- Scene JSON is the compiled render artifact — consumed by the 3D viewer
- Two LangGraph workflows: project_authoring (WF1), geometry_compilation (WF2)
- CodingAgentProvider is the swap point for LLM workers

## Running the backend
```bash
cd packages/backend
uv run uvicorn src.main:app --reload
```

## Running the frontend
```bash
cd packages/frontend
pnpm install
pnpm dev
```
Vite proxies `/api` → `localhost:8000` so the backend must be running.

## Layer Boundaries
1. Frontend ↔ Backend: REST (JSON) + future WebSocket
2. WF1 output → WF2 input: validated ProjectJSON (internal Python)
3. WF2 output → Frontend: SceneJSON
4. Frontend NEVER interprets ProjectJSON for rendering
