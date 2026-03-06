from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import create_router
from src.compiler.scene_compiler import DefaultSceneCompiler
from src.models.scene import SceneJSON
from src.services.project_service import ProjectService
from src.services.scene_service import SceneService
from src.storage.project_store import FileProjectStore
from src.validators.project_validator import DefaultProjectValidator


class StubGraph:
    async def ainvoke(self, _: dict) -> dict:
        raise AssertionError("This test should not invoke the graph")


def create_test_client(tmp_path) -> TestClient:
    app = FastAPI()
    store = FileProjectStore(tmp_path / "projects")
    project_service = ProjectService(store=store, validator=DefaultProjectValidator())
    scene_service = SceneService(compiler=DefaultSceneCompiler())
    router = create_router(
        project_service=project_service,
        scene_service=scene_service,
        authoring_graph=StubGraph(),
        compilation_graph=StubGraph(),
    )
    app.include_router(router)
    return TestClient(app)


def test_save_and_load_project_bundle_via_api(tmp_path) -> None:
    client = create_test_client(tmp_path)

    create_res = client.post("/api/projects", json={"name": "Persisted Project"})
    assert create_res.status_code == 200
    project = create_res.json()["project"]
    project_id = project["id"]

    scene = SceneJSON(metadata={"source_project_id": project_id}).model_dump(mode="json")
    save_res = client.post(
        f"/api/projects/{project_id}/save",
        json={"project": project, "scene": scene},
    )
    assert save_res.status_code == 200
    save_payload = save_res.json()
    assert save_payload["metadata"]["project_id"] == project_id
    assert save_payload["metadata"]["has_render_scene"] is True
    assert save_payload["scene"]["metadata"]["source_project_id"] == project_id

    get_res = client.get(f"/api/projects/{project_id}")
    assert get_res.status_code == 200
    get_payload = get_res.json()
    assert get_payload["project"]["id"] == project_id
    assert get_payload["scene"]["metadata"]["source_project_id"] == project_id

    list_res = client.get("/api/projects")
    assert list_res.status_code == 200
    list_payload = list_res.json()
    assert len(list_payload) == 1
    assert list_payload[0]["project_id"] == project_id
