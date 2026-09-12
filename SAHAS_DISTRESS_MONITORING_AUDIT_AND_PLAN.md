# SAHAS Distress Scoring and Monitoring: Audit and Target Plan

Audit date: 2026-09-12  
Status: Read-only technical audit; implementation pending approval.

This document records the inspected repository implementation and proposes an additive monitoring layer. Creating this document does not authorize or implement application changes.

The repository implements historical questionnaire scoring and text-AI monitoring, but they are not fused into one case priority. Alerts and Analytics also use different inputs.

The worked questionnaire example and an indicator-persistence failure were verified using extracted repository functions and an isolated in-memory database. No existing database records were changed. This was not a live deployment or full test-suite verification.

## 1. CURRENT IMPLEMENTED ALGORITHM

### 1.1 Scope and backend variants

The main findings concern `sih_backend_latest` and `sih_frontend_latest`, whose registered routes implement the monitoring features described here.

| Backend | Questionnaire scoring | Monitoring |
|---|---|---|
| `sih_backend` | Questionnaire-only normalized sum; no historical weighting | Does not contain the newer monitoring modules |
| `sih_backend_newai` | Questionnaire-only normalized sum, plus separate text analysis | No newer monitoring/operations/chat layer; `main.py` imports the voice router but does not register it |
| `sih_backend_latest` | Questionnaire plus historical weighting and rising bonus | Text-AI priority, persisted questionnaire/text indicators, reviews, support requests, voice transcription |

`START_HERE.md` names older directory paths. It does not establish which backend is actually running. This audit establishes source behavior, not the deployment's selected process or database.

Primary route registration: [sih_backend_latest/app/main.py](sih_backend_latest/app/main.py).

### 1.2 Questionnaire distress score

Sources:

- [cases.py](sih_backend_latest/app/cases.py): `questionnaire_distress_score`, `recent_assessment_history`, `historical_distress`, `calculate_distress_score`, `risk_level_for_score`, `submit_assessment`.
- [schemas.py](sih_backend_latest/app/schemas.py): `AssessmentCreate`.
- [models.py](sih_backend_latest/app/models.py): `Assessment`, `Case`.

#### Exact current inputs

The backend accepts six strict integers, each from 0 through 4:

```text
mood
anxiety
sleep
hopelessness
social_withdrawal
self_harm_thoughts
```

All six have equal weight:

```text
total = mood + anxiety + sleep + hopelessness
        + social_withdrawal + self_harm_thoughts

Q = round(total / 24 × 100)
```

`round` is Python's rounding behavior, including ties-to-even.

#### Historical selection

Before inserting the new assessment, `recent_assessment_history`:

1. Fetches the case's newest 100 assessments, ordered by descending database ID.
2. Parses timestamps as UTC; naive timestamps are treated as UTC.
3. Keeps rows satisfying `now − 4 days <= created_at < now`.
4. Stops after four qualifying assessments.

Consequences:

- History contains up to four submissions, not four daily averages.
- Multiple submissions on one day can occupy all four positions.
- Ordering is by ID, not parsed timestamp.
- Invalid timestamps and rows outside the window are excluded.
- The historical values are existing `Assessment.distress_score` values, which may already contain history and bonuses.

#### Historical weighted score

For newest-to-oldest historical scores `F₁ … Fₙ`:

```text
weights = [0.4, 0.3, 0.2, 0.1][:n]

H = round(Σ(Fᵢ × weightᵢ) / Σ(weightᵢ), 1)
```

Weights are renormalized when fewer than four prior scores exist.

#### Questionnaire trend and rising bonus

```text
delta = newest prior stored score − oldest selected prior stored score

rising  when delta >= 10
falling when delta <= −10
stable  otherwise

bonus = 5 if rising, otherwise 0
```

This uses prior assessments only. The submission currently being scored is not included. With zero prior assessments, trend is `stable`; with one, delta is zero. There is no distinct-day requirement.

#### Final stored questionnaire score

```text
If no history:
    H_effective = Q
Otherwise:
    H_effective = H

F = clamp(round(0.8 × Q + 0.2 × H_effective + bonus), 0, 100)
```

There is no negative bonus for a falling trend. Falling history can still affect the score through `H`.

#### Risk thresholds and self-harm override

Applied to `F`, in this order:

| Condition | Stored questionnaire risk |
|---|---|
| Current `self_harm_thoughts >= 3` | `Critical`, regardless of `F` |
| Otherwise `F >= 75` | `Critical` |
| Otherwise `F >= 50` | `High` |
| Otherwise `F >= 25` | `Moderate` |
| Otherwise | `Low` |

The self-harm override changes the risk label, not the numeric score. With no history and only `self_harm_thoughts=3`, the score is 12 but risk is `Critical`.

The override is not latched across submissions: a later assessment replaces `Case.risk_level`.

