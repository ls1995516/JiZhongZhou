# Architecture Documentation

This document describes every file in the system, what it does, and how components call each other.

## End-to-End Request Flow

When a user sends a chat message, this is the complete call chain:

```
Frontend                          Backend
────────                          ───────
Chat.tsx
  └→ appStore.sendMessage(text)
       └→ api/client.ts: sendTurn(projectId, {prompt})
            │
            │  POST /api/projects/{id}/turn
            ▼
            routes.py: update_project()
              ├→ project_service.get_project(id)     ← loads from FileProjectStore
              │    └→ project_store.load(id)          ← reads data/projects/{id}.json
              │
              ├→ WF1: authoring_graph.ainvoke(state)  ← LangGraph workflow
              │    ├→ parse_request()                  ← classify intent
              │    ├→ agent_worker()                   ← calls CodingAgentProvider.invoke()
              │    │    └→ OpenAIAgentProvider          ← sends to OpenAI Responses API
              │    │         └→ _extract_json_from_text()  ← parses JSON from LLM response
              │    ├→ validate()                        ← DefaultProjectValidator.validate()
              │    ├→ persist()                         ← FileProjectStore.save()
              │    └→ respond()                         ← format assistant message
              │
              ├→ WF2: compilation_graph.ainvoke(state) ← LangGraph workflow
              │    ├→ decompose()                       ← split project into CompileUnits
              │    ├→ compile()                         ← deterministic geometry generation
              │    │    ├→ compile_floor_slab()          ← geometry.py
              │    │    ├→ compile_wall()                ← geometry.py
              │    │    └→ compile_opening()             ← geometry.py
              │    ├→ agent_refine()                     ← passthrough (extension point)
              │    ├→ assemble()                         ← add lights + auto-frame camera
              │    └→ validate_scene()                   ← DefaultSceneValidator.validate()
              │
              └→ return TurnResponse(message, project, scene)
                   │
                   ▼
       appStore receives response
         ├→ updates messages[]
         ├→ updates project (ProjectJSON)
         └→ updates scene (SceneJSON)
              │
              ▼
       Viewer3D.tsx re-renders
         └→ SceneObjectRenderer.tsx
              └→ maps SceneObject tree → <mesh> / <group> R3F elements
```

## Backend File Reference

### Entry Point

#### `src/main.py`
**App factory.** Creates the FastAPI app and wires all dependencies together.

- Creates `FileProjectStore`, validators, compiler, and agent provider
- Agent provider is selected by `create_agent_provider()` based on `AI_PROVIDER` env var
- Builds both LangGraph workflows, injecting dependencies into each
- Creates the API router, passing in services and compiled graphs
- Configures CORS middleware

**Calls:** `create_agent_provider()`, `build_project_authoring_graph()`, `build_geometry_compilation_graph()`, `create_router()`

---

### API Layer (`src/api/`)

#### `api/routes.py`
**REST endpoint definitions.** Factory function `create_router()` takes injected dependencies and returns an `APIRouter`.

Endpoints:
- `POST /api/projects` → calls `project_service.create_project()`
- `GET /api/projects/{id}` → calls `project_service.get_project()`
- `GET /api/projects` → calls `project_service.list_projects()`
- `POST /api/projects/{id}/turn` → orchestrates WF1 then WF2 (see flow above)
- `POST /api/projects/{id}/compile` → runs WF2 only (no LLM, deterministic)

**Called by:** FastAPI (HTTP requests)
**Calls:** `ProjectService`, `authoring_graph.ainvoke()`, `compilation_graph.ainvoke()`

---

### Models (`src/models/`)

All models are Pydantic v2 `BaseModel` subclasses. They define the data shapes used throughout the system.

#### `models/project.py`
**Project JSON schema** — the semantic source of truth for a building.

Key types:
- `ProjectJSON` — top-level document with `id`, `metadata`, `site`, `building`
- `BuildingInfo` — contains `floors[]` and `roof_type`
- `Floor` — `id`, `elevation`, `height`, `outline` (Polygon), `walls[]`, `rooms[]`
- `Wall` — `id`, `start`/`end` (Vector2), `thickness`, `openings[]`
- `Opening` — `id`, `type` (door/window), `position` (0-1 normalized), `width`, `height`
- `Room` — `id`, `label`, `outline`, `function`
- `Vector2`, `Vector3`, `Polygon` — geometric primitives

