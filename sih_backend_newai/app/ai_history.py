"""Read-only, case-scoped AI history using the existing auth/case relationships."""
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, field_serializer
from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_db
from . import models


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    assessment_id: int
    source_type: Literal['assessment'] = 'assessment'
    case_id: int
    victim_id: int
    status: Literal['pending', 'completed', 'failed']
    distress_score: int | None
    risk_level: Literal['low', 'medium', 'high', 'critical'] | None
    emotions: list[str] | None
    requires_attention: bool | None
    reason: str | None
    provider: Literal['gemini', 'groq', 'openrouter'] | None
    created_at: datetime
    finished_at: datetime | None

    @field_serializer('created_at', 'finished_at')
    def utc_timestamp(self, value):
        if value is None:
            return None
        # SQLite drops tzinfo; both DBs store these application-generated UTC times.
        return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()


class AnalysisHistory(BaseModel):
    items: list[AnalysisOut]
    limit: int
    offset: int
    has_more: bool


def authenticated_account(db: Session, current_user: dict) -> models.User:
    """Existing token verification + live account/role check for sensitive records."""
    user_id = current_user.get('user_id')
    if type(user_id) is not int:
        raise HTTPException(status_code=401, detail='Invalid account')
    user = db.get(models.User, user_id)
    if user is None or user.role != current_user.get('role'):
        raise HTTPException(status_code=401, detail='Invalid account')
    return user


router = APIRouter(prefix='/api', tags=['AI history'])


@router.get('/cases/{case_id}/ai-analyses', response_model=AnalysisHistory)
def case_analysis_history(
    case_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = authenticated_account(db, current_user)
    cases = db.query(models.Case).filter(models.Case.case_id == case_id)
    if user.role == 'victim':
        cases = cases.filter(models.Case.victim_id == user.id)
    elif user.role == 'counsellor':
        cases = cases.filter(models.Case.assigned_counsellor_id == user.id)
    elif user.role != 'authority':
        raise HTTPException(status_code=403, detail='Access forbidden for this role')
    case = cases.first()
    if case is None:
        # Same result for unknown and inaccessible cases: no existence disclosure.
        raise HTTPException(status_code=404, detail='Case not found')
    analyses = db.query(models.AIAnalysis).join(
        models.Assessment,
        (models.Assessment.id == models.AIAnalysis.assessment_id)
        & (models.Assessment.case_id == models.AIAnalysis.case_id),
    ).filter(models.AIAnalysis.case_id == case.id)
    if user.role == 'victim':
        # Preserve original author ownership even if a case is later reassigned.
        analyses = analyses.filter(models.AIAnalysis.victim_id == user.id)
    rows = analyses.order_by(models.AIAnalysis.created_at, models.AIAnalysis.id).offset(offset).limit(limit + 1).all()
    return AnalysisHistory(items=[AnalysisOut.model_validate(row) for row in rows[:limit]],
                           limit=limit, offset=offset, has_more=len(rows) > limit)
