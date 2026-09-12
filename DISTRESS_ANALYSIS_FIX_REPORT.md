# Distress analysis fix — 13 September 2026

## Findings before editing

- `AdaptiveQuestionnaire.tsx` sends the initial trimmed note with `POST /api/victim/questionnaire/submit`. Follow-up requests send null. The backend handler is `submit_questionnaire` in `app/questionnaire.py`.
- A non-empty normalized note creates an `AIAnalysis` only when the assessment has no existing analysis. Pending is committed with the assessment, then `analyze_saved_check_in` calls Gemini → Groq → OpenRouter. A validated result becomes `completed`; unsuccessful inference/storage becomes `failed`, or remains explicitly `pending` if even the failure update cannot be stored.
- Configured database: PostgreSQL, Neon host `ep-calm-unit-ae1lvg1r-pooler.c-2.us-east-2.aws.neon.tech`, database `neondb`. Gemini, Groq and OpenRouter keys were all detected. Values were not printed. This verifies the local configured application, not an unidentified remote deployment's environment.
- Counsellor ID 2 has exactly three entirely unassessed cases: `SAH-29B667612A7A`, `SAH-120D9052D023`, `SAH-14B5197AD63F`. Each had zero assessments and zero analyses. These match the symptom, but the displayed account has not been confirmed by the user.
- Before validation the cloud had one AI record, status `failed`, for `SAH-A6D3AA80338A`. Its source link passed the history filter. There were zero completed records, so a completed-record filter was not hiding existing results.
- Other assigned cases had questionnaire scores and saved notes without AI records. Their provenance was not established; no bulk backfill was performed.
- Local HEAD: `96e66d857aed694aa9323a0503dc5034ad2fbdbf`, with substantial pre-existing uncommitted work. No frontend/backend listeners were found on ports 5173/8000/8001/3000 and no Uvicorn process was identified. Remote deployment URLs/version metadata were unavailable; deployed commit parity is unverified.

## Root causes and changes

The three empty cases cannot have real scores until actual assessments exist. Separately, a safety-signal-created assessment did not save the written note supplied on submission, completed-request retries returned 409, historical empty case projections could conceal questionnaire scores, and score/failure labels did not accurately distinguish questionnaire and AI results.

Files changed in this task (pre-existing edits were preserved):

- `sih_backend_latest/app/database.py`: resolve the backend `.env` explicitly, preserving process-variable precedence.
- `sih_backend_latest/app/questionnaire.py`: save notes on existing assessments, analyze the saved note, serialize questionnaire/safety writes using PostgreSQL row locks, and return the existing analysis on completed-request retries. The existing unique assessment constraint prevents duplicate AI records.
- `sih_backend_latest/app/ai_history.py`: expose a non-secret failure explanation derived from the durable failed status, without a schema migration or fabricated result fields.
- `sih_backend_latest/app/monitoring.py`: read preserved questionnaire/analysis sources when the case projection has no score; return the latest attempt and questionnaire score separately.
- `sih_frontend_latest/src/lib/monitoring.ts`: corresponding API types.
- `sih_frontend_latest/src/components/monitoring/PriorityQueue.tsx`: explicit questionnaire/AI score labels, AI explanation, failed/pending states. Existing 15-second polling and manual refresh retained.
- `sih_frontend_latest/src/components/monitoring/CaseMonitoring.tsx`: accurate source/failure labels and complete paginated history.
- `sih_frontend_latest/src/components/monitoring/AnalysisHistory.tsx`: all analysis records through the existing authenticated paginated history API, including statuses, scores, risk, emotions and explanation. The chart remains limited to recent history.
- `sih_backend_latest/tests/test_questionnaire.py`, `tests/test_monitoring.py`: regression coverage for saved notes after safety signals, provider failure durability, idempotent completion retries, explicit failure output and missing historical projections.
- `sih_backend_latest/validate_distress_flow.py`: opt-in validation using one existing cloud note; no invented questionnaire answers, users or scores.

## Verification

- `python -m unittest tests.test_ai`: 15 passed.
- `python -m unittest tests.test_questionnaire tests.test_ai_workflow tests.test_monitoring`: 56 passed.
- Running all four suites in one process initially exposed an existing test-bootstrap/import-order issue (`no such table: users` in the standalone AI suite). Independent suite runs passed. This harness issue was not broadly refactored.
- `npm run build`: TypeScript and production build passed; existing large-bundle warning remains.
- Real cloud inference: added **AIAnalysis 2**, linked to **assessment 11**, **victim 15**, internal **case 10**, public case **SAH-DD11F3E02A3E**. Status **completed**, provider **Groq**, returned score **0**, risk **low**. These are the provider's validated values, not fallback or hard-coded values. Gemini returned HTTP **401**; Groq succeeded, so OpenRouter was not called for this attempt. All-provider fallback/failure cases are covered with mocked providers in tests.
- Independently read back that row from PostgreSQL after validation. It has both creation and completion timestamps.
- Application routes with real JWT verification and existing account/role lookups allowed the existing victim and assigned counsellor to read the result. The assigned counsellor's `/api/monitoring/cases` returned analysis 2 as its latest successful result. Validation used a local FastAPI test host against cloud PostgreSQL, not a deployed browser session.
- The existing assessment and note were retained. No users were created, no data was migrated, no historical records were deleted, and the prior failed analysis was preserved. One real analysis and its normal case projection update were written. SER was not involved.

## Remaining deployment and acceptance work

Deploy/restart the changed latest backend and deploy the rebuilt latest frontend with the intended API URL. Confirm deployed versions and cloud configuration using the actual deployment URLs. The Gemini credential needs attention because its live request returned 401; Groq currently provides working fallback.

Cloud validation started from a saved assessment, so it does not claim to test a fresh victim questionnaire submission or a deployed browser session. The questionnaire submission path passed isolated integration tests. A fresh end-to-end cloud submission still requires actual questionnaire answers and a note from an existing victim; no responses were invented for the three empty cases.
