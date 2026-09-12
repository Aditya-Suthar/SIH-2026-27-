"""Scoped monitoring views and acknowledgement; reads never invoke AI."""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .auth import get_current_user
from .database import get_db
from . import models
from .ai_history import authenticated_account, valid_source_query, AnalysisOut
from .monitoring_rules import prioritize, valid, utc
from .case_state import current_state, normalized_risk, utc as state_utc

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


def case_view(case, rows, reviews, indicators, now, assessment=None):
    state = current_state(case)
    # Read preserved sources even when the historical case projection is empty.
    if state['score'] is None and state['source'] in (None, 'legacy_case'):
        successful = max((r for r in rows if valid(r)), key=lambda r:(utc(r.created_at), r.id), default=None)
        if successful is not None:
            state.update(score=successful.distress_score, risk=successful.risk_level,
                         source='text_ai', observed_at=utc(successful.finished_at or successful.created_at))
        elif assessment is not None:
            state.update(score=assessment.distress_score, risk=normalized_risk(assessment.risk_level),
                         source='questionnaire', observed_at=state_utc(assessment.created_at))
    result = prioritize(rows, now, state if state['risk'] is not None else None)
    latest = result.pop('latest')
    attempt = max(rows,key=lambda r:(utc(r.created_at),r.id),default=None)
    reviewed = next((r for r in reviews if latest is not None and r.analysis_id==latest.id
                     and r.reviewer_id==case.assigned_counsellor_id),None)
    active_indicator = next((row for row in indicators if row.reviewed_at is None), None)
    return dict(result, case_id=case.case_id, assigned_counsellor=case.assigned_counsellor,
                current_risk=state['risk'], current_score=state['score'],
                current_source=state['source'],
                current_state_at=state['observed_at'].isoformat() if state['observed_at'] else None,
                latest_analysis=AnalysisOut.model_validate(latest).model_dump(mode='json') if latest else None,
                latest_attempt_status=attempt.status if attempt else 'none',
                latest_attempt=AnalysisOut.model_validate(attempt).model_dump(mode='json') if attempt else None,
                questionnaire_score=assessment.distress_score if assessment else None,
                latest_activity=utc(attempt.created_at).isoformat() if attempt else None,
                review={'analysis_id':reviewed.analysis_id,'reviewer_id':reviewed.reviewer_id,
                        'reviewed_at':utc(reviewed.reviewed_at).isoformat()} if reviewed else None,
                needs_review=bool(result['alerts']) and reviewed is None and active_indicator is not None)


def all_views(db, cases):
    now = datetime.now(timezone.utc)
    ids = [c.id for c in cases]
    if not ids: return []
    rows = source_rows(db, ids, now)
    grouped = {cid:[] for cid in ids}
    for row in rows: grouped[row.case_id].append(row)
    reviews = db.query(models.AnalysisReview).join(models.AIAnalysis).filter(models.AIAnalysis.case_id.in_(ids)).all()
    indicator_rows = db.query(models.MonitoringIndicator).filter(models.MonitoringIndicator.case_id.in_(ids)).all()
    indicators = {cid: [] for cid in ids}
    for row in indicator_rows: indicators[row.case_id].append(row)
    assessment_ids = db.query(func.max(models.Assessment.id)).filter(models.Assessment.case_id.in_(ids)).group_by(models.Assessment.case_id)
    assessments = {a.case_id:a for a in db.query(models.Assessment).filter(models.Assessment.id.in_(assessment_ids)).all()}
    items = [case_view(c,grouped[c.id],reviews,indicators[c.id],now,assessments.get(c.id)) for c in cases]
    rank = {'URGENT':0,'HIGH':1,'MEDIUM':2,'NORMAL':3,'UNASSESSED':4}
    return sorted(items,key=lambda x:(rank[x['category']],-(x['score'] or 0),x['case_id']))


@router.get('/monitoring/indicators')
def monitoring_indicators(db: Session=Depends(get_db),current_user: dict=Depends(get_current_user)):
    _, query = professional_cases(db,current_user); cases=query.all()
    ids=[c.id for c in cases]; lookup={c.id:c.case_id for c in cases}
    rows=db.query(models.MonitoringIndicator).filter(models.MonitoringIndicator.case_id.in_(ids),models.MonitoringIndicator.reviewed_at.is_(None)).order_by(models.MonitoringIndicator.created_at.desc()).all() if ids else []
    return {'items':[{'id':r.id,'case_id':lookup[r.case_id],'severity':r.severity,'source':r.source,'reason':r.reason,'current_score':r.current_score,'trend':r.trend,'assessment_id':r.assessment_id,'ai_analysis_id':r.analysis_id,'source_record_id':r.analysis_id if r.source=='text_ai' else r.assessment_id,'created_at':utc(r.created_at).isoformat(),'reviewed':False} for r in rows]}


