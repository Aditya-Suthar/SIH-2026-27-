Verification of Authority Alerts and saved text analysis — 13 September 2026

Local changes are based on commit `4c5ab4d584e8355bccabee9fb747cd5ab7c7a707`.
The deployed frontend/backend URLs and their commit metadata were not available.
The local frontend defaults to `http://127.0.0.1:8000`; no local frontend environment override was present.
The configured backend uses the existing Neon PostgreSQL `neondb` database.
This does not establish which database or build the deployed backend uses.

Confirmed causes and fixes

- `useRemote` retained protected data after polling errors, including 401/403/404.
  The request helper collapsed 403 and 404 into the same account-permission message.
  It now preserves HTTP status, clears inaccessible data, clears all mounted remote
  resources on expired authentication, removes session storage and redirects to login.
  Temporary refresh failures say “Refresh failed” in their affected section.
- Support requests and monitoring indicators already used separate hooks. Each now
  has an explicitly labelled error and manual refresh control. Indicator review errors
  are caught and followed by a queue refresh. Failed loading no longer says the queue is empty.
- Saved Check-ins previously displayed “Saved” for both completed and not-requested AI.
  It now displays all four requested AI statuses independently of questionnaire scores.
- The case graph previously showed text-AI only. It now has independently labelled
  questionnaire and text-AI series, chronological timestamps, visible single points,
  and no numerical entries for unavailable/pending/failed observations. A legitimate
  completed AI zero is retained. The backend's insufficient-distinct-days trend state
  is displayed explicitly. The existing history pagination retains access beyond the
  latest 200 AI observations used by the chart.
- A null current safety score could previously fall back to an older AI score.
  Fallback now applies only to absent/legacy projections. Separate current questionnaire
  evidence includes risk, timestamp and a redacted safety-override explanation.
- Starting a questionnaire created a session through GET. Start now uses
  `POST /api/victim/questionnaire`; GET is read-only. Deploy frontend and backend together.
- Historical evidence remains selected by indicator ID. Source lookups are checked
  against the case. Migration repair now backfills links without deleting/rescoring
  history; ordinary indicator ensures preserve existing snapshots. Only explicit
  questionnaire writes may update the same in-progress questionnaire indicator.

Alerts request inventory

All production statuses remain unverified until deployment URLs/access are supplied.
The following statuses were verified through the local API using existing cloud accounts
and cloud PostgreSQL, with read-only database transactions.

| Request | Caller and timing | Cloud-backed local API result |
| --- | --- | --- |
| GET `/api/support-requests` | Authority; mount, 15-second visible-tab polling, manual refresh | 200 on both repeated reads |
| GET `/api/monitoring/indicators` | Authority; mount, polling, manual refresh, after review | 200 on both repeated reads |
| GET `/api/monitoring/summary` | Authority Analytics/dashboard; not mounted by Alerts | 200 on both repeated reads |
| POST `/api/monitoring/indicators/{id}/review` | Authority/counsellor action; no polling | Scoped acknowledgement and exact-ID refresh tested in isolated tests; no live review changed |
| PATCH `/api/support-requests/{id}` | Staff action | Existing scoped operation covered by operations tests; no live support request changed |

No deployed network trace was available to establish whether the reported error came
from support requests, the queue, a polling response, a stale deployment, or session expiry.
The shared hook defect is confirmed in code and regression tests; the deployed trigger is not.

Recent persisted assessments (all 16 assessed records at audit time)

Zero note characters means no non-empty note. Missing analyses below mean no persisted
attempt exists, not that an attempt completed. No note text or previews were output.

| Assessment | Case | Note characters | Analysis | Status | Provider | Score/risk/emotions | Counsellor access |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| 16 | SAH-1CD051291C38 | 57 | 3 | completed | groq | 30 / medium / sad, anxious, confused | No counsellor assigned; victim API 200 |
| 15 | SAH-76B04B4D7F6D | 0 | none | not requested | none | unavailable | Assigned; no AI row to retrieve |
| 14 | SAH-76B04B4D7F6D | 0 | none | not requested | none | unavailable | Assigned; no AI row to retrieve |
| 13 | SAH-BB499132C0A7 | 0 | none | not requested | none | unavailable | Assigned; no AI row to retrieve |
| 12 | SAH-A6D3AA80338A | 0 | none | not requested | none | unavailable | Assigned; no AI row to retrieve |
| 11 | SAH-DD11F3E02A3E | 34 | 2 | completed | groq | 0 / low / empty emotion list | Victim and assigned counsellor API 200, exact row found |
| 10 | SAH-DD11F3E02A3E | 34 | none | no persisted attempt | none | unavailable | Assigned; no AI row to retrieve |
| 9 | SAH-DD11F3E02A3E | 34 | none | no persisted attempt | none | unavailable | Assigned; no AI row to retrieve |
| 8 | SAH-9D0CC12642A6 | 35 | none | no persisted attempt | none | unavailable | Assigned; no AI row to retrieve |
| 7 | SAH-9D0CC12642A6 | 35 | none | no persisted attempt | none | unavailable | Assigned; no AI row to retrieve |
| 6 | SAH-9D0CC12642A6 | 35 | none | no persisted attempt | none | unavailable | Assigned; no AI row to retrieve |
| 5 | SAH-8839C2090E8C | 34 | none | no persisted attempt | none | unavailable | Assigned; no AI row to retrieve |
| 4 | SAH-8839C2090E8C | 34 | none | no persisted attempt | none | unavailable | Assigned; no AI row to retrieve |
| 3 | SAH-8839C2090E8C | 34 | none | no persisted attempt | none | unavailable | Assigned; no AI row to retrieve |
| 2 | SAH-A6D3AA80338A | 0 | none | not requested | none | unavailable | Assigned; no AI row to retrieve |
| 1 | SAH-A6D3AA80338A | 30 | 1 | failed | none | null score/risk/emotions | Victim and assigned counsellor API 200, exact row found |

