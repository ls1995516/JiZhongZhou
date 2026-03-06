# AI Building Authoring Studio

A multi-layer system where users describe buildings through natural language chat, and coding-agent-style AI workers generate structured project data that is compiled into 3D-renderable geometry.

This is **not** a plain LLM wrapper. The pipeline separates user intent, semantic project data, and render output into distinct layers with clear boundaries.

## How It Works

```
User: "Build a 2-story house with a garage"
        │
        ▼
┌──────────────────┐
│  Project Author   │  LangGraph workflow + coding-agent worker
│  (WF1)            │  Interprets intent, generates/updates Project JSON
└────────┬─────────┘
         │  Validated ProjectJSON (semantic source of truth)
         ▼
┌──────────────────┐
│  Scene Compiler   │  LangGraph workflow + deterministic compiler
│  (WF2)            │  Converts project elements into positioned geometry
└────────┬─────────┘
         │  SceneJSON (meshes, materials, lights, camera)
         ▼
┌──────────────────┐
│  3D Viewer        │  React Three Fiber
│  (Frontend)       │  Renders the scene in the browser
└──────────────────┘
```

## Architecture

### Four Layers

| Layer | Technology | Responsibility |
|-------|-----------|---------------|
| **Frontend** | React, TypeScript, Vite, React Three Fiber, Zustand | Chat UI, 3D viewer, project inspector |
| **Project Author (WF1)** | LangGraph, Claude (via CodingAgentProvider) | Generate and edit Project JSON from user prompts |
| **Scene Compiler (WF2)** | LangGraph, deterministic Python compiler | Convert validated Project JSON into render-ready Scene JSON |
| **Storage** | Local file system (MVP) | Persist projects as JSON files on disk |

### Key Design Rules

- **Project JSON** is the semantic source of truth. It describes *what* the building is (floors, walls, rooms, openings) — not how to render it.
- **Scene JSON** is a compiled artifact. It contains positioned geometry primitives, materials, lights, and camera — ready for Three.js consumption.
- The frontend **never** interprets Project JSON for rendering. It only consumes Scene JSON.
- Validation and geometry compilation are **deterministic** wherever possible. The AI agent handles intent interpretation and complex spatial reasoning.

### Data Schemas

**Project JSON** models a building semantically:
- Site (dimensions, elevation)
- Building with stacked Floors
- Each Floor has an outline polygon, walls, and rooms
- Walls have start/end points, thickness, and openings (doors/windows)
- All dimensions in meters, coordinates relative to building origin

**Scene JSON** models a renderable scene:
- Tree of SceneObjects (groups and meshes)
- Each mesh has geometry (box, cylinder, extrusion, or custom vertices), material (color, opacity, PBR), and a transform (position, rotation, scale)
- Lights (ambient, directional, point) and camera with auto-framing
- `source_id` on each object links back to the project element for selection

## Project Structure

