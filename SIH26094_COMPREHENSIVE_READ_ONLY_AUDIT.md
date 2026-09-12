# SIH26094 Comprehensive Read-Only Audit

**Project:** Sahas — AI-Powered Dynamic Mental Health Monitoring and Distress Prediction System  
**Problem statement:** SIH26094  
**Audit date:** 12 September 2026  
**Audit mode:** Read-only; no application code, model, or database modifications

## Executive conclusion

**Overall PS completion: 58%**

Sahas is a credible, working web prototype with authentication, victim check-ins, persistent chat, Whisper transcription, text-AI history, longitudinal text monitoring, explainable prioritization, appointments, support requests, and role-scoped dashboards.

However, it is not yet the unified multimodal distress-prediction system described by SIH26094. The largest architectural issue is that the project currently has two independent scoring systems:

1. Questionnaire scoring, including a recently added short historical component.
2. LLM-generated text scoring used for professional monitoring and prioritization.

They are not fused. Whisper only produces text. Speech Emotion Recognition (SER) is experimental and disconnected. Engagement features are not scored. High-risk alerts exist only as dashboard indicators, not delivered alerts. Intervention recommendations are mostly static resources rather than case-specific recommendations.

## 1. Production architecture actually in use

The latest application is:

- Backend: `sih_backend_latest`
- Frontend: `sih_frontend_latest`
- Configured application database: PostgreSQL through `sih_backend_latest/.env`
- Local SQLite files: separate ordinary/demo databases, not the currently configured application database
- SER: standalone `Speech-Emotion-Recognition` project plus root evaluation scripts

The repository also contains older copies:

- `sih_backend`
- `sih_backend_newai`
- `sih_frontend`
- `sih_frontend_newai`
- `sih_frontend_old`

These copies contain older, hardcoded, or mock implementations. They are a serious packaging and demo-operator risk, although they are not imported by the latest application.

## 2. Requirements classification

| SIH26094 requirement | Status | Verified assessment |
|---|---|---|
| Periodic victim interactions | **PARTIALLY COMPLETE** | Real web questionnaire, text chat, support requests, and appointment workflow exist. No scheduled check-in engine, reminders, SMS, IVRS, mobile app, or helpline integration. |
| Voice analysis | **PARTIALLY COMPLETE** | Browser recording → authenticated API → local faster-Whisper → editable transcript works in code. No acoustic distress or voice-emotion analysis in production. |
| Text/NLP and sentiment analysis | **COMPLETE** | Assessment notes and eligible victim messages are persisted, sent to configured LLM providers, validated, stored in `ai_analyses`, and shown to professionals with score, emotions, reason, and risk. Availability depends on provider credentials and network access. |
| Behavioural/engagement analysis | **STARTED BUT NOT INTEGRATED** | Interaction timestamps, chat, appointments, support requests, and assessment activity exist, but no missed-check-in frequency, response latency, disengagement, session attendance, or behavioural feature affects a score. |
| Emotion AI | **STARTED BUT NOT INTEGRATED** | Text AI returns emotion labels and standalone SER experiments exist. Audio emotion results are not produced by the backend or consumed by Sahas. |
| Dynamic Distress Score | **PARTIALLY COMPLETE** | Questionnaire plus short history is dynamic, and text priority changes over time. There is no single multimodal score incorporating all expected signals. |
| Longitudinal distress/trend analysis | **PARTIALLY COMPLETE** | Two historical algorithms exist. Text AI has a chart and 14-day trend rules. Questionnaire has a four-day weighted history, but that history is not rendered in the latest victim frontend. |
| Predict escalation before crisis | **PARTIALLY COMPLETE** | Trend rules detect worsening and rapid deterioration after multiple observations. This is retrospective thresholding, not a validated forward prediction model. |
| Threshold alerts | **PARTIALLY COMPLETE** | High/critical text analyses create alert labels and `needs_review`. There is no notification service, push/SMS/email delivery, escalation roster, SLA, or alert lifecycle. Questionnaire Critical can leave AI monitoring `UNASSESSED`. |
| Intervention recommendations | **PARTIALLY COMPLETE** | Human chat, appointments, callbacks, threat reports, resources, case status, and rehabilitation state exist. No signal-to-intervention recommendation engine covers medical care, witness protection, relocation, financial assistance, legal aid, etc. |
| District/State/National monitoring | **PARTIALLY COMPLETE** | Cases store district and state, and authority users see global aggregate statistics. No district/state/national filters, hierarchy, jurisdiction scoping, drilldowns, or separate administrative levels. |
| Explainable AI | **PARTIALLY COMPLETE** | LLM reason, emotions, explicit priority point contributions, trend explanation, and human acknowledgement are displayed. There is no unified multimodal feature attribution or evidence trace. |
| Privacy protection | **PARTIALLY COMPLETE** | Voice files are temporary, raw audio is deleted, case access is scoped, authority summary is aggregated, and error logging avoids source text. Missing consent records, retention/deletion policy enforcement, de-identification, and external-AI disclosure/controls. |
| Data security and RBAC | **PARTIALLY COMPLETE** | Bcrypt, JWT expiration, production secret enforcement, victim-only signup, live-account validation, and backend case scoping are present. Missing rate limiting, MFA, token revocation, audit trail, secure cookies, password recovery, encryption controls, and jurisdiction-based authority restrictions. |
| Multilingual conversational AI | **NOT IMPLEMENTED** | UI and workflows are English. Whisper explicitly forces `language="en"` despite using a multilingual-capable model. No translation, language preference, localized questionnaire, or multilingual chatbot. |
| Automated case prioritization | **PARTIALLY COMPLETE** | A deterministic, explainable priority queue works end-to-end for completed text-AI analyses. It ignores questionnaire score, self-harm override, voice/SER, engagement, and operational urgency from threat reports. |
| Real-time/high-risk alerts | **PARTIALLY COMPLETE** | Frontend polls monitoring every 15 seconds and chat every five seconds. No WebSocket, push notification, dispatch, external delivery, or guaranteed real-time processing. |
| Continuous wellbeing monitoring/follow-up | **PARTIALLY COMPLETE** | Persistent check-ins, chat, trends, appointments, support requests, status updates, and review acknowledgement exist. No automated follow-up scheduling, missed-check-in detection, reminders, or longitudinal care plan. |