#### Persistence, determinism, and downstream effects

```text
Assessment:
    six answers
    distress_score = F
    risk_level
    created_at
    note
    case_id

Case:
    risk_level = latest submitted assessment risk
    last_assessment = submission time
```

The submission response also returns:

```text
distressMetadata:
    currentScore
    historicalScore
    finalScore
    recentTrend
    trendDelta
    escalationBonus
    recentScores
```

That metadata is not persisted. `Assessment.distress_score` is currently a blended questionnaire/history result, not the raw normalized answer score. The raw normalized score remains recoverable from the six persisted answers.

The calculation is deterministic. It updates case risk, victim display, and questionnaire monitoring indicators. It does not feed the text-AI professional priority calculation.

`get_victim_dashboard` recomputes historical display values at read time using recent assessments, which now include the latest saved assessment. Those display values are not the exact historical inputs originally used to calculate that latest submission.

### 1.3 Worked example: 25 → 39 → 58

This exact sequence is defined by the rising fixture in [seed_historical_demo.py](sih_backend_latest/app/seed_historical_demo.py), `PLANS` and `expected_rows`.

Assume daily submissions, all within the history window. Answer order is mood, anxiety, sleep, hopelessness, withdrawal, self-harm.

| Submission | Answers | Raw Q | Prior history, newest first | H | Prior trend / bonus | Calculation | Stored F |
|---|---|---:|---|---:|---|---|---:|
| 1 | `1,1,1,1,1,1` | 25 | None | Baseline 25 | Stable / 0 | `0.8×25 + 0.2×25` | **25** |
| 2 | `2,2,2,2,1,1` | 42 | `[25]` | 25 | Stable / 0 | `0.8×42 + 0.2×25 = 38.6` | **39** |
| 3 | `3,3,2,2,2,2` | 58 | `[39,25]` | 33 | Rising / 5 | `0.8×58 + 0.2×33 + 5 = 58` | **58** |

For submission 3:

```text
H = (39×0.4 + 25×0.3) / 0.7 = 33
delta = 39 − 25 = 14
```

Without the rising bonus, submission 3 would store:

```text
round(46.4 + 6.6) = 53
```

Repeat submission 3's answers on day 4:

```text
Q = 58
history = [58, 39, 25]

H = round((58×0.4 + 39×0.3 + 25×0.2) / 0.9, 1)
  = 44.3

delta = 58 − 25 = 33
bonus = 5

F = round(46.4 + 8.86 + 5) = 60
```

Unchanged current answers can therefore produce `58 → 60`. Historical weighting is recursive: previous blended scores, including earlier bonuses, become later inputs.

The sequence alone does not uniquely identify answers. These are the concrete answers used by the repository's fixture.

### 1.4 Text-AI distress score

Sources:

- [ai_service.py](sih_backend_latest/app/ai_service.py): `SYSTEM_PROMPT`, `analyze_distress`, `_attempt`, `parse_indicators`.
- [ai_workflow.py](sih_backend_latest/app/ai_workflow.py): `analyze_saved_check_in`.
- [chat.py](sih_backend_latest/app/chat.py): `eligible_message`, `send_message`.

#### Exact input

One submitted text string, stripped and validated to 1–4,000 characters:

- An assessment's nonblank `note`; or
- An eligible victim chat message.

The provider receives the system prompt and that text. It receives no questionnaire answers, previous scores, conversation history, SER output, or engagement data.

#### Calculation and validation

There is no arithmetic formula for the text score. A cloud model generates it.

Providers are attempted in order:

```text
Gemini → Groq → OpenRouter
```

Configured model names can override defaults. Temperature is zero, but provider inference is not a guaranteed deterministic calculation.

The backend accepts only consistent results:

```text
distress_score: integer 0–100

low:       0–24
medium:   25–49
high:     50–74
critical: 75–100

requires_attention = (distress_score >= 50)
```

Inconsistent score/risk/attention combinations are rejected, not repaired.

The prompt requests Critical indicators for explicit immediate danger or immediate intent to harm self or others. This is an AI instruction, not an independent deterministic safety detector.

#### Persistence and downstream effects

The assessment/message and pending `AIAnalysis` commit before inference. The workflow then stores:

```text
status
distress_score
risk_level
emotions
requires_attention
reason
provider
finished_at
```

The row also retains `created_at`, case/victim IDs, and exactly one source link: `assessment_id` or `message_id`.

Failure normally leaves a `failed` row with null result fields; persistent storage failure can leave the already-committed row `pending`.

Text-AI never updates `Assessment.distress_score` or `Case.risk_level`. Persisted successful results affect AI priority, AI history, AI Analytics, and text monitoring indicators.

The opt-in `/api/ai/analyze` development endpoint, implemented in [ai.py](sih_backend_latest/app/ai.py), returns analysis without persistence. Its results do not enter monitoring.

