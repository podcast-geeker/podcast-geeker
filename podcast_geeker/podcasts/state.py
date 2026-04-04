from __future__ import annotations

from operator import add
from pathlib import Path
from typing import Annotated, Any, List, NotRequired, Optional, Union

from podcast_creator.core import Dialogue, Outline, Segment
from podcast_creator.speakers import SpeakerProfile
from typing_extensions import TypedDict


class PodcastAgentState(TypedDict, total=False):
    # podcast-creator compatible state fields
    content: Union[str, List[str]]
    briefing: str
    num_segments: int
    outline: Optional[Outline]
    transcript: List[Dialogue]
    audio_clips: Annotated[List[Path], add]
    final_output_file_path: Optional[Path]
    output_dir: Path
    episode_name: str
    speaker_profile: Optional[SpeakerProfile]

    # Input normalization helpers
    speakers: NotRequired[List[dict[str, Any]]]

    # Multi-agent dialogue loop fields
    skip_evaluation: NotRequired[bool]
    max_segment_retries: NotRequired[int]
    current_segment_index: NotRequired[int]
    current_segment: NotRequired[Optional[Segment]]
    segment_buffer: NotRequired[List[Dialogue]]
    segment_turns: NotRequired[int]
    max_turns_this_segment: NotRequired[int]
    segment_retry_count: NotRequired[int]
    quality_score: NotRequired[float]
    quality_passed: NotRequired[bool]
    review_feedback: NotRequired[str]
