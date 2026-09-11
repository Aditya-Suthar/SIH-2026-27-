# Voice check-in implementation

This continuation adds local speech-to-text to the completed Sahas project without replacing the existing AI distress workflow.

## Flow

1. A signed-in victim records audio from the dashboard.
2. The browser sends the raw recording to `POST /api/victim/voice/transcribe`.
3. The backend validates the live account/role, type and size, writes only a temporary file, and runs `faster-whisper` locally.
4. The temporary audio file is deleted immediately after transcription.
5. The returned transcript fills the existing optional check-in text field so the victim can review/edit it.
6. Only when the victim presses **Submit Check-in** does the existing assessment endpoint persist the text and invoke the existing Gemini → Groq → OpenRouter distress-analysis workflow.

No audio is persisted by the voice endpoint, and the transcription endpoint itself does not create a distress score or diagnosis.

## Setup

Install backend requirements:

```powershell
python -m pip install -r requirements.txt
```

The default local configuration is:

```env
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

The first real transcription may download the Whisper model. For an offline demo, run one transcription while internet is available beforehand so the model is already cached.

## API

`POST /api/victim/voice/transcribe`

- authentication: Bearer token
- role: victim only
- body: raw audio bytes
- supported content types: WebM, WAV, MP3, MP4 audio, OGG
- maximum body size: 15 MiB

Example response:

```json
{
  "transcript": "I have been feeling overwhelmed and I have not been sleeping well.",
  "language": "en",
  "language_probability": 0.98
}
```

## Deliberate scope

The previously tested emotion-recognition experiments are not part of this integration. The production demo path is voice → Whisper transcript → existing text distress analysis/history. emotion2vec/openSMILE can be added later as supporting multimodal signals without changing this flow.
