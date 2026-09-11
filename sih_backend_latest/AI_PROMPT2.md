# AI Prompt 2 — persistent AI analysis of victim check-ins

## Implemented workflow

The existing victim dashboard's **Optional text check-in** input was only held in
React state. The assessment POST omitted it. The existing backend had no message,
journal or case-description creation endpoint; victim chat and counsellor chat
were local/demo state. This change connects that existing check-in field to the
existing assessment workflow rather than inventing another messaging system.

1. Victim enters the optional note and submits the existing questionnaire.
2. The existing bearer authentication checks the request. For text submissions,
   the backend also verifies the live account and role, and finds the case through
   its existing `Case.victim_id` relationship.
3. Backend validates the note, saves it once on `Assessment.note`, and commits the
   assessment, existing questionnaire updates and a `pending` AI record together.
4. Only after that transaction commits, the sync endpoint's worker calls the
   unchanged async Prompt 1 service using `asyncio.run`. No database transaction
   is held while waiting for providers.
5. The existing Gemini → Groq → OpenRouter chain returns validated indicators.
   The persistence boundary validates them again and stores a completed result.
6. The check-in POST returns its existing questionnaire score/risk and an additive
   `ai_analysis` ID/status. Authorized clients retrieve detailed history by case.

The real workflow does not depend on `AI_TEST_ENDPOINT_ENABLED`. That switch still
controls only Prompt 1's development endpoint. No live providers were called in
automated tests. No cloud calls or API keys are added to the frontend.

## Files changed and why

Paths are relative to the project root.

| File | Change | Why |
| --- | --- | --- |
| `sih_backend/app/cases.py` | Existing assessment POST saves note and pending analysis, commits before inference, exposes status, safely handles initial storage errors | Integrates into the real submission while preserving its questionnaire response and updates |
| `sih_backend/app/models.py` | Nullable assessment note and dedicated `AIAnalysis` model | Keeps source text once and retains each result with foreign keys |
| `sih_backend/app/schemas.py` | Optional validated `note` on `AssessmentCreate` | Accepts existing requests unchanged and validates the newly connected input |
| `sih_backend/app/main.py` | Import/register history router | Exposes authorized history without changing existing routers |
| `sih_frontend/pages/VictimDashboard.tsx` | Sends existing note, limits length, prevents repeat clicks while waiting, clears after successful save, reports failed/pending analysis, adds cloud-analysis explanation | Makes the existing check-in input functional without redesigning the page |
| `sih_backend/app/ai_workflow.py` (new) | Post-commit inference, validation and result persistence with isolated failure handling | Keeps provider/persistence failures from destroying saved check-ins |
| `sih_backend/app/ai_history.py` (new) | Response schemas, live account check, scoped and paginated chronological history | Exposes records only through existing user/case relationships |
| `sih_backend/app/migrate_ai_prompt2.py` (new) | Repeatable additive database upgrade | Adds the note to existing databases; `create_all()` alone cannot add columns |
| `sih_backend/tests/test_ai_workflow.py` (new) | 16 workflow, access and migration tests with mocked AI | Verifies persistence, isolation, failures and compatibility without API quota |
| `sih_backend/AI_PROMPT2.md` (new) | This report, deployment steps, API examples and limitations | Provides a concrete handoff for local use and Prompt 3 |

No dependencies were added or changed. Prompt 1's `ai_service.py`, `ai.py`,
`tests/test_ai.py`, `requirements.txt`, `.env.example` and `AI_SETUP.md` remain
byte-for-byte unchanged. Authentication, database connection configuration, case
models' existing fields, messaging screens and counsellor/authority behavior
remain intact. Existing core files receive only the changes listed above.

## Database changes

`assessments.note`: nullable TEXT. Original optional note, at most 4,000 characters
at the API boundary. Existing rows get NULL; old scores and answers are preserved.
Absent, null, empty and whitespace-only notes are treated as no text, so ordinary
questionnaire-only submissions do not create an AI record or call a provider.

New `ai_analyses` table:

| Column | Meaning |
| --- | --- |
| `id` | Analysis primary key |
| `assessment_id` | Unique foreign key to the source assessment |
| `case_id` | Foreign key to the source case |
| `victim_id` | Foreign key to the authenticated submitting user |
| `status` | pending / completed / failed |
| `distress_score` | Nullable integer 0–100 |
| `risk_level` | Nullable low / medium / high / critical |
| `emotions` | Nullable JSON list of short emotion names |
| `requires_attention` | Nullable boolean; NULL is unknown, not false |
| `reason` | Nullable concise analysis summary, maximum 400 characters |
| `provider` | Nullable gemini / groq / openrouter |
| `created_at` | UTC time the pending record was created |
| `finished_at` | UTC time analysis was completed or marked failed |

