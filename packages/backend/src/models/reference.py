"""Reference library models for curated reusable building examples."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReferenceMetadata(BaseModel):
    id: str
    title: str
    description: str
    tags: list[str] = Field(default_factory=list)
    created_by: str
    updated_by: str
    version: str = "1.0.0"
