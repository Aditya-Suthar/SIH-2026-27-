# Sahas — final demo setup

Read this file before older prompt-specific setup notes. This package includes Prompts 1–3 plus the final workflow completion. It updates source code; it does not update a previously running server automatically.

## Existing project / PostgreSQL

1. Back up your database and preserve your own `.env` before replacing source files. No real credentials or database files are shipped in this archive.
2. In `sih_backend`, activate your Python environment and run `python -m pip install -r requirements.txt`.
3. Set `DATABASE_URL` in your `.env` to your **existing database**. The source no longer contains the old hardcoded PostgreSQL password. If omitted, the local default is a new SQLite file `sahas.db`; that is not your existing PostgreSQL data.
4. Set a random `JWT_SECRET` with at least 32 bytes. You can generate one locally with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Keep it private. Existing tokens signed with the old placeholder secret are invalid; sign in again.
5. Stop backend workers; run `python -m app.migrate_final` once, then `python -m uvicorn app.main:app --reload`. Back up before applying migrations. SQLite migration tests passed; a live PostgreSQL upgrade was not available for verification.
6. In `sih_frontend`, run `npm ci` and `npm run dev`. Restart any old frontend process. Open the URL printed by Vite, normally `http://localhost:5173`.
7. Leave your AI provider variables from Prompt 1 in the backend `.env`. Gemini → Groq → OpenRouter remains unchanged. With no working provider, text still saves and analysis shows failed/unavailable.

The frontend accepts `VITE_API_BASE_URL` (see its `.env.example`). Backend `CORS_ORIGINS` must list the frontend origins. No provider keys belong in frontend variables.

## Fresh, isolated demo on Windows / PowerShell

Tested with Python 3.12 and Node 24. Use two terminals. Example backend preparation:

```powershell
cd sih_backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`: set `DATABASE_URL=sqlite:///./sahas-demo.db`, a private random `JWT_SECRET`, and optional provider keys. Then:

```powershell
python -m app.seed_demo
python -m uvicorn app.main:app --reload
```

The seed command asks you to choose and confirm a password. It refuses production, non-SQLite databases, non-demo filenames and databases containing users. It creates **synthetic** accounts/history only; it never calls an AI provider and never replaces existing users. Use that password for:

- `authority@demo.example` — Authority
- `counsellor@demo.example` — Counsellor
- `victim1@demo.example` through `victim4@demo.example` — Victim

All seeded observations explicitly say `SYNTHETIC DEMO`; no real victim data is included. A provider enum value is required by the existing schema on these completed fixtures, but it is not evidence of an actual provider call. New submissions always use the normal configured AI service.

Frontend terminal:

```powershell
cd sih_frontend
npm ci
npm run dev
```

For a clean database without fixtures, run `python -m app.migrate_final` instead of the seed command. Provision privileged accounts locally:

```powershell
python -m app.manage --role authority --email officer@example.com --name "Demo Officer"
python -m app.manage --role counsellor --email counsellor@example.com --name "Demo Counsellor"
```

Each command securely prompts for a password. Public signup creates victims only and automatically opens their support case. Authority → Counsellors assigns a counsellor. Existing victims without a case can open the dashboard to create one.

## Five-minute demo path

1. **Authority:** `/authority` → `/counsellors` to assign a newly registered victim. Open `/analytics`, `/reports` and `/alerts` for real scoped data, CSV export and support follow-up.
2. **Victim:** `/victim` → complete questionnaire / optional text → submit. Open “Talk to Counsellor” and send a meaningful message. Try “Request Call Back”; the persisted request appears to staff. `/sessions` requests a future appointment.
3. **Counsellor:** `/counsellor` shows ordered priorities. Open `DEMO-1` for rising synthetic history, `DEMO-2` for stable high history, `DEMO-3` for improvement, `DEMO-4` for no history. `/cases/{caseId}` combines explanation, graph, review action and human chat.
4. Review a case with “Mark as reviewed”. A newer completed analysis requires its own acknowledgement. `/counsellor/messages` provides a separate case conversation list.
5. Confirm the victim's appointment in `/sessions`, acknowledge their callback request in `/alerts`, and check the saved results after refresh.

Use separate browser profiles for simultaneous roles. Tabs in one profile share login storage. Chat polls every 5 seconds and monitoring every 15 seconds while visible. Trend detection requires at least three distinct UTC days; sending many messages today alone does not establish a trend.

## Verification and limits

- Backend: `python -m unittest discover -s tests -v` — **59 passed, 0 failed**.
- Frontend: `npm run build` — **passed** (non-blocking bundle-size advisory).
- Seed + actual login/API smoke check for victim, counsellor and authority — passed with isolated synthetic data.
- **Browser rendering / click-through was blocked** by the cloud browser (`ERR_BLOCKED_BY_CLIENT` for localhost). No successful visual or browser end-to-end verification is claimed. Perform the short demo path above on your machine.
- Voice/Whisper/emotion2vec, video calls, SMS/IVRS, email delivery, push notifications, automatic emergency dispatch, password recovery and a production operations/security review remain outside this release. The app clearly does not claim to dispatch emergency help.
- Local SQLite is for a single-machine demo. Use the existing PostgreSQL deployment for stronger concurrent transaction behavior; validate its migration on a backup/staging database first.
- Priority/trend thresholds are deterministic engineering conventions, not clinically validated predictions. This is human decision support.

See `IMPLEMENTATION_REPORT.md` for every changed file, algorithms, APIs, access rules and the remaining limitations.

## Voice check-ins (added after final completion)

Victims can now record a short voice check-in from the dashboard. Sahas sends the recording to its own backend, transcribes it locally with `faster-whisper`, returns an editable transcript, and only runs the existing distress-analysis workflow after the victim presses **Submit Check-in**.

Install/update backend dependencies before starting the server:

```powershell
python -m pip install -r requirements.txt
```

Default voice settings are in `sih_backend/.env.example`. The default model is multilingual Whisper `small` on CPU/int8. The first transcription can download the model; for a reliable offline demo, perform one real transcription beforehand so the model is cached.

See `VOICE_IMPLEMENTATION.md` for the endpoint, privacy behavior, and flow.
