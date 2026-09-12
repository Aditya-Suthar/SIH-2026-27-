"""Authenticated victim API for age-aware adaptive questionnaire v2."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from . import models, schemas
from .ai_history import authenticated_account
from .ai_workflow import analyze_saved_check_in
from .auth import get_current_user
from .case_state import ensure_indicator, update_from_assessment
from .database import get_db
from .question_bank import BY_ID, CORE_IDS, VERSION
from .questionnaire_engine import (SCORING_VERSION, age_group, public_question,
                                   answer_severity, score_answers, select_questions, triggered_followups)

router = APIRouter(prefix="/api/victim", tags=["adaptive questionnaire"])


def victim_context(db, current_user):
    user = authenticated_account(db, current_user)
    if user.role != "victim": raise HTTPException(403, "Only victims can use questionnaires")
    case = db.query(models.Case).filter_by(victim_id=user.id).first()
    if case is None: raise HTTPException(404, "No case found for this victim")
    return user, case


@router.put("/profile")
def update_victim_profile(data: schemas.VictimProfileUpdate, db: Session = Depends(get_db),
                          current_user: dict = Depends(get_current_user)):
    user, _ = victim_context(db, current_user)
    user.date_of_birth = data.date_of_birth
    db.commit()
    return {"date_of_birth": user.date_of_birth.isoformat(), "age_group": age_group(user.date_of_birth)}


@router.get("/questionnaire")
def next_questionnaire(db: Session = Depends(get_db),
                       current_user: dict = Depends(get_current_user)):
    user, case = victim_context(db, current_user)
    if user.date_of_birth is None:
        raise HTTPException(409, "Date of birth is required before starting the questionnaire")
    group = age_group(user.date_of_birth)
    now = datetime.now(timezone.utc)
    pending = db.query(models.QuestionnaireSession).filter_by(
        victim_id=user.id, status="pending", questionnaire_version=VERSION
    ).order_by(models.QuestionnaireSession.created_at.desc()).first()
    if pending is not None and pending.created_at.replace(tzinfo=pending.created_at.tzinfo or timezone.utc) >= now-timedelta(hours=24):
        session = pending
        questions = [BY_ID[qid] for qid in session.selected_question_ids]
    else:
        history = db.query(models.QuestionnaireSession).filter_by(victim_id=user.id).filter(
            models.QuestionnaireSession.status.in_(("followup","completed"))
        ).order_by(models.QuestionnaireSession.created_at.desc()).limit(12).all()
        latest_assessment = db.query(models.Assessment).filter_by(case_id=case.id).order_by(models.Assessment.id.desc()).first()
        if not history and latest_assessment is not None:
            # Legacy six-item history can guide breadth without inventing question-level answers.
            history = [SimpleNamespace(selected_question_ids=[], answers={}, domain_scores={
                "mood":latest_assessment.mood*25, "anxiety":latest_assessment.anxiety*25,
                "sleep":latest_assessment.sleep*25, "hopelessness":latest_assessment.hopelessness*25,
                "social_withdrawal":latest_assessment.social_withdrawal*25})]
        questions = select_questions(group, list(reversed(history)), user.id)
        session = models.QuestionnaireSession(
            id=str(uuid4()), victim_id=user.id, case_id=case.id,
            questionnaire_version=VERSION, scoring_version=SCORING_VERSION,
            age_group=group, selected_question_ids=[q.id for q in questions],
            triggered_follow_up_ids=[], answers={}, safety_flags=[], status="pending",
        )
        db.add(session); db.commit()
    return {"questionnaire_id":session.id, "questionnaire_version":VERSION,
            "scoring_version":SCORING_VERSION, "age_group":group,
            "age_group_name":{"13-17":"Adolescent","18-24":"Young Adult","25-44":"Adult","45-59":"Middle-aged Adult","60+":"Older Adult"}[group],
            "questions":[public_question(q) for q in questions],
            "notice":"This is a project-specific distress-monitoring check-in, not a medical diagnosis."}


def assessment_values(result):
    domains = result["domain_scores"]
    scale = lambda name: min(4, max(0, round(domains.get(name, 0)/25)))
    return dict(mood=scale("mood"), anxiety=scale("anxiety"), sleep=scale("sleep"),
                hopelessness=scale("hopelessness"),
                social_withdrawal=scale("social_withdrawal"),
                self_harm_thoughts=4 if "Q064" in result["safety_flags"] else 0)


@router.post("/questionnaire/safety-signal")
def record_safety_signal(data: schemas.QuestionnaireSafetySignal, db: Session = Depends(get_db),
                         current_user: dict = Depends(get_current_user)):
    """Persist a concerning selected safety answer without waiting for the full form."""
    user, case = victim_context(db, current_user)
    session = db.query(models.QuestionnaireSession).filter_by(id=data.questionnaire_id).with_for_update().first()
    question = BY_ID.get(data.question_id)
    if session is None or session.victim_id != user.id or session.case_id != case.id:
        raise HTTPException(404, "Questionnaire not found")
    allowed = set(session.selected_question_ids) | set(session.triggered_follow_up_ids or [])
    if question is None or question.id not in allowed or not question.critical:
        raise HTTPException(422, "This is not an available safety question")
    try: severity = answer_severity(question, data.answer)
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    if severity < 3: return {"recorded":False, "risk_level":case.risk_level}
    merged = dict(session.answers or {}); merged[question.id] = data.answer
    result = score_answers(merged); session.answers = merged; session.safety_flags = result["safety_flags"]
    values = assessment_values(result)
    if session.assessment_id is None:
        assessment = models.Assessment(case_id=case.id, distress_score=round(result["questionnaire_score"]),
            risk_level=result["risk_level"], created_at=datetime.now(timezone.utc).isoformat(), note=None, **values)
        db.add(assessment); db.flush(); session.assessment_id = assessment.id
    else:
        assessment = db.get(models.Assessment, session.assessment_id)
        assessment.risk_level = result["risk_level"]
        assessment.self_harm_thoughts = values["self_harm_thoughts"]
    update_from_assessment(case, assessment); ensure_indicator(db, case); db.commit()
    return {"recorded":True, "risk_level":result["risk_level"],
            "safety_flags":result["safety_flags"],
            "triggered_followups":[public_question(q) for q in triggered_followups(merged, session.selected_question_ids)]}


@router.post("/questionnaire/submit")
def submit_questionnaire(data: schemas.QuestionnaireSubmit, db: Session = Depends(get_db),
                         current_user: dict = Depends(get_current_user)):
    user, case = victim_context(db, current_user)
    session = db.query(models.QuestionnaireSession).filter_by(id=data.questionnaire_id).with_for_update().first()
    if session is None or session.victim_id != user.id or session.case_id != case.id:
        raise HTTPException(404, "Questionnaire not found")
    if session.status == "completed":
        assessment = db.get(models.Assessment, session.assessment_id)
        if any(session.answers.get(key) != value for key, value in data.answers.items()) or (data.note is not None and data.note != assessment.note):
            raise HTTPException(409, "Questionnaire is already complete")
        result = score_answers(session.answers)
        analysis = db.query(models.AIAnalysis).filter_by(assessment_id=session.assessment_id).first()
        response = {**result, "questionnaire_id":session.id, "questionnaire_version":VERSION,
                    "scoring_version":SCORING_VERSION, "age_group":session.age_group,
                    "triggered_followups":[], "complete":True,
                    "distress_metadata":{"source":"adaptive_questionnaire", "top_contributors":result["top_contributors"]}}
        if analysis is not None:
            response["ai_analysis"] = {"id":analysis.id, "status":analysis.status}
        db.commit()
        return response
    allowed = set(session.selected_question_ids) | set(session.triggered_follow_up_ids or [])
    unknown = set(data.answers) - allowed
    if unknown: raise HTTPException(422, f"Answers include questions not selected: {sorted(unknown)}")
    if session.status == "pending":
        missing_core = set(CORE_IDS) - set(data.answers)
        if missing_core: raise HTTPException(422, f"Core questions are required: {sorted(missing_core)}")
    merged = dict(session.answers or {}); merged.update(data.answers)
    try: result = score_answers(merged)
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    followups = triggered_followups(merged, session.selected_question_ids)
    followup_ids = [q.id for q in followups]
    waiting = [qid for qid in followup_ids if qid not in merged]
    session.answers = merged
    session.triggered_follow_up_ids = followup_ids
    session.domain_scores = result["domain_scores"]
    session.questionnaire_score = result["questionnaire_score"]
    session.safety_flags = result["safety_flags"]
    session.explanation = {**result["explanation"], "top_contributors":result["top_contributors"]}
    session.status = "followup" if waiting else "completed"
    session.completed_at = None if waiting else datetime.now(timezone.utc)
    values = assessment_values(result)
    if session.assessment_id is None:
        assessment = models.Assessment(case_id=case.id, distress_score=round(result["questionnaire_score"]),
            risk_level=result["risk_level"], created_at=datetime.now(timezone.utc).isoformat(),
            note=data.note, **values)
        db.add(assessment); db.flush(); session.assessment_id = assessment.id
    else:
        assessment = db.get(models.Assessment, session.assessment_id)
        for key,value in values.items(): setattr(assessment,key,value)
        assessment.distress_score = round(result["questionnaire_score"])
        assessment.risk_level = result["risk_level"]
        if data.note is not None and not db.query(models.AIAnalysis).filter_by(assessment_id=assessment.id).first():
            assessment.note = data.note
    update_from_assessment(case, assessment)
    case.last_assessment = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    ensure_indicator(db, case)
    analysis_id = None
    note = (assessment.note or '').strip()
    if note and session.status in ("followup","completed") and not db.query(models.AIAnalysis).filter_by(assessment_id=assessment.id).first():
        analysis = models.AIAnalysis(assessment_id=assessment.id, case_id=case.id,
                                     victim_id=user.id, status="pending")
        db.add(analysis); db.flush(); analysis_id = analysis.id
    try: db.commit()
    except SQLAlchemyError:
        db.rollback(); raise HTTPException(503, "Questionnaire could not be saved. Please try again.") from None
    response = {**result, "questionnaire_id":session.id, "questionnaire_version":VERSION,
                "scoring_version":SCORING_VERSION, "age_group":session.age_group,
                "triggered_followups":[public_question(q) for q in followups],
                "complete":not waiting,
                "distress_metadata":{"source":"adaptive_questionnaire", "top_contributors":result["top_contributors"]}}
    if analysis_id is not None:
        response["ai_analysis"] = {"id":analysis_id, "status":analyze_saved_check_in(db, analysis_id, note)}
    else:
        analysis = db.query(models.AIAnalysis).filter_by(assessment_id=assessment.id).first()
        if analysis is not None:
            response["ai_analysis"] = {"id":analysis.id, "status":analysis.status}
    return response
