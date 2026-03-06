from __future__ import annotations

from src.models.project import (
    BuildingInfo,
    Floor,
    Polygon,
    ProjectJSON,
    ProjectMetadata,
    Vector2,
)
from src.models.scene import SceneJSON
from src.storage.project_store import FileProjectStore


def make_project(project_id: str = "project-1") -> ProjectJSON:
    return ProjectJSON(
        id=project_id,
        metadata=ProjectMetadata(name="Test Project"),
        building=BuildingInfo(
            floors=[
                Floor(
                    id="floor-1",
                    label="Ground Floor",
                    elevation=0,
                    height=3,
                    outline=Polygon(
                        points=[
                            Vector2(x=0, y=0),
                            Vector2(x=10, y=0),
                            Vector2(x=10, y=10),
                        ]
                    ),
                )
            ]
        ),
    )


async def test_file_project_store_persists_project_scene_and_metadata(tmp_path) -> None:
    store = FileProjectStore(tmp_path / "projects")
    project = make_project()
    scene = SceneJSON(metadata={"source_project_id": project.id})

    await store.save_bundle(project, scene)

    project_dir = tmp_path / "projects" / project.id
    assert (project_dir / "project_schema.json").exists()
    assert (project_dir / "render_scene.json").exists()
    assert (project_dir / "metadata.json").exists()
    assert (project_dir / "history.json").exists()

    record = await store.load_bundle(project.id)
    assert record is not None
    assert record.project.id == project.id
    assert record.scene is not None
    assert record.scene.metadata["source_project_id"] == project.id
    assert record.metadata["has_render_scene"] is True
    assert len(record.history) == 1

    summaries = await store.list_projects()
    assert len(summaries) == 1
    assert summaries[0].project_id == project.id
    assert summaries[0].has_render_scene is True
