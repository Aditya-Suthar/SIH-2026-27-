import os
import tempfile

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
)

from .auth import get_current_user
from .voice_service import transcribe_audio


router = APIRouter(
    prefix="/api/victim/voice",
    tags=["voice"],
)

MAX_AUDIO_BYTES = 15 * 1024 * 1024

ALLOWED_TYPES = {
    "audio/webm": ".webm",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".mp4",
    "audio/ogg": ".ogg",
}


@router.post("/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    content_type = (
        audio.content_type or ""
    ).split(";", 1)[0].lower()

    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio format: {content_type}",
        )

    audio_bytes = await audio.read()

    if not audio_bytes:
        raise HTTPException(
            status_code=400,
            detail="Empty audio recording",
        )

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Audio recording is too large",
        )

    suffix = ALLOWED_TYPES[content_type]
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:
            temp_file.write(audio_bytes)
            temporary_path = temp_file.name

        result = transcribe_audio(temporary_path)

        if not result["transcript"]:
            raise HTTPException(
                status_code=422,
                detail="No speech detected. Please try again.",
            )

        return {
            "transcript": result["transcript"][:4000],
            "language": result["language"],
            "language_probability":
                result["language_probability"],
        }

    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)