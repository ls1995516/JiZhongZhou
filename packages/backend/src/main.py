"""FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import create_router
from .compiler.scene_compiler import DefaultSceneCompiler
from .services.project_service import ProjectService
from .services.scene_service import SceneService
from .storage.project_store import FileProjectStore
from .validators.project_validator import DefaultProjectValidator

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "projects"


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
    store = FileProjectStore(base_dir=DATA_DIR)
    validator = DefaultProjectValidator()
    compiler = DefaultSceneCompiler()

    project_service = ProjectService(store=store, validator=validator)
    scene_service = SceneService(compiler=compiler)

    router = create_router(project_service, scene_service)
    app.include_router(router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
