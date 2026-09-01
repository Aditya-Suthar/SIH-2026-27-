from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .auth import get_current_user
from . import models, schemas

router = APIRouter(prefix="/api")


@router.get("/cases", response_model=List[schemas.CaseOut])
def get_cases(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    role = current_user.get("role")

    if role not in ["authority", "counsellor"]:
        raise HTTPException(
            status_code=403,
            detail="Access forbidden for this role"
        )

    query = db.query(models.Case)

    if role == "counsellor":
        query = query.filter(
            models.Case.assigned_counsellor_id == current_user.get("user_id")
        )

    cases = query.all()

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


@router.get(
    "/victim/dashboard",
    response_model=schemas.VictimDashboardOut
)
def get_victim_dashboard(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if current_user.get("role") != "victim":
        raise HTTPException(
            status_code=403,
            detail="Access forbidden for this role"
        )

    victim_user_id = current_user.get("user_id")

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

    counsellor_name = "Not Assigned"

    if case.assigned_counsellor_id:
        counsellor = (
            db.query(models.User)
            .filter(
                models.User.id == case.assigned_counsellor_id,
                models.User.role == "counsellor",
            )
            .first()
        )

        if counsellor:
            counsellor_name = counsellor.name

    return schemas.VictimDashboardOut(
        caseId=case.case_id,
        riskLevel=case.risk_level,
        distressScore=42,
        assignedCounsellor=counsellor_name,
        caseStage="Investigation",
    )