# AI Building Authoring Studio (JiZhongZhou)

## Project Overview
- Multi-layer system where coding-agent-style workers generate and transform building descriptions.
- Flow: user chats -> Project JSON (semantic) -> Scene JSON (geometry) -> 3D render.

## Repository Layout
- `packages/backend/` - Python backend built with FastAPI and LangGraph.
- `packages/frontend/` - React + TypeScript + Vite + React Three Fiber + Zustand.
- `packages/shared/` - Shared JSON Schema definitions across layers.

## Key Conventions
- Use Python 3.11+.
- Use `uv` for Python dependency management.
- Use Pydantic v2 for backend models.
- All dimensions are in meters.
- All coordinates are relative to the building origin.
- `ProjectJSON` is the semantic source of truth and must not be rendered directly.
- `SceneJSON` is the compiled render artifact consumed by the 3D viewer.
- The system has two LangGraph workflows:
  - `project_authoring` (WF1)
  - `geometry_compilation` (WF2)
- `CodingAgentProvider` is the swap point for LLM workers.

## Runtime Commands
### Backend
```bash
cd packages/backend
uv run uvicorn src.main:app --reload
```

### Frontend
```bash
cd packages/frontend
pnpm install
pnpm dev
```

- Vite proxies `/api` to `http://localhost:8000`, so the backend must be running for frontend API calls to work.

## Layer Boundaries
1. Frontend <-> Backend: REST with JSON today, WebSocket planned later.
2. WF1 output -> WF2 input: validated `ProjectJSON` inside Python.
3. WF2 output -> Frontend: `SceneJSON`.
4. Frontend must never interpret `ProjectJSON` for rendering.

## Working Guidance For Agents
- Preserve the separation between semantic authoring and geometry compilation.
- Treat backend validation and compilation as deterministic steps around agent outputs.
- When changing rendering behavior, update the Scene JSON pipeline rather than teaching the frontend to infer geometry from Project JSON.
- When changing LLM integration behavior, start at `packages/backend/src/services/agent_provider.py`.
