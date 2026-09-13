import logging
from typing import List
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .database import get_db
from .auth import get_current_user
from . import models, schemas
from .ai_history import authenticated_account
from .ai_workflow import analyze_saved_check_in
from .case_state import current_state, ensure_indicator, update_from_assessment
from .case_identity import victim_names


# Router for all API-related endpoints
router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# GET CASES
# Returns cases accessible to authority and counsellor users
# ---------------------------------------------------------
@router.get("/cases", response_model=List[schemas.CaseOut])
def get_cases(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):


    # Get the role of the currently authenticated user
    role = current_user.get("role")

    # Only authority and counsellor users can access case data
    if role not in ["authority", "counsellor"]:
        raise HTTPException(
            status_code=403,
            detail="Access forbidden for this role"
        )

    authenticated_account(db, current_user)
    # Start a query for all cases
    query = db.query(models.Case)

    # Counsellors can only view cases assigned to them
    if role == "counsellor":
        query = query.filter(
            models.Case.assigned_counsellor_id == current_user.get("user_id")
        )

    # Execute the query and retrieve the cases
    cases = query.all()
    names = victim_names(db, cases)

    # Convert database Case objects into the API response format
    return [
        schemas.CaseOut(
            caseId=c.case_id,
            victimName=names[c.id],
            riskLevel=current_state(c)['risk_display'],
            assignedCounsellor=c.assigned_counsellor,
            lastAssessment=c.last_assessment,
            interventionStatus=c.intervention_status,
            district=c.district,
            state=c.state,
        )
        for c in cases
    ]
# ---------------------------------------------------------
# GET SINGLE CASE
# Returns details for one specific case
# ---------------------------------------------------------
@router.get("/cases/{case_id}", response_model=schemas.CaseOut)
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    role = current_user.get("role")

    # Only authority and counsellor users can access case data
    if role not in ["authority", "counsellor"]:
        raise HTTPException(
            status_code=403,
            detail="Access forbidden for this role"
        )

    authenticated_account(db, current_user)
    # Find the requested case
    query = db.query(models.Case).filter(
        models.Case.case_id == case_id
    )

    # Counsellors can only view cases assigned to them
    if role == "counsellor":
        query = query.filter(
            models.Case.assigned_counsellor_id
            == current_user.get("user_id")
        )

    case = query.first()

    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    return schemas.CaseOut(
        caseId=case.case_id,
        victimName=victim_names(db, [case])[case.id],
        riskLevel=current_state(case)['risk_display'],
        assignedCounsellor=case.assigned_counsellor,
        lastAssessment=case.last_assessment,
        interventionStatus=case.intervention_status,
        district=case.district,
        state=case.state,
    )
# ---------------------------------------------------------
# GET USERS
# Returns all registered users to authority users only
# ---------------------------------------------------------
@router.get("/users", response_model=List[schemas.UserOut])
def get_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    authenticated_account(db, current_user)
    # Only authority users should be able to view all users
    if current_user.get("role") != "authority":
        raise HTTPException(
            status_code=403,
            detail="Access forbidden for this role"
        )

    # Retrieve all registered users
    users = db.query(models.User).all()

    return users

# ---------------------------------------------------------
# VICTIM DASHBOARD
# Returns dashboard information for the logged-in victim
# ---------------------------------------------------------
@router.get(
    "/victim/dashboard",
    response_model=schemas.VictimDashboardOut
)
def get_victim_dashboard(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Ensure that only victim users can access this endpoint
    if current_user.get("role") != "victim":
        raise HTTPException(
            status_code=403,
            detail="Access forbidden for this role"
        )

    # Get the authenticated victim's user ID
    victim_user_id = current_user.get("user_id")

    # Find the case associated with the logged-in victim
    case = (
        db.query(models.Case)
        .filter(models.Case.victim_id == victim_user_id)
        .first()
    )

    # Return an error if no case exists for the victim
    if not case:
        raise HTTPException(
            status_code=404,
            detail="No case found for this victim"
        )

    authenticated_account(db, current_user)
    # Default value when no counsellor has been assigned
    counsellor_name = "Not Assigned"

    # If a counsellor is assigned, retrieve their user information
    if case.assigned_counsellor_id:
        counsellor = (
            db.query(models.User)
            .filter(
                models.User.id == case.assigned_counsellor_id,
                models.User.role == "counsellor",
            )
            .first()
        )

        # Use the counsellor's name if the user was found
        if counsellor:
            counsellor_name = counsellor.name

    latest_assessment = (
        db.query(models.Assessment)
        .filter_by(case_id=case.id)
        .order_by(models.Assessment.id.desc())
        .first()
    )
    recent_history = recent_assessment_history(db, case.id, datetime.now(timezone.utc))
    history = historical_distress(recent_history)

    # Return victim dashboard data
    return schemas.VictimDashboardOut(
        caseId=case.case_id,
        riskLevel=case.risk_level,
        distressScore=latest_assessment.distress_score if latest_assessment else None,
        historicalScore=history['score'],
        recentTrend=history['trend'] if recent_history else None,
        recentScores=[{'score': row['score'], 'createdAt': row['created_at']} for row in reversed(recent_history)],
        assignedCounsellor=counsellor_name,
        caseStage=case.intervention_status,
        dateOfBirth=authenticated_account(db, current_user).date_of_birth,
    )

HISTORY_LOOKBACK_DAYS = 4
HISTORY_MAX_CHECK_INS = 4
HISTORY_WEIGHTS = (0.4, 0.3, 0.2, 0.1)  # Newest to oldest.
SIGNIFICANT_TREND_POINTS = 10
RISING_TREND_BONUS = 5


def questionnaire_distress_score(data):
    """Keep the existing six-question questionnaire calculation unchanged."""
    total = (
        data.mood
        + data.anxiety
        + data.sleep
        + data.hopelessness
        + data.social_withdrawal
        + data.self_harm_thoughts
    )

    # 6 questions, each 0-4 → max raw score = 24
    return round((total / 24) * 100)


def risk_level_for_score(score, self_harm_thoughts):
    """Use existing thresholds, preserving the self-harm safety override."""
    if self_harm_thoughts >= 3:
        risk_level = "Critical"
    elif score >= 75:
        risk_level = "Critical"
    elif score >= 50:
        risk_level = "High"
    elif score >= 25:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    return risk_level


def parse_assessment_timestamp(value):
    """Read legacy naive ISO strings and current UTC ISO strings as UTC."""
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (AttributeError, TypeError, ValueError):
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc).astimezone(timezone.utc)