Foreign keys prevent dangling source/user/case references. The submitting endpoint
derives all three associations server-side and never takes those IDs from the
request body. History retrieval additionally joins the assessment to the same case.
The unique assessment key prevents multiple AI records for a single source; each
new check-in creates a new assessment and analysis, preserving earlier results.
An index on case/time/ID supports history, plus a victim index. Database constraints
check status, bounds, enums and completed-versus-empty result states.

No original text is duplicated into the AI table. No keys, raw provider payloads
or internal exceptions are stored. Failed/pending rows have NULL analysis fields.
Questionnaire scores and AI scores remain distinct, with different field naming
and purpose; the existing case risk is still updated by the questionnaire only.

## API changes

### Modified: POST /api/victim/assessment

Existing bearer authentication and victim-only submission remain. Existing
questionnaire fields retain their behavior. New optional field: `note`.

```json
{
  "mood": 1,
  "anxiety": 1,
  "sleep": 1,
  "hopelessness": 1,
  "social_withdrawal": 1,
  "self_harm_thoughts": 1,
  "note": "I feel afraid and have been struggling to sleep."
}
```

Example response:

```json
{
  "message": "Assessment submitted successfully",
  "distressScore": 25,
  "riskLevel": "Moderate",
  "ai_analysis": {"id": 1, "status": "completed"}
}
```

`distressScore` and `riskLevel` above are the existing questionnaire results,
**not** the AI indicators. Retrieve the AI values from the history endpoint.
When no meaningful note was supplied, the response is exactly the prior three
fields; `ai_analysis` is absent. Failed inference still returns HTTP 200 after the
source is saved, with status `failed`. Missing account/role/ownership and invalid
input fail before AI runs. Extra submitted identity IDs are ignored by the existing
schema and are never used to associate any record.

### New: GET /api/cases/{case_id}/ai-analyses

`case_id` in the URL is the existing public case identifier, such as `SAH-A-0001`.
Bearer authentication is required. Optional `limit` (1–100, default 50) and
`offset` (>=0, default 0). Results are ascending by `created_at`, then `id`.
This endpoint does not return raw source notes or run/retry AI.

```json
{
  "items": [
    {
      "id": 1,
      "assessment_id": 7,
      "source_type": "assessment",
      "case_id": 10,
      "victim_id": 1,
      "status": "completed",
      "distress_score": 65,
      "risk_level": "high",
      "emotions": ["fear"],
      "requires_attention": true,
      "reason": "The text expresses fear and difficulty sleeping.",
      "provider": "groq",
      "created_at": "2026-09-10T15:00:00+00:00",
      "finished_at": "2026-09-10T15:00:02+00:00"
    }
  ],
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

Numeric `case_id` in each returned record is the database foreign key. All values
above are illustrative. `has_more` tells clients whether to fetch another page.
The endpoint includes failed and pending rows; clients must not interpret their
NULL scores as zero when building charts in Prompt 3.

## Authorization

| Caller | Permitted history |
| --- | --- |
| Victim | Only their current owned case and only records originally submitted by that user |
| Counsellor | Cases currently assigned through `assigned_counsellor_id` |
| Authority | All cases, matching the existing case API's authority permission |
| Other roles | Denied with 403 |
| Missing/invalid bearer token | Denied by existing authentication |
| Deleted account or role no longer matching token | Denied with 401 |

Inaccessible and nonexistent cases both return 404. Case reassignment removes
former counsellor access immediately. Reassigning a case to another victim does
not give that victim access to the previous victim's records. As in the current
application, the assessment POST selects the existing first owned case; this
prompt does not add a client-controlled case selector.

These checks preserve the existing authentication trust boundary. The supplied
baseline still contains a hardcoded JWT signing placeholder and allows public
role registration. Those existing weaknesses mean the application as a whole
cannot be claimed production-secure; they were deliberately not rewritten under
the locked scope. Preserve newer secure local auth files if you already have them.

## Failure behavior

- **All providers fail or output is malformed:** the source is already committed;
  mark the analysis failed, leave all indicator fields NULL, and return success
  for the check-in. Never fabricate a low/zero score.
- **Unexpected AI exception:** same safe failed state; only a fixed diagnostic
  category is logged, not its message/traceback.
- **Result write fails:** roll back only the result transaction and attempt to
  persist a clean failed state. The original source remains saved.
- **Database still unavailable for the failure update:** return/expose pending;
  the original pending row and source remain durable. It honestly means incomplete,
  not successful or queued for an automatic retry.
- **Process stops after source commit:** the durable pending row remains. No
  automatic recovery/retry worker is included in this prompt.
- **Initial source transaction fails:** return generic 503, roll back, and do not
  call AI or claim the check-in was saved. This is a database save failure, not
  an inference failure. SQL exception text is not exposed or logged by this route.

AI may add up to approximately 30 seconds to a text submission through Prompt 1's
bounded fallback chain. The existing synchronous route runs in FastAPI's worker
pool, so inference does not block its main async event loop. The submit button is
disabled during the wait. No durable work queue, automatic retry or network-retry
idempotency is added; if a client retries a completed POST it is a new check-in.

## Local upgrade and test commands (PowerShell)

Retain your existing `.env`, PostgreSQL database and Git history. The source ZIP
omits secrets, dependency folders and generated artifacts. If your local project
has newer code, merge the listed changes rather than overwriting its auth files.
Stop backend workers while applying the additive migration. Do not drop tables.

From the project root, with your existing PostgreSQL service available:

```powershell
cd sih_backend
.\.venv\Scripts\python.exe -m app.migrate_ai_prompt2
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If you use an activated environment instead, replace the executable with `python`.
Use the existing Prompt 1 setup if this is a new environment. No new packages or
environment variables are needed. Existing GEMINI_API_KEY, GROQ_API_KEY and
OPENROUTER_API_KEY settings continue to apply.

