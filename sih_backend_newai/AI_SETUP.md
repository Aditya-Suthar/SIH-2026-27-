# Prompt 1 of 3 — cloud AI infrastructure

Implemented one async internal operation, `await analyze_distress(message)`, with
strict validated results and the fixed chain **Gemini → Groq → OpenRouter → 503**.
Every provider is tried at most once. Missing keys are skipped. HTTP failures,
timeouts, connection failures, malformed JSON, blocked/truncated completions and
invalid schemas all trigger fallback. Invalid client input returns 422 without
contacting providers. No AI records are persisted and no UI changes were made.

## Files

Created:
- Repository `.gitignore`: ignore environment secrets, caches and dependencies.
- `sih_backend/.env.example`: key placeholders, model defaults, endpoint switch.
- `sih_backend/app/ai_service.py`: settings, shared prompt, strict schemas,
  provider adapters, bounded requests, fallback and safe diagnostics.
- `sih_backend/app/ai.py`: authenticated opt-in development endpoint.
- `sih_backend/tests/test_ai.py`: quota-free service and full-app tests.
- `sih_backend/AI_SETUP.md`: this implementation report and local instructions.

Modified:
- `sih_backend/app/main.py`: only import and register the new router.
- `sih_backend/requirements.txt`: declare Pydantic v2 and missing dependencies
  required by existing backend imports. Existing dependency entries retained.

`httpx` and `python-dotenv` were already listed; no provider SDKs were added.
Added `pydantic>=2,<3`, `PyJWT`, `passlib[bcrypt]`, `bcrypt>=4.0,<4.1`,
`psycopg2-binary`, and `email-validator`. The bcrypt bound keeps existing Passlib
hashing compatible; actual hash/verify was tested. No unrelated package upgrades
were requested. Tests use Python's standard-library unittest.

## Models and costs

Official documentation checked on 10 September 2026:

| Provider | Default model | Basis |
| --- | --- | --- |
| Gemini | `gemini-2.5-flash-lite` | Standard text input/output listed as free-tier eligible |
| Groq | `openai/gpt-oss-20b` | Listed in current free-plan limits; low reasoning effort used |
| OpenRouter | `openrouter/free` | Routes only to currently available free models; requests JSON support |

Sources:
- https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-flash-lite
- https://ai.google.dev/api/generate-content
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/models
- https://console.groq.com/docs/structured-outputs
- https://openrouter.ai/openrouter/free

The current Groq models page labels the older Llama 3.1/3.3 models Enterprise;
this implementation does not assume their old free-tier availability.

Models are centralized and overridden by GEMINI_MODEL, GROQ_MODEL and
OPENROUTER_MODEL. Paid OpenRouter overrides are rejected: only `openrouter/free`
or an explicit `:free` model is accepted. No paid fallback is configured.
Gemini/Groq billing depends on your account: use free-plan projects and avoid
enabling paid billing for this demo. A model ID alone cannot enforce account
billing settings. Quotas and access can change; no guarantee of free availability.

## Contract and limits

`POST /api/ai/analyze`, with an existing bearer login token:

```json
{"message":"I feel scared and haven't slept properly."}
```

Illustrative response (actual provider output varies):

```json
{
  "distress_score": 65,
  "risk_level": "high",
  "emotions": ["fear"],
  "requires_attention": true,
  "reason": "The message expresses fear and difficulty sleeping.",
  "provider": "gemini"
}
```

- Message: string, stripped, 1–4,000 characters; unknown request fields rejected.
- Strict result types: no numeric strings, floats for score, or string booleans.
- Score: integer 0–100. Emotions: at most 8 names, 1–32 characters each.
- Reason: 1–400 characters. Unknown/missing output fields are rejected.
- Backend assigns provider; the model cannot spoof it.
- Shared demo convention: low 0–24, medium 25–49, high 50–74, critical 75–100.
  Attention is true for high/critical. Inconsistent outputs trigger fallback.
  These thresholds are unvalidated demo conventions, not clinical cutoffs.
- Each provider has a 10-second overall deadline (up to approximately 30 seconds
  for the chain), with 3-second connect and 8-second HTTP operation timeouts.
