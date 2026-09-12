"""Deterministic selection and explainable scoring for questionnaire v2."""
from collections import defaultdict
from datetime import date

from .question_bank import ALL_AGES, BY_ID, CORE_IDS, QUESTIONS, RESPONSE_OPTIONS

SCORING_VERSION = "2.0"
TARGET_INITIAL = 12
MAX_FOLLOWUPS = 3
DOMAIN_WEIGHTS = {
    "mood": 1.2, "anxiety": 1.1, "trauma": 1.2, "sleep": .8,
    "physical_wellbeing": .7, "anger": .8, "social_withdrawal": .9,
    "hopelessness": 1.3, "concentration": .7, "functioning": 1.2,
    "social_support": .8, "family": .7, "education_work": .8,
    "financial": .8, "relationship": .8, "physical_stress": .6,
    "avoidance": .9, "hypervigilance": 1.0, "substance_use": .9,
    "loneliness": .9, "grief": .8, "sense_of_control": .8,
    "coping": .9, "protective_factors": 1.0,
}
AGE_NAMES = {"13-17":"Adolescent", "18-24":"Young Adult", "25-44":"Adult",
             "45-59":"Middle-aged Adult", "60+":"Older Adult"}


def age_on(dob: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def age_group(dob: date, today: date | None = None) -> str:
    age = age_on(dob, today)
    if age < 13 or age > 120: raise ValueError("Questionnaires support ages 13 through 120")
    if age <= 17: return "13-17"
    if age <= 24: return "18-24"
    if age <= 44: return "25-44"
    if age <= 59: return "45-59"
    return "60+"


def answer_severity(question, value: int) -> int:
    maximum = 1 if question.response_type in ("yes_no", "safety_yes_no") else 4
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError(f"Invalid answer for {question.id}")
    severity = value * 4 if maximum == 1 else value
    return 4 - severity if question.reverse_scored else severity


def select_questions(group: str, previous_sessions=(), victim_id: int = 0):
    """Six universal cores plus six rotated, age-eligible questions."""
    if group not in ALL_AGES: raise ValueError("Unknown age group")
    asked_at = {}
    elevated = defaultdict(float)
    previous_answers = {}
    for sequence, session in enumerate(previous_sessions):
        for qid in session.selected_question_ids or []: asked_at[qid] = sequence
        for domain, score in (session.domain_scores or {}).items():
            elevated[domain] = max(elevated[domain], float(score))
        previous_answers.update(getattr(session, "answers", None) or {})
    candidates = [q for q in QUESTIONS if group in q.age_groups and q.id not in CORE_IDS
                  and not q.follow_up_for and not q.critical]
    # Elevated domains first; then least recently asked; stable ID offset rotates ties.
    offset = (len(previous_sessions) + victim_id) % max(1, len(candidates))
    rotated_rank = {q.id:(i-offset) % len(candidates) for i,q in enumerate(candidates)}
    candidates.sort(key=lambda q:(-(elevated[q.domain] >= 60), asked_at.get(q.id, -10_000),
                                  -q.severity_weight, rotated_rank[q.id], q.id))
    selected = [BY_ID[qid] for qid in CORE_IDS]
    used_domains = {q.domain for q in selected}
    historical_followups = []
    for child in QUESTIONS:
        if group not in child.age_groups or not child.follow_up_for: continue
        if any(parent in previous_answers and answer_severity(BY_ID[parent], previous_answers[parent]) >= 3
               for parent in child.follow_up_for):
            historical_followups.append(child)
    historical_followups.sort(key=lambda q:(not q.critical, asked_at.get(q.id, -10_000), -q.severity_weight, q.id))
    for question in historical_followups[:2]:
        if question.id not in {q.id for q in selected}:
            selected.append(question); used_domains.add(question.domain)
    for question in candidates:
        if len(selected) >= TARGET_INITIAL: break
        # Prefer breadth until all six adaptive slots have distinct domains.
        if question.domain in used_domains and any(q.domain not in used_domains for q in candidates):
            continue
        selected.append(question); used_domains.add(question.domain)
    if len(selected) < TARGET_INITIAL:
        selected.extend(q for q in candidates if q not in selected)[:TARGET_INITIAL-len(selected)]
    return selected


def triggered_followups(answers: dict[str, int], already_selected=()):
    triggered = []
    selected = set(already_selected)
    for child in QUESTIONS:
        if not child.follow_up_for or child.id in selected: continue
        for parent_id in child.follow_up_for:
            if parent_id not in answers: continue
            parent = BY_ID[parent_id]
            if answer_severity(parent, answers[parent_id]) >= 3:
                triggered.append(child); break
    triggered.sort(key=lambda q:(not q.critical, -q.severity_weight, q.id))
    return triggered[:MAX_FOLLOWUPS]


def score_answers(answers: dict[str, int]):
    numerators, denominators = defaultdict(float), defaultdict(float)
    contributions = []
    safety_flags = []
    for qid, value in answers.items():
        question = BY_ID.get(qid)
        if question is None: raise ValueError(f"Unknown question {qid}")
        severity = answer_severity(question, value)
        weighted = severity * question.severity_weight
        numerators[question.domain] += weighted
        denominators[question.domain] += 4 * question.severity_weight
        contributions.append({"question_id":qid, "domain":question.domain,
                              "severity":severity, "weight":question.severity_weight,
                              "weighted_severity":weighted})
        if question.critical and severity >= 3:
            safety_flags.append(qid)
    domain_scores = {domain:round(100*numerators[domain]/denominators[domain], 1)
                     for domain in numerators if denominators[domain]}
    general = [(score, DOMAIN_WEIGHTS[domain]) for domain,score in domain_scores.items()
               if domain in DOMAIN_WEIGHTS]
    overall = round(sum(score*weight for score,weight in general)/sum(weight for _,weight in general), 1) if general else 0.0
    contributions.sort(key=lambda row:(-row["weighted_severity"], row["question_id"]))
    severe = set(safety_flags)
    if severe & {"Q065","Q066","Q067","Q068","Q069","Q070","Q071"}: risk = "Critical"
    elif "Q064" in severe or overall >= 75: risk = "Critical"
    elif overall >= 50: risk = "High"
    elif overall >= 25: risk = "Moderate"
    else: risk = "Low"
    return {"questionnaire_score":overall, "domain_scores":domain_scores,
            "safety_flags":safety_flags, "risk_level":risk,
            "top_contributors":contributions[:5],
            "explanation":{"formula":"weighted mean of normalized answered non-safety domains",
                           "safety_rule":"critical safety signals are evaluated separately and cannot be diluted",
                           "answered_count":len(answers), "scoring_version":SCORING_VERSION}}


def public_question(question):
    data = question.public()
    data["options"] = list(RESPONSE_OPTIONS[question.response_type])
    return data
