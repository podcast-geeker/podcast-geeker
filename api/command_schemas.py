"""
Request/input schemas for job commands submitted by the API.

Defined here so the API can build command payloads without importing the
commands package (which pulls in heavy deps like podcast_creator and can block
API startup). Field names and types must match the corresponding CommandInput
classes in commands/* so worker deserialization works.
"""

from typing import Any, Dict, List

from pydantic import BaseModel


class SourceProcessingInput(BaseModel):
    """Payload for process_source command. Mirrors commands.source_commands.SourceProcessingInput."""

    source_id: str
    content_state: Dict[str, Any]
    notebook_ids: List[str]
    transformations: List[str]
    embed: bool