#### Victim chat eligibility

`eligible_message` analyzes only victim messages satisfying:

```text
After trimming, case-folding, and stripping terminal " .!?":
    length >= 4
    at least one alphanumeric character
    not in:
        hello, thank you, thanks, okay,
        good morning, good night, thankyou
```

Counsellor messages are stored but not analyzed. Each eligible message is analyzed independently. Chat message retries use a client-message ID to avoid duplicate source/analysis creation.

### 1.5 Text-AI longitudinal trend

Source: [monitoring_rules.py](sih_backend_latest/app/monitoring_rules.py), `valid` and `trend`.

Eligible observations must have:

```text
status == completed
distress_score is an integer in 0–100
risk_level in low/medium/high/critical
created_at <= now
```

`trend`:

1. Selects observations within the last 14 days, inclusive.
2. Groups by UTC calendar day.
3. Calculates the median distress score for each day.
4. Keeps the newest seven observed days.
5. Requires at least three distinct days; otherwise returns `insufficient_data`.

For daily medians `yᵢ` and elapsed-day positions `xᵢ`:

```text
slope = Σ((xᵢ − mean(x)) × (yᵢ − mean(y)))
        / Σ((xᵢ − mean(x))²)

change = latest daily median − earliest daily median
span = last x
```

Classification, in order:

| Condition | Trend |
|---|---|
| `change >= 20`, `slope >= 5`, `span <= 7` | `rapidly_worsening` |
| `change >= 5`, `slope >= 1` | `worsening` |
| `change <= −5`, `slope <= −1` | `improving` |
| Otherwise | `stable` |

Returned slope is rounded to two decimals and change to one decimal. Classification uses the unrounded values.

Assessment-note and eligible chat analyses are pooled. Emotion labels do not affect this calculation. The trend is deterministic given persisted inputs, calculated on reads, and not persisted.

### 1.6 Text-AI professional priority score

Source: [monitoring_rules.py](sih_backend_latest/app/monitoring_rules.py), `prioritize`.

Let `D` be the latest valid successful AI distress score, ordered by creation time and ID:

```text
P = min(100, round(
      0.5 × D
      + risk_points
      + attention_points
      + trend_points
      + repeated_high_points,
      1
    ))
```

| Component | Points |
|---|---:|
| Latest AI risk `low` | 0 |
| Latest AI risk `medium` | 8 |
| Latest AI risk `high` | 18 |
| Latest AI risk `critical` | 30 |
| Latest `requires_attention=True` | 12 |
| Trend `worsening` | 10 |
| Trend `rapidly_worsening` | 25 |
| Other trends | 0 |
| High/Critical AI observations on at least two distinct UTC days within seven days | 8 |

```text
URGENT: P >= 80
HIGH:   P >= 55
MEDIUM: P >= 30
NORMAL: P < 30

UNASSESSED: no valid successful AI result
```

Additional behavior:

- Successful AI history remains usable even if the newest attempt failed.
- A latest successful result older than seven days produces `stale=True` and an explanation.
- Staleness does not reduce the score.
- Questionnaire risk and self-harm answers are not inputs.
- AI emotion names and explanation text are display fields, not numerical inputs.
- Score/category/reasons/trend are response fields, not stored priority records.

The priority calculation is deterministic given the stored AI results. Its underlying text scores are AI-generated.

A notable boundary:

```text
Single AI result D=75, critical, attention=True:
P = 37.5 + 30 + 12 = 79.5 → HIGH
```

Current AI `critical` does not invariably mean `URGENT` queue priority.

### 1.7 Alerts, Analytics, queues, and case details

Sources:

- [monitoring.py](sih_backend_latest/app/monitoring.py): `source_rows`, `case_view`, `all_views`, `refresh_questionnaire_indicators`, `monitoring_indicators`, `review_indicator`, `monitoring_summary`, `review_case`.
- [ai_history.py](sih_backend_latest/app/ai_history.py): `valid_source_query`.
- [Operations.tsx](sih_frontend_latest/src/pages/Operations.tsx): `Alerts`, `Analytics`, `Reports`.
- [PriorityQueue.tsx](sih_frontend_latest/src/components/monitoring/PriorityQueue.tsx).
- [AuthorityMonitoring.tsx](sih_frontend_latest/src/components/monitoring/AuthorityMonitoring.tsx).
- [CaseDetails.tsx](sih_frontend_latest/src/pages/CaseDetails.tsx) and [CaseMonitoring.tsx](sih_frontend_latest/src/components/monitoring/CaseMonitoring.tsx).

There are two different things labelled “Priority monitoring queue.”

