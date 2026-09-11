"""Authenticated, victim-only local voice transcription endpoint."""
import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from .ai_history import authenticated_account
from .auth import get_current_user
from .database import get_db
from .voice_service import VoiceTranscriptionError, transcribe_audio

router = APIRouter(prefix="/api/victim/voice", tags=["voice"])

MAX_AUDIO_BYTES = 15 * 1024 * 1024
ALLOWED_AUDIO_TYPES = {
    "audio/webm": ".webm",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".mp4",
    "audio/ogg": ".ogg",
}


@router.post("/transcribe")
async def transcribe_voice(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Convert raw recorded audio to text without saving the recording."""
    user = authenticated_account(db, current_user)
    if user.role != "victim":
        raise HTTPException(status_code=403, detail="Only victims can submit voice check-ins")

    raw_content_type = request.headers.get("content-type", "")
    content_type = raw_content_type.split(";", 1)[0].strip().lower()
    suffix = ALLOWED_AUDIO_TYPES.get(content_type)
    if suffix is None:
        raise HTTPException(status_code=415, detail="Unsupported audio format")

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_AUDIO_BYTES:
                raise HTTPException(status_code=413, detail="Audio recording is too large")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid audio request")

    audio_bytes = await request.body()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio recording")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio recording is too large")

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary_file:
            temporary_file.write(audio_bytes)
            temporary_path = temporary_file.name

        try:
            result = await run_in_threadpool(transcribe_audio, temporary_path)
        except VoiceTranscriptionError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        transcript = result.get("transcript", "").strip()
        if not transcript:
            raise HTTPException(
                status_code=422,
                detail="No speech could be detected. Please try recording again.",
            )

        # Existing assessment note validation caps text at 4000 characters.
        transcript = transcript[:4000].rstrip()
        return {
            "transcript": transcript,
            "language": result.get("language"),
            "language_probability": result.get("language_probability"),
        }
    finally:
        if temporary_path and os.path.exists(temporary_path):
            try:
                os.remove(temporary_path)
            except OSError:
                # The endpoint must not leak a local path to the client.
                pass