def recent_assessment_history(db, case_id, now):
    """Return at most four prior questionnaire scores for this case in four days."""
    cutoff = now - timedelta(days=HISTORY_LOOKBACK_DAYS)
    rows = (
        db.query(models.Assessment)
        .filter(models.Assessment.case_id == case_id)
        .order_by(models.Assessment.id.desc())
        .limit(100)
        .all()
    )
    history = []
    for row in rows:
        created_at = parse_assessment_timestamp(row.created_at)
        if created_at is None or not cutoff <= created_at < now:
            continue
        history.append({'score': row.distress_score, 'created_at': created_at.isoformat()})
        if len(history) == HISTORY_MAX_CHECK_INS:
            break
    return history


def historical_distress(history):
    """Weight newest scores most heavily and classify their end-to-end movement."""
    if not history:
        return {'score': None, 'trend': 'stable', 'delta': 0}
    weights = HISTORY_WEIGHTS[:len(history)]
    denominator = sum(weights)
    score = round(sum(row['score'] * weight for row, weight in zip(history, weights)) / denominator, 1)
    delta = history[0]['score'] - history[-1]['score']
    trend = ('rising' if delta >= SIGNIFICANT_TREND_POINTS else
             'falling' if delta <= -SIGNIFICANT_TREND_POINTS else 'stable')
    return {'score': score, 'trend': trend, 'delta': delta}


def calculate_distress_score(data, history):
    """Combine unchanged questionnaire score with a bounded historical component."""
    current_score = questionnaire_distress_score(data)
    historical = historical_distress(history)
    # With no prior check-in, use today's score as the history baseline so a
    # first submission remains exactly the existing questionnaire result.
    history_score = historical['score'] if historical['score'] is not None else current_score
    escalation_bonus = RISING_TREND_BONUS if historical['trend'] == 'rising' else 0
    final_score = min(100, max(0, round(
        current_score * 0.8 + history_score * 0.2 + escalation_bonus
    )))
    risk_level = risk_level_for_score(final_score, data.self_harm_thoughts)
    metadata = {
        'currentScore': current_score,
        'historicalScore': historical['score'],
        'finalScore': final_score,
        'recentTrend': historical['trend'],
        'trendDelta': historical['delta'],
        'escalationBonus': escalation_bonus,
        'recentScores': list(reversed(history)),
    }
    return final_score, risk_level, metadata

@router.post("/victim/assessment")
def submit_assessment(
    assessment: schemas.AssessmentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "victim":
        raise HTTPException(
            status_code=403,
            detail="Only victims can submit assessments"
        )

    victim_user_id = current_user.get("user_id")
    if assessment.note is not None:
        authenticated_account(db, current_user)

    case = (
        db.query(models.Case)
        .filter(models.Case.victim_id == victim_user_id)
        .first()
    )

    if not case:
        raise HTTPException(
            status_code=404,
            detail="No case found for this victim"
        )

    now = datetime.now(timezone.utc)
    history = recent_assessment_history(db, case.id, now)
    score, risk_level, distress_metadata = calculate_distress_score(assessment, history)

    new_assessment = models.Assessment(
        case_id=case.id,
        mood=assessment.mood,
        anxiety=assessment.anxiety,
        sleep=assessment.sleep,
        hopelessness=assessment.hopelessness,
        social_withdrawal=assessment.social_withdrawal,
        self_harm_thoughts=assessment.self_harm_thoughts,
        distress_score=score,
        risk_level=risk_level,
        created_at=now.isoformat(),
        note=assessment.note,
    )

    db.add(new_assessment)

    try:
        db.flush()
        update_from_assessment(case, new_assessment, now)
        case.last_assessment = now.strftime("%Y-%m-%d %H:%M")
        ensure_indicator(db, case)
        analysis_id = None
        if assessment.note is not None:
            analysis = models.AIAnalysis(
                assessment_id=new_assessment.id,
                case_id=case.id,
                victim_id=victim_user_id,
                status='pending',
            )
            db.add(analysis)
            db.flush()
            analysis_id = analysis.id
    
        # Commit the original text and pending record before any external inference.
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        # SQL exceptions may contain the submitted note in query parameters.
        logger.warning('check_in category=source_storage_failed')
        raise HTTPException(status_code=503, detail='Check-in could not be saved. Please try again.') from None

    response = {
        "message": "Assessment submitted successfully",
        "distressScore": score,
        "riskLevel": risk_level,
        "distressMetadata": distress_metadata,
    }
    if analysis_id is not None:
        status = analyze_saved_check_in(db, analysis_id, assessment.note)
        response['ai_analysis'] = {'id': analysis_id, 'status': status}
    return response
