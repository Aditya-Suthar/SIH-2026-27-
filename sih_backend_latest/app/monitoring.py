"""Scoped monitoring views and acknowledgement; reads never invoke AI."""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .auth import get_current_user
from .database import get_db
from . import models
from .ai_history import authenticated_account, valid_source_query, AnalysisOut
from .monitoring_rules import prioritize, valid, utc

router = APIRouter(prefix='/api', tags=['AI monitoring'])


def professional_cases(db, current_user):
    user = authenticated_account(db, current_user)
    if user.role not in ('counsellor','authority'):
        raise HTTPException(403,'Professional monitoring access required')
    query = db.query(models.Case)
    if user.role == 'counsellor':
        query = query.filter(models.Case.assigned_counsellor_id == user.id)
    return user, query


def source_rows(db, case_ids, now):
    # Include recent history plus each case's latest completed and latest attempt.
    # This avoids one query per case while retaining stale/failed status correctly.
    order = (models.AIAnalysis.created_at.desc(), models.AIAnalysis.id.desc())
    attempts = db.query(models.AIAnalysis.id.label('id'), func.row_number().over(
        partition_by=models.AIAnalysis.case_id, order_by=order).label('rank')
    ).filter(models.AIAnalysis.case_id.in_(case_ids)).subquery()
    successes = db.query(models.AIAnalysis.id.label('id'), func.row_number().over(
        partition_by=models.AIAnalysis.case_id, order_by=order).label('rank')
    ).filter(models.AIAnalysis.case_id.in_(case_ids), models.AIAnalysis.status=='completed').subquery()
    latest = db.query(attempts.c.id).filter(attempts.c.rank==1)
    completed = db.query(successes.c.id).filter(successes.c.rank==1)
    return valid_source_query(db).filter(models.AIAnalysis.case_id.in_(case_ids),or_(
        models.AIAnalysis.created_at >= now-timedelta(days=14), models.AIAnalysis.id.in_(latest), models.AIAnalysis.id.in_(completed),
    )).order_by(models.AIAnalysis.created_at,models.AIAnalysis.id).all()


def case_view(case, rows, reviews, now):
    result = prioritize(rows, now)
    latest = result.pop('latest')
    attempt = max(rows,key=lambda r:(utc(r.created_at),r.id),default=None)
    reviewed = next((r for r in reviews if latest is not None and r.analysis_id==latest.id
                     and r.reviewer_id==case.assigned_counsellor_id),None)
    return dict(result, case_id=case.case_id, assigned_counsellor=case.assigned_counsellor,
                latest_analysis=AnalysisOut.model_validate(latest).model_dump(mode='json') if latest else None,
                latest_attempt_status=attempt.status if attempt else 'none',
                latest_activity=utc(attempt.created_at).isoformat() if attempt else None,
                review={'analysis_id':reviewed.analysis_id,'reviewer_id':reviewed.reviewer_id,
                        'reviewed_at':utc(reviewed.reviewed_at).isoformat()} if reviewed else None,
                needs_review=bool(result['alerts']) and reviewed is None)


def all_views(db, cases):
    now = datetime.now(timezone.utc)
    ids = [c.id for c in cases]
    if not ids: return []
    rows = source_rows(db, ids, now)
    grouped = {cid:[] for cid in ids}
    for row in rows: grouped[row.case_id].append(row)
    reviews = db.query(models.AnalysisReview).join(models.AIAnalysis).filter(models.AIAnalysis.case_id.in_(ids)).all()
    items = [case_view(c,grouped[c.id],reviews,now) for c in cases]
    rank = {'URGENT':0,'HIGH':1,'MEDIUM':2,'NORMAL':3,'UNASSESSED':4}
    return sorted(items,key=lambda x:(rank[x['category']],-(x['score'] or 0),x['case_id']))


@router.get('/monitoring/cases')
def monitoring_cases(db: Session=Depends(get_db),current_user: dict=Depends(get_current_user)):
    _, query = professional_cases(db,current_user)
    return {'items':all_views(db,query.all())}


