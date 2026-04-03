from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ai_prompter import Prompter
from esperanto import AIFactory
from langchain_core.runnables import RunnableConfig
from loguru import logger
from podcast_creator.core import Dialogue
from podcast_creator.speakers import Speaker, SpeakerProfile

from podcast_geeker.podcasts.state import PodcastAgentState
from podcast_geeker.utils import clean_thinking_content

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _resolve_provider_and_model(
    config: dict[str, Any],
    prefix: str,
    default_provider: str,
    default_model: str,
) -> tuple[str, str]:
    provider = str(config.get(f"{prefix}_provider") or default_provider)
    model = str(config.get(f"{prefix}_model") or default_model)

    # Allow "provider/model" compact syntax for compatibility.
    if "/" in model and f"{prefix}_provider" not in config:
        maybe_provider, maybe_model = model.split("/", 1)
        if maybe_provider and maybe_model:
            provider, model = maybe_provider, maybe_model

    # Normalize underscore aliases (openai_compatible -> openai-compatible)
    if provider.replace("_", "-").lower() == "openai-compatible":
        provider = "openai-compatible"

    return provider, model


def _turns_for_segment_size(size: str) -> int:
    normalized = (size or "").lower()
    if normalized == "short":
        return 3
    if normalized == "long":
        return 7
    return 5


def _ensure_speaker_profile(
    state: PodcastAgentState, config: RunnableConfig
) -> SpeakerProfile:
    profile = state.get("speaker_profile")
    if profile:
        return profile

    configurable = config.get("configurable", {})
    speakers_raw = state.get("speakers") or []
    if not speakers_raw:
        raise ValueError("Missing speakers input for multi-agent podcast generation")

    speakers = [
        speaker if isinstance(speaker, Speaker) else Speaker(**speaker)
        for speaker in speakers_raw
    ]
    profile = SpeakerProfile(
        tts_provider=str(configurable.get("tts_provider") or "openai"),
        tts_model=str(configurable.get("tts_model") or "gpt-4o-mini-tts"),
        speakers=speakers,
    )
    return profile


def _build_language_model(
    config: RunnableConfig,
    prefix: str,
    default_provider: str = "openai",
    default_model: str = "gpt-4o-mini",
    max_tokens: int = 1200,
):
    configurable = config.get("configurable", {})
    provider, model = _resolve_provider_and_model(
        configurable,
        prefix=prefix,
        default_provider=default_provider,
        default_model=default_model,
    )
    return AIFactory.create_language(
        provider,
        model,
        config={"max_tokens": max_tokens},
    ).to_langchain()


def _extract_line(content: str) -> str:
    cleaned = clean_thinking_content(content).strip()
    if not cleaned:
        return ""
    for line in cleaned.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped.strip('"').strip("'")
    return cleaned


def _normalize_json_booleans(text: str) -> str:
    """Fix Python-style True/False/None to JSON-compliant lowercase."""
    result = re.sub(r'\bTrue\b', 'true', text)
    result = re.sub(r'\bFalse\b', 'false', result)
    result = re.sub(r'\bNone\b', 'null', result)
    return result


def _try_parse_json(text: str) -> dict[str, Any] | None:
    normalized = _normalize_json_booleans(text)
    try:
        return json.loads(normalized)
    except (json.JSONDecodeError, ValueError):
        pass

    match = _JSON_OBJECT_RE.search(normalized)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass
    return None


_PARSE_FAILURE_SENTINEL = "__parse_failure__"
_QUALITY_PASS_THRESHOLD = 0.65


def _parse_review_response(content: str) -> dict[str, Any]:
    cleaned = clean_thinking_content(content).strip()
    if not cleaned:
        return {
            "score": 0.0,
            "feedback": _PARSE_FAILURE_SENTINEL,
            "passed": False,
        }

    payload = _try_parse_json(cleaned)

    if not payload:
        stripped = re.sub(r"```(?:json)?|```", "", cleaned).strip()
        if stripped != cleaned:
            payload = _try_parse_json(stripped)

    if not payload:
        logger.warning(
            "Could not parse quality review JSON. Raw response (first 500 chars): "
            f"{cleaned[:500]}"
        )
        return {
            "score": 0.0,
            "feedback": _PARSE_FAILURE_SENTINEL,
            "passed": False,
        }

    score = float(payload.get("score", 0.0))
    score = max(0.0, min(1.0, score))
    feedback = str(payload.get("feedback") or "").strip()
    passed = score >= _QUALITY_PASS_THRESHOLD
    return {"score": score, "feedback": feedback, "passed": passed}


