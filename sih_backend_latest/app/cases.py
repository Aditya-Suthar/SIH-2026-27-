import logging
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .database import get_db
from .auth import get_current_user
from . import models, schemas
from .ai_history import authenticated_account
from .ai_workflow import analyze_saved_check_in


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

    # Convert database Case objects into the API response format
    return [
        schemas.CaseOut(
            caseId=c.case_id,
            riskLevel=c.risk_level,
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
        riskLevel=case.risk_level,
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

    # Return victim dashboard data
    return schemas.VictimDashboardOut(
        caseId=case.case_id,
        riskLevel=case.risk_level,
        distressScore=(db.query(models.Assessment).filter_by(case_id=case.id).order_by(models.Assessment.id.desc()).first().distress_score if db.query(models.Assessment).filter_by(case_id=case.id).first() else None),
        assignedCounsellor=counsellor_name,
        caseStage=case.intervention_status,
    )

def calculate_distress_score(data):
    total = (
        data.mood
        + data.anxiety
        + data.sleep
        + data.hopelessness
        + data.social_withdrawal
        + data.self_harm_thoughts
    )

    # 6 questions, each 0-4 → max raw score = 24
    score = round((total / 24) * 100)

    if data.self_harm_thoughts >= 3:
        risk_level = "Critical"
    elif score >= 75:
        risk_level = "Critical"
    elif score >= 50:
        risk_level = "High"
    elif score >= 25:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    return score, risk_level

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

    score, risk_level = calculate_distress_score(assessment)

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
        created_at=datetime.now().isoformat(),
        note=assessment.note,
    )

    db.add(new_assessment)

    case.risk_level = risk_level
    case.last_assessment = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        analysis_id = None
        if assessment.note is not None:
            db.flush()  # Database-generated source ID, never a client-supplied ID.
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
    }
    if analysis_id is not None:
        status = analyze_saved_check_in(db, analysis_id, assessment.note)
        response['ai_analysis'] = {'id': analysis_id, 'status': status}
    return response
