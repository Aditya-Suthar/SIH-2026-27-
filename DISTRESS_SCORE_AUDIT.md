# SIH Distress Score Algorithm Audit

## Scope

This audit describes the integrated backend in `sih_backend_latest`. The historical questionnaire component below was added after the initial audit; it does not alter the text-analysis, Whisper, or SER pipelines.

The repository contains two independent score streams that are **not fused**:

1. A deterministic six-question questionnaire score, shown to the victim and stored on the assessment/case.
2. An LLM-generated text distress indicator, used for counsellor/authority monitoring and prioritization.

## 1. Questionnaire distress score

**File/functions:** `sih_backend_latest/app/cases.py`, `questionnaire_distress_score(data)`, `recent_assessment_history(...)`, `historical_distress(...)`, and `calculate_distress_score(data, history)`.

**Validated inputs** (`sih_backend_latest/app/schemas.py`, `AssessmentCreate`):

- `mood`
- `anxiety`
- `sleep`
- `hopelessness`
- `social_withdrawal`
- `self_harm_thoughts`

Each is a required integer from 0 through 4.

### Formula

The unchanged questionnaire component is:

```text
raw_total = mood + anxiety + sleep + hopelessness
          + social_withdrawal + self_harm_thoughts

current_questionnaire_score = round((raw_total / 24) * 100)
```

All six responses have equal weight. One raw point is 1/24 of the maximum, or about 4.167 percentage points before rounding.

### Historical component and final score

No history table was created. Prior scores are read from the existing `assessments` table for the authenticated victim's current case only. The query accepts at most four prior assessments from the previous four 24-hour days; it runs before the new assessment is saved.

Scores are ordered newest to oldest and weighted `0.4, 0.3, 0.2, 0.1`. When fewer than four scores exist, the available weights are normalized to sum to one.

```text
historical_score = sum(recent_score[i] * weight[i]) / sum(available weights)
trend_delta = newest_prior_score - oldest_prior_score

trend = rising  when trend_delta >= 10
        falling when trend_delta <= -10
        stable  otherwise

escalation_bonus = 5 when trend is rising, otherwise 0
final_distress_score = clamp(0, 100,
    round(0.8 * current_questionnaire_score
        + 0.2 * historical_score
        + escalation_bonus))
```

For a first check-in, no historical score exists. The current questionnaire score is used as the temporary history baseline, so the final score remains exactly the original questionnaire result.

### Questionnaire risk levels

```text
if self_harm_thoughts >= 3: Critical
else if final_distress_score >= 75: Critical
else if final_distress_score >= 50: High
else if final_distress_score >= 25: Moderate
else: Low
```

So the normal bands are Low 0-24, Moderate 25-49, High 50-74, and Critical 75-100. A self-harm response of 3 or 4 overrides the numerical band and makes the risk Critical.

### Example

```text
mood=2, anxiety=3, sleep=1,
hopelessness=2, social_withdrawal=2, self_harm_thoughts=2

raw_total = 2 + 3 + 1 + 2 + 2 + 2 = 12
current_questionnaire_score = round((12 / 24) * 100) = 50
no prior history -> final_distress_score = 50
risk_level = High
```

### Storage and victim delivery

`submit_assessment()` in `sih_backend_latest/app/cases.py` stores the final composite score in:

- `assessments.distress_score`
- `assessments.risk_level`

It also updates:

- `cases.risk_level`
- `cases.last_assessment`

Existing `distressScore` and `riskLevel` response keys remain. The submission response additionally has `distressMetadata` containing `currentScore`, `historicalScore`, `finalScore`, `recentTrend`, `trendDelta`, `escalationBonus`, and `recentScores`. `/api/victim/dashboard` additionally exposes `historicalScore`, `recentTrend`, and `recentScores`.

This questionnaire history feature does not use text, audio, LLM output, or emotion recognition.

## 2. LLM text distress indicator

**Files/functions:**

- `sih_backend_latest/app/ai_service.py`, `analyze_distress(message)`
- `sih_backend_latest/app/ai_service.py`, `parse_indicators(raw)`
- `sih_backend_latest/app/ai_workflow.py`, `analyze_saved_check_in(...)`

### Inputs and providers

The only scoring input is submitted text:

- optional assessment `note`, or
- an eligible victim chat message.

Providers are tried in this fixed order when configured:

1. Gemini (`gemini-2.5-flash-lite` by default)
2. Groq (`openai/gpt-oss-20b` by default)
3. OpenRouter (`openrouter/free` by default)

Provider temperature is zero, but the resulting score is still LLM-generated, not a deterministic formula. The prompt says to consider only indicators explicitly present in the text.

### LLM output validation and levels

The provider must return an integer score 0-100, a lowercase risk level, emotions, `requires_attention`, and a reason. The backend validates:

```text
0-24   -> low
25-49  -> medium
50-74  -> high
75-100 -> critical

requires_attention = (score >= 50)
```

The backend rejects a provider response whose risk level or attention flag does not match these rules. It does not independently calculate a text score.

### Storage

One pending `AIAnalysis` record is committed before the external call. On success the returned fields are stored in `ai_analyses`:

