from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


AssistantContextType = Literal["catalog", "channel", "program"]
AssistantGenerationSource = Literal["gemini", "fallback"]
AssistantSourceType = Literal[
    "catalog_metadata",
    "program_metadata",
    "channel_metadata",
    "season_metadata",
    "credits_metadata",
    "related_metadata",
    "search_index",
    "transcript",
]


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=600)
    context_type: AssistantContextType
    content_slug: str | None = Field(default=None, min_length=1, max_length=180)
    channel_id: int | None = Field(default=None, ge=1)
    epg_entry_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_context(self) -> "AssistantChatRequest":
        if self.context_type == "catalog" and not self.content_slug:
            raise ValueError("content_slug is required when context_type is catalog.")
        if self.context_type == "channel" and not self.channel_id:
            raise ValueError("channel_id is required when context_type is channel.")
        if self.context_type == "program" and not self.epg_entry_id:
            raise ValueError("epg_entry_id is required when context_type is program.")
        return self


class AssistantContextRead(BaseModel):
    context_type: AssistantContextType
    title: str
    description: str | None = None
    category_label: str | None = None
    content_slug: str | None = None
    channel_id: int | None = None
    epg_entry_id: int | None = None
    channel_name: str | None = None
    live_status: str | None = None
    current_program_title: str | None = None
    next_program_title: str | None = None
    has_transcript: bool
    metadata_only: bool


class AssistantSourceRead(BaseModel):
    chunk_id: str
    source_type: AssistantSourceType
    title: str
    snippet: str


class AssistantLLMResponse(BaseModel):
    answer: str = Field(min_length=8, max_length=2400)
    limitation_note: str | None = Field(default=None, max_length=400)
    cited_chunk_ids: list[str] = Field(default_factory=list, max_length=8)
    follow_up_questions: list[str] = Field(default_factory=list, max_length=3)


class AssistantChatResponse(BaseModel):
    answer: str
    limitation_note: str | None = None
    grounded: bool
    used_rag: bool
    generation_source: AssistantGenerationSource
    model: str | None = None
    context: AssistantContextRead
    sources: list[AssistantSourceRead]
    follow_up_questions: list[str] = Field(default_factory=list)
