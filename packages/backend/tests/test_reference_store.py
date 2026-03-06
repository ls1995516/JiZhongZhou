from __future__ import annotations

from src.models.reference import ReferenceMetadata
from src.storage.reference_store import FileReferenceStore

from .test_project_store import make_project


async def test_file_reference_store_persists_metadata_and_project_schema(tmp_path) -> None:
    store = FileReferenceStore(tmp_path / "references")
    metadata = ReferenceMetadata(
        id="test-reference",
        title="Test Reference",
        description="Reference description",
        tags=["test", "example"],
        created_by="tester",
        updated_by="tester",
        version="1.0.0",
    )
    project = make_project("reference-project")

    await store.save_reference(metadata, project)

    reference_dir = tmp_path / "references" / metadata.id
    assert (reference_dir / "metadata.json").exists()
    assert (reference_dir / "project_schema.json").exists()

    record = await store.load_reference(metadata.id)
    assert record is not None
    assert record.metadata.title == "Test Reference"
    assert record.project.id == "reference-project"

    references = await store.list_references()
    assert len(references) == 1
    assert references[0].id == metadata.id
