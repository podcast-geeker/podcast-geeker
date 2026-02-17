import os
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from loguru import logger
from pydantic import BaseModel
from surreal_commands import CommandInput, CommandOutput, command

from open_notebook.ai.key_provider import provision_provider_keys
from open_notebook.config import DATA_FOLDER
from open_notebook.database.repository import ensure_record_id, repo_query
from open_notebook.podcasts.models import EpisodeProfile, PodcastEpisode, SpeakerProfile


def _load_podcast_creator():
    """
    Import podcast_creator lazily so worker startup doesn't eagerly load
    heavy movie/audio dependencies unless podcast generation is executed.
    """
    try:
        from podcast_creator import configure, create_podcast
    except ImportError as e:
        logger.error(f"Failed to import podcast_creator: {e}")
        raise ValueError("podcast_creator library not available") from e
    return configure, create_podcast


def full_model_dump(model):
    if isinstance(model, BaseModel):
        return model.model_dump()
    elif isinstance(model, dict):
        return {k: full_model_dump(v) for k, v in model.items()}
    elif isinstance(model, list):
        return [full_model_dump(item) for item in model]
    else:
        return model


def _ensure_no_proxy_for_local_ollama(base_url: Optional[str]) -> None:
    """
    Ensure localhost-style Ollama endpoints bypass system proxies.

    Worker-side podcast generation uses podcast-creator/langchain_ollama directly,
    so we need a local safeguard here (API-layer httpx settings don't apply).
    """
    if not base_url:
        return

    host = urlparse(base_url).hostname
    if host not in {"localhost", "127.0.0.1"}:
        return

    for key in ("NO_PROXY", "no_proxy"):
        current = os.environ.get(key, "")
        entries = [entry.strip() for entry in current.split(",") if entry.strip()]
        changed = False
        for required in ("localhost", "127.0.0.1"):
            if required not in entries:
                entries.append(required)
                changed = True
        if changed:
            os.environ[key] = ",".join(entries)
            logger.debug(f"Updated {key} to bypass proxy for local Ollama")


def _normalize_provider_for_podcast_creator(provider: Optional[str]) -> Optional[str]:
    """
    Normalize provider aliases for podcast-creator/Esperanto compatibility.

    Stored provider names may use underscore style (openai_compatible), while
    some Esperanto versions expect hyphen style (openai-compatible).
    """
    if not provider:
        return provider

    if provider.replace("_", "-").lower() == "openai-compatible":
        return "openai-compatible"

    return provider


_OPENAI_TO_KOKORO_VOICE_MAP = {
    "alloy": "af_alloy",
    "ash": "am_adam",
    "echo": "am_echo",
    "fable": "bm_fable",
    "nova": "af_nova",
    "onyx": "am_onyx",
    "shimmer": "af_sarah",
}


def _normalize_voice_id_for_provider_model(
    voice_id: Optional[str], provider: Optional[str], model: Optional[str]
) -> Optional[str]:
    """Normalize voice IDs when provider/model have stricter voice requirements."""
    if not voice_id:
        return voice_id

    normalized_provider = _normalize_provider_for_podcast_creator(provider)
    model_lower = (model or "").lower()

    # Kokoro-based OpenAI-compatible endpoints require provider-specific IDs
    # (e.g. af_nova) rather than OpenAI voice aliases (e.g. nova).
    if normalized_provider == "openai-compatible" and "kokoro" in model_lower:
        return _OPENAI_TO_KOKORO_VOICE_MAP.get(voice_id.lower(), voice_id)

    return voice_id


class PodcastGenerationInput(CommandInput):
    episode_profile: str
    speaker_profile: str
    episode_name: str
    content: str
    briefing_suffix: Optional[str] = None


class PodcastGenerationOutput(CommandOutput):
    success: bool
    episode_id: Optional[str] = None
    audio_file_path: Optional[str] = None
    transcript: Optional[dict] = None
    outline: Optional[dict] = None
    processing_time: float
    error_message: Optional[str] = None


