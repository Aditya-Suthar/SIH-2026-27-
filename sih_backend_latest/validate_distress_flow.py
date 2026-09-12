"""Opt-in cloud validation using one existing saved note, never invented answers.

Run without arguments for metadata only. --analyze-existing-note adds one real
AI attempt to a latest assessment lacking an attempt, then checks scoped APIs.
No source text, credentials, tokens, or provider responses are printed.
"""
import argparse
import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from app import models
from app.ai_service import provider_configs
from app.ai_workflow import analyze_saved_check_in
from app.ai_history import router as history_router, valid_source_query
from app.auth import create_access_token
from app.database import engine, get_db
from app.monitoring import router as monitoring_router


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analyze-existing-note', action='store_true')
    args = parser.parse_args()
    logging.getLogger('httpx').setLevel(logging.WARNING)
    if engine.url.get_backend_name() != 'postgresql':
        raise RuntimeError('Cloud PostgreSQL configuration required')
    cloud = create_engine(engine.url, connect_args={'connect_timeout':8}, pool_pre_ping=True)
    sessions = sessionmaker(bind=cloud, autoflush=False)
    print(json.dumps({'database_host':cloud.url.host, 'database_name':cloud.url.database,
                      'provider_keys_detected':{p.name:bool(p.api_key) for p in provider_configs()}}), flush=True)
    with sessions() as db:
        print(json.dumps({'analysis_status_counts':dict(db.query(models.AIAnalysis.status, func.count(models.AIAnalysis.id)).group_by(models.AIAnalysis.status).all()),
                          'completed_valid_sources':valid_source_query(db).filter(models.AIAnalysis.status=='completed').count()}), flush=True)
        if not args.analyze_existing_note:
            return
        latest = db.query(func.max(models.Assessment.id)).group_by(models.Assessment.case_id)
        assessment = db.query(models.Assessment).join(models.Case).outerjoin(
            models.AIAnalysis, models.AIAnalysis.assessment_id == models.Assessment.id
        ).filter(models.Assessment.id.in_(latest), models.AIAnalysis.id.is_(None),
                 func.length(func.trim(models.Assessment.note)) > 0,
                 models.Case.assigned_counsellor_id.is_not(None)).order_by(models.Assessment.id.desc()).with_for_update(of=models.Assessment).first()
        if assessment is None:
            print('No eligible latest saved note without an analysis; no records changed.')
            return
        case = db.get(models.Case, assessment.case_id)
        note = assessment.note.strip()
        row = models.AIAnalysis(assessment_id=assessment.id, case_id=case.id, victim_id=case.victim_id, status='pending')
        db.add(row)
        db.flush()
        analysis_id, assessment_id, case_id, victim_id, counsellor_id = row.id, assessment.id, case.case_id, case.victim_id, case.assigned_counsellor_id
        db.commit()
        status = analyze_saved_check_in(db, analysis_id, note)
        print(json.dumps({'analysis_id':analysis_id, 'assessment_id':assessment_id, 'case_id':case_id, 'status':status}), flush=True)
    application = FastAPI()
    application.include_router(monitoring_router)
    application.include_router(history_router)
    def database():
        with sessions() as db:
            yield db
    application.dependency_overrides[get_db] = database
    with TestClient(application) as client:
        for uid, role in ((victim_id, 'victim'), (counsellor_id, 'counsellor')):
            token = create_access_token({'user_id':uid, 'role':role})
            headers = {'Authorization':'Bearer ' + token}
            response = client.get(f'/api/cases/{case_id}/ai-analyses', headers=headers)
            assert response.status_code == 200
            assert any(item['id'] == analysis_id and item['status'] == status for item in response.json()['items'])
            if role == 'counsellor':
                response = client.get('/api/monitoring/cases', headers=headers)
                assert response.status_code == 200
                item = next(item for item in response.json()['items'] if item['case_id'] == case_id)
                assert item['latest_attempt']['id'] == analysis_id
                assert item['latest_attempt_status'] == status
                if status == 'completed':
                    assert item['latest_analysis']['id'] == analysis_id
                    assert item['latest_analysis']['distress_score'] is not None
                else:
                    assert item['latest_attempt']['error_message'] or status == 'pending'
            print(json.dumps({'role':role, 'scoped_api_verified':True}), flush=True)
    cloud.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Exceptions may contain DB credentials or private source data.
        print(json.dumps({'validation_failed':type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