@router.post('/monitoring/indicators/{indicator_id}/review')
def review_indicator(indicator_id:int,db: Session=Depends(get_db),current_user: dict=Depends(get_current_user)):
    user,query=professional_cases(db,current_user)
    row=db.get(models.MonitoringIndicator,indicator_id)
    if row is None or query.filter(models.Case.id==row.case_id).first() is None: raise HTTPException(404,'Indicator not found')
    if row.reviewed_at is None:
        row.reviewed_by=user.id; row.reviewed_at=datetime.now(timezone.utc); db.commit()
    return {'reviewed_indicator_id':indicator_id}


@router.get('/monitoring/cases')
def monitoring_cases(db: Session=Depends(get_db),current_user: dict=Depends(get_current_user)):
    _, query = professional_cases(db,current_user)
    return {'items':all_views(db,query.all())}


@router.get('/cases/{case_id}/monitoring')
def monitoring_detail(case_id: str,indicator_id: int | None=Query(default=None,gt=0),db: Session=Depends(get_db),current_user: dict=Depends(get_current_user)):
    _, query = professional_cases(db,current_user)
    case = query.filter(models.Case.case_id==case_id).first()
    if case is None: raise HTTPException(404,'Case not found')
    result = all_views(db,[case])[0]
    history = valid_source_query(db).filter(models.AIAnalysis.case_id == case.id).order_by(models.AIAnalysis.created_at.desc(), models.AIAnalysis.id.desc()).limit(201).all()
    result['history'] = [AnalysisOut.model_validate(row).model_dump(mode='json') for row in reversed(history[:200])]
    result['history_limited'] = len(history) > 200
    assessments = db.query(models.Assessment).filter_by(case_id=case.id).order_by(
        models.Assessment.created_at, models.Assessment.id).all()
    sessions = {s.assessment_id:s for s in db.query(models.QuestionnaireSession).filter_by(case_id=case.id)}
    def questionnaire_evidence(a):
        session = sessions.get(a.id)
        observed = state_utc(session.completed_at if session and session.completed_at else a.created_at)
        return {'id':a.id,'score':a.distress_score,'risk':normalized_risk(a.risk_level),
                'observed_at':observed.isoformat() if observed else None,
                'safety_override':bool(a.self_harm_thoughts >= 3 or (session and session.safety_flags))}
    result['questionnaire_history'] = [questionnaire_evidence(a) for a in assessments]
    result['current_questionnaire'] = result['questionnaire_history'][-1] if assessments else None
    result['selected_evidence'] = None
    if indicator_id is not None:
        indicator = db.query(models.MonitoringIndicator).filter_by(id=indicator_id,case_id=case.id).first()
        if indicator is None: raise HTTPException(404,'Indicator not found for this case')
        assessment = db.query(models.Assessment).filter_by(id=indicator.assessment_id,case_id=case.id).first() if indicator.assessment_id else None
        analysis = valid_source_query(db).filter(models.AIAnalysis.id==indicator.analysis_id,models.AIAnalysis.case_id==case.id).first() if indicator.analysis_id else None
        safety_override = bool(assessment is not None and indicator.severity=='URGENT'
                               and (assessment.self_harm_thoughts >= 3 or
                                    (sessions.get(assessment.id) and sessions[assessment.id].safety_flags)))
        result['selected_evidence'] = {
            'id':indicator.id, 'score_snapshot':indicator.current_score,
            'severity':indicator.severity, 'source':indicator.source,
            'source_record_id':indicator.analysis_id if indicator.source=='text_ai' else indicator.assessment_id,
            'created_at':utc(indicator.created_at).isoformat(),
            'triggering_rule':('Critical safety override triggered by the questionnaire response.'
                               if safety_override else indicator.reason),
            'safety_override':safety_override,
            'assessment':({'id':assessment.id,'distress_score':assessment.distress_score,
                           'risk_level':normalized_risk(assessment.risk_level)} if assessment else None),
            'analysis':AnalysisOut.model_validate(analysis).model_dump(mode='json') if analysis else None,
            'reviewed':indicator.reviewed_at is not None,
            'reviewed_at':utc(indicator.reviewed_at).isoformat() if indicator.reviewed_at else None,
        }
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
        for indicator in db.query(models.MonitoringIndicator).filter_by(
            case_id=case.id, analysis_id=analysis.id
        ).filter(models.MonitoringIndicator.reviewed_at.is_(None)):
            indicator.reviewed_by=user.id
            indicator.reviewed_at=datetime.now(timezone.utc)
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
        distribution[item['current_risk'] or 'unassessed']+=1
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