def _get_host_and_expert(profile: SpeakerProfile) -> tuple[Speaker, Speaker]:
    host = profile.speakers[0]
    expert = profile.speakers[1] if len(profile.speakers) > 1 else profile.speakers[0]
    return host, expert


async def prepare_graph_state_node(
    state: PodcastAgentState, config: RunnableConfig
) -> dict[str, Any]:
    output_dir = state.get("output_dir")
    if output_dir is None:
        raise ValueError("output_dir is required for podcast generation")

    output_path = output_dir if isinstance(output_dir, Path) else Path(str(output_dir))
    output_path.mkdir(parents=True, exist_ok=True)

    configurable = config.get("configurable", {})
    skip_eval = bool(
        state.get("skip_evaluation", configurable.get("skip_evaluation", False))
    )

    profile = _ensure_speaker_profile(state, config)

    return {
        "speaker_profile": profile,
        "output_dir": output_path,
        "num_segments": int(state.get("num_segments") or configurable.get("num_segments", 5)),
        "skip_evaluation": skip_eval,
        "max_segment_retries": int(configurable.get("max_segment_retries", 2)),
        "current_segment_index": int(state.get("current_segment_index", 0)),
        "segment_buffer": list(state.get("segment_buffer", [])),
        "segment_turns": int(state.get("segment_turns", 0)),
        "segment_retry_count": int(state.get("segment_retry_count", 0)),
        "transcript": list(state.get("transcript", [])),
        "audio_clips": list(state.get("audio_clips", [])),
        "review_feedback": str(state.get("review_feedback", "")),
    }


async def prepare_segment_node(state: PodcastAgentState) -> dict[str, Any]:
    outline = state.get("outline")
    if not outline:
        raise ValueError("outline must exist before segment preparation")

    segment_index = int(state.get("current_segment_index", 0))
    if segment_index >= len(outline.segments):
        return {"current_segment": None}

    current_segment = outline.segments[segment_index]
    return {
        "current_segment": current_segment,
        "segment_buffer": [],
        "segment_turns": 0,
        "segment_retry_count": 0,
        "quality_score": 0.0,
        "quality_passed": False,
        "max_turns_this_segment": _turns_for_segment_size(current_segment.size),
    }


async def host_turn_node(state: PodcastAgentState, config: RunnableConfig) -> dict[str, Any]:
    profile = _ensure_speaker_profile(state, config)
    host, _ = _get_host_and_expert(profile)
    current_segment = state.get("current_segment")
    if not current_segment:
        raise ValueError("current_segment is missing before host_turn")

    transcript_recent = list(state.get("segment_buffer", []))[-6:]
    prompt = Prompter(prompt_template="podcast/host_turn").render(
        data={
            "host": host,
            "briefing": state.get("briefing", ""),
            "content": state.get("content", ""),
            "current_segment": current_segment,
            "segment_index": int(state.get("current_segment_index", 0)),
            "transcript_recent": transcript_recent,
        }
    )

    model = _build_language_model(config, prefix="transcript", max_tokens=600)
    response = await model.ainvoke(prompt)
    line = _extract_line(str(response.content))
    if not line:
        line = "Let's unpack this topic from first principles."

    updated_buffer = list(state.get("segment_buffer", []))
    updated_buffer.append(Dialogue(speaker=host.name, dialogue=line))

    return {
        "segment_buffer": updated_buffer,
        "segment_turns": int(state.get("segment_turns", 0)) + 1,
    }


async def expert_turn_node(
    state: PodcastAgentState, config: RunnableConfig
) -> dict[str, Any]:
    profile = _ensure_speaker_profile(state, config)
    _, expert = _get_host_and_expert(profile)
    current_segment = state.get("current_segment")
    if not current_segment:
        raise ValueError("current_segment is missing before expert_turn")

    transcript_recent = list(state.get("segment_buffer", []))[-6:]
    host_last_line = transcript_recent[-1].dialogue if transcript_recent else ""

    prompt = Prompter(prompt_template="podcast/expert_turn").render(
        data={
            "expert": expert,
            "briefing": state.get("briefing", ""),
            "content": state.get("content", ""),
            "current_segment": current_segment,
            "host_last_line": host_last_line,
            "transcript_recent": transcript_recent,
        }
    )

    model = _build_language_model(config, prefix="transcript", max_tokens=700)
    response = await model.ainvoke(prompt)
    line = _extract_line(str(response.content))
    if not line:
        line = "A practical way to view this is through a concrete example."

    updated_buffer = list(state.get("segment_buffer", []))
    updated_buffer.append(Dialogue(speaker=expert.name, dialogue=line))

    return {
        "segment_buffer": updated_buffer,
        "segment_turns": int(state.get("segment_turns", 0)) + 1,
    }


