"""Authoritative per-case distress projection built from preserved source rows."""
from datetime import datetime, timezone

from . import models


RISK_TO_API = {
    "low": "Low",
    "medium": "Moderate",
    "moderate": "Moderate",
    "high": "High",
    "critical": "Critical",
}
RISK_TO_INTERNAL = {
    "low": "low",
    "medium": "medium",
    "moderate": "medium",
    "high": "high",
    "critical": "critical",
}


def utc(value):
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


def normalized_risk(value):
    return RISK_TO_INTERNAL.get((value or "").strip().lower())


def display_risk(value):
    return RISK_TO_API.get((value or "").strip().lower(), "Not assessed")


def current_state(case):
    """Return the persisted projection, with safe pre-migration compatibility."""
    risk = normalized_risk(case.risk_level)
    source = getattr(case, "latest_risk_source", None)
    score = getattr(case, "latest_distress_score", None)
    observed_at = utc(getattr(case, "latest_state_at", None))
    if source is None and risk is not None and (case.last_assessment or '').strip().lower() not in ('', 'never'):
        source = "legacy_case"
    if source is None:
        risk = None
    return {
        "risk": risk,
        "risk_display": display_risk(risk),
        "score": score,
        "source": source,
        "observed_at": observed_at,
        "assessment_id": getattr(case, "latest_assessment_id", None),
        "analysis_id": getattr(case, "latest_analysis_id", None),
    }


def update_from_assessment(case, assessment, observed_at=None):
    risk = normalized_risk(assessment.risk_level)
    if risk is None:
        raise ValueError("Assessment has no valid risk level")
    case.risk_level = display_risk(risk)
    case.latest_distress_score = assessment.distress_score
    case.latest_risk_source = "questionnaire"
    case.latest_state_at = utc(observed_at or assessment.created_at) or datetime.now(timezone.utc)
    case.latest_assessment_id = assessment.id
    case.latest_analysis_id = None


def update_from_analysis(case, analysis):
    risk = normalized_risk(analysis.risk_level)
    if analysis.status != "completed" or risk is None or type(analysis.distress_score) is not int:
        raise ValueError("Only a valid completed AI analysis can update case state")
    case.risk_level = display_risk(risk)
    case.latest_distress_score = analysis.distress_score
    case.latest_risk_source = "text_ai"
    case.latest_state_at = utc(analysis.finished_at or analysis.created_at) or datetime.now(timezone.utc)
    case.latest_assessment_id = analysis.assessment_id
    case.latest_analysis_id = analysis.id


def indicator_values(case, state=None):
    state = state or current_state(case)
    risk = state["risk"]
    if risk not in ("high", "critical"):
        return None
    source = "text_ai" if state["source"] == "text_ai" else "questionnaire"
    source_id = state["analysis_id"] if source == "text_ai" else state["assessment_id"]
    source_id = source_id if source_id is not None else "legacy"
    score_text = f" ({state['score']}/100)" if state["score"] is not None else ""
    return {
        "source": source,
        "severity": "URGENT" if risk == "critical" else "HIGH",
        "fingerprint": f"authoritative:{source}:{source_id}:{risk}:{state['score']}",
        "reason": f"Current authoritative risk is {display_risk(risk)}{score_text}.",
        "current_score": state["score"],
        "analysis_id": state["analysis_id"],
    }


def ensure_indicator(db, case):
    values = indicator_values(case)
    if values is None:
        return None
    existing = db.query(models.MonitoringIndicator).filter_by(
        case_id=case.id, fingerprint=values["fingerprint"]
    ).first()
    if existing is not None:
        return existing
    row = models.MonitoringIndicator(case_id=case.id, trend=None, **values)
    db.add(row)
    db.flush()
    return row