@command("generate_podcast", app="open_notebook")
async def generate_podcast_command(
    input_data: PodcastGenerationInput,
) -> PodcastGenerationOutput:
    """
    Real podcast generation using podcast-creator library with Episode Profiles
    """
    start_time = time.time()

    try:
        configure, create_podcast = _load_podcast_creator()
        logger.info(
            f"Starting podcast generation for episode: {input_data.episode_name}"
        )
        logger.info(f"Using episode profile: {input_data.episode_profile}")

        # 1. Load Episode and Speaker profiles from SurrealDB
        episode_profile = await EpisodeProfile.get_by_name(input_data.episode_profile)
        if not episode_profile:
            raise ValueError(
                f"Episode profile '{input_data.episode_profile}' not found"
            )

        speaker_profile = await SpeakerProfile.get_by_name(
            episode_profile.speaker_config
        )
        if not speaker_profile:
            raise ValueError(
                f"Speaker profile '{episode_profile.speaker_config}' not found"
            )

        logger.info(f"Loaded episode profile: {episode_profile.name}")
        logger.info(f"Loaded speaker profile: {speaker_profile.name}")

        # Worker-side proxy safeguard for local Ollama providers.
        # podcast-creator uses langchain_ollama in this process and can inherit
        # host-level proxy settings unless NO_PROXY/no_proxy is present.
        uses_local_ollama = (
            episode_profile.outline_provider == "ollama"
            or episode_profile.transcript_provider == "ollama"
        )
        if uses_local_ollama:
            _ensure_no_proxy_for_local_ollama(
                os.environ.get("OLLAMA_API_BASE")
                or os.environ.get("OLLAMA_BASE_URL")
                or "http://localhost:11434"
            )

        # 3. Load all profiles and configure podcast-creator
        episode_profiles = await repo_query("SELECT * FROM episode_profile")
        speaker_profiles = await repo_query("SELECT * FROM speaker_profile")

        # Transform the surrealdb array into a dictionary for podcast-creator
        episode_profiles_dict = {}
        for profile in episode_profiles:
            normalized = dict(profile)
            normalized["outline_provider"] = _normalize_provider_for_podcast_creator(
                normalized.get("outline_provider")
            )
            normalized["transcript_provider"] = _normalize_provider_for_podcast_creator(
                normalized.get("transcript_provider")
            )
            episode_profiles_dict[normalized["name"]] = normalized

        speaker_profiles_dict = {}
        for profile in speaker_profiles:
            normalized = dict(profile)
            normalized["tts_provider"] = _normalize_provider_for_podcast_creator(
                normalized.get("tts_provider")
            )
            normalized_speakers = []
            for speaker in normalized.get("speakers", []):
                normalized_speaker = dict(speaker)
                normalized_speaker["voice_id"] = _normalize_voice_id_for_provider_model(
                    normalized_speaker.get("voice_id"),
                    normalized.get("tts_provider"),
                    normalized.get("tts_model"),
                )
                normalized_speakers.append(normalized_speaker)
            normalized["speakers"] = normalized_speakers
            speaker_profiles_dict[normalized["name"]] = normalized

        # 4. Generate briefing
        briefing = episode_profile.default_briefing
        if input_data.briefing_suffix:
            briefing += f"\n\nAdditional instructions: {input_data.briefing_suffix}"

        # Create the a record for the episose and associate with the ongoing command
        episode = PodcastEpisode(
            name=input_data.episode_name,
            episode_profile=full_model_dump(episode_profile.model_dump()),
            speaker_profile=full_model_dump(speaker_profile.model_dump()),
            command=ensure_record_id(input_data.execution_context.command_id)
            if input_data.execution_context
            else None,
            briefing=briefing,
            content=input_data.content,
            audio_file=None,
            transcript=None,
            outline=None,
        )
        await episode.save()

        configure("speakers_config", {"profiles": speaker_profiles_dict})
        configure("episode_config", {"profiles": episode_profiles_dict})

        logger.info("Configured podcast-creator with episode and speaker profiles")

        # Provision API keys from Settings (Credential DB) into env vars.
        # podcast-creator/Esperanto reads from env; without this, only .env is used.
        providers_to_provision = {
            episode_profile.outline_provider,
            episode_profile.transcript_provider,
            speaker_profile.tts_provider,
        }
        for prov in providers_to_provision:
            if prov and prov.lower() != "ollama":
                # key_provider expects openai_compatible (underscore)
                normalized = prov.replace("-", "_").lower()
                await provision_provider_keys(normalized)

        logger.info(f"Generated briefing (length: {len(briefing)} chars)")

        # 5. Create output directory
        output_dir = Path(f"{DATA_FOLDER}/podcasts/episodes/{input_data.episode_name}")
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created output directory: {output_dir}")

        # 6. Generate podcast using podcast-creator
        logger.info("Starting podcast generation with podcast-creator...")

        result = await create_podcast(
            content=input_data.content,
            briefing=briefing,
            episode_name=input_data.episode_name,
            output_dir=str(output_dir),
            speaker_config=speaker_profile.name,
            episode_profile=episode_profile.name,
        )

        episode.audio_file = (
            str(result.get("final_output_file_path")) if result else None
        )
        episode.transcript = {
            "transcript": full_model_dump(result["transcript"]) if result else None
        }
        episode.outline = full_model_dump(result["outline"]) if result else None
        await episode.save()

        processing_time = time.time() - start_time
        logger.info(
            f"Successfully generated podcast episode: {episode.id} in {processing_time:.2f}s"
        )

        return PodcastGenerationOutput(
            success=True,
            episode_id=str(episode.id),
            audio_file_path=str(result.get("final_output_file_path"))
            if result
            else None,
            transcript={"transcript": full_model_dump(result["transcript"])}
            if result.get("transcript")
            else None,
            outline=full_model_dump(result["outline"])
            if result.get("outline")
            else None,
            processing_time=processing_time,
        )

    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Podcast generation failed: {e}")
        logger.exception(e)

        # Check for specific GPT-5 extended thinking issue
        error_msg = str(e)
        if "Invalid json output" in error_msg or "Expecting value" in error_msg:
            # This often happens with GPT-5 models that use extended thinking (<think> tags)
            # and put all output inside thinking blocks
            error_msg += (
                "\n\nNOTE: This error commonly occurs with GPT-5 models that use extended thinking. "
                "The model may be putting all output inside <think> tags, leaving nothing to parse. "
                "Try using gpt-4o, gpt-4o-mini, or gpt-4-turbo instead in your episode profile."
            )

        return PodcastGenerationOutput(
            success=False, processing_time=processing_time, error_message=error_msg
        )
