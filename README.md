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
| **Frontend** | React 18, TypeScript, Vite, React Three Fiber, Zustand | Chat UI, 3D viewer, project inspector |
| **Project Author (WF1)** | LangGraph, OpenAI (default) or Anthropic via `CodingAgentProvider` | Generate and edit Project JSON from user prompts |
| **Scene Compiler (WF2)** | LangGraph, deterministic Python compiler | Convert validated Project JSON into render-ready Scene JSON |
| **Storage** | Local file system (MVP) | Persist projects as JSON files on disk |

### Key Design Rules

- **Project JSON** is the semantic source of truth — describes *what* the building is (floors, walls, rooms, openings), not how to render it.
- **Scene JSON** is a compiled artifact — positioned geometry primitives, materials, lights, and camera, ready for Three.js.
- The frontend **never** interprets Project JSON for rendering. It only consumes Scene JSON.
- Validation and geometry compilation are **deterministic** wherever possible.
- The LLM provider is **vendor-agnostic** — a single `CodingAgentProvider` interface abstracts all agent calls, selected via environment variable.

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

For detailed architecture documentation including file-by-file descriptions and call graphs, see **[packages/ARCHITECTURE.md](packages/ARCHITECTURE.md)**.

## Project Structure

```
JiZhongZhou/
├── start-backend.sh                # Start backend dev server
├── start-frontend.sh               # Start frontend dev server
├── packages/
│   ├── ARCHITECTURE.md             # Detailed architecture & call graph documentation
│   ├── backend/                    # Python — FastAPI + LangGraph + OpenAI
│   │   ├── .env.example            # Environment variable template
│   │   ├── pyproject.toml          # Python dependencies
│   │   ├── src/
│   │   │   ├── main.py             # App factory, dependency wiring
│   │   │   ├── api/routes.py       # REST endpoints
│   │   │   ├── models/             # Pydantic models (project, scene, state, api)
│   │   │   ├── graphs/             # LangGraph workflows (WF1, WF2)
│   │   │   ├── services/           # Agent provider, project service, scene service
│   │   │   ├── compiler/           # Deterministic geometry compilation
│   │   │   ├── validators/         # Project + scene validation
│   │   │   └── storage/            # File-based project persistence
│   │   └── data/projects/          # Persisted project JSON files
│   │
│   ├── frontend/                   # React + TypeScript + Vite
│   │   ├── src/
│   │   │   ├── App.tsx             # Root layout
│   │   │   ├── api/client.ts       # Typed fetch wrappers
│   │   │   ├── components/         # Chat, Viewer3D, ProjectPanel, Toolbar
│   │   │   ├── stores/appStore.ts  # Zustand state management
│   │   │   └── types/              # TypeScript types mirroring backend
│   │   └── package.json
│   │
│   └── shared/schemas/             # JSON Schema definitions (shared reference)
│
├── CLAUDE.md                       # Project conventions for AI agents
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/projects` | Create a new project (default single-floor building) |
| `GET` | `/api/projects` | List all project IDs |
| `GET` | `/api/projects/{id}` | Get a project by ID |
| `POST` | `/api/projects/{id}/turn` | Send a user prompt — runs WF1 then WF2, returns updated project + scene |
| `POST` | `/api/projects/{id}/compile` | Compile current project to scene via WF2 (deterministic, no LLM) |
| `GET` | `/health` | Health check |

## LangGraph Workflows

### WF1: Project Authoring

```
parse_request ──┬── "clarify" ──────────────────────────── respond → END
                └── "create"/"edit" → agent_worker → validate ─┬── pass → persist → respond → END
                                        ↑                      │
                                        └── retry (< 2 times) ─┘
                                                               └── fail → respond (errors) → END
```

### WF2: Geometry Compilation

```
START → decompose → compile → agent_refine → assemble → validate_scene → END
```

### AI Provider Selection

Provider is selected via environment variables through `create_agent_provider()`:

| `AI_PROVIDER` | Required env | Description |
|---------------|-------------|-------------|
| `openai` (default) | `OPENAI_API_KEY` | OpenAI Responses API, model configurable via `OPENAI_MODEL` |
| `anthropic` | `ANTHROPIC_API_KEY` | Anthropic Claude (stub, future implementation) |
| `mock` | none | No LLM — passes project through unchanged, for pipeline testing |

If `AI_PROVIDER=openai` but `OPENAI_API_KEY` is not set, falls back to mock automatically with a warning.

## Extensibility

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
- An OpenAI API key (for AI-powered editing; optional — mock mode works without it)

### Quick Start

```bash
# 1. Configure your API key
cp packages/backend/.env.example packages/backend/.env
# Edit packages/backend/.env and set OPENAI_API_KEY=sk-your-key-here

# 2. Terminal 1 — Backend
./start-backend.sh

# 3. Terminal 2 — Frontend
./start-frontend.sh
```

Or manually:

### Run the Backend

```bash
cd packages/backend
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY

uv sync
uv run uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`.

To run without an API key (mock mode, no AI):
```bash
AI_PROVIDER=mock uv run uvicorn src.main:app --reload
```

### Run the Frontend

```bash
cd packages/frontend
npm install
npm run dev
```

The app will open at `http://localhost:5173`. Vite proxies `/api` requests to the backend automatically.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `openai` | Which LLM provider to use: `openai`, `anthropic`, or `mock` |
| `OPENAI_API_KEY` | — | Your OpenAI API key (required when `AI_PROVIDER=openai`) |
| `OPENAI_MODEL` | `gpt-4.1` | OpenAI model to use |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (for future use) |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Anthropic model (for future use) |

## Current Status

What works end-to-end:

- Create a project via API (default 10x10m single-floor building)
- Full LangGraph pipeline: user prompt → WF1 (intent parsing, agent call, validation, persistence) → WF2 (decompose, compile, assemble, validate) → response
- OpenAI integration via Responses API (default provider for local dev)
- Automatic fallback to mock when API key is missing
- Clarification routing (questions skip the agent, return help text directly)
- Validation retry loop (up to 2 retries with error feedback to the agent)
- Deterministic scene compilation (floor slabs, walls, openings as box primitives with auto camera)
- Scene validation (structure checks, duplicate IDs, geometry completeness)
- Frontend renders compiled SceneJSON in a 3D viewer with orbit controls
- Chat UI sends prompts to the backend and displays responses
- Project inspector shows raw Project JSON and Scene JSON for debugging
- File-based project persistence (survives server restarts)

What remains:

- Implement `AnthropicAgentProvider` with real Anthropic API calls
- WebSocket streaming for chat responses
- Roof geometry compilation (gable, hip)
- Tests

## License

See [LICENSE](LICENSE).