| Surface | Actual input | Behavior |
|---|---|---|
| Counsellor dashboard queue | `/api/monitoring/cases` | Text-AI priority formula |
| Analytics queue | Same endpoint | Same text-AI priority |
| Authority monitoring summary | `/api/monitoring/summary` | Latest successful AI risk and derived AI alerts |
| Alerts-page “Priority monitoring queue” | `/api/monitoring/indicators` | Persisted questionnaire/text indicators, newest first |
| Case overview risk | `/api/cases/{id}` | `Case.risk_level`, normally last questionnaire risk |
| Case monitoring/history | `/api/cases/{id}/monitoring` | AI priority and AI history |
| Support requests on Alerts page | `/api/support-requests` | Separate human-request workflow |

The professional AI queue sorts by category, descending score, then case ID. The Alerts-page indicator list sorts by creation time, not severity.

Professional monitoring is scoped to assigned cases for counsellors and all accessible cases for authorities. AI queue/history source validation checks that analyses refer to actual assessments or victim messages for their case. Authority case detail includes AI-derived observations; raw case chat is available only to the victim and assigned counsellor.

#### Questionnaire indicator generation

`refresh_questionnaire_indicators` selects the newest three assessments by ID, without any age limit.

It calls `historical_distress` on those scores, including the latest assessment. This differs from scoring-time history, which excludes the new submission and applies a four-day window.

Create an indicator when:

```text
latest risk is High/Critical
OR latest-to-oldest selected score change >= 10
```

Persisted fields:

```text
source = questionnaire_trend if rising, else questionnaire
severity = URGENT if latest risk is Critical or latest score >= 75
           HIGH otherwise
current_score = latest stored questionnaire score
trend
reason
fingerprint
case_id
created_at
```

A rising sequence can generate a `HIGH` indicator even if its latest questionnaire risk is Low or Moderate. This is deterministic and does not update case risk or the AI priority score.

#### Text indicator generation

The latest completed AI row generates an indicator if:

```text
requires_attention
OR risk_level in high/critical
```

Severity is `URGENT` for Critical; otherwise `HIGH`.

It persists `source='text_ai'`, score, reason, fingerprint, and `analysis_id`. Chat analyses are included under the same `text_ai` label.

Unlike the professional queue, this lookup does not use the source-validation query or explicitly exclude future timestamps. Indicator selection/severity are deterministic; their source result is AI-generated.

#### Creation timing

Indicators are generated and committed during:

```text
GET /api/monitoring/indicators
```

They are not created when an assessment or AI result is saved. Consequently:

- Alert creation depends on someone reading this endpoint.
- `created_at` represents discovery time, not the original observation time.
- Intermediate historical triggers can be missed because discovery examines latest rows.

#### Confirmed persistence defect

The refresh function attempts text-indicator creation in two loops. [database.py](sih_backend_latest/app/database.py) configures `autoflush=False`.

When a questionnaire trigger and a new qualifying text result coexist:

1. The first loop adds a text indicator without flushing.
2. The second loop cannot find that pending row through its database query.
3. It adds the same fingerprint again.
4. Commit fails on the unique `(case_id, fingerprint)` constraint.

This exact failure was reproduced in an isolated in-memory database:

```text
UNIQUE constraint failed:
monitoring_indicators.case_id, monitoring_indicators.fingerprint
```

The failed transaction also prevents the newly added questionnaire indicator from committing.

#### Existing acknowledgement mechanisms

These are real persisted mechanisms, but separate:

| Record | Current acknowledgement |
|---|---|
| `MonitoringIndicator` | Authority or scoped counsellor sets `reviewed_by`, `reviewed_at`; reviewed rows disappear from the endpoint |
| `AnalysisReview` | Assigned counsellor acknowledges a specific completed AI analysis |
| `SupportRequest` | Staff changes `Open → Reviewed/Resolved`, recording reviewer/time |

For AI queue entries:

```text
needs_review = generated AI alerts exist
               AND latest successful analysis has no review
                   by the currently assigned counsellor
```

Reviewing an indicator does not acknowledge its AIAnalysis, and reviewing AIAnalysis does not clear the indicator.

There is no unified Alert entity, multi-step alert lifecycle, intervention/follow-up linkage, or append-only lifecycle audit.

#### Analytics exact counts

`monitoring_summary` returns:

```text
risk_distribution:
    latest successful AI risk per case, otherwise unassessed

requiring_attention:
    number of cases with any generated AI alert string

unreviewed_urgent:
    AI priority == URGENT and needs_review

analysis_unavailable:
    latest attempt status is pending or failed
```

Generated AI alert strings represent latest High/Critical risk, attention flags, worsening/rapid deterioration, or repeated high days. They are not Alert database rows.

`requiring_attention` is not an unresolved persisted-alert count and does not exclude reviewed cases. Questionnaire-only Critical cases can remain `UNASSESSED` in the AI queue and AI risk distribution while having questionnaire indicators on Alerts.