def should_continue(state: PodcastAgentState) -> str:
    if int(state.get("segment_turns", 0)) < int(state.get("max_turns_this_segment", 0)):
        return "continue"
    if bool(state.get("skip_evaluation", False)):
        return "finalize"
    return "review"


async def quality_review_node(
    state: PodcastAgentState, config: RunnableConfig
) -> dict[str, Any]:
    current_segment = state.get("current_segment")
    if not current_segment:
        raise ValueError("current_segment is missing before quality_review")

    segment_transcript = list(state.get("segment_buffer", []))
    if not segment_transcript:
        return {"quality_score": 0.0, "quality_passed": False}

    prompt = Prompter(prompt_template="podcast/quality_review").render(
        data={
            "current_segment": current_segment,
            "segment_transcript": segment_transcript,
            "review_feedback": state.get("review_feedback", ""),
        }
    )

    model = _build_language_model(config, prefix="transcript", max_tokens=500)
    response = await model.ainvoke(prompt)
    raw_content = str(response.content)
    review = _parse_review_response(raw_content)

    segment_idx = int(state.get("current_segment_index", 0))
    retry_count = int(state.get("segment_retry_count", 0))
    max_retries = int(state.get("max_segment_retries", 2))
    is_parse_failure = review["feedback"] == _PARSE_FAILURE_SENTINEL

    logger.info(
        f"Quality review for segment {segment_idx} "
        f"(retry {retry_count}/{max_retries}): "
        f"score={review['score']:.2f}, passed={review['passed']}, "
        f"parse_ok={not is_parse_failure}"
    )
    if is_parse_failure:
        logger.debug(
            f"Raw review response (segment {segment_idx}): "
            f"{raw_content[:800]}"
        )

    passed = bool(review["passed"])

    if passed:
        return {
            "quality_score": review["score"],
            "quality_passed": True,
            "review_feedback": review["feedback"],
        }

    if is_parse_failure:
        logger.warning(
            f"Quality review parse failure for segment {segment_idx}; "
            "accepting segment to avoid wasting retries on format issues."
        )
        return {
            "quality_score": 0.5,
            "quality_passed": True,
            "review_feedback": "Accepted due to review response parse failure.",
        }

    if retry_count < max_retries:
        return {
            "quality_score": review["score"],
            "quality_passed": False,
            "review_feedback": review["feedback"],
            "segment_retry_count": retry_count + 1,
            "segment_buffer": [],
            "segment_turns": 0,
        }

    logger.warning(
        f"Quality review failed for segment {segment_idx} but reached "
        f"retry cap ({max_retries}); accepting segment to avoid dead loop."
    )
    return {
        "quality_score": review["score"],
        "quality_passed": True,
        "review_feedback": f"{review['feedback']} (retry cap reached)",
    }


def after_review(state: PodcastAgentState) -> str:
    return "pass" if bool(state.get("quality_passed", False)) else "retry"


async def advance_segment_node(state: PodcastAgentState) -> dict[str, Any]:
    transcript = list(state.get("transcript", []))
    transcript.extend(list(state.get("segment_buffer", [])))

    return {
        "transcript": transcript,
        "current_segment_index": int(state.get("current_segment_index", 0)) + 1,
        "segment_buffer": [],
        "segment_turns": 0,
        "segment_retry_count": 0,
    }


def route_after_advance(state: PodcastAgentState) -> str:
    outline = state.get("outline")
    if not outline:
        raise ValueError("outline missing during segment routing")

    if int(state.get("current_segment_index", 0)) < len(outline.segments):
        return "next_segment"
    return "generate_audio"


def route_prepared_segment(state: PodcastAgentState) -> str:
    if state.get("current_segment") is None:
        return "generate_audio"
    return "host_turn"
