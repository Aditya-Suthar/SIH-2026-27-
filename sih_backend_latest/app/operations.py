"""Small case administration, human support requests and appointment workflows."""
from datetime import datetime, timezone, timedelta
from typing import Literal
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from .database import get_db
from .auth import get_current_user
from .ai_history import authenticated_account
from .monitoring_rules import utc
from . import models
from .case_identity import victim_names

router = APIRouter(prefix='/api', tags=['Support operations'])


def scope(db, claims):
    user = authenticated_account(db, claims)
    query = db.query(models.Case)
    if user.role == 'victim': query = query.filter(models.Case.victim_id == user.id)
    elif user.role == 'counsellor': query = query.filter(models.Case.assigned_counsellor_id == user.id)
    elif user.role != 'authority': raise HTTPException(403, 'Access denied')
    return user, query


def new_victim_case(db, victim_id):
    row = models.Case(case_id='SAH-'+uuid4().hex[:12].upper(), victim_id=victim_id,
        assigned_counsellor='Not Assigned', risk_level='Not assessed', last_assessment='Never',
        intervention_status='Awaiting assignment', district='', state='')
    db.add(row)
    return row


@router.post('/victim/case')
def ensure_case(db:Session=Depends(get_db), claims:dict=Depends(get_current_user)):
    user, query = scope(db, claims)
    if user.role != 'victim': raise HTTPException(403,'Victim access required')
    # Lock parent so concurrent onboarding requests cannot create duplicate cases.
    db.query(models.User).filter_by(id=user.id).with_for_update().first()
    row=query.first()
    if row is None: row=new_victim_case(db,user.id);db.commit()
    return {'caseId':row.case_id}


@router.get('/counsellors')
def counsellors(db:Session=Depends(get_db), claims:dict=Depends(get_current_user)):
    user,_=scope(db,claims)
    if user.role!='authority': raise HTTPException(403,'Authority access required')
    cases=db.query(models.Case).all()
    return {'items':[{'id':u.id,'name':u.name,'assigned_cases':sum(c.assigned_counsellor_id==u.id for c in cases)} for u in db.query(models.User).filter_by(role='counsellor').order_by(models.User.name)]}


class CaseUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    counsellor_id: int | None = Field(default=None,gt=0)
    status: Literal['Awaiting assignment','Monitoring','Follow-up pending','Rehabilitation','Closed'] | None = None
    district: str | None = Field(default=None,max_length=100)
    state: str | None = Field(default=None,max_length=100)


