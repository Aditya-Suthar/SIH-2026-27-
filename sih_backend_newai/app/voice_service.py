"""Local speech-to-text service for victim voice check-ins.

The audio is decoded and transcribed with faster-whisper. No audio or transcript is
persisted here; persistence happens only if the victim later submits the editable
transcript through the existing assessment workflow.
"""
from functools import lru_cache
import logging
import os
from pathlib import Path
from threading import Lock

logger = logging.getLogger(__name__)
_inference_lock = Lock()


class VoiceTranscriptionError(RuntimeError):
    """Controlled error for unavailable/failed local transcription."""


@lru_cache(maxsize=1)
def get_whisper_model():
    """Load the configured Whisper model once and reuse it between requests."""
    try:
        from faster_whisper import WhisperModel
    except (ImportError, OSError) as exc:
        logger.exception("Whisper native runtime could not be imported")
        raise VoiceTranscriptionError(
            "Voice transcription runtime is unavailable on this server. Check faster-whisper installation and native library compatibility in deployment logs."
        ) from exc

    model_name = os.getenv("WHISPER_MODEL", "small").strip() or "small"
    device = os.getenv("WHISPER_DEVICE", "cpu").strip() or "cpu"
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8").strip() or "int8"

    try:
        return WhisperModel(
            model_name, device=device, compute_type=compute_type,
            download_root=os.getenv("WHISPER_DOWNLOAD_ROOT") or None,
            local_files_only=os.getenv("WHISPER_LOCAL_FILES_ONLY", "false").lower() == "true",
            cpu_threads=int(os.getenv("WHISPER_CPU_THREADS", "2")),
            num_workers=1,
        )
    except Exception as exc:
        logger.exception("Whisper model initialization failed")
        raise VoiceTranscriptionError(
            "Voice transcription model could not be loaded. Check deployed model files, cache permissions, download access, device configuration, and memory in backend logs."
        ) from exc


def transcribe_audio(audio_path: str) -> dict:
    # Prevent simultaneous cold loads and overlapping inference memory spikes.
    if not _inference_lock.acquire(blocking=False):
        raise VoiceTranscriptionError("Voice transcription is busy. Please try again shortly.")
    try:
        return _transcribe_audio(audio_path)
    finally:
        _inference_lock.release()


def _transcribe_audio(audio_path: str) -> dict:
    """Transcribe one temporary audio file and return safe metadata."""
    path = Path(audio_path)
    if not path.is_file():
        raise VoiceTranscriptionError("Audio recording is unavailable.")

    model = get_whisper_model()

    try:
        segments, info = model.transcribe(
            str(path),
            language="en",
            task="transcribe",
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )

        parts = []

        for segment in segments:
            text = segment.text.strip()
            if text:
                parts.append(text)

        transcript = " ".join(parts).strip()

    except Exception as exc:
        logger.exception("Whisper decoding or inference failed")
        raise VoiceTranscriptionError("Voice transcription failed during audio decoding or inference. Check backend logs for the runtime reason.") from exc

    return {
        "transcript": transcript,
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
    }