- Responses are bounded to 64 KiB; model JSON is bounded to 8,192 characters.
- One complete JSON code fence is tolerated; surrounding prose and duplicate JSON
  keys are rejected. Blocked/truncated generations are not accepted.
- All providers failing returns 503 with exactly:
  `{"detail":"AI analysis is temporarily unavailable."}`
- Disabled endpoint: 404. Missing/invalid authentication: 401 or 403 according to
  the existing auth implementation. No provider keys/details are returned.

## Privacy and scope

Only submitted text and the shared analysis instructions are sent. No account,
case, email, token or database context is forwarded. Logs contain only provider,
error category and HTTP status; never full messages, keys or exception bodies.
Fallback may send the same text to up to three third-party services. Use synthetic
examples for development: free inference is not inherently private; Gemini's
pricing page explicitly says free-tier data may be used to improve products.
Do not enable HTTP wire/header/body debug logging around sensitive traffic.

The prompt prohibits diagnosis, unsupported inference and conversational advice.
Schema validation does not establish clinical accuracy or eliminate model errors.
There is no history, trends, dashboard integration, authority escalation, speech,
medical diagnosis, or long-term memory in this change.

## Run locally — Windows PowerShell

If your working project has newer fixes, copy ONLY the files listed above into it.
For main.py merge the new router import/registration instead of replacing newer
code. This source archive excludes .git, .env, virtual environments, node_modules
and bytecode; retain your existing local environment and Git history.

From your project root:

```powershell
cd sih_backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Add the entries from `.env.example` to your existing `sih_backend/.env` without
replacing other settings. Put your three keys there and set:

```dotenv
AI_TEST_ENDPOINT_ENABLED=true
```

Process environment variables take precedence over this file. Missing keys are
skipped. Changes are read on process restart (restart after editing .env).

Start your existing local PostgreSQL server/database as usual, then:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second PowerShell terminal, log in with an existing account and test:

```powershell
$cred = Get-Credential -Message 'Enter your existing account email and password'
$loginBody = @{
    email = $cred.UserName
    password = $cred.GetNetworkCredential().Password
    role = 'victim'
} | ConvertTo-Json
$session = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/login' -Method Post -ContentType 'application/json' -Body $loginBody
$headers = @{ Authorization = "Bearer $($session.access_token)" }
$body = @{ message = "I feel scared and haven't slept properly." } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/ai/analyze' -Method Post -Headers $headers -ContentType 'application/json' -Body $body
```

Set role to your existing account's role if it is not victim. You can also open
http://127.0.0.1:8000/docs and use Authorize with the login token. Leave the test
endpoint disabled outside development. It shares the existing auth trust boundary.

## Verification and unresolved baseline issues

Executed under Python 3.12:
- 15 unittest tests, including multiple subcases: passed.
- Actual app import, table creation and TestClient startup with an isolated SQLite
  engine substituted in tests: passed. No PostgreSQL credentials used by tests.
- Full endpoint → actual service → mocked provider HTTP → normalized response:
  passed, including all-provider failure → generic 503.
- Provider order, timeouts, network/HTTP errors, malformed/schema-invalid output,
  blocked/truncated output, strict bounds, missing keys, no paid OpenRouter
  request, no secret in logs/errors, and no AI DB writes: passed.
- Existing root, JWT-protected role routes, case access restrictions, victim
  dashboard route, and password hash/verify smoke checks: passed.
- `python -m compileall -q app`: passed.
- `python -m pip check`: no broken requirements.
- No prior test suite was included in the source archive.

Live provider inference, clinical quality, Windows runtime and your PostgreSQL
instance were not tested. No live API quota was consumed. Existing dependencies
emit deprecation warnings; the existing JWT key emits a short-key warning.

The supplied archive still has a hardcoded JWT placeholder, unrestricted role
registration, and a hardcoded PostgreSQL connection string. Those pre-existing
issues are not fixed here because Prompt 1 explicitly preserves authentication
and database logic. Their earlier fixes are absent from this upload. Do not
replace newer secure local files with these older copies. Full production startup
still needs the original PostgreSQL setup; the isolated test does not verify it.
