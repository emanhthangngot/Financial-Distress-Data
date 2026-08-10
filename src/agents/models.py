"""Shared, transport-neutral agent response models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_uri: str = Field(min_length=1, max_length=2048)
    label: str = Field(min_length=1, max_length=256)


class SpecialistResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    specialist: str
    answer: str = Field(min_length=1, max_length=100_000)
    citations: list[Citation] = Field(min_length=1, max_length=64)


class AgentFailure(BaseModel):
    status: str = "failed"
    decision: str = "stop"
    error: str