## 3. Actual production distress-scoring pipeline

### 3.1 Questionnaire production score

Implemented in `sih_backend_latest/app/cases.py`.

It uses:

- Mood
- Anxiety
- Sleep disturbance
- Hopelessness
- Social withdrawal
- Self-harm thoughts
- Up to four earlier questionnaire scores from the preceding four days

Formula:

```text
current = round(sum(six answers) / 24 × 100)

historical = weighted average of prior scores
weights newest→oldest = 0.4, 0.3, 0.2, 0.1

final = round(
    0.8 × current
  + 0.2 × historical
  + 5 if prior history is rising
)
```

The first assessment remains exactly the questionnaire score. Self-harm responses of 3 or 4 force `Critical`.

#### Production inputs

| Signal | Influences questionnaire distress score? |
|---|---:|
| Questionnaire responses | **Yes** |
| Historical questionnaire scores | **Yes** |
| Trend/change over time | **Yes**, only as a five-point rising bonus |
| Free-text analysis | **No** |
| Whisper transcript analysis | **No direct effect** |
| SER output/probabilities | **No** |
| Engagement/behavioural features | **No** |

The optional note is saved and separately analyzed after the assessment transaction commits. Its AI result does not update `assessments.distress_score`, `assessments.risk_level`, or `cases.risk_level`.

### 3.2 Text-AI monitoring score

Implemented through:

- `sih_backend_latest/app/ai_service.py`
- `sih_backend_latest/app/ai_workflow.py`
- `sih_backend_latest/app/monitoring_rules.py`

Inputs are exclusively:

- Optional assessment note
- Eligible victim chat message
- Historical completed AI text analyses

The LLM supplies a 0–100 score, risk level, emotions, attention flag, and reason. The backend validates ranges and consistency but does not independently calculate the text score.

The priority algorithm then uses:

- 50% of the latest LLM text score
- Risk-level points
- `requires_attention`
- Text-score trend
- Repeated high/critical days

It does not use questionnaire, Whisper metadata, audio emotion, or engagement.

### 3.3 Critical disconnect

A victim can submit a questionnaire with a score of 100 and risk `Critical`, while the counsellor’s AI monitoring queue remains `UNASSESSED` if no note/text analysis succeeded.

This is the most important demo and safety gap.

## 4. Historical scoring verification

### 4.1 Recently added questionnaire-history algorithm