@router.patch('/cases/{case_id}/assignment')
def assign(case_id:str, data:CaseUpdate, db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    user,query=scope(db,claims)
    if user.role!='authority': raise HTTPException(403,'Authority access required')
    case=query.filter_by(case_id=case_id).with_for_update().first()
    if case is None: raise HTTPException(404,'Case not found')
    if data.counsellor_id is not None:
        counsellor=db.query(models.User).filter_by(id=data.counsellor_id,role='counsellor').first()
        if counsellor is None: raise HTTPException(422,'Choose an existing counsellor')
        if case.assigned_counsellor_id != counsellor.id:
            # A reassignment must not leave old appointments falsely confirmed.
            db.query(models.SupportSession).filter(models.SupportSession.case_id==case.id,models.SupportSession.status.in_(['Requested','Confirmed'])).update({'status':'Cancelled'})
        case.assigned_counsellor_id=counsellor.id;case.assigned_counsellor=counsellor.name
        if case.intervention_status=='Awaiting assignment':case.intervention_status='Monitoring'
    if data.status is not None:case.intervention_status=data.status
    if data.district is not None:case.district=data.district.strip()
    if data.state is not None:case.state=data.state.strip()
    db.commit()
    return {'message':'Case updated'}


@router.get('/sessions')
def sessions(db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    user,query=scope(db,claims)
    rows=db.query(models.SupportSession,models.Case).join(models.Case).filter(models.Case.id.in_(query.with_entities(models.Case.id)))
    if user.role=='victim':rows=rows.filter(models.SupportSession.victim_id==user.id)
    if user.role=='counsellor':rows=rows.filter(models.SupportSession.counsellor_id==user.id)
    rows = rows.order_by(models.SupportSession.starts_at.desc()).limit(200).all()
    names = victim_names(db, [c for _, c in rows]) if user.role != 'victim' else {}
    return {'items':[{'id':s.id,'case_id':c.case_id,
                     **({'victim_name':names[c.id]} if user.role != 'victim' else {}),
                     'counsellor':c.assigned_counsellor,'starts_at':utc(s.starts_at).isoformat(),'duration_minutes':s.duration_minutes,'status':s.status} for s,c in rows]}


class SessionCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    case_id:str
    starts_at:datetime
    duration_minutes:int=Field(default=45,ge=15,le=120,strict=True)


@router.post('/sessions')
def create_session(data:SessionCreate,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    user,query=scope(db,claims)
    case=query.filter_by(case_id=data.case_id).first()
    if case is None:raise HTTPException(404,'Case not found')
    if not case.assigned_counsellor_id or not case.victim_id:raise HTTPException(409,'Assign a counsellor first')
    if data.starts_at.tzinfo is None:raise HTTPException(422,'Include a timezone')
    starts=utc(data.starts_at)
    if not datetime.now(timezone.utc)<starts<datetime.now(timezone.utc)+timedelta(days=366):raise HTTPException(422,'Choose a future time within one year')
    # Serialize bookings for a counsellor on PostgreSQL; reject overlapping active slots.
    db.query(models.User).filter_by(id=case.assigned_counsellor_id).with_for_update().first()
    existing=db.query(models.SupportSession).filter_by(counsellor_id=case.assigned_counsellor_id).filter(models.SupportSession.status.in_(['Requested','Confirmed'])).all()
    if any(starts<utc(s.starts_at)+timedelta(minutes=s.duration_minutes) and starts+timedelta(minutes=data.duration_minutes)>utc(s.starts_at) for s in existing):raise HTTPException(409,'This time overlaps another appointment')
    row=models.SupportSession(case_id=case.id,victim_id=case.victim_id,counsellor_id=case.assigned_counsellor_id,starts_at=starts,duration_minutes=data.duration_minutes,status='Requested' if user.role=='victim' else 'Confirmed',created_by=user.id)
    db.add(row);db.commit()
    return {'id':row.id,'status':row.status}


class SessionUpdate(BaseModel):
    status:Literal['Confirmed','Completed','Cancelled']


@router.patch('/sessions/{session_id}')
def update_session(session_id:int,data:SessionUpdate,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    user,query=scope(db,claims)
    row=db.query(models.SupportSession).filter(models.SupportSession.id==session_id,models.SupportSession.case_id.in_(query.with_entities(models.Case.id))).first()
    if row is None or (user.role=='victim' and row.victim_id!=user.id) or (user.role=='counsellor' and row.counsellor_id!=user.id):raise HTTPException(404,'Session not found')
    if user.role=='victim' and data.status!='Cancelled':raise HTTPException(403,'Only staff can confirm or complete sessions')
    if row.status in ('Completed','Cancelled'):raise HTTPException(409,'Session is already closed')
    if data.status=='Completed' and (row.status!='Confirmed' or utc(row.starts_at)>datetime.now(timezone.utc)):raise HTTPException(409,'Only a confirmed session that has started can be completed')
    row.status=data.status;db.commit()
    return {'status':row.status}


class RequestCreate(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind:Literal['Callback','Threat report','Support']


@router.post('/support-requests')
def create_request(data:RequestCreate,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    user,query=scope(db,claims)
    if user.role!='victim':raise HTTPException(403,'Victim access required')
    case=query.first()
    if case is None:raise HTTPException(409,'Open your support case first')
    row=db.query(models.SupportRequest).filter_by(case_id=case.id,victim_id=user.id,kind=data.kind,status='Open').first()
    if row is None:row=models.SupportRequest(case_id=case.id,victim_id=user.id,kind=data.kind);db.add(row);db.commit()
    return {'id':row.id,'status':row.status}


@router.get('/support-requests')
def requests(db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    user,query=scope(db,claims)
    rows=db.query(models.SupportRequest,models.Case).join(models.Case).filter(models.Case.id.in_(query.with_entities(models.Case.id)))
    if user.role=='victim':rows=rows.filter(models.SupportRequest.victim_id==user.id)
    rows = rows.order_by(models.SupportRequest.id.desc()).limit(200).all()
    names = victim_names(db, [c for _, c in rows]) if user.role != 'victim' else {}
    return {'items':[{'id':r.id,'case_id':c.case_id,
                     **({'victim_name':names[c.id]} if user.role != 'victim' else {}),
                     'kind':r.kind,'status':r.status,'created_at':utc(r.created_at).isoformat(),'reviewed_by':r.reviewed_by,'reviewed_at':utc(r.reviewed_at).isoformat() if r.reviewed_at else None} for r,c in rows]}


class RequestUpdate(BaseModel):
    status:Literal['Reviewed','Resolved']


@router.patch('/support-requests/{request_id}')
def review_request(request_id:int,data:RequestUpdate,db:Session=Depends(get_db),claims:dict=Depends(get_current_user)):
    user,query=scope(db,claims)
    if user.role=='victim':raise HTTPException(403,'Staff access required')
    row=db.query(models.SupportRequest).filter(models.SupportRequest.id==request_id,models.SupportRequest.case_id.in_(query.with_entities(models.Case.id))).first()
    if row is None:raise HTTPException(404,'Request not found')
    if row.status=='Resolved' and data.status!='Resolved':raise HTTPException(409,'Request already resolved')
    row.status=data.status;row.reviewed_by=user.id;row.reviewed_at=datetime.now(timezone.utc);db.commit()
    return {'status':row.status}