The safe failure classification for analysis 1 is “failed, no valid result saved.”
The database does not persist a provider failure category, so its specific historical
HTTP error cannot be reconstructed from this row. No pending analyses were present.
Groq has two real completed results. This proves past persisted Groq successes, not
current deployed fallback health. Local Gemini, Groq and OpenRouter keys were detected
as present; key values were never printed. Deployed Gemini 401 and deployed key detection
remain unverified. Provider order and the existing bounded provider calls were preserved.

The adaptive submission code persists its assessment and one uniquely linked pending
analysis before inference. Session-row locking and completed-submission replay protect
against duplicate attempts. Provider exceptions persist failed status and null result
fields while retaining the questionnaire. These behaviours pass mocked-provider API tests.
Existing older notes without attempts were not silently analyzed or inserted into history.
Worker crashes or simultaneous result/failure-storage outages are handled by the new
`recover_pending_analyses.py` maintenance command: attempts still pending after ten minutes
become failed with null results. Active attempts and terminal results are preserved.
Configure this command once per minute in the deployed scheduler; that schedule is not
yet installed because deployment access is unavailable. No deployed-provider success
or active deployed recovery schedule is claimed by this verification.

Cloud checks and database changes

- No cloud data/schema writes or migrations were performed in this task.
- The audit compared row fingerprints before/after reads for users, cases, assessments,
  AI analyses, monitoring indicators, questionnaire sessions, support requests and analysis reviews.
  All fingerprints matched. No users, cases, scores, notes, history or review states were changed.
- Existing cloud indicator 7 returned snapshot 66 with current score 48.
  Existing cloud indicator 9 returned snapshot 48 with current score 48.
- All existing AI analyses were retrievable by their original victim; both analyses
  whose cases have assigned counsellors were retrieved by those counsellors.
- Local API read checks used existing-account signed tokens internally and PostgreSQL
  read-only transactions. They were not requests to a deployed backend and did not test
  browser login, deployed polling, or deployed CORS behaviour.

Files changed

- Backend: `app/ai_workflow.py`, `app/case_state.py`, `app/migrate_indicator_evidence.py`, `app/monitoring.py`,
  `app/questionnaire.py`; `tests/test_ai.py`, `tests/test_monitoring.py`,
  `tests/test_questionnaire.py`; new `audit_cloud_status.py`, `recover_pending_analyses.py` and this report.
- Frontend: `src/lib/api.ts`, `src/lib/monitoring.ts`, `src/pages/Operations.tsx`,
  `src/components/monitoring/AdaptiveQuestionnaire.tsx`, `CaseMonitoring.tsx`,
  `VictimCheckIns.tsx`; new `tests/api.test.cjs`.

Validation

- `python -B -m unittest discover -s tests`: 90 tests, including abandoned-pending recovery.
- `node --test tests/api.test.cjs`: 4 passed (403 data clearing, temporary refresh failure/retry,
  expired-session clearing/redirect, graph series/null/zero/timezone handling).
- `npm run build`: TypeScript and production bundle passed; bundle-size warning remains.
- `git diff --check`: passed.
- Windows sandbox temp-folder/process restrictions required approved test execution outside
  the sandbox. Test fixtures remained isolated; they were not cloud users or cloud scores.

Still required for end-to-end completion

Supply the deployed frontend/backend URLs and deployment access or build metadata, then
deploy both changes together. Verify the frontend API base URL, backend commit, cloud DB,
provider-key detection and Gemini → Groq → OpenRouter runtime behaviour without logging secrets.
An existing victim must supply real answers for a new no-note submission and a new eligible-note
submission. Then verify exactly one analysis, visible status, assigned-counsellor graph/history,
and an intentional Authority review. No real questionnaire answers or victim notes were invented.
