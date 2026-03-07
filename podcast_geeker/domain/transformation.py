from typing import ClassVar, Optional

from pydantic import Field

from podcast_geeker.domain.base import ObjectModel, RecordModel


class Transformation(ObjectModel):
    table_name: ClassVar[str] = "transformation"
    name: str
    title: str
    description: str
    prompt: str
    apply_default: bool


class DefaultPrompts(RecordModel):
    record_id: ClassVar[str] = "podcast_geeker:default_prompts"
    transformation_instructions: Optional[str] = Field(
        None, description="Instructions for executing a transformation"
    )