@router.get('/cases/{case_id}/monitoring')
def monitoring_detail(case_id: str,db: Session=Depends(get_db),current_user: dict=Depends(get_current_user)):
    _, query = professional_cases(db,current_user)
    case = query.filter(models.Case.case_id==case_id).first()
    if case is None: raise HTTPException(404,'Case not found')
    result = all_views(db,[case])[0]
    history = valid_source_query(db).filter(models.AIAnalysis.case_id == case.id).order_by(models.AIAnalysis.created_at.desc(), models.AIAnalysis.id.desc()).limit(201).all()
    result['history'] = [AnalysisOut.model_validate(row).model_dump(mode='json') for row in reversed(history[:200])]
    result['history_limited'] = len(history) > 200
    return result


class ReviewRequest(BaseModel):
    analysis_id: int = Field(gt=0,strict=True)


@router.post('/cases/{case_id}/ai-review')
def review_case(case_id: str,data: ReviewRequest,db: Session=Depends(get_db),current_user: dict=Depends(get_current_user)):
    user, query = professional_cases(db,current_user)
    if user.role != 'counsellor': raise HTTPException(403,'Only the assigned counsellor can review')
    case=query.filter(models.Case.case_id==case_id).first()
    if case is None: raise HTTPException(404,'Case not found')
    analysis=valid_source_query(db).filter(models.AIAnalysis.id==data.analysis_id,models.AIAnalysis.case_id==case.id).first()
    if analysis is None: raise HTTPException(404,'Analysis not found')
    if not valid(analysis): raise HTTPException(409,'Only completed analyses can be reviewed')
    # Bind acknowledgement to the exact analysis the counsellor actually saw.
    prior=db.query(models.AnalysisReview).filter_by(analysis_id=analysis.id,reviewer_id=user.id).first()
    if prior is None:
        db.add(models.AnalysisReview(analysis_id=analysis.id,reviewer_id=user.id))
        try: db.commit()
        except IntegrityError: db.rollback()  # Concurrent identical acknowledgement.
    return {'reviewed_analysis_id':data.analysis_id}


@router.get('/monitoring/summary')
def monitoring_summary(db: Session=Depends(get_db),current_user: dict=Depends(get_current_user)):
    user,query=professional_cases(db,current_user)
    if user.role != 'authority': raise HTTPException(403,'Authority access required')
    items=all_views(db,query.all())
    distribution={risk:0 for risk in ('low','medium','high','critical','unassessed')}
    for item in items:
        distribution[item['latest_analysis']['risk_level'] if item['latest_analysis'] else 'unassessed']+=1
    # Aggregates only: no conversation text, emotions or AI reasoning.
    return {'total_cases':len(items),'risk_distribution':distribution,
            'requiring_attention':sum(bool(x['alerts']) for x in items),
            'unreviewed_urgent':sum(x['category']=='URGENT' and x['needs_review'] for x in items),
            'analysis_unavailable':sum(x['latest_attempt_status'] in ('pending','failed') for x in items)}


@router.get('/victim/check-ins')
def victim_checkins(db: Session=Depends(get_db),current_user: dict=Depends(get_current_user)):
    user=authenticated_account(db,current_user)
    if user.role!='victim': raise HTTPException(403,'Victim access required')
    rows=db.query(models.Assessment,models.AIAnalysis.status).join(
        models.Case, models.Case.id==models.Assessment.case_id,
    ).outerjoin(models.AIAnalysis,models.AIAnalysis.assessment_id==models.Assessment.id).filter(
        models.Case.victim_id==user.id,
        or_(models.AIAnalysis.id.is_(None),models.AIAnalysis.victim_id==user.id),
    ).order_by(models.Assessment.id.desc()).limit(20).all()
    return {'items':[{'id':a.id,'created_at':a.created_at,'text_included':bool(a.note),
                      'analysis_status':status or 'not_requested'} for a,status in rows]}