The implementation is coherent and works against the existing `assessments` table:

- Queries before inserting the new assessment
- Restricts history to the victim’s current case
- Excludes future and unparsable timestamps
- Uses at most four assessments from the preceding 96 hours
- Normalizes weights when fewer than four scores exist
- Clamps the final score to 0–100
- Preserves the self-harm Critical override

The algorithm does not require a database migration because it reuses existing assessment columns.

### 4.2 Actual configured database

The configured PostgreSQL database was reached read-only:

- 16 users
- 11 cases
- 2 assessments
- 1 AI analysis
- 1 chat message

The two application assessments belong to the same case, are approximately 22 seconds apart, and both have questionnaire score 100/Critical. Therefore:

- The second submission can read the first as history.
- The calculation operates on the actual configured application database.
- The current data cannot demonstrate rising/falling questionnaire history because both observations are identical and on the same day.

### 4.3 Limitations and defects

- Rows are ordered by assessment ID, not parsed timestamp. This normally tracks insertion order but is weaker than ordering on a real timestamp column.
- `created_at` is stored as text rather than a database timestamp.
- Multiple submissions on one day all count independently in the four-entry questionnaire history.
- A four-day window is too short to justify “longitudinal mental-health prediction.”
- Historical metadata is returned by the backend, but the current `VictimDashboardData` TypeScript type and UI do not consume `historicalScore`, `recentTrend`, or `recentScores`.
- The professional trend chart is a different algorithm using only AI text results.

## 5. Speech Emotion Recognition audit

### 5.1 Original SUPERB baseline

The standalone microphone implementation uses:

```text
superb/wav2vec2-base-superb-er
```

The recorded 200-sample RAVDESS evaluation reports:

- Accuracy: **44.5%**
- Macro F1: approximately **36.8%**
- Sad recall: **4%**
- Happy recall: **16%**
- Angry recall: **94%**

This is an experimental emotion baseline, not a distress predictor.

### 5.2 Testing 4

Testing 4 is materially different:

- Base encoder: `facebook/wav2vec2-base`
- Encoder frozen
- New `Dropout(0.2) + Linear(768 → 4)` classification head
- Four labels: neutral, happy, sad, angry
- Actor-disjoint train/validation/test split
- Saved checkpoint: approximately 377 MB
- Best validation macro F1: **55.03%**

The checkpoint and training metadata exist. However:

- The untouched Testing 4 test result file was not present.
- The supplied evaluator would write result files, so it was not executed during this read-only audit.
- Validation performance must not be represented as final test accuracy.
- Root `testing4_ser.py` contains only a model identifier and is not an integration module.
- A Hugging Face model ID alone is not evidence that the backend loads it.

### 5.3 Production SER status

| Question | Finding |
|---|---|
| Is SUPERB integrated into Sahas? | **No** |
| Is Testing 4 integrated into Sahas? | **No** |
| Does the voice endpoint return emotion probabilities? | **No** |
| Are SER results stored in the database? | **No** |
| Do SER probabilities affect questionnaire score? | **No** |
| Do SER probabilities affect text AI score? | **No** |
| Do SER probabilities affect prioritization? | **No** |

Classification: **STARTED BUT NOT INTEGRATED**.

## 6. Frontend → API → backend → database → frontend flows

### 6.1 Working end-to-end flows

- Victim registration → user and case creation
- Login → JWT → role-specific landing page
- Questionnaire → calculation → assessment persistence → case update → victim score display
- Optional note → pending AI record → provider analysis → stored AI result
- Victim message → message persistence → optional text analysis → counsellor history
- Counsellor message → persistence → victim chat
- Authority case assignment → database update → counsellor scoping
- Appointment request/confirmation/completion/cancellation
- Callback/threat/support request → staff acknowledgement/resolution
- Text-AI history → trend/priority → counsellor queue
- Authority aggregate monitoring
- Counsellor acknowledgement of a specific AI analysis
- CSV export of authorized monitoring records

### 6.2 Incomplete or misleading flows

