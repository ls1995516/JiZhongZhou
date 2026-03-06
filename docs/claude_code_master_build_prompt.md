# Claude Code Master Prompt — AI Building Authoring Studio

You are the lead engineer for an MVP called AI Building Authoring Studio.

We are NOT building a plain single-LLM app.
We are building a layered system where the user describes a building in chat, the system generates structured project JSON, a conversion layer compiles that JSON into renderable scene output, and the frontend visualizes the result in the browser.

Core concept:
chat -> project schema JSON -> render scene JSON / geometry output -> browser rendering

Target architecture:

1. Frontend layer
- React + TypeScript
- Chat interface
- 3D viewer
- Project/history panel
- Optional debug JSON inspector

2. Project authoring layer
- Implemented as a LangGraph workflow
- Responsible for generating and updating project schema JSON from user requests
- Must preserve project state and support incremental edits
- Must validate project JSON against a schema

3. Geometry compilation layer
- Implemented as a separate LangGraph workflow
- Responsible for converting validated project schema JSON into render-oriented output
- Output can be scene JSON, mesh JSON, or geometry code suitable for browser rendering
- Do NOT implement BIM/IFC export yet
- Do NOT require Rhino in v1, but keep extension points for Rhino/Grasshopper later

4. Rendering layer
- Frontend rendering in browser
- Use React Three Fiber
- Consume render-oriented scene data from backend
- Support orbit/pan/zoom and basic interaction if practical

Important design rules:
- Do NOT design this as a single LLM call.
- Maintain a clear separation between:
  a) user intent
  b) project schema JSON (semantic source of truth)
  c) render scene JSON / render artifacts (compiled output)
- Favor deterministic validation and compilation wherever possible.
- Use clean interfaces so model/provider implementations can be swapped later.
- Prefer practical engineering choices over research complexity.
- Favor a deterministic compiler over LLM-generated runtime behavior.

Tech stack:
- Frontend: React + TypeScript
- 3D rendering: React Three Fiber
- Backend: Python + FastAPI
- Orchestration: LangGraph
- Storage: simple local file/json storage for MVP
- No authentication unless necessary for basic separation
- No BIM export yet
- No Rhino dependency in v1 unless isolated behind interfaces

Product requirements:
1. The user interacts through a chat UI.
2. The system converts natural language building requests into a structured intermediate JSON format.
3. The backend validates and stores the JSON project state.
4. The frontend renders the building from JSON using simple primitives.
5. The system supports iterative updates such as:
   - "make the living room larger"
   - "add a second floor"
6. The system should preserve project state and support incremental edits, not full regeneration every time.
7. The architecture must be extensible later for:
   - Rhino / Grasshopper export
   - IFC / BIM metadata export
   - more advanced multi-agent workflows

The schema should eventually support:
- project metadata
- levels
- rooms
- slabs
- walls
- openings placeholder
- style metadata
- future extension hooks for BIM semantics

The initial render layer should support:
- slabs
- room boxes
- walls
- labels

Your workflow must be done in phases.

---

## Phase 1 — Architecture and Design Only

Deliver Phase 1 only.

What I want:
1. Propose the full architecture
2. Propose the monorepo structure
3. Define the boundaries between the four layers
4. Define the shared types/interfaces
5. Define the project schema JSON structure
6. Define the render scene JSON structure
7. Define the two LangGraph workflows at a high level
8. Explain how project state is persisted across turns
9. Explain assumptions, non-goals, and MVP limitations

Important:
- Do not generate full implementation code yet.
- Keep the design minimal and MVP-friendly.
- Stop after Phase 1.

---

## Phase 2 — Backend Skeleton

After completing Phase 1, proceed to Phase 2 only.

Generate the backend skeleton in Python using FastAPI.

Requirements:
- Create API endpoints for:
  - create project
  - get project
  - update project from user prompt
  - compile render scene
- Create pydantic models for:
  - project schema JSON
  - render scene JSON
  - graph state
- Create folders for:
  - api
  - graphs
  - models
  - services
  - validators
  - storage
  - compiler
- Stub two LangGraph workflows:
  - project_authoring_graph
  - geometry_compilation_graph
- Add clear interfaces for:
  - AgentProvider or ModelProvider
  - ProjectValidator
  - SceneCompiler
  - ProjectStore
- Use simple local file persistence for MVP
- Do not generate frontend code in this phase

At the end of Phase 2, explain:
- what files were created
- why each file exists
- what still remains to implement

Stop after Phase 2.

---

## Phase 3 — Frontend Skeleton

After completing Phase 2, proceed to Phase 3 only.

Generate the frontend skeleton in React + TypeScript.

Requirements:
- Create a layout with:
  - left chat panel
  - right 3D viewer
  - optional side panel for project/schema inspection
- Create a simple API client for backend endpoints
- Create frontend types matching backend response shapes
- Render a placeholder scene using React Three Fiber
- Add support for loading render scene JSON from the backend
- Keep styling simple and clean
- Do not add authentication
- Do not add advanced UI libraries unless necessary