### 1.8 Explicit questionnaire-input verification

| Signal | Changes questionnaire score F? | Actual downstream use |
|---|---|---|
| Six questionnaire answers | **Yes** | Raw component, stored risk, case risk |
| Previous questionnaire scores | **Yes** | 20% historical component |
| Prior questionnaire trend | **Yes** | Rising adds 5 |
| Free-text AI | **No** | Separate AIAnalysis, AI priority, text indicators |
| Whisper transcription | **No** | Editable note; if submitted, analyzed as ordinary text |
| SER | **No** | Not integrated into this backend |
| Victim chat analysis | **No** | Separate AIAnalysis; affects AI priority/history/text indicators |
| Engagement/behaviour | **No** | No scoring implementation |
| Support requests/threat reports | **No** | Separate persisted request and staff follow-up |

### 1.9 Voice and support data flow

Voice sources:

- [voice.py](sih_backend_latest/app/voice.py): `transcribe_voice`.
- [voice_service.py](sih_backend_latest/app/voice_service.py): `get_whisper_model`, `transcribe_audio`.
- [VictimDashboard.tsx](sih_frontend_latest/pages/VictimDashboard.tsx): recording, transcription, and assessment submission.

```text
temporary audio
→ faster-whisper transcription
→ transcript returned to browser
→ victim edits/submits note
→ Assessment.note + ordinary AIAnalysis
```

The endpoint itself persists neither audio nor transcript. Temporary audio is deleted. Whisper explicitly uses `language="en"`, `task="transcribe"`, `beam_size=5`, `vad_filter=True`, and `condition_on_previous_text=False`. Defaults are Whisper `small`, CPU, int8 unless configured otherwise.

Returned `language_probability` is language metadata, not distress or emotion confidence, and is not persisted. No acoustic emotion inference runs in this path.

An indirect UI issue matters: the victim form initializes all questionnaire answers to zero and submits those alongside the note. A text/voice check-in can create a zero-answer assessment if those values remain untouched. That changes questionnaire history through submitted answers—not through AI or voice fusion.

Support sources: [operations.py](sih_backend_latest/app/operations.py), `create_request`, `requests`, `review_request`; [models.py](sih_backend_latest/app/models.py), `SupportRequest`, `SupportSession`.

Request kinds are `Callback`, `Threat report`, and `Support`. The endpoint records the kind and workflow status; it does not analyze a threat narrative or change distress/risk/priority. Sessions persist requested/confirmed/completed/cancelled states, but these states do not feed scoring.

## 2. TARGET ALGORITHM WE WANT TO ACHIEVE

Use an additive, versioned monitoring layer. Preserve existing `Assessment`, `AIAnalysis`, and review records.

**All numbers below are engineering/demo settings, not clinically validated thresholds.**

### 2.1 Four persisted layers

| Layer | Proposed records | Contents |
|---|---|---|
| Raw/source evidence | Existing Assessment/AIAnalysis plus `VoiceObservation` and `CaseSignal` | Source links, questionnaire answers/raw score, legacy score, AI outputs, transcript revisions, SER probabilities, provenance |
| Derived features | Feature payload attached to each monitoring snapshot | Trends, repeated high days, agreement/disagreement, recency, missing/failed modalities |
| Unified priority | `CaseMonitoringSnapshot` | Score, category, severity, requires_attention, contributions, rule IDs, evidence IDs, calculation time, configuration version |
| Alert lifecycle | `Alert` and append-only `AlertEvent` | Trigger, severity, acknowledgement, review, resolution, escalation, intervention/follow-up references |

`CaseSignal` should reference existing AIAnalysis records rather than duplicating or replacing them. Give each source event a unique idempotency key and distinguish observation time from processing time.

For questionnaires, retain both:

```text
legacy_distress_score = existing Assessment.distress_score
raw_questionnaire_score = round(sum(saved answers) / 24 × 100)
```

For new monitoring fusion, use the reconstructed raw questionnaire score as the weighted numeric input. Keep the legacy score and risk visible, and honor legacy Critical risk through a safety override. This avoids applying historical weighting and trend bonuses twice.

This is an intentional new-layer decision, not a change to historical questionnaire records.

### 2.2 Explicit base fusion

Use questionnaire evidence and text evidence as the two primary families.

```text
Q = latest raw questionnaire score

Text candidates:
    latest successful assessment-note analysis
    latest successful eligible victim-chat analysis
    latest successful confirmed-transcript analysis

T = highest distress score among eligible text candidates
    (tie: newest observation)
```

Choosing the highest latest-per-source text result is a conservative demo policy. It prevents a low-score observation from immediately replacing another source's concerning result.

Text and transcript analysis belong to one family. They do not receive separate independent weights merely because they arrived through different interfaces. A single transcript analysis linked through an assessment must be counted once, using source identity/provenance.