```
JiZhongZhou/
├── packages/
│   ├── backend/                    # Python — FastAPI + LangGraph
│   │   ├── src/
│   │   │   ├── main.py             # FastAPI app, dependency wiring
│   │   │   ├── api/
│   │   │   │   └── routes.py       # REST endpoints
│   │   │   ├── models/
│   │   │   │   ├── project.py      # ProjectJSON Pydantic models
│   │   │   │   ├── scene.py        # SceneJSON Pydantic models
│   │   │   │   ├── state.py        # LangGraph workflow state
│   │   │   │   └── api.py          # Request/response models
│   │   │   ├── graphs/
│   │   │   │   ├── project_authoring.py    # WF1: plan → agent → validate → respond
│   │   │   │   └── geometry_compilation.py # WF2: decompose → compile → refine → assemble
│   │   │   ├── services/
│   │   │   │   ├── agent_provider.py       # CodingAgentProvider interface (LLM swap point)
│   │   │   │   ├── project_service.py      # Project CRUD orchestration
│   │   │   │   └── scene_service.py        # Compilation orchestration
│   │   │   ├── compiler/
│   │   │   │   ├── scene_compiler.py       # SceneCompiler interface + default implementation
│   │   │   │   ├── geometry.py             # Floor slab, wall, opening → box primitives
│   │   │   │   ├── materials.py            # Default material palette by semantic type
│   │   │   │   └── transforms.py           # Spatial transform utilities
│   │   │   ├── validators/
│   │   │   │   └── project_validator.py    # Structural validation beyond Pydantic
│   │   │   └── storage/
│   │   │       └── project_store.py        # ProjectStore interface + file implementation
│   │   ├── data/projects/                  # Persisted project JSON files
│   │   └── pyproject.toml
│   │
│   ├── frontend/                   # React + TypeScript + Vite
│   │   ├── src/
│   │   │   ├── App.tsx             # Root layout: toolbar + chat | viewer | inspector
│   │   │   ├── main.tsx            # React entry point
│   │   │   ├── index.css           # Dark theme styles
│   │   │   ├── api/
│   │   │   │   └── client.ts       # Typed fetch wrappers for all endpoints
│   │   │   ├── components/
│   │   │   │   ├── Chat.tsx        # Chat panel with message history
│   │   │   │   ├── Viewer3D.tsx    # R3F Canvas with lights, grid, orbit controls
│   │   │   │   ├── SceneObjectRenderer.tsx  # Recursive scene tree → meshes
│   │   │   │   ├── ProjectPanel.tsx         # Debug JSON inspector
│   │   │   │   └── Toolbar.tsx              # Top bar with actions
│   │   │   ├── stores/
│   │   │   │   └── appStore.ts     # Zustand store (project, scene, chat state)
│   │   │   └── types/
│   │   │       ├── project.ts      # Mirrors backend models/project.py
│   │   │       ├── scene.ts        # Mirrors backend models/scene.py
│   │   │       └── api.ts          # Mirrors backend models/api.py
│   │   └── package.json
│   │
│   └── shared/                     # JSON Schema definitions (shared reference)
│       └── schemas/
│
└── CLAUDE.md                       # Project conventions for AI agents
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/projects` | Create a new project (returns default single-floor building) |
| `GET` | `/api/projects` | List all project IDs |
| `GET` | `/api/projects/{id}` | Get a project by ID |
| `POST` | `/api/projects/{id}/turn` | Send a user prompt — runs authoring workflow, returns updated project + compiled scene |
| `POST` | `/api/projects/{id}/compile` | Compile current project to scene (no LLM, deterministic only) |
| `GET` | `/health` | Health check |

## LangGraph Workflows

### WF1: Project Authoring

```
START → plan → agent_worker → validate → respond → END
              ↑                   │
              └── retry (on fail) ┘
```

- **plan**: Classifies user intent as `create`, `edit`, or `clarify`
- **agent_worker**: Coding-agent-style LLM call that reads current project + schema and produces updated JSON
- **validate**: Deterministic structural validation (duplicate IDs, positive heights, valid polygons)
- **respond**: Formats the assistant's reply summarizing changes

### WF2: Geometry Compilation

```
START → decompose → compile → agent_refine → assemble → END
```

- **decompose**: Splits project into compilable units (floor slabs, walls, openings)
- **compile**: Deterministic geometry generation — each element becomes a positioned box primitive
- **agent_refine**: Extension point for agent-assisted complex geometry (passthrough in MVP)
- **assemble**: Adds lights, auto-frames camera, produces final SceneJSON

## Extensibility

The system is designed for future extension without restructuring:

| Future Capability | Extension Point |
|-------------------|----------------|
| Swap LLM provider (Codex, Claude Code, etc.) | `CodingAgentProvider` interface in `services/agent_provider.py` |
| Rhino/Grasshopper integration | `SceneCompilerBase` — add a Rhino-backed compiler alongside the default |
| BIM/IFC export | New exporter consuming ProjectJSON (same source of truth) |
| Complex geometry (curves, custom roofs) | `agent_refine` node in WF2 |
| Persistent storage (SQLite, Redis) | `ProjectStore` interface in `storage/project_store.py` |
| Real-time streaming | WebSocket endpoint alongside existing REST |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Run the Backend

```bash
cd packages/backend
uv sync
uv run uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`.

### Run the Frontend

```bash
cd packages/frontend
npm install
npm run dev
```

The app will open at `http://localhost:5173`. Vite proxies `/api` requests to the backend automatically.

## Current Status

This is an MVP skeleton. What works end-to-end:

- Create a project via API (default 10x10m single-floor building)
- Deterministic scene compilation (floor slabs, walls, openings as box primitives with auto camera)
- Frontend renders compiled SceneJSON in a 3D viewer with orbit controls
- Chat UI sends prompts to the backend and displays responses
- Project inspector shows raw JSON for debugging

What remains:

- Wire `AnthropicAgentProvider` to real Claude API calls
- Connect the authoring graph's agent worker so `/turn` actually modifies the building
- WebSocket streaming for chat responses
- Roof geometry compilation (gable, hip)
- Tests

## License

See [LICENSE](LICENSE).
