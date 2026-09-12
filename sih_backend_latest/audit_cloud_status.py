"""Read-only cloud audit. Never emits notes, credentials, tokens or provider bodies."""
import json
from sqlalchemy import create_engine, text
from app.database import engine
from app.ai_service import provider_configs

def main():
    assert engine.url.get_backend_name() == 'postgresql'
    cloud = create_engine(engine.url, connect_args={'connect_timeout':8})
    print(json.dumps({'database_host':cloud.url.host,'database':cloud.url.database,
                      'local_key_detection':{p.name:bool(p.api_key) for p in provider_configs()}}))
    with cloud.connect() as conn:
        rows=conn.execute(text('''SELECT a.id AS assessment_id,c.case_id,
            length(trim(coalesce(a.note,''))) AS note_characters,
            x.id AS analysis_id,x.status,x.provider,x.distress_score,x.risk_level,x.emotions,
            x.created_at,x.finished_at,c.assigned_counsellor_id
            FROM assessments a JOIN cases c ON c.id=a.case_id
            LEFT JOIN ai_analyses x ON x.assessment_id=a.id
            ORDER BY a.id DESC LIMIT 30''')).mappings()
        print(json.dumps([dict(r) for r in rows],default=str,indent=2))
    verify_scoped_reads(cloud)
    cloud.dispose()

def verify_scoped_reads(cloud):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker
    from app import models
    from app.database import get_db
    from app.auth import create_access_token
    from app.monitoring import router as monitoring
    from app.operations import router as operations
    from app.ai_history import router as history
    sessions=sessionmaker(bind=cloud)
    app=FastAPI()
    for router in (monitoring,operations,history):app.include_router(router)
    def database():
        with sessions() as db:
            db.execute(text('SET TRANSACTION READ ONLY'))
            yield db
    app.dependency_overrides[get_db]=database
    def snapshot():
        with cloud.connect() as conn:
            return {name:conn.scalar(text(f'SELECT md5(coalesce(string_agg(to_jsonb(t)::text, chr(10) ORDER BY id),\'\')) FROM {name} t'))
                    for name in ('users','cases','assessments','ai_analyses','monitoring_indicators','questionnaire_sessions','support_requests','analysis_reviews')}
    before=snapshot()
    with sessions() as db, TestClient(app) as client:
        authority=db.query(models.User).filter_by(role='authority').first()
        def get(path,user):
            response=client.get(path,headers={'Authorization':'Bearer '+create_access_token({'user_id':user.id,'role':user.role})})
            print(json.dumps({'local_api_cloud_db':path,'role':user.role,'status':response.status_code}))
            assert response.status_code==200
            return response.json()
        for _ in range(2):
            for path in ('/api/support-requests','/api/monitoring/indicators','/api/monitoring/summary'):get(path,authority)
        for row in db.query(models.AIAnalysis):
            case=db.get(models.Case,row.case_id)
            victim=db.get(models.User,case.victim_id)
            result=get(f'/api/cases/{case.case_id}/ai-analyses',victim)
            assert any(r['id']==row.id for r in result['items'])
            if case.assigned_counsellor_id:
                staff=db.get(models.User,case.assigned_counsellor_id)
                result=get(f'/api/cases/{case.case_id}/ai-analyses',staff)
                assert any(r['id']==row.id for r in result['items'])
        case=db.query(models.Case).filter_by(case_id='SAH-76B04B4D7F6D').one()
        for row in db.query(models.MonitoringIndicator).filter_by(case_id=case.id):
            result=get(f'/api/cases/{case.case_id}/monitoring?indicator_id={row.id}',authority)
            assert result['selected_evidence']['score_snapshot']==row.current_score
            print(json.dumps({'indicator':row.id,'snapshot':row.current_score,'current_score':result['current_score']}))
    assert before==snapshot(), 'Cloud records changed during read verification'
    print(json.dumps({'cloud_row_fingerprints_unchanged':True}))

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(json.dumps({'audit_error':type(exc).__name__}))
        raise SystemExit(1) from None