- Voice is transcription, not voice-emotion analysis.
- A voice transcript only affects text AI after the victim reviews and submits it.
- “How are you feeling?” mood buttons set `selectedMood`, but that value is decorative and never submitted.
- Six numeric questionnaire fields initialize to zero. A victim can submit without actively answering, producing a valid zero result.
- The backend returns questionnaire history metadata, but the victim frontend ignores it.
- Authority dashboard is global, not district/state/national.
- “Emergency Assistance” only displays advice; it cannot dispatch help.
- Appointments explicitly have no connected video call.
- Resource bookmarks are browser-local and not persisted.
- Static resources are not AI recommendations.
- Alerts are dashboard state and polling, not delivered notifications.
- Generic routes such as `/cases`, `/alerts`, `/sessions`, `/reports`, and `/settings` are not individually wrapped in `ProtectedRoute`. Backend APIs still enforce access, but direct navigation produces confusing or partially visible pages.
- `ComingSoon.tsx` remains in the latest source but is currently unused.
- Mock data remains imported for navigation and an unused mock distress chart component. The active monitoring queue itself uses backend data.

### 6.3 Backend endpoints with limited or no latest-frontend use

- `/victim/test`, `/counsellor/test`, `/authority/test`: diagnostic only.
- `/api/ai/analyze`: disabled-by-default development endpoint.
- `/api/cases/{case_id}/ai-analyses`: the monitoring-detail endpoint provides history separately; the latest UI does not directly call this paginated endpoint.
- `/api/victim/check-ins`: used, but only shows submission/status metadata, not questionnaire scores or returned questionnaire trend.

## 7. Security and privacy findings

### 7.1 Strong controls

- Public registration restricted to victims
- Bcrypt password hashing
- JWT expiry
- Production requires a sufficiently long JWT secret
- Live user/role validation on sensitive newer endpoints
- Backend case scoping for victim and assigned counsellor
- Unknown and inaccessible cases generally share the same 404 response
- Idempotent chat message IDs
- Pending AI record committed before external inference
- Failed AI inference does not destroy source data
- Provider payloads and victim text are intentionally excluded from logs
- Audio is temporary and deleted after transcription
- Authority monitoring summary excludes message text and AI explanations
- AI result schema and cross-field validation are strict

### 7.2 Weaknesses

- Bearer token is stored in `localStorage`, exposing it to successful XSS.
- No refresh-token/revocation/session-management mechanism.
- No rate limiting or login throttling.
- No MFA for counsellors or authorities.
- No password reset/account recovery.
- No security/audit event log.
- No data-access audit record for sensitive case views.
- No consent model for recording, AI processing, or external-provider transfer.
- No retention, deletion, correction, or subject-access workflow.
- No application-level encryption of sensitive text fields.
- Authority role can view all users and cases; there is no district/state jurisdiction scope.
- External LLM processing may transmit victim text to configured cloud providers without a recorded consent/processing policy.
- CORS defaults are reasonable for local development but deployment configuration remains operator-dependent.
- PostgreSQL migration is documented but not backed by a live staging migration test in the repository evidence.

## 8. Mock, hardcoded, random, and placeholder inventory

- `seed_cases.py` generates random risk, location, last assessment, and intervention status.
- `seed_demo.py` creates synthetic AI scores and labels them as synthetic. These are appropriate fixtures but must not be presented as live model output.
- `sih_frontend_latest/data/mockData.ts` and `mockConversations.ts` remain.
- An unused `DistressTrendCard` consumes mock trend data.
- Older frontend copies contain substantially more mock dashboards.
- Older backends contain hardcoded victim distress values.
- Root `testing4_ser.py` is effectively a one-line placeholder.
- Static resource content is hardcoded.
- AI thresholds, historical weights, trend cutoffs, and priority weights are engineering heuristics, not clinically validated.
- No random value was found in the active runtime scoring path; randomness is confined to legacy/demo seeding.
- `ComingSoon.tsx` remains, although the currently routed operations pages have mostly been replaced with functional implementations.

## 9. Weighted completion assessment

Weights emphasize core PS outcomes rather than counting pages or files.