- `distress_score`
- `risk_level`
- `emotions`
- `requires_attention`
- `reason`
- `provider`
- completion status/timestamps

On a provider or validation failure, the source text remains stored and the AI-analysis row becomes `failed` with score/result fields set to `NULL`. AI results do not overwrite the questionnaire score, assessment risk, or case risk.

## 3. Historical trend and priority score

**File/functions:**

- `sih_backend_latest/app/monitoring_rules.py`, `trend(rows)`
- `sih_backend_latest/app/monitoring_rules.py`, `prioritize(rows)`

These rules use only valid, completed AI text analyses. Questionnaire score history does not contribute.

### Trend algorithm

Eligible records are completed AI results with an integer 0-100 score, valid AI risk level, and timestamp in the previous 14 days.

1. Group scores by UTC calendar day.
2. Take the median score for each day.
3. Keep the latest seven daily medians.
4. Require at least three distinct days.
5. Calculate least-squares slope and total change.

```text
slope = sum((x - mean(x)) * (y - mean(y))) / sum((x - mean(x))^2)
change = latest_daily_median - earliest_daily_median
```

Trend states:

```text
rapidly_worsening: change >= 20 and slope >= 5 and elapsed_days <= 7
worsening:         change >= 5 and slope >= 1
improving:         change <= -5 and slope <= -1
stable:            otherwise
insufficient_data: fewer than three daily values
```

### Priority formula

For the latest valid AI analysis:

```text
priority_points = latest_ai_score * 0.5
                + AI-risk points
                + 12 if requires_attention
                + trend bonus
                + 8 if high/critical occurred on >=2 distinct days in last 7 days

AI-risk points: low=0, medium=8, high=18, critical=30
Trend bonus: worsening=10, rapidly_worsening=25, otherwise=0

priority_score = min(100, round(priority_points, 1))
```

Priority levels:

```text
0-29    NORMAL
30-54   MEDIUM
55-79   HIGH
80-100  URGENT
no valid AI result -> UNASSESSED
```

An analysis older than seven days is flagged as stale, but this does not alter its priority points or category.

### Priority example

For four daily AI scores of 30, 45, 61, and 78:

```text
latest score:                  78 * 0.5 = 39
latest risk is critical:                      +30
requires_attention:                           +12
change = 78 - 30 = 48; slope = +16/day
rapidly worsening trend:                      +25
high/critical on two days:                    + 8
                                              ----
raw priority:                                  114
capped priority score:                         100
priority level:                              URGENT
```

## 4. Voice and speech-emotion recognition

`sih_backend_latest/app/voice_service.py`, `transcribe_audio()` uses local faster-whisper only to turn audio into an editable transcript. The endpoint does not calculate an audio score, extract acoustic features for the backend score, or persist audio.

Whisper can indirectly affect an LLM text indicator only when the victim elects to submit the resulting transcript as assessment text. Whisper itself has no numerical weight.

The standalone `Speech-Emotion-Recognition/` project calculates emotion probabilities, but it is not imported or called by `sih_backend_latest`. Its emotion output does not affect the questionnaire score, text score, risk levels, trend, or priority.

## 5. Frontend/API flow

- Victim dashboard: `/api/victim/dashboard` shows the latest questionnaire score and questionnaire case risk.
- Victim check-in submission: `/api/victim/assessment` returns questionnaire score/risk immediately; optional text can separately create an AI-analysis record.
- Counsellor/authority monitoring: `/api/monitoring/cases` and `/api/cases/{case_id}/monitoring` provide the latest AI indicator, emotions, historical trend, priority score/category, reasons, and alerts.
- Authority summary: `/api/monitoring/summary` provides aggregates.

The latest frontend's case-details view intentionally shows questionnaire risk in the case overview and AI monitoring separately.

## 6. Placeholders, synthetic data, and duplicate implementations

- The questionnaire formula, LLM thresholds, trend algorithm, and priority weights are explicit heuristic/demo rules, not clinically calibrated rules.
- Normal runtime uses live configured LLM providers; tests mock providers and Whisper.
- `sih_backend_latest/app/seed_demo.py` creates explicitly synthetic AI scores without an AI call.
- `seed_cases.py` assigns risk and related demo fields with `random.choice()`.
- Frontend `data/mockData.ts` and `mockConversations.ts` contain display-only fake values.

Repository copies conflict:

- `sih_backend_latest` is the complete integrated implementation.
- `sih_backend` has the same questionnaire algorithm but no integrated AI monitoring/voice workflow and hardcodes victim-dashboard `distressScore=42`.
- `sih_backend_newai` also hardcodes `distressScore=42`, lacks the latest monitoring rules, and has an inconsistent voice-service layout.
- Older frontend copies contain mock score charts and an older client-side counsellor-ranking heuristic; the latest frontend uses backend monitoring priority data.

## Key integration gap

A case can have a questionnaire risk of Critical but monitoring can remain UNASSESSED. This is expected under the current implementation because monitoring priority consumes only completed LLM text analyses and deliberately ignores questionnaire results.
