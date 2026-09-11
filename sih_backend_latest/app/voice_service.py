"""Local speech-to-text service for victim voice check-ins.

The audio is decoded and transcribed with faster-whisper. No audio or transcript is
persisted here; persistence happens only if the victim later submits the editable
transcript through the existing assessment workflow.
"""
from functools import lru_cache
import os
from pathlib import Path


class VoiceTranscriptionError(RuntimeError):
    """Controlled error for unavailable/failed local transcription."""


@lru_cache(maxsize=1)
def get_whisper_model():
    """Load the configured Whisper model once and reuse it between requests."""
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # Keeps the rest of the backend importable for tests/setup.
        raise VoiceTranscriptionError(
            "Voice transcription is not installed on this server."
        ) from exc

    model_name = os.getenv("WHISPER_MODEL", "small").strip() or "small"
    device = os.getenv("WHISPER_DEVICE", "cpu").strip() or "cpu"
    compute_type = os.getenv("WHISPER_COMPUTE_TYPE", "int8").strip() or "int8"

    try:
        return WhisperModel(model_name, device=device, compute_type=compute_type)
    except Exception as exc:
        # Do not expose local paths/model-download details through the API.
        raise VoiceTranscriptionError("Voice transcription model could not be loaded.") from exc


def transcribe_audio(audio_path: str) -> dict:
    """Transcribe one temporary audio file and return safe metadata."""
    path = Path(audio_path)
    if not path.is_file():
        raise VoiceTranscriptionError("Audio recording is unavailable.")

    model = get_whisper_model()
    try:
        segments, info = model.transcribe(
            str(path),
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=True,
        )
        parts = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                parts.append(text)
        transcript = " ".join(parts).strip()
    except Exception as exc:
        raise VoiceTranscriptionError("Voice transcription failed.") from exc

    return {
        "transcript": transcript,
        "language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
    }