| Area | Score | Why |
|---|---:|---|
| Core victim workflow | **80%** | Registration, case creation, questionnaire, text, voice transcription, chat, requests, appointments, resources, and persistence work. Missing reminders, explicit-answer validation, multilingual access, and true emergency integration. |
| AI/ML functionality | **47%** | Real LLM text analysis and strong SER experimentation exist. No multimodal fusion, production SER, behavioural model, calibrated prediction, or clinical validation. |
| Dynamic distress scoring | **48%** | Questionnaire plus recent history and separate text priority are functional, but the system lacks one authoritative multimodal score. |
| Longitudinal monitoring | **62%** | Two historical implementations, persistent AI history, charts, trend rules, repeated-risk detection, and stale status exist. Questionnaire history is hidden and monitoring excludes questionnaire observations. |
| Counsellor workflow | **79%** | Assigned queue, explanations, trends, review acknowledgement, case chat, sessions, requests, and case scoping are strong. Missing intervention plans, alert delivery, notes/outcomes, and unified clinical view. |
| Authority workflow | **61%** | Assignment, users/cases, support requests, aggregates, reports, and monitoring work. Missing jurisdiction hierarchy, geographic filtering, resource planning, privacy-preserving drilldown, and escalation management. |
| Alerts/prioritization | **54%** | Explainable automated prioritization and polling exist. Questionnaire Critical is ignored, and there is no outbound real-time alert or escalation lifecycle. |
| Intervention recommendations | **43%** | Resources and human-support operations exist, but recommendations are not personalized or linked to detected needs. Major statutory assistance categories are absent. |
| Multilingual/accessibility | **18%** | Basic semantic controls and browser voice capture exist. UI is English and Whisper is forced to English; no multilingual conversation or localization. |
| Security/privacy | **59%** | Good baseline RBAC, hashing, JWT configuration, scoped queries, temporary audio, and safe logging. Missing several controls expected for highly sensitive mental-health/atrocity data. |
| Explainability | **73%** | Priority contributions, alert reasons, trend explanation, LLM rationale, timestamps, source types, and human review are shown. No unified score explanation or model confidence/calibration. |
| Testing/evidence | **68%** | Strong backend unit coverage and previous frontend build evidence. Whisper/provider tests use mocks; no browser E2E, live PostgreSQL migration suite, real Whisper integration evidence, or final Testing 4 test metrics. |
| Demo readiness | **70%** | A coherent role-to-role demo path exists and the configured PostgreSQL is reachable. Provider/model dependencies, duplicate versions, disconnected risk streams, missing alert delivery, and zero-default questionnaire create material demo risks. |

### Weighted overall

Using the highest weights for victim workflow, AI/ML, dynamic scoring, longitudinal monitoring, alerts, and security yields:

**Overall PS completion: 58%**

## 10. Priorities

### P0 — Must complete for SIH

1. **Create one unified case risk/priority calculation**
   - Combine questionnaire current score and self-harm override.
   - Add historical questionnaire change.
   - Add text-AI score when available.
   - Add SER only when available and validated.
   - Add engagement features.
   - Preserve missing-signal semantics; never replace missing data with fake zeroes.

2. **Ensure questionnaire Critical immediately reaches professionals**
   - Create a persistent alert/event.
   - Show it in counsellor and authority queues even when no text was submitted.
   - Require acknowledgement and record status/timestamps.

3. **Integrate Testing 4 SER into the backend voice flow**
   - Load the local checkpoint once.
   - Return four probabilities and model/version metadata.
   - Persist the audio-derived result, not raw audio.
   - Use a small, bounded contribution to unified risk.
   - Do not claim distress accuracy from RAVDESS emotion accuracy.

4. **Add case-specific intervention recommendations**
   - Deterministic rule mapping is sufficient for SIH.
   - Cover counselling, medical help, legal aid, witness protection/safety review, relocation, financial support, and rehabilitation.
   - Display rationale and require human approval.

5. **Implement actual alert records and delivery**
   - Database alert table with type, severity, source, state, assignee, created/acknowledged/resolved timestamps.
   - Immediate frontend notification via WebSocket/SSE or short polling.
   - At minimum, one external/demo delivery mechanism such as email/SMS gateway sandbox.

6. **Expose questionnaire history in professional monitoring**
   - One combined chart or clearly labeled parallel series.
   - Current score, prior baseline, delta, modality availability, and explanation.

7. **Fix the victim check-in input**
   - Require explicit responses to all six questions.
   - Either submit the mood-chip selection or remove it.
   - Show a non-alarming success result without relying on browser `alert()`.

8. **Produce a clean reproducible demo package**
   - Clearly designate only `*_latest`.
   - Provide a single startup script/readme.
   - Pre-cache Whisper and SER models.
   - Confirm one AI provider.
   - Use synthetic, clearly labeled demo data.

### P1 — Strongly recommended