Recency, applied to each selected observation:

```text
r(age) = 1.0 for age <= 2 days
         0.5 for 2 < age <= 7 days
         0   for age > 7 days
```

Exclude future-dated, failed, pending, invalid, and superseded results. Eligible text candidates must have nonzero recency weight before selecting T.

```text
wQ = 0.60 × rQ, if Q exists
wT = 0.40 × rT, if T exists

base = (wQ×Q + wT×T) / (wQ + wT)
```

Missing modalities do not become zero scores. If no eligible primary evidence remains, numeric priority is unavailable; unresolved safety alerts still apply.

Persist evidence age and coverage. Recency affects influence, not a claim that someone's condition improved.

### 2.3 Derived features and bounded additions

Use separate questionnaire and text trends. Never mix their values into one time series.

For each family, reuse the explainable daily-median/regression approach:

```text
14-day window
latest seven observed UTC days
minimum three distinct days
```

Use the current explicit slope/change thresholds, but standardize labels as rising, rapidly rising, falling, stable, or insufficient.

Questionnaire trend uses raw questionnaire scores. Text daily medians use deduplicated text observations.

| Feature | Proposed contribution |
|---|---:|
| Either family rising | +10 |
| Either family rapidly rising | +20 instead of +10 |
| High observations on at least two distinct days within seven days | +8 |
| Questionnaire and text both >=50, observed within 24 hours of each other | +5 |
| Questionnaire/text score difference >=30 within 24 hours | Explanation flag; no automatic numeric bonus |
| Unreliable/missing behavioural evidence | 0 |

Take the highest trend bonus across families, not the sum. Count each calendar day once for repeated-high detection, regardless of submission count or number of modalities. High observations are questionnaire/text scores >=50 or their High/Critical risk labels; SER alone does not qualify a day.

Emotion labels remain persisted and displayed as explanation context. Free-form emotion names should not create extra points on top of the AI distress score.

### 2.4 Conservative SER contribution

The actual local Testing 4 artifact is [best_frozen_wav2vec2_head.pt](Speech-Emotion-Recognition/testing4_output/best_frozen_wav2vec2_head.pt).

Its [evaluation implementation](Speech-Emotion-Recognition/evaluate_testing4_checkpoint.py) specifies:

```text
facebook/wav2vec2-base frozen encoder
pooled 768-dimensional features
Dropout(0.2) + Linear(768, 4)

labels:
    neutral=0, happy=1, sad=2, angry=3
```

Preprocessing includes 16 kHz mono audio, mean centering, conditional peak normalization, and a maximum five-second center crop.

The saved [test_results.json](Speech-Emotion-Recognition/testing4_output/test_results.json) reports:

```text
112 samples, held-out actors 21–24
accuracy:          43.75%
balanced accuracy: 42.19%
macro F1:          0.3721
Sad recall:         3.125%
```

These are saved evaluation results, not a new evaluation run. The root `testing4_ser.py` is only an unrelated model-ID assignment; it is not this checkpoint's inference implementation. The tiny-overfit diagnostic in experiment metadata is not generalization performance.

Proposed persisted output:

```text
predicted_emotion
probabilities for all four classes
top_probability
top_two_margin
model/checkpoint/preprocessing versions
audio quality/status
observation ID and timestamp
```

Proposed contribution:

```text
p_negative = p(sad) + p(angry)

SER_bonus = 3 × p_negative
```

Apply it only when all conditions hold:

```text
quality checks passed
prediction is sad or angry
top_probability >= 0.70
top_two_margin >= 0.20
a questionnaire or text score >=50 corroborates it within 24 hours
```

Otherwise contribution is zero, with the raw result still visible.

Additional restrictions:

- Maximum contribution: 3 points.
- SER alone cannot create High/Critical priority.
- If pre-SER priority is below 80, SER cannot push it to 80 or above; cap such a result at 79.9.
- Happy/neutral predictions never subtract points or cancel safety evidence.
- Softmax probabilities are model outputs, not calibrated probabilities of distress or harm.
- Audio quality gates and duration handling must be specified and tested before enabling this contribution; missing/failed quality checks mean zero contribution.

### 2.5 Unified score, safety overrides, and attention

```text
ordinary_score = clamp(
    base + trend_bonus + repeated_high_bonus + agreement_bonus,
    0, 100
)

candidate_score = ordinary_score + gated_SER_bonus
```

Apply the SER threshold restriction, clamp to 0–100, round to one decimal, then apply explicit floors:

| Evidence/rule | Minimum priority |
|---|---|
| Current eligible questionnaire or text High risk | 55 / HIGH |
| Questionnaire `self_harm_thoughts >=3` | 90 / URGENT |
| Questionnaire Critical risk, including legacy Critical | 90 / URGENT |
| Text Critical or separately recorded serious self-harm/immediate-danger signal | 90 / URGENT |
| Unresolved safety alert from earlier evidence | Preserve its safety floor |