At the end of Phase 3, explain:
- which files were created
- how chat connects to backend
- how viewer consumes render scene data

Stop after Phase 3.

---

## Phase 4 — LangGraph Workflows

After completing Phase 3, proceed to Phase 4 only.

Implement the minimal LangGraph workflows.

Workflow A: project_authoring_graph
- input: current project state + user prompt
- steps:
  - parse request
  - generate or update project schema JSON
  - validate project schema JSON
  - persist project schema JSON
- output: updated project schema JSON

Workflow B: geometry_compilation_graph
- input: validated project schema JSON
- steps:
  - compile project schema JSON into render scene JSON
  - validate render scene JSON
- output: render scene JSON

Important:
- Do not hardcode a specific vendor deeply into graph logic
- Use abstractions/interfaces
- Keep implementation simple and readable
- Add TODO comments where real providers can be integrated later

At the end of Phase 4, explain:
- graph flow
- state transitions
- files added or changed
- what is still mocked or simplified

Stop after Phase 4.

---

## Phase 5 — Local Run, Integration, and UI Verification

After completing Phase 4, proceed to Phase 5 only.

Goal:
Get the app into a state where I can run both backend and frontend locally, open the webpage, send a sample building prompt, and see a rendered result in the browser.

Tasks:
1. Inspect the repo and determine what is still missing to run locally.
2. Add or fix all required setup files and wiring, including:
   - package.json scripts
   - Python requirements / pyproject if missing
   - environment variable examples
   - startup commands
   - CORS setup
   - API base URL config
   - frontend-backend integration issues
   - missing imports / broken types / broken routes
   - placeholder/mock provider implementations if real model providers are not configured yet
3. Make the app runnable in a fully local MVP mode, even if AI parts are mocked.
4. Ensure there is a deterministic demo path:
   - a sample user prompt
   - a sample generated project schema JSON
   - a sample compiled render scene JSON
   - a visible 3D result in the UI
5. Add seed/demo logic if needed so I can test without real model credentials.
6. Add clear developer scripts to run backend and frontend.
7. Add a short README section with exact local run steps.
8. Add a basic smoke test checklist for manual verification.

Testing expectations:
Please make sure the code supports this flow:
1. Start backend
2. Start frontend
3. Open the app
4. Enter a sample prompt like:
   "Create a one-story modern house with a living room, kitchen, and two bedrooms"
5. Backend returns project schema JSON
6. Geometry compilation produces render scene JSON
7. Frontend renders slabs / room boxes / walls in the viewer

Deliverables for Phase 5:
1. A list of all code changes made
2. Any new files created
3. Exact run commands
4. Exact test steps for use in the browser
5. Any known limitations still remaining

Important:
- Prioritize a working vertical slice over architectural perfection.
- Do not redesign the whole system.
- Fix the minimum necessary issues to make the app runnable and testable.
- Keep mock paths clearly separated so they can be replaced later.

Stop after Phase 5.


We have already completed the 5 implementation phases.

Now move to the next stage: verify the project runs locally and fix any remaining issues so I can test it through the UI.

Your goal:
Get the app into a state where I can start backend and frontend, open the webpage, send a sample building prompt, and see a rendered result in the browser.

Tasks:
1. Inspect the current codebase and identify what is still missing or broken.
2. Fix any local runtime, wiring, config, or integration issues.
3. Make sure a no-credentials demo path exists if no model key is configured.
4. Verify the end-to-end flow:
   - prompt -> project schema JSON
   - project schema -> render scene JSON
   - viewer renders result
5. Update README with exact local run steps.
6. Provide exact commands and browser test steps.

At the end, provide:
- files changed
- run commands
- env vars needed
- browser test steps
- remaining limitations


The current provider implementation is blocked because I do not have an Anthropic API token.

Please switch the default AI provider to OpenAI for the local MVP/demo path.

Requirements:
1. Implement a new OpenAIAgentProvider that can be used in place of AnthropicAgentProvider.
2. Use the current OpenAI Responses API, not a legacy-only integration.
3. Make OpenAI the default provider for local development.
4. Keep the provider abstraction intact so Anthropic can be added back later.
5. Preserve the existing pipeline and interfaces.

Implementation requirements:
- Add an OpenAIAgentProvider.invoke() implementation.
- Read the API key from OPENAI_API_KEY.
- Use a configurable model name with a sensible default.
- Return the same AgentResult shape expected by the rest of the app.
- Extract structured JSON from the model response and validate it before returning.
- If the project already has a provider factory or DI setup, wire OpenAI into that instead of hardcoding it.
- If needed, add a mock/fallback path when the OpenAI key is missing.

Please also:
1. Update .env.example
2. Update any config/provider selection logic
3. Update README run instructions to mention OPENAI_API_KEY
4. Verify the existing end-to-end demo still works

At the end, provide:
- files changed
- env vars needed
- exact run commands
- remaining limitations

