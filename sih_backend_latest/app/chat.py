"""Persistent transport for the existing case chat screens; no generated replies."""
import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, StringConstraints, field_serializer
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .auth import get_current_user
from .database import get_db
from . import models
from .ai_history import authenticated_account
from .ai_workflow import analyze_saved_check_in

router = APIRouter(prefix='/api', tags=['Case chat'])
logger = logging.getLogger(__name__)


def chat_case(db, current_user, case_id):
    user = authenticated_account(db, current_user)
    if user.role not in ('victim', 'counsellor'):
        raise HTTPException(403, 'Conversations are available only to the victim and assigned counsellor')
    query = db.query(models.Case).filter(models.Case.case_id == case_id)
    query = query.filter(models.Case.victim_id == user.id) if user.role == 'victim' else query.filter(models.Case.assigned_counsellor_id == user.id)
    case = query.first()
    if case is None:
        raise HTTPException(404, 'Case not found')
    return user, case


def eligible_message(content):
    text = content.strip().casefold().strip(' .!?')
    return (len(text) >= 4 and any(c.isalnum() for c in text)
            and text not in {'hello', 'thank you', 'thanks', 'okay', 'good morning', 'good night', 'thankyou'})


class SendMessage(BaseModel):
    model_config = ConfigDict(extra='forbid')
    content: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=4000)]
    client_message_id: UUID


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sender_role: str
    content: str
    created_at: datetime
    client_message_id: str

    @field_serializer('created_at')
    def utc_time(self, value):
        return value.replace(tzinfo=value.tzinfo or timezone.utc).isoformat()


@router.get('/cases/{case_id}/messages')
def list_messages(case_id: str, before_id: int | None = Query(None, ge=1), limit: int = Query(50, ge=1, le=100),
                  db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    _, case = chat_case(db, current_user, case_id)
    query = db.query(models.CaseMessage).filter(models.CaseMessage.case_id == case.id,
                                               models.CaseMessage.victim_id == case.victim_id)
    if before_id is not None:
        query = query.filter(models.CaseMessage.id < before_id)
    rows = query.order_by(models.CaseMessage.id.desc()).limit(limit + 1).all()
    return {'items': [MessageOut.model_validate(row) for row in reversed(rows[:limit])],
            'has_more': len(rows) > limit}


@router.post('/cases/{case_id}/messages')
def send_message(case_id: str, data: SendMessage, db: Session = Depends(get_db),
                 current_user: dict = Depends(get_current_user)):
    user, case = chat_case(db, current_user, case_id)
    if case.victim_id is None or case.assigned_counsellor_id is None:
        raise HTTPException(409, 'A victim and counsellor must be assigned before messaging')
    sender_id, victim_id, internal_case_id = user.id, case.victim_id, case.id
    key = str(data.client_message_id)

    def previous():
        return db.query(models.CaseMessage).filter_by(sender_id=sender_id, client_message_id=key).first()

    def replay(row):
        if row.case_id != internal_case_id or row.victim_id != victim_id or row.content != data.content:
            raise HTTPException(409, 'This message request ID was already used')
        return {'message': MessageOut.model_validate(row), 'replayed': True}

    prior = previous()
    if prior is not None:
        return replay(prior)
    row = models.CaseMessage(case_id=internal_case_id, victim_id=victim_id, sender_id=sender_id,
                             sender_role=user.role, content=data.content, client_message_id=key)
    analysis_id = None
    try:
        db.add(row); db.flush()
        if user.role == 'victim' and eligible_message(data.content):
            analysis = models.AIAnalysis(message_id=row.id, case_id=internal_case_id,
                                         victim_id=victim_id, status='pending')
            db.add(analysis); db.flush(); analysis_id = analysis.id
        saved_message = MessageOut.model_validate(row)
        db.commit()
    except IntegrityError:
        db.rollback()
        prior = previous()
        if prior is not None:
            return replay(prior)
        raise HTTPException(503, 'Message could not be saved. Please retry.') from None
    except SQLAlchemyError:
        db.rollback()
        logger.warning('chat category=source_storage_failed')
        raise HTTPException(503, 'Message could not be saved. Please retry.') from None
    if analysis_id is not None:
        # Reuse Prompt 2's post-commit failure-safe persistence unchanged.
        analyze_saved_check_in(db, analysis_id, data.content)
    return {'message': saved_message, 'replayed': False}