- Add missed-check-in, response-gap, appointment attendance, and message-frequency engagement features.
- Add district/state filters and authority jurisdiction scoping.
- Add Hindi plus one additional regional language to UI, questionnaire, resources, and Whisper auto-detection.
- Add consent capture for voice and cloud AI processing.
- Add immutable audit events for access, alerts, reviews, assignments, and exports.
- Add alert escalation deadlines and ownership.
- Run and preserve Testing 4 untouched actor test results.
- Validate the full voice path with real browser audio.
- Add model/version and modality contribution display.
- Add clinically reviewed disclaimers, thresholds, intervention mappings, and emergency contacts.
- Add integration/E2E tests against an isolated PostgreSQL database.

### P2 — Optional/polish

- Mobile/PWA packaging
- IVRS and helpline operator screen
- Full SMS conversational flow
- Video counselling integration
- Password recovery and profile management
- National map visualizations
- PDF reports
- Localization beyond the initial supported languages
- Code splitting and bundle-size optimization
- Removal/archival of older project copies after the demo is stable

## 11. Shortest roadmap to approximately 90–95% PS coverage

### Phase 1 — Unify safety signals

Build a `CaseSignal`/`Alert` persistence layer and a deterministic fusion service using existing data. Feed questionnaire, text AI, historical trend, engagement, and later SER into one professional priority result. Preserve the current questionnaire and text records unchanged.

Target: fix the most serious disconnect without broad refactoring.

### Phase 2 — Connect Testing 4 SER

Wrap the existing frozen model as a cached backend service and call it alongside Whisper. Persist only probabilities, predicted emotion, confidence caveat, checkpoint version, and timestamp. Add a conservative configurable SER contribution.

Target: demonstrate real multimodal processing.

### Phase 3 — Alerts and interventions

Persist alerts, show live/unacknowledged alerts to counsellors and authorities, and add deterministic intervention mappings with human approval.

Target: close the core SIH loop:

```text
victim signal → prediction/priority → alert → recommendation → human action → follow-up
```

### Phase 4 — Engagement and regional monitoring

Calculate simple explainable engagement features from existing timestamps and statuses. Add district/state filters and scoped authority summaries.

Target: cover behavioural monitoring and administrative-level requirements with minimal new infrastructure.

### Phase 5 — Multilingual and evidence

Enable Whisper language detection, translate the questionnaire/UI into Hindi plus one relevant regional language, and ensure text AI uses the selected language. Add PostgreSQL integration tests, browser E2E for the three roles, real Whisper smoke evidence, and frozen Testing 4 test metrics.

Target: presentation confidence and defensible claims.

With disciplined implementation, these phases can reach approximately **91–93% PS coverage** without replacing working workflows.

## Final summary

**Current completion percentage: 58%**

### Five biggest gaps

1. Questionnaire, text AI, voice, SER, and engagement are not fused into one dynamic distress/risk pipeline.
2. Testing 4 SER is trained but entirely disconnected from Sahas.
3. Critical questionnaire/self-harm results do not automatically enter professional AI monitoring or persistent alerts.
4. No delivered real-time alert system or escalation lifecycle exists.
5. Multilingual interaction and district/state/national monitoring are largely absent.

### Five strongest existing components

1. Persistent, role-scoped victim–counsellor chat with idempotency and AI analysis of eligible victim messages.
2. Failure-safe text-AI workflow with strict output validation, historical storage, and safe provider fallback.
3. Explainable counsellor priority queue with trend rules, reasons, alerts, and per-analysis acknowledgement.
4. Strong victim-to-human-support workflow: case creation, assignment, appointments, callbacks, threat reports, and follow-up status.
5. Security-conscious foundations: victim-only signup, bcrypt, JWT checks, case scoping, safe logs, and temporary voice-file deletion.

### Minimum work required for a convincing SIH demo

- Fuse questionnaire, text history, and self-harm safety signals into one professional priority.
- Connect Testing 4 SER to the voice endpoint and store its probabilities.
- Persist and acknowledge high-risk alerts.
- Generate explainable case-specific intervention suggestions.
- Display unified history and modality contributions.
- Add at least Hindi UI/text/voice support.
- Fix zero-default questionnaire submission.
- Prepare one verified synthetic end-to-end demo using only the latest app directories.

**Estimated completion after all P0 items: approximately 88%.**

Adding the P1 multilingual, regional monitoring, engagement, consent/audit, and stronger evidence items would raise defensible coverage to approximately **91–93%**.
