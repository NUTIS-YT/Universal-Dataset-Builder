"""Validated request models for the local UDB API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    directory: str = Field(min_length=1, max_length=4096)
    name: str = Field(min_length=1, max_length=120)
    metadata_format: Literal["jsonl"] = "jsonl"


class ProjectOpenRequest(BaseModel):
    database_path: str = Field(min_length=1, max_length=4096)


class ScanRequest(BaseModel):
    recursive: bool = True


class NormalizeRequest(BaseModel):
    start_number: int = Field(default=1, ge=1, le=999_999_999)
    alpha_mode: Literal["preserve", "white", "black"] = "preserve"
    skip_duplicates: bool = True
    sort_mode: Literal[
        "filename_asc",
        "filename_desc",
        "largest_first",
        "smallest_first",
    ] = "filename_asc"


class CaptionGenerationRequest(BaseModel):
    selection_mode: Literal["missing", "unreviewed"] = "missing"
    limit: int = Field(default=0, ge=0, le=1_000_000)
    model: str | None = Field(default=None, max_length=512)
    prompt: str | None = Field(default=None, max_length=20_000)


class CaptionCharacterSettingsUpdateRequest(BaseModel):
    enabled: bool = False
    description: str = Field(default="", max_length=10_000)
    trigger_word: str = Field(default="", max_length=512)


class CaptionUpdateRequest(BaseModel):
    caption: str = Field(min_length=1, max_length=20_000)


class ImageStatusUpdateRequest(BaseModel):
    status: Literal[
        "Pending",
        "Normalized",
        "Captioned",
        "Reviewed",
        "Failed",
        "Excluded",
    ]


class SettingsUpdateRequest(BaseModel):
    theme: Literal["dark", "light"] | None = None
    vlm_base_url: str | None = Field(default=None, max_length=2048)
    vlm_api_key: str | None = Field(default=None, max_length=4096)
    vlm_timeout: int | None = Field(default=None, ge=5, le=600)
    vlm_model: str | None = Field(default=None, max_length=512)
    vlm_models: list[str] | None = None
    caption_prompt: str | None = Field(default=None, max_length=20_000)


class VLMTestRequest(BaseModel):
    base_url: str = Field(min_length=1, max_length=2048)
    api_key: str = Field(default="", max_length=4096)
    timeout_seconds: int = Field(default=120, ge=5, le=600)