Treat text-generated danger as an urgent review signal, not a confirmed emergency or diagnosis.

```text
NORMAL: <30
MEDIUM: 30–54.9
HIGH:   55–79.9
URGENT: >=80
```

Suggested severity mapping:

```text
NORMAL → informational
MEDIUM → moderate
HIGH → high
URGENT → critical
```

`requires_attention=True` for High/Urgent priority or an unresolved alert requiring professional action.

A normal modality must never average away Critical evidence. Acknowledgement must not remove a safety floor; documented professional review and resolution are required. Resolved evidence must be recorded as handled so replaying it does not repeatedly reapply the same unresolved safety event. New safety evidence is evaluated independently.

For existing `AIAnalysis`, use the Critical result as a conservative override. A later version can add structured safety findings in a separate linked record without altering existing AIAnalysis schemas or records.

Support requests remain operational evidence. An open threat report can receive a separately explained High-priority triage floor, without pretending its request type measures psychological distress. Callback requests alone need no distress-score increment.

### 2.6 Alert lifecycle and end-to-end flow

```text
Questionnaire / text / eligible chat / submitted voice
→ persist source and processing status
→ persist completed modality outputs
→ derive features
→ persist versioned unified priority
→ create/update durable alert
→ Authority/Counsellor acknowledgement
→ professional review
→ intervention / follow-up
→ documented resolution
```

Use lifecycle states:

```text
OPEN → ACKNOWLEDGED → UNDER_REVIEW → RESOLVED
```

Every transition appends an `AlertEvent` with actor, time, prior/new state, reason, and evidence references.

Creation rules:

- Create alerts for High/Urgent priority or explicit safety rules.
- Deduplicate by case, rule, and evidence/episode.
- Repeated reads never create alerts.
- Escalation appends evidence and an event.
- New safety evidence after acknowledgement requires renewed attention.
- Resolution does not modify raw observations or erase history.
- Reprocessing identical evidence must not recreate a resolved alert.

Persist raw source data before inference. Use durable processing/recompute jobs so failures or restarts cannot silently lose monitoring updates. A small database-backed job table and runner are sufficient; a broad infrastructure rewrite is unnecessary.

Recompute on source completion and at recency boundaries so persisted snapshots do not silently remain fresh forever. Preserve access scoping and distinguish full evidence access from authority aggregate views.

## 3. GAP ANALYSIS

Paths below are relative to `sih_backend_latest/app` or `sih_frontend_latest`, unless specified. New files are proposals, not existing implementations.

| Feature | Current implementation | Target implementation | Gap | Files likely affected |
|---|---|---|---|---|
| Questionnaire history | Four recent submissions; recursive blended score; separate three-row alert trend | Preserve legacy output; raw-score history and versioned features | Inconsistent windows; no persisted calculation provenance | `cases.py`, `models.py`, new signal/features modules |
| Text AI | Persisted AIAnalysis; independently generated scores | Existing records referenced by unified layer | Does not influence questionnaire-based case risk or unified priority | `ai_workflow.py`, `monitoring_rules.py`, new fusion service |
| Whisper | Temporary transcription; edited text becomes ordinary note; English forced | Persist submitted transcript/provenance and analysis linkage | Voice source identity and metadata lost | `voice.py`, `voice_service.py`, `schemas.py`, victim dashboard |
| SER | Local experimental checkpoint; absent from application pipeline | Exact checkpoint inference, persisted probabilities, gated contribution | No inference adapter, schema, or fusion | New `ser_service.py`; voice service; model/schema additions |
| Multimodal fusion | Questionnaire and text-AI paths separate | Explicit versioned fusion with safety floors | No unified state or score | New `case_signals.py`, `monitoring_service.py`; rules |
| Analytics | Latest AI risk/priority only | Unified severity, attention, stale/missing evidence, unresolved-alert counts | Questionnaire-only Critical cases omitted from priority | `monitoring.py`; `AuthorityMonitoring.tsx`, `Operations.tsx` |
| Alerts | GET-generated indicators; review timestamp | Event-driven persisted alerts and lifecycle | Discovery delay, duplicate insertion defect, no full lifecycle | `monitoring.py`, `models.py`, new alerts service |
| Authority case detail | Questionnaire risk plus separate AI history | Unified explanation, provenance, alert history with scoped evidence | No multimodal evidence/timeline | `CaseDetails.tsx`, `CaseMonitoring.tsx`, monitoring endpoints |
| Counsellor case detail | AI graph/review plus chat | Unified priority, modality evidence, interventions/follow-up | AI review is disconnected from indicator review | Same components; chat/alert APIs |
| Persistence | Assessment, AIAnalysis, indicators, analysis reviews | Additive CaseSignal, voice output, snapshots, Alert/Event/job tables | No reproducible fusion snapshots or raw voice/SER records | `models.py`, new additive migration |
| Alert acknowledgement | Three separate review mechanisms | Explicit acknowledgement distinct from review/resolution | No shared episode or audit trail | `monitoring.py`, `operations.py`, alert UI |
| Behaviour/engagement | Sessions and requests exist; no validated engagement features | Only reliable scheduled/observed features | No expected check-in schedule or reliable missed-session status | `operations.py`, new feature extraction |
| Regional analytics | Location fields exist; current monitoring summary is not regional | Scoped aggregation with unknown-location handling | New cases may have empty geography | `monitoring.py`, assignment/analytics UI |