**Used by:** everything (this is the core data model)

#### `models/scene.py`
**Render scene schema** — geometry-oriented output for the 3D viewer.

Key types:
- `SceneJSON` — top-level with `scene` (SceneData) and `metadata`
- `SceneData` — `objects[]`, `lights[]`, `camera`
- `SceneObject` — `id`, `type` (mesh/group), `geometry`, `material`, `transform`, `children[]`, `source_id`
- `Geometry` — `primitive` (box/cylinder/extrusion/custom), `params`, optional `vertices`/`indices`
- `Material` — `color`, `opacity`, `metalness`, `roughness`
- `Transform` — `position`, `rotation`, `scale` (all 3-tuples)
- `Light` — `type` (ambient/directional/point), `color`, `intensity`, `position`
- `Camera` — `position`, `target`, `fov`

**Used by:** compiler, WF2 graph, routes, frontend

#### `models/state.py`
**LangGraph workflow state definitions.**

- `ProjectAuthoringState` — state for WF1: `user_prompt`, `project`, `plan`, `updated_project`, `validation_errors`, `retry_count`, `response_text`
- `GeometryCompilationState` — state for WF2: `project`, `compile_units[]`, `scene`, `validation_errors`
- `CompileUnit` — a single element to compile: `element_type`, `element_id`, `data`
- `AuthorPlan` — enum: `create`, `edit`, `clarify`

**Used by:** graph node functions, routes

#### `models/api.py`
**Request/response models** for the REST API.

