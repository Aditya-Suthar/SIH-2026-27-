# Cloud voice check-in investigation

Status: source fixes complete; live deployment verification is pending the frontend URL, backend URL, hosting service, and deployed source directories. No cloud environment settings were available in this workspace. No production deployment was performed.

## Confirmed repository defects

- `sih_frontend_latest` already routed dashboard and chat voice through the shared `VITE_API_BASE_URL`, but its shared configuration silently used `http://127.0.0.1:8000` if that build variable was absent. In a deployed browser this addresses the visitor's machine. The build now rejects missing, HTTP, and loopback API configuration. Development retains its existing local default.
- `sih_backend_latest/.env` currently lists only local frontend origins. This is evidence about the checkout, not the cloud environment. Set the real HTTPS frontend origin in the backend host's `CORS_ORIGINS`. Trailing slashes are now normalized.
- `sih_frontend_newai/pages/VictimDashboard.tsx` explicitly used a loopback voice URL. Voice now uses `VITE_API_BASE_URL`; its build has the same production URL validation.
- `sih_backend_newai/app/main.py` imported but never registered the voice router, and allowed only local origins. Registration and environment-based CORS are fixed.
- `sih_backend_newai/app/voice_service.py` contained an endpoint and imported itself instead of implementing transcription. It is now a real faster-whisper service, using the same implementation as latest. Its endpoint runs inference in a threadpool and translates controlled service errors to HTTP 503.

These defects do not establish which defect caused the deployed failure until the live bundle and backend are identified. Other old `newai` features still have legacy local URLs; they were outside this voice change. The `latest` application already has a shared API configuration for its other requests.

## Request contract

The production URL will be the build-time `VITE_API_BASE_URL`, with trailing slashes removed, plus `/api/victim/voice/transcribe`. The actual production hostname is UNKNOWN. `https://backend.example/api/victim/voice/transcribe` was used only for isolated frontend tests/builds, never as a production endpoint.

Both variants send `POST` and `Authorization: Bearer <access_token>`.

- Latest frontend + latest backend: raw Blob body, Content-Type matching recorded audio. No FormData fields.
- Newai frontend + newai backend: multipart FormData field `audio`; the browser supplies the multipart boundary. Do not manually set its Content-Type.
- Mixing these pairs produces format/validation errors (415/422), not a working upload.

The latest router is registered at `/api/victim/voice/transcribe`, and verifies the live victim account. Newai's missing registration was added. Existing auth behavior was retained.

The latest dashboard and chat now share voice request/error handling. HTTP failures include status and backend detail, including non-JSON gateway failure status. Transport failures report the target URL and frontend origin and explicitly state that no HTTP status is available. Browsers do not expose a backend reason when networking/CORS prevents reading a response.

## Whisper deployment

Inference is real faster-whisper; no production mock or fallback transcription was introduced. The services support `WHISPER_MODEL` (model name or baked model directory), `WHISPER_DOWNLOAD_ROOT`, `WHISPER_LOCAL_FILES_ONLY`, `WHISPER_CPU_THREADS`, `WHISPER_DEVICE`, and `WHISPER_COMPUTE_TYPE`. Defaults retain small / CPU / int8. Inference is limited to one request per worker to avoid concurrent cold model loads and memory spikes. Additional worker processes still allocate separate models.

Native runtime import, model initialization, and decoding/inference failures log their original exception and return a useful HTTP 503 reason. Latest also handles unwritable/full temporary storage with a controlled 503. An OS memory kill cannot be caught by Python and requires host logs and capacity adjustment.

To verify on the ACTUAL backend host:

1. Install the requirements belonging to the deployed backend. Newai requires `python-multipart` as already declared in its manifest.
2. Run `python -c "from app.voice_service import get_whisper_model; get_whisper_model(); print('Whisper model loaded')"` in the same image/user/environment as the running service. This performs real model initialization/download. For restricted runtime networking, bake/cache model files at build time and configure `WHISPER_MODEL` to that directory with `WHISPER_LOCAL_FILES_ONLY=true`.
3. Run `python -c "from app.voice_service import transcribe_audio; print(transcribe_audio('/tmp/known-speech.wav'))"` using an actual known speech recording. Check native platform support, available RAM, temporary disk, cache permissions, and host request timeouts if it fails. No inference success is claimed here.
4. Verify HTTPS GET `/` and the OpenAPI routes, then OPTIONS the voice URL with the real frontend Origin, Access-Control-Request-Method POST, and Access-Control-Request-Headers authorization,content-type. Expect the exact allowed frontend origin.
5. Use an authorized victim session for a real browser upload and inspect its POST status and response. Do not test with private victim audio without authorization.

Vite embeds environment variables at build time, so changing the frontend hosting setting requires a rebuild: https://vite.dev/guide/env-and-mode . Runtime installation and model download behavior: https://github.com/SYSTRAN/faster-whisper .

## Validation performed

- 14 frontend API/voice tests passed, including auth, raw-body/MIME contract, backend error details, gateway status, and network diagnostics.
- Four existing latest voice endpoint tests passed. Those unit tests stub inference and are NOT evidence of real Whisper execution.
- Both frontend TypeScript/Vite builds passed with an explicit HTTPS test URL. Latest build without an API URL was correctly rejected.
- Latest actual FastAPI app passed an isolated CORS preflight with a test HTTPS origin, allowed Authorization/Content-Type, and included the voice route. An in-memory test database was used.
- Newai route import in the local Python environment was blocked by missing python-multipart. Its manifest already declares the dependency. This is not evidence about cloud installation.
- No live cloud frontend bundle, HTTPS endpoint, CORS response for the real origin, authenticated production upload, deployment logs, memory limits, or real cloud transcription could be inspected without deployment details.

## Files changed

- `sih_frontend_latest/src/lib/config.ts`
- `sih_frontend_latest/src/lib/voice.ts` (new shared voice client)
- `sih_frontend_latest/pages/VictimDashboard.tsx`
- `sih_frontend_latest/src/components/monitoring/CaseChat.tsx`
- `sih_frontend_latest/vite.config.ts`
- `sih_frontend_latest/.env.example`
- `sih_frontend_latest/tests/voice.test.cjs`
- `sih_backend_latest/app/main.py`
- `sih_backend_latest/app/voice.py`
- `sih_backend_latest/app/voice_service.py`
- `sih_backend_latest/.env.example`
- `sih_frontend_newai/pages/VictimDashboard.tsx`
- `sih_frontend_newai/src/lib/config.ts`
- `sih_frontend_newai/vite.config.ts`
- `sih_frontend_newai/.env.example`
- `sih_backend_newai/app/main.py`
- `sih_backend_newai/app/voice.py`
- `sih_backend_newai/app/voice_service.py`
- `VOICE_CLOUD_FIX_REPORT.md`

Existing unrelated Speech-Emotion-Recognition submodule changes were left intact.
