import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urlparse

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from loguru import logger
from pydantic import BaseModel

from api.podcast_service import (
    PodcastGenerationRequest,
    PodcastGenerationResponse,
    PodcastService,
)
from podcast_geeker.config import DATA_FOLDER

router = APIRouter()


class PodcastEpisodeResponse(BaseModel):
    id: str
    name: str
    episode_profile: dict
    speaker_profile: dict
    briefing: str
    audio_file: Optional[str] = None
    audio_url: Optional[str] = None
    transcript: Optional[dict] = None
    outline: Optional[dict] = None
    created: Optional[str] = None
    job_status: Optional[str] = None


def _resolve_audio_path(audio_file: str) -> Path:
    data_root = Path(DATA_FOLDER).resolve()

    if audio_file.startswith("file://"):
        parsed = urlparse(audio_file)
        resolved_path = Path(unquote(parsed.path))
    else:
        resolved_path = Path(audio_file)

    # Happy path: stored file path is already valid.
    if resolved_path.exists():
        return resolved_path

    parts = resolved_path.parts
    lower_parts = [part.lower() for part in parts]

    # Compatibility for migrated databases:
    # old records may contain absolute paths from another machine, e.g.
    # /Users/.../podcast-geeker/data/podcasts/episodes/<name>/audio/<file>.mp3
    if "data" in lower_parts:
        data_index = lower_parts.index("data")
        remapped_path = data_root.joinpath(*parts[data_index + 1 :])
        if remapped_path.exists():
            return remapped_path

    # Secondary fallback if "data" segment is missing but podcast suffix exists.
    if "podcasts" in lower_parts:
        podcasts_index = lower_parts.index("podcasts")
        remapped_path = data_root.joinpath(*parts[podcasts_index:])
        if remapped_path.exists():
            return remapped_path

    return resolved_path


def _episode_disk_dir(episode_name: str) -> Path:
    return Path(DATA_FOLDER).resolve() / "podcasts" / "episodes" / episode_name


def _try_load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


async def _backfill_episode_from_disk(episode) -> bool:
    """Populate missing audio/transcript/outline from disk files.

    Returns True if any field was recovered and the record was saved.
    """
    disk_dir = _episode_disk_dir(episode.name)
    if not disk_dir.is_dir():
        return False

    changed = False

    if not episode.audio_file:
        audio_dir = disk_dir / "audio"
        if audio_dir.is_dir():
            mp3s = list(audio_dir.glob("*.mp3"))
            if mp3s:
                episode.audio_file = str(mp3s[0])
                changed = True

    if not episode.transcript or episode.transcript == {}:
        transcript_path = disk_dir / "transcript.json"
        if transcript_path.exists():
            raw = _try_load_json(transcript_path)
            if raw is not None:
                if isinstance(raw, list):
                    episode.transcript = {"transcript": raw}
                elif isinstance(raw, dict) and "transcript" in raw:
                    episode.transcript = raw
                else:
                    episode.transcript = {"transcript": raw}
                changed = True

    if not episode.outline or episode.outline == {}:
        outline_path = disk_dir / "outline.json"
        if outline_path.exists():
            raw = _try_load_json(outline_path)
            if raw is not None:
                episode.outline = raw
                changed = True

    if changed:
        try:
            await episode.save()
            logger.info(f"Backfilled episode '{episode.name}' from disk files")
        except Exception as e:
            logger.warning(f"Failed to persist backfilled episode data: {e}")

    return changed


@router.post("/podcasts/generate", response_model=PodcastGenerationResponse)
async def generate_podcast(request: PodcastGenerationRequest):
    """
    Generate a podcast episode using Episode Profiles.
    Returns immediately with job ID for status tracking.
    """
    try:
        job_id = await PodcastService.submit_generation_job(
            episode_profile_name=request.episode_profile,
            speaker_profile_name=request.speaker_profile,
            episode_name=request.episode_name,
            notebook_id=request.notebook_id,
            content=request.content,
            briefing_suffix=request.briefing_suffix,
            generation_mode=request.generation_mode,
            skip_evaluation=request.skip_evaluation,
        )

        return PodcastGenerationResponse(
            job_id=job_id,
            status="submitted",
            message=f"Podcast generation started for episode '{request.episode_name}'",
            episode_profile=request.episode_profile,
            episode_name=request.episode_name,
        )

    except Exception as e:
        logger.error(f"Error generating podcast: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to generate podcast"
        )


@router.get("/podcasts/jobs/{job_id}")
async def get_podcast_job_status(job_id: str):
    """Get the status of a podcast generation job"""
    try:
        status_data = await PodcastService.get_job_status(job_id)
        return status_data

    except Exception as e:
        logger.error(f"Error fetching podcast job status: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to fetch job status"
        )


