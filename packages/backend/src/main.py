"""FastAPI application entry point."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import create_router
from .compiler.scene_compiler import DefaultSceneCompiler
from .graphs.geometry_compilation import build_geometry_compilation_graph
from .graphs.project_authoring import build_project_authoring_graph
from .services.agent_provider import create_agent_provider
from .services.project_service import ProjectService
from .services.reference_service import ReferenceService
from .services.scene_service import SceneService
from .storage.project_store import FileProjectStore
from .storage.reference_store import FileReferenceStore
from .validators.project_validator import DefaultProjectValidator
from .validators.scene_validator import DefaultSceneValidator

logging.basicConfig(level=logging.INFO)

PROJECTS_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "projects"
REFERENCES_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "references"


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Building Authoring Studio",
        version="0.1.0",
        description="Backend API for the AI Building Authoring Studio MVP",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Dependency wiring ---
    store = FileProjectStore(base_dir=PROJECTS_DATA_DIR)
    reference_store = FileReferenceStore(base_dir=REFERENCES_DATA_DIR)
    project_validator = DefaultProjectValidator()
    scene_validator = DefaultSceneValidator()
    compiler = DefaultSceneCompiler()

    # Agent provider — selected via AI_PROVIDER env var.
    # Defaults to OpenAI if OPENAI_API_KEY is set, otherwise falls back to mock.
    # See .env.example for configuration options.
    agent = create_agent_provider()

    project_service = ProjectService(store=store, validator=project_validator)
    reference_service = ReferenceService(store=reference_store, project_service=project_service)
    scene_service = SceneService(compiler=compiler)

    # --- Build LangGraph workflows ---
    authoring_graph = build_project_authoring_graph(
        agent=agent,
        validator=project_validator,
        store=store,
    )
    compilation_graph = build_geometry_compilation_graph(
        agent=agent,
        scene_validator=scene_validator,
    )

    # --- Routes ---
    router = create_router(
        project_service=project_service,
        reference_service=reference_service,
        scene_service=scene_service,
        authoring_graph=authoring_graph,
        compilation_graph=compilation_graph,
    )
    app.include_router(router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