## 4. IMPLEMENTATION PLAN

### P0 — Unify existing evidence and make alerts reliable

1. **Add schemas and an additive migration.** Introduce CaseSignal, monitoring snapshots, Alert/Event, and durable recompute jobs. Preserve existing scores, AIAnalysis, indicators, and reviews.
2. **Implement one deterministic fusion service.** Questionnaire plus text, daily features, recency, source validation, explicit safety floors, and contribution explanations. Backfill source references without rerunning AI or rewriting assessments.
3. **Trigger recomputation from writes.** Questionnaire commit and AI completion enqueue idempotent recomputation. Remove indicator creation from GET requests. Resolve the confirmed duplicate-insertion defect as part of this transition.
4. **Implement alert lifecycle and scoped acknowledgement.** Preserve legacy review provenance; do not reinterpret an old “reviewed” timestamp as documented resolution.
5. **Point queues, Analytics, reports, and case details at the same snapshot.** Keep questionnaire and AI raw results separately visible. Fix the text-only form path so untouched defaults do not silently become completed questionnaire answers.
6. **Verify critical boundaries.** Test questionnaire-only Critical cases, self-harm with low numeric score, conflicting modalities, AI failure, stale evidence, repeated submissions, concurrent processing, acknowledgement versus resolution, and authorization.

### P1 — Integrate Testing 4 conservatively

1. Load the exact saved architecture/checkpoint and verify label mapping and preprocessing.
2. Add voice observation persistence and linked transcript/SER results.
3. Run Whisper and SER against submitted audio before temporary-file cleanup; isolate their failures.
4. Store complete probabilities and provenance.
5. Enable the capped, corroborated contribution behind configuration.
6. Verify known checkpoint outputs and that weak/normal SER cannot cancel or independently create Critical priority.

### P2 — Improve coverage

- Introduce explicit expected check-in schedules before calculating missed-engagement features.
- Distinguish no-show, cancellation, completed session, and unavailable records.
- Add regional aggregates with missing-location handling and appropriate access controls.
- Remove forced-English transcription only alongside multilingual validation.
- Validate language-specific chat eligibility, safety extraction, and SER performance before increasing their influence.

## 5. RISKS, ASSUMPTIONS, AND VERIFICATION LIMITS

- **Deployment selection remains unverified.** The latest source tree is the implementation audited here.
- **Historical `distress_score` is already blended.** Preserve it and clearly name reconstructed raw questionnaire scores.
- **Existing questionnaire history can amplify itself.** Submission frequency also influences the current four-record history.
- **Current self-harm protection is incomplete downstream.** It updates questionnaire risk but does not impose an AI-queue floor.
- **Alerts currently have a confirmed transaction failure path.** This belongs in P0.
- **Saved SER performance is weak and uneven.** Confidence gating does not establish calibration or clinical validity.
- **Voice has no current source provenance.** Older notes cannot reliably be classified retrospectively as typed versus transcribed.
- **Missing data is not low distress.** Failed inference, stale observations, and uncompleted questionnaires must remain explicit.
- **Existing demo records may be synthetic.** Backfill should preserve provenance and exclude identifiable fixtures from real analytics.
- **Safety migration needs provenance-aware handling.** Do not silently close historical safety evidence or treat synthetic fixtures as live emergencies; review legacy evidence as part of rollout policy.
- **Concurrent submissions and processing require idempotency and transaction handling.** A versioned snapshot should identify precisely which evidence it consumed.
- **Model and configuration provenance matter.** Existing AIAnalysis stores provider but not a full model/prompt version; future processing should record those details in the additive layer.
- **The proposed fusion rules require evaluation and professional review.** They provide transparent engineering behavior, not a validated clinical assessment.
- **Verification was bounded.** Formula execution and the duplicate-indicator failure were checked in isolation. No production database, running deployment, browser workflow, model inference, or complete test suite was validated during this audit.

## Approval boundary

This document is the analysis deliverable. Application code changes, database migrations/backfills, and model integration remain pending approval of the analysis and implementation scope.