@router.get("/podcasts/episodes", response_model=List[PodcastEpisodeResponse])
async def list_podcast_episodes():
    """List all podcast episodes"""
    try:
        episodes = await PodcastService.list_episodes()

        response_episodes = []
        for episode in episodes:
            # Try to recover missing data from disk before filtering
            if not episode.audio_file or not episode.transcript or episode.transcript == {} or not episode.outline or episode.outline == {}:
                await _backfill_episode_from_disk(episode)

            # Skip incomplete episodes without command or audio
            if not episode.command and not episode.audio_file:
                continue

            # Get job status if available
            job_status = None
            if episode.command:
                try:
                    job_status = await episode.get_job_status()
                except Exception:
                    job_status = "unknown"
            else:
                # No command but has audio file = completed import
                job_status = "completed"

            audio_url = None
            if episode.audio_file:
                audio_path = _resolve_audio_path(episode.audio_file)
                if audio_path.exists():
                    audio_url = f"/api/podcasts/episodes/{episode.id}/audio"

            response_episodes.append(
                PodcastEpisodeResponse(
                    id=str(episode.id),
                    name=episode.name,
                    episode_profile=episode.episode_profile,
                    speaker_profile=episode.speaker_profile,
                    briefing=episode.briefing,
                    audio_file=episode.audio_file,
                    audio_url=audio_url,
                    transcript=episode.transcript,
                    outline=episode.outline,
                    created=str(episode.created) if episode.created else None,
                    job_status=job_status,
                )
            )

        return response_episodes

    except Exception as e:
        logger.error(f"Error listing podcast episodes: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to list podcast episodes"
        )


@router.get("/podcasts/episodes/{episode_id}", response_model=PodcastEpisodeResponse)
async def get_podcast_episode(episode_id: str):
    """Get a specific podcast episode"""
    try:
        episode = await PodcastService.get_episode(episode_id)

        if not episode.audio_file or not episode.transcript or episode.transcript == {} or not episode.outline or episode.outline == {}:
            await _backfill_episode_from_disk(episode)

        # Get job status if available
        job_status = None
        if episode.command:
            try:
                job_status = await episode.get_job_status()
            except Exception:
                job_status = "unknown"
        else:
            # No command but has audio file = completed import
            job_status = "completed" if episode.audio_file else "unknown"

        audio_url = None
        if episode.audio_file:
            audio_path = _resolve_audio_path(episode.audio_file)
            if audio_path.exists():
                audio_url = f"/api/podcasts/episodes/{episode.id}/audio"

        return PodcastEpisodeResponse(
            id=str(episode.id),
            name=episode.name,
            episode_profile=episode.episode_profile,
            speaker_profile=episode.speaker_profile,
            briefing=episode.briefing,
            audio_file=episode.audio_file,
            audio_url=audio_url,
            transcript=episode.transcript,
            outline=episode.outline,
            created=str(episode.created) if episode.created else None,
            job_status=job_status,
        )

    except Exception as e:
        logger.error(f"Error fetching podcast episode: {str(e)}")
        raise HTTPException(status_code=404, detail="Episode not found")


@router.get("/podcasts/episodes/{episode_id}/audio")
async def stream_podcast_episode_audio(episode_id: str):
    """Stream the audio file associated with a podcast episode"""
    try:
        episode = await PodcastService.get_episode(episode_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching podcast episode for audio: {str(e)}")
        raise HTTPException(status_code=404, detail="Episode not found")

    if not episode.audio_file:
        await _backfill_episode_from_disk(episode)

    if not episode.audio_file:
        raise HTTPException(status_code=404, detail="Episode has no audio file")

    audio_path = _resolve_audio_path(episode.audio_file)
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        filename=audio_path.name,
    )


@router.delete("/podcasts/episodes/{episode_id}")
async def delete_podcast_episode(episode_id: str):
    """Delete a podcast episode and its associated audio file"""
    try:
        # Get the episode first to check if it exists and get the audio file path
        episode = await PodcastService.get_episode(episode_id)

        # Delete the physical audio file if it exists
        if episode.audio_file:
            audio_path = _resolve_audio_path(episode.audio_file)
            if audio_path.exists():
                try:
                    audio_path.unlink()
                    logger.info(f"Deleted audio file: {audio_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete audio file {audio_path}: {e}")

        # Delete the episode from the database
        await episode.delete()

        logger.info(f"Deleted podcast episode: {episode_id}")
        return {"message": "Episode deleted successfully", "episode_id": episode_id}

    except Exception as e:
        logger.error(f"Error deleting podcast episode: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to delete episode"
        )