- `CreateProjectRequest` — `name`, `description?`
- `UpdateProjectRequest` — `prompt` (user's natural language)
- `ProjectResponse` — wraps `ProjectJSON`
- `SceneResponse` — wraps `SceneJSON`
- `TurnResponse` — `assistant_message` + `project` + `scene`

**Used by:** routes

---

### Graphs (`src/graphs/`)

#### `graphs/project_authoring.py`
**WF1: Project Authoring LangGraph workflow.**

Graph: `parse_request → agent_worker → validate → persist → respond`

`build_project_authoring_graph(agent, validator, store)` takes injected dependencies and returns a compiled graph.

`make_nodes(agent, validator, store)` creates node functions as closures:

| Node | What it does | Calls |
|------|-------------|-------|
| `parse_request` | Classifies user intent as create/edit/clarify via keyword heuristic | — |
| `agent_worker` | Builds system prompt with schema + current project, calls `CodingAgentProvider.invoke()`, parses JSON result into `ProjectJSON` | `CodingAgentProvider.invoke()` |
| `validate` | Runs deterministic validation on updated project | `ProjectValidator.validate()` |
| `persist` | Saves validated project to disk | `ProjectStore.save()` |
| `respond` | Formats the assistant's response text | — |

Routing:
- After `parse_request`: if `clarify` → skip to `respond`; else → `agent_worker`
- After `validate`: if errors and retries < 2 → back to `agent_worker`; if errors exhausted → `respond`; if pass → `persist`

Also defines `PROJECT_AUTHOR_SYSTEM_PROMPT` — the template sent to the LLM with schema summary and current project.

**Called by:** `routes.py` via `authoring_graph.ainvoke()`
**Calls:** `CodingAgentProvider`, `ProjectValidator`, `ProjectStore`

#### `graphs/geometry_compilation.py`
**WF2: Geometry Compilation LangGraph workflow.**

Graph: `decompose → compile → agent_refine → assemble → validate_scene`

`build_geometry_compilation_graph(agent, scene_validator)` takes injected dependencies and returns a compiled graph.

`make_nodes(agent, scene_validator)` creates node functions as closures:

| Node | What it does | Calls |
|------|-------------|-------|
| `decompose` | Iterates project floors/walls/openings, creates `CompileUnit` list | — |
| `compile` | For each unit, calls the appropriate geometry function, groups results by floor | `compile_floor_slab()`, `compile_wall()`, `compile_opening()` |
| `agent_refine` | Passthrough in MVP. Extension point for agent-generated custom geometry. | (future: `CodingAgentProvider.invoke()`) |
| `assemble` | Adds default lights, computes camera position from project bounding box | `_compute_camera()` |
| `validate_scene` | Runs structural checks on final scene | `SceneValidator.validate()` |

**Called by:** `routes.py` via `compilation_graph.ainvoke()`
**Calls:** `compiler/geometry.py` functions, `SceneValidator`

---

### Services (`src/services/`)

#### `services/agent_provider.py`
**LLM provider abstraction** — the swap point for AI backends.

Classes:
- `CodingAgentProvider` (ABC) — defines `invoke(system_prompt, user_request, context) → AgentResult`
- `OpenAIAgentProvider` — uses the OpenAI Responses API (`client.responses.create()`). Reads `OPENAI_API_KEY` from env. Extracts JSON from response via `_extract_json_from_text()`.
- `AnthropicAgentProvider` — stub that passes project through unchanged
- `MockAgentProvider` — passes project through unchanged, no LLM call

Factory:
- `create_agent_provider()` — reads `AI_PROVIDER` env var, instantiates the appropriate provider. Falls back to mock if API key is missing.

Helper:
- `_extract_json_from_text(text)` — extracts JSON from LLM output. Tries: fenced code blocks → raw JSON → outermost `{...}` block.

Data:
- `AgentResult` — `raw_text` (explanation) + `json_output` (parsed dict or None)

**Called by:** WF1 `agent_worker` node, `main.py` factory
**Calls:** OpenAI SDK (`AsyncOpenAI.responses.create`)

#### `services/project_service.py`
**Project CRUD orchestration.**

- `create_project(name)` — creates a default project with one 10x10m floor, validates, saves
- `get_project(id)` → loads from store
- `save_project(project)` → validates then saves
- `list_projects()` → lists all IDs

**Called by:** `routes.py`
**Calls:** `ProjectStore`, `ProjectValidator`

#### `services/scene_service.py`
**Scene compilation orchestration.** Thin wrapper around `SceneCompilerBase`.

- `compile(project)` → delegates to `DefaultSceneCompiler.compile()`

**Called by:** (available but `/compile` endpoint now uses WF2 graph instead)
**Calls:** `SceneCompilerBase.compile()`

---

### Compiler (`src/compiler/`)

#### `compiler/scene_compiler.py`
**SceneCompiler interface + default implementation.**

- `SceneCompilerBase` (ABC) — defines `compile(project) → SceneJSON`
- `DefaultSceneCompiler` — iterates floors, generates floor slabs + walls + openings, adds lights, auto-frames camera

**Called by:** `SceneService`, (also duplicated logic in WF2 for graph-based path)
**Calls:** `geometry.py` functions

#### `compiler/geometry.py`
**Pure geometry generation functions.** Each takes project elements and returns a `SceneObject`.

- `compile_floor_slab(floor)` — creates a thin box at the floor's elevation, sized to bounding box of outline
- `compile_wall(wall, floor)` — creates a box along the wall line, positioned at midpoint, rotated to match angle
- `compile_opening(opening, wall, floor)` — creates a box for door/window, positioned along the wall, colored by type (blue glass for windows, brown for doors)

Helper functions:
- `_wall_length(wall)` — Euclidean distance between start and end
- `_wall_angle(wall)` — angle in radians via `atan2`

**Called by:** `scene_compiler.py`, WF2 `compile` node
**Calls:** — (pure functions, no dependencies)

#### `compiler/materials.py`
**Default material palette.** Maps semantic types to PBR materials.

- `DEFAULT_MATERIALS` dict — floor-slab (gray), wall (light gray), window (blue translucent), door (brown), roof (rust), ground (green)
- `get_material(semantic_type)` — lookup with gray fallback

**Called by:** (available for use, not yet wired into main compilation path)

#### `compiler/transforms.py`
**Spatial transform utilities.**

- `translate(transform, dx, dy, dz)` — offset a Transform's position
- `rotate_y(transform, angle)` — add rotation around Y axis
- `degrees_to_radians(deg)` — conversion helper

**Called by:** (available for use in custom geometry)

---

### Validators (`src/validators/`)

#### `validators/project_validator.py`
**Deterministic project validation** beyond Pydantic's type checking.

- `ProjectValidator` (ABC) — defines `validate(project) → list[str]`
- `DefaultProjectValidator` — checks:
  - Building has at least one floor
  - No duplicate floor IDs
  - Floor height is positive
  - Outline has >= 3 points
  - No duplicate wall IDs within a floor
  - Wall start != end
  - Opening positions in [0, 1]

**Called by:** WF1 `validate` node, `ProjectService`

#### `validators/scene_validator.py`
**Deterministic scene validation.**

- `SceneValidator` (ABC) — defines `validate(scene) → list[str]`
- `DefaultSceneValidator` — checks:
  - Scene has at least one object
  - No duplicate object IDs (recursive)
  - Mesh objects have geometry
  - Scene has lights

**Called by:** WF2 `validate_scene` node

---

### Storage (`src/storage/`)

#### `storage/project_store.py`
**Project persistence — abstract interface + file implementation.**

- `ProjectStore` (ABC) — defines `save()`, `load()`, `delete()`, `list_ids()`
- `FileProjectStore` — stores each project as `data/projects/{id}.json`. Uses Pydantic's `model_dump_json()` / `model_validate_json()` for serialization.

**Called by:** `ProjectService`, WF1 `persist` node

---

## Frontend File Reference

### Entry

#### `src/main.tsx`
React root mount. Renders `<App />` inside `<StrictMode>`.

#### `src/App.tsx`
**Root layout.** Renders `<Toolbar>` at the top, then a 3-column body: `<Chat>` | `<Viewer3D>` | `<ProjectPanel>` (if inspector is open).

**Calls:** all component imports, `useAppStore`

#### `src/index.css`
**Dark theme styles.** CSS custom properties for colors, layout grid for the 3-column body, chat message bubbles, toolbar buttons, inspector panel. No CSS framework.

### API Client (`src/api/`)

#### `api/client.ts`
**Typed fetch wrappers** for all backend endpoints.

- `createProject(req)` → `POST /api/projects`
- `getProject(id)` → `GET /api/projects/{id}`
- `listProjects()` → `GET /api/projects`
- `sendTurn(projectId, req)` → `POST /api/projects/{id}/turn`
- `compileScene(projectId)` → `POST /api/projects/{id}/compile`

Internal `request<T>()` helper handles JSON headers and error checking. Vite proxy forwards `/api` to `localhost:8000`.

**Called by:** `appStore.ts`

### State (`src/stores/`)

#### `stores/appStore.ts`
**Zustand store** — single source of truth for frontend state.

State:
- `projectId`, `project` (ProjectJSON), `scene` (SceneJSON)
- `messages[]` (ChatMessage), `isSending`
- `showInspector`

Actions:
- `createProject(name)` → calls `api.createProject()` + `api.compileScene()`, sets initial assistant message
- `loadProject(id)` → calls `api.getProject()` + `api.compileScene()`
- `sendMessage(text)` → adds user message, calls `api.sendTurn()`, adds assistant response, updates project + scene
- `compileScene()` → calls `api.compileScene()`, updates scene
- `toggleInspector()` → toggles debug panel

**Called by:** all components via `useAppStore(selector)`
**Calls:** `api/client.ts`

### Components (`src/components/`)

#### `components/Chat.tsx`
**Chat panel.** Displays message history with role-based styling (user messages right-aligned, assistant left-aligned). Form input with submit handler that calls `appStore.sendMessage()`. Auto-scrolls to bottom on new messages. Shows "Thinking..." indicator during `isSending`.

**Calls:** `useAppStore` (messages, isSending, sendMessage)

#### `components/Viewer3D.tsx`
**3D viewer.** Wraps a React Three Fiber `<Canvas>` component.

- Reads `scene` from store
- Renders lights from `scene.scene.lights` (ambient, directional, point)
- Renders a ground `<Grid>` via drei
- Maps `scene.scene.objects` → `<SceneObjectRenderer>` for each root object
- Sets camera from `scene.scene.camera` (position, fov, target)
- Adds `<OrbitControls>` for pan/zoom/rotate
- Shows a wireframe placeholder box when no scene is loaded

**Calls:** `useAppStore` (scene), `SceneObjectRenderer`

#### `components/SceneObjectRenderer.tsx`
**Recursive scene tree renderer.** Takes a `SceneObject` and renders it as R3F elements.

- If `type === "group"`: renders `<group>` with position/rotation/scale, recursively renders children
- If `type === "mesh"`: renders `<mesh>` with:
  - Geometry via `<PrimitiveGeometry>` — maps `primitive` to `<boxGeometry>`, `<cylinderGeometry>`, etc.
  - Material via `<meshStandardMaterial>` with color, opacity, metalness, roughness
  - Transform via position/rotation/scale props

**Called by:** `Viewer3D.tsx` (and recursively by itself for nested groups)

#### `components/ProjectPanel.tsx`
**Debug inspector.** Displays raw `project` and `scene` JSON in `<pre>` blocks with monospace formatting. Only visible when `showInspector` is true.

**Calls:** `useAppStore` (project, scene, showInspector)

#### `components/Toolbar.tsx`
**Top bar.** Shows app title, current project name, "New Project" button (prompts for name via `window.prompt`), and "Show/Hide Inspector" toggle.

**Calls:** `useAppStore` (projectId, project, showInspector, toggleInspector, createProject)

### Types (`src/types/`)

TypeScript interfaces mirroring backend Pydantic models. These are consumed by the API client, store, and components.

#### `types/project.ts`
Mirrors `models/project.py`: `ProjectJSON`, `Floor`, `Wall`, `Opening`, `Room`, `BuildingInfo`, `SiteInfo`, `ProjectMetadata`, `Vector2`, `Polygon`, etc.

#### `types/scene.ts`
Mirrors `models/scene.py`: `SceneJSON`, `SceneObject`, `Geometry`, `Material`, `Transform`, `SceneLight`, `SceneCamera`, `SceneData`, etc.

#### `types/api.ts`
Mirrors `models/api.py`: `CreateProjectRequest`, `UpdateProjectRequest`, `ProjectResponse`, `SceneResponse`, `TurnResponse`.

#### `types/index.ts`
Re-exports all types from the three type files.

---

## Dependency Injection Map

All major components are wired via constructor/factory injection in `main.py`:

```
main.py
  │
  ├→ FileProjectStore(base_dir)
  ├→ DefaultProjectValidator()
  ├→ DefaultSceneValidator()
  ├→ DefaultSceneCompiler()
  ├→ create_agent_provider()          ← reads AI_PROVIDER env var
  │    └→ OpenAIAgentProvider         ← or MockAgentProvider / AnthropicAgentProvider
  │
  ├→ ProjectService(store, validator)
  ├→ SceneService(compiler)
  │
  ├→ build_project_authoring_graph(agent, validator, store)
  │    └→ make_nodes(agent, validator, store)  ← closures capture dependencies
  │
  ├→ build_geometry_compilation_graph(agent, scene_validator)
  │    └→ make_nodes(agent, scene_validator)
  │
  └→ create_router(project_service, scene_service, authoring_graph, compilation_graph)
```

No global state. Every dependency is explicitly passed. To swap any component (e.g., a Redis-backed store, a different LLM, a Rhino-based compiler), change one line in `main.py`.

---

## Data Flow Diagram

```
                    ┌─────────────┐
                    │   User Chat  │
                    └──────┬──────┘
                           │ prompt (string)
                           ▼
                    ┌─────────────┐
                    │  WF1: Author │
                    │  LangGraph   │
                    └──────┬──────┘
                           │ ProjectJSON (validated, persisted)
                           ▼
                    ┌─────────────┐
                    │  WF2: Compile│
                    │  LangGraph   │
                    └──────┬──────┘
                           │ SceneJSON (geometry, lights, camera)
                           ▼
                    ┌─────────────┐
                    │  Frontend    │
                    │  R3F Viewer  │
                    └─────────────┘

  ProjectJSON                          SceneJSON
  (semantic)                           (render)
  ─────────────                        ──────────
  floors[]:                            objects[]:
    outline, walls, rooms                groups → meshes
  walls[]:                             geometry:
    start, end, openings                 box/cylinder primitives
  openings[]:                          materials:
    type, position, size                 color, opacity, PBR
                                       lights[], camera
        │                                   │
        │         NEVER crosses             │
        └─────── this boundary ─────────────┘
                  directly
```

The frontend renders SceneJSON only. ProjectJSON is shown in the inspector panel for debugging but never interpreted for 3D rendering.