The migration supports a fresh database and an existing core schema, is safe to
rerun sequentially, preserves old rows, and uses the existing database engine.
It must be run explicitly for an existing database because app startup's existing
`create_all()` does not add `assessments.note`. Run it once before workers start,
not concurrently from each worker. It does not fix earlier unrelated missing
columns or migrations.

In another terminal, log in and test with synthetic text:

```powershell
$cred = Get-Credential -Message 'Existing victim account email and password'
$loginBody = @{ email=$cred.UserName; password=$cred.GetNetworkCredential().Password; role='victim' } | ConvertTo-Json
$session = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/login' -Method Post -ContentType 'application/json' -Body $loginBody
$headers = @{ Authorization="Bearer $($session.access_token)" }
$dashboard = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/victim/dashboard' -Headers $headers
$body = @{ mood=1; anxiety=1; sleep=1; hopelessness=1; social_withdrawal=1; self_harm_thoughts=1; note='I feel afraid and have been struggling to sleep.' } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/victim/assessment' -Method Post -ContentType 'application/json' -Headers $headers -Body $body
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/cases/$($dashboard.caseId)/ai-analyses" -Headers $headers
```

The victim must already be linked to a case, as required by the existing workflow.
Alternatively, use the dashboard's existing optional text field and Submit Check-in.
Frontend verification locally:

```powershell
cd sih_frontend
npm ci
npm run build
npm run dev
```

## Tests and checks executed

**31 backend tests passed: 15 unchanged Prompt 1 tests plus 16 new tests.**
New tests cover:

1. Source visible on a separate DB connection before AI; exact persisted fields.
2. Client-supplied user/case/source IDs cannot override server associations.
3. Multiple submissions preserve history and chronological pagination.
4. Victim/counsellor/authority/unknown/invalid account access matrix.
5. Reassignment enforces current case access and original victim ownership.
6. Numeric-only, null and blank-note submissions retain the original contract.
7. Invalid notes and unauthorized submissions do not call AI.
8. Unavailable service and malformed normalized responses preserve sources.
9. Real Prompt 1 fallback over mocked HTTP fails safely without secrets in logs.
10. Initial source storage failure returns safe 503 without calling AI.
11. Real check-in inference is independent of the development endpoint switch.
12. Result commit failure preserves the source and marks failed.
13. Persistent result-storage outage leaves an honest pending record.
14. Existing case and victim dashboard routes still work.
15. Existing database migration preserves data and is repeatable.
16. Fresh database migration is repeatable.

Executed on Python 3.12 using isolated SQLite databases with foreign keys enabled
for workflow tests. No real provider HTTP or user PostgreSQL was used by tests.
App import/startup is exercised by TestClient. Python compilation and `pip check`
pass. Frontend `tsc -b` passes using the dependencies supplied in the original ZIP.

Production frontend bundling was attempted but blocked by the supplied Windows
node_modules lacking Linux `@rolldown/binding-linux-x64-gnu`. No manifest/lockfile
was altered to work around this environment issue. Run `npm ci` and `npm run build`
on the target machine. Live PostgreSQL migration, Windows execution and live AI
quality remain unverified. Existing dependency deprecation/JWT key warnings remain.

## Intentionally left for Prompt 3 or later

- Dashboard charts and presentation of real AI history.
- Worsening/improving calculations and counsellor prioritization.
- Reviewed escalation/notification logic consuming the stored indicators.
- Clear presentation of questionnaire scores versus AI text indicators.
- Recovery policy for stale pending/failed records, if needed for deployment.
- Final incomplete counsellor/authority pages and actual backend chat integration.

No speech analysis, diagnosis, automatic emergency action, long-term AI memory,
new messaging architecture, or retroactive analysis of old check-ins was added.
