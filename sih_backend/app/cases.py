from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .auth import get_current_user
from . import models, schemas


# Router for all API-related endpoints
router = APIRouter(prefix="/api")


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
        distressScore=42,
        assignedCounsellor=counsellor_name,
        caseStage="Investigation",
    )