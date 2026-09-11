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
    current_user: dict = Depends(get_current_user),
):
    # --------------------------------------------------
    # Security
    # --------------------------------------------------

    if current_user.get("role") != "victim":
        raise HTTPException(
            status_code=403,
            detail="Only victims can submit voice check-ins",
        )

    content_type = (
        audio.content_type or ""
    ).split(";", 1)[0].lower()

    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio format: {content_type}",
        )

    # --------------------------------------------------
    # Read uploaded audio
    # --------------------------------------------------

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
        # --------------------------------------------------
        # Whisper needs an actual temporary audio file
        # --------------------------------------------------

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temporary_file:

            temporary_file.write(audio_bytes)

            temporary_path = (
                temporary_file.name
            )

        # --------------------------------------------------
        # Run faster-whisper
        # --------------------------------------------------

        result = transcribe_audio(
            temporary_path
        )

        transcript = result[
            "transcript"
        ]

        if not transcript:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No speech could be detected. "
                    "Please try recording again."
                ),
            )

        # Prevent feeding arbitrarily large text
        # into the existing AI check-in workflow.
        transcript = transcript[:4000]

        return {
            "transcript": transcript,
            "language": result["language"],
            "language_probability":
                result["language_probability"],
        }

    finally:

        if (
            temporary_path
            and os.path.exists(
                temporary_path
            )
        ):
            os.remove(
                temporary_path
            )