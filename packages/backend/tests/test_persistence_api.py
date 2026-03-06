from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import create_router
from src.compiler.scene_compiler import DefaultSceneCompiler
from src.models.reference import ReferenceMetadata
from src.models.scene import SceneJSON
from src.services.project_service import ProjectService
from src.services.reference_service import ReferenceService
from src.services.scene_service import SceneService
from src.storage.project_store import FileProjectStore
from src.storage.reference_store import FileReferenceStore
from src.validators.project_validator import DefaultProjectValidator


class StubGraph:
    async def ainvoke(self, _: dict) -> dict:
        raise AssertionError("This test should not invoke the graph")


def create_test_client(tmp_path) -> TestClient:
    app = FastAPI()
    store = FileProjectStore(tmp_path / "projects")
    reference_store = FileReferenceStore(tmp_path / "references")
    project_service = ProjectService(store=store, validator=DefaultProjectValidator())
    reference_service = ReferenceService(store=reference_store, project_service=project_service)
    scene_service = SceneService(compiler=DefaultSceneCompiler())
    router = create_router(
        project_service=project_service,
        reference_service=reference_service,
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


def test_reference_routes_list_get_and_load_into_workspace(tmp_path) -> None:
    client = create_test_client(tmp_path)

    create_res = client.post("/api/projects", json={"name": "Source Project"})
    assert create_res.status_code == 200
    source_project = create_res.json()["project"]

    create_reference_res = client.post(
        "/api/references",
        json={
            "metadata": ReferenceMetadata(
                id="starter-reference",
                title="Starter Reference",
                description="A curated starter layout.",
                tags=["starter", "residential"],
                created_by="tester",
                updated_by="tester",
                version="1.0.0",
            ).model_dump(mode="json"),
            "source_project_id": source_project["id"],
        },
    )
    assert create_reference_res.status_code == 200

    list_res = client.get("/api/references")
    assert list_res.status_code == 200
    list_payload = list_res.json()
    assert len(list_payload) == 1
    assert list_payload[0]["id"] == "starter-reference"

    get_res = client.get("/api/references/starter-reference")
    assert get_res.status_code == 200
    get_payload = get_res.json()
    assert get_payload["metadata"]["title"] == "Starter Reference"

    load_res = client.post("/api/references/starter-reference/load")
    assert load_res.status_code == 200
    loaded_project = load_res.json()["project"]
    assert loaded_project["id"] != source_project["id"]
    assert loaded_project["metadata"]["name"] == source_project["metadata"]["name"]
