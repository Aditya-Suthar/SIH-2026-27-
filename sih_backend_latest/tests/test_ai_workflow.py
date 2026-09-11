"""Prompt 2 integration tests: real DB/API, synthetic identities, mocked AI only."""
import io
import json
import logging
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

# Delay full-app imports until tests run, preserving Prompt 1's import isolation.
from app import ai_service


def load_backend():
    global app, models, create_access_token, Base, get_db, upgrade
    bootstrap_engine = create_engine('sqlite://')
    with patch('sqlalchemy.create_engine', return_value=bootstrap_engine):
        from app.main import app
    from app import models
    from app.auth import create_access_token
    from app.database import Base, get_db
    from app.migrate_ai_prompt2 import upgrade


GOOD = dict(distress_score=65, risk_level='high', emotions=['fear'],
            requires_attention=True, reason='The text expresses fear.', provider='groq')
QUESTIONNAIRE = dict(mood=1, anxiety=1, sleep=1, hopelessness=1,
                     social_withdrawal=1, self_harm_thoughts=1)
NOTE = 'Synthetic private note: I am afraid and cannot sleep.'


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_backend()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.engine = create_engine('sqlite:///' + str(Path(self.temp.name) / 'test.db'),
                                    connect_args={'check_same_thread': False})
        @event.listens_for(self.engine, 'connect')
        def foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session.begin() as db:
            for uid, role in ((1,'victim'),(2,'victim'),(3,'counsellor'),(4,'counsellor'),
                              (5,'authority'),(6,'victim'),(7,'unknown')):
                db.add(models.User(id=uid, name=f'User {uid}', email=f'u{uid}@example.com',
                                   password_hash='unused-in-token-tests', role=role))
            db.flush()
            for cid, victim, counsellor in ((10,1,3),(20,2,4)):
                db.add(models.Case(id=cid, case_id=f'CASE-{cid}', victim_id=victim,
                                   assigned_counsellor_id=counsellor, assigned_counsellor='Test',
                                   risk_level='Low', last_assessment='Never', district='Test',
                                   state='Test', intervention_status='Pending'))
        def override_db():
            with self.Session() as db:
                yield db
        app.dependency_overrides[get_db] = override_db
        self.addCleanup(app.dependency_overrides.pop, get_db, None)
        self.client = TestClient(app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.real_analyze = ai_service.analyze_distress
        self.provider_patch = patch('app.ai_service.analyze_distress', return_value=ai_service.DistressResult(**GOOD))
        self.ai = self.provider_patch.start()
        self.addCleanup(self.provider_patch.stop)

    def headers(self, uid=1, role='victim'):
        return {'Authorization':'Bearer ' + create_access_token({'user_id':uid, 'role':role})}

    def submit(self, uid=1, note=NOTE, **extra):
        return self.client.post('/api/victim/assessment', headers=self.headers(uid),
                                json=dict(QUESTIONNAIRE, note=note, **extra))

    def history(self, uid=1, role='victim', case='CASE-10', suffix=''):
        return self.client.get(f'/api/cases/{case}/ai-analyses{suffix}', headers=self.headers(uid,role))

    def test_text_saved_before_ai_and_correct_result_persisted(self):
        async def analyze(note):
            self.assertEqual(note, NOTE)
            # A separate connection sees committed text, ownership and pending state.
            with self.Session() as db:
                source = db.query(models.Assessment).one()
                row = db.query(models.AIAnalysis).one()
                self.assertEqual(source.note, NOTE)
                self.assertEqual((row.assessment_id,row.case_id,row.victim_id,row.status),
                                 (source.id,10,1,'pending'))
                self.assertIsNone(row.distress_score)
            return ai_service.DistressResult(**GOOD)
        self.ai.side_effect = analyze
        response = self.submit()
        self.assertEqual(response.status_code,200,response.text)
        self.ai.assert_awaited_once_with(NOTE)
        self.assertEqual(response.json()['ai_analysis']['status'],'completed')
        result = self.history().json()['items'][0]
        for key,value in GOOD.items():
            self.assertEqual(result[key],value)
        self.assertEqual(result['victim_id'],1)
        self.assertEqual(result['case_id'],10)
        self.assertEqual(result['source_type'],'assessment')
        self.assertTrue(result['created_at'].endswith('+00:00'))
        self.assertIsNotNone(result['finished_at'])
        self.assertNotIn(NOTE,json.dumps(result))
        # Existing questionnaire score/risk are not silently replaced by AI values.
        self.assertEqual(response.json()['distressScore'],25)
        self.assertEqual(response.json()['riskLevel'],'Moderate')
        with self.Session() as db:
            self.assertEqual(db.get(models.Case,10).risk_level,'Moderate')
            self.assertEqual(db.query(models.Assessment).one().distress_score,25)

    def test_client_cannot_override_victim_case_or_source(self):
        response = self.submit(victim_id=2, user_id=2, case_id=20, assessment_id=999)
        self.assertEqual(response.status_code,200,response.text)
        with self.Session() as db:
            row = db.query(models.AIAnalysis).one()
            source = db.query(models.Assessment).one()
            self.assertEqual((row.victim_id,row.case_id,row.assessment_id),(1,10,source.id))
            self.assertEqual(source.case_id,10)

    def test_history_append_only_and_pagination(self):
        self.submit(note='First synthetic note')
        first = self.history().json()['items'][0]
        self.ai.return_value = ai_service.DistressResult(**dict(GOOD, distress_score=20,risk_level='low',requires_attention=False))
        self.submit(note='Second synthetic note')
        self.ai.side_effect = ai_service.AIServiceUnavailable()
        self.submit(note='Third synthetic note')
        items = self.history().json()['items']
        self.assertEqual(len(items),3)
        self.assertEqual(items[0],first)
        self.assertEqual([x['distress_score'] for x in items],[65,20,None])
        self.assertEqual([x['status'] for x in items],['completed','completed','failed'])
        self.assertEqual(len({x['assessment_id'] for x in items}),3)
        self.assertEqual([x['created_at'] for x in items],sorted(x['created_at'] for x in items))
        page = self.history(suffix='?limit=1&offset=1').json()
        self.assertEqual(page['items'],items[1:2]); self.assertTrue(page['has_more'])
        self.assertFalse(self.history(suffix='?limit=1&offset=2').json()['has_more'])
        self.assertEqual(self.history(suffix='?limit=0').status_code,422)
        self.assertEqual(self.history(suffix='?limit=101').status_code,422)
        self.assertEqual(self.history(suffix='?offset=-1').status_code,422)

    def test_authorization_matrix(self):
        self.submit()
        for uid, role, expected in ((1,'victim',200),(2,'victim',404),(3,'counsellor',200),
                                    (4,'counsellor',404),(5,'authority',200),(7,'unknown',403),
                                    (999,'victim',401),(1,'authority',401)):
            with self.subTest(uid=uid,role=role):
                response = self.history(uid,role)
                self.assertEqual(response.status_code,expected,response.text)
                if expected != 200:
                    self.assertNotIn('distress_score',response.text)
        self.assertEqual(self.history(case='DOES-NOT-EXIST').status_code,404)
        no_auth = self.client.get('/api/cases/CASE-10/ai-analyses')
        self.assertIn(no_auth.status_code,(401,403))
        bad = self.client.get('/api/cases/CASE-10/ai-analyses', headers={'Authorization':'Bearer invalid'})
        self.assertEqual(bad.status_code,401)

    def test_reassignment_enforces_current_permissions_and_original_author(self):
        self.submit()
        with self.Session.begin() as db:
            case=db.get(models.Case,10);case.assigned_counsellor_id=4;case.victim_id=2
        self.assertEqual(self.history(3,'counsellor').status_code,404)
        self.assertEqual(self.history(4,'counsellor').status_code,200)
        self.assertEqual(self.history(1,'victim').status_code,404)
        self.assertEqual(self.history(2,'victim').json()['items'],[])

    def test_numeric_only_and_blank_checkins_preserve_contract(self):
        for note in (None,'',' \t\n '):
            response = self.submit(note=note)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json(),{'message':'Assessment submitted successfully',
                                              'distressScore':25,'riskLevel':'Moderate'})
        response = self.client.post('/api/victim/assessment',json=QUESTIONNAIRE,headers=self.headers())
        self.assertEqual(response.status_code,200)
        self.ai.assert_not_awaited()
        with self.Session() as db:
            self.assertEqual(db.query(models.Assessment).count(),4)
            self.assertEqual(db.query(models.AIAnalysis).count(),0)
            self.assertTrue(all(x.note is None for x in db.query(models.Assessment)))

    def test_invalid_input_and_unauthorized_submission_do_not_trigger_ai(self):
        for note in ('x'*4001,5,[],True):
            self.assertEqual(self.submit(note=note).status_code,422)
        for uid,role in ((3,'counsellor'),(5,'authority')):
            response = self.client.post('/api/victim/assessment',json=dict(QUESTIONNAIRE,note=NOTE),headers=self.headers(uid,role))
            self.assertEqual(response.status_code,403)
        self.assertEqual(self.submit(uid=6).status_code,404)
        self.assertEqual(self.submit(uid=999).status_code,401)
        response = self.client.post('/api/victim/assessment',json=dict(QUESTIONNAIRE,note=NOTE))
        self.assertIn(response.status_code,(401,403))
        self.ai.assert_not_awaited()
        with self.Session() as db:
            self.assertEqual(db.query(models.Assessment).count(),0)

    def test_provider_failure_and_malformed_results_preserve_sources(self):
        bad_values = [None, 'not json', dict(GOOD,distress_score=101), dict(GOOD,distress_score='65'),
                      dict(GOOD,risk_level='low'),dict(GOOD,reason=None),dict(GOOD,provider='other')]
        self.ai.side_effect = ai_service.AIServiceUnavailable()
        self.assertEqual(self.submit().json()['ai_analysis']['status'],'failed')
        self.ai.side_effect = None
        for bad in bad_values:
            self.ai.return_value=bad
            response=self.submit()
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['ai_analysis']['status'],'failed')
        with self.Session() as db:
            self.assertEqual(db.query(models.Assessment).count(),len(bad_values)+1)
            for row in db.query(models.AIAnalysis):
                self.assertEqual(row.status,'failed')
                for key in GOOD:
                    self.assertIsNone(getattr(row,key))

    def test_full_fallback_chain_failure_is_safe(self):
        real_analyze = self.real_analyze
        seen=[]
        def handler(request):
            seen.append(request.url.host)
            if len(seen)==1: return httpx.Response(429,text='secret-key '+NOTE)
            if len(seen)==2: return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'invalid JSON'}}]})
            raise httpx.ConnectError('secret-key '+NOTE)
        async def analyze(note):
            return await real_analyze(note,transport=httpx.MockTransport(handler))
        self.ai.side_effect=analyze
        stream=io.StringIO(); log_handler=logging.StreamHandler(stream)
        logging.getLogger().addHandler(log_handler)
        self.addCleanup(logging.getLogger().removeHandler,log_handler)
        with patch.dict(os.environ,{'GEMINI_API_KEY':'secret-key','GROQ_API_KEY':'secret-key',
                                    'OPENROUTER_API_KEY':'secret-key','OPENROUTER_MODEL':'openrouter/free'}):
            response=self.submit()
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['ai_analysis']['status'],'failed')
        self.assertEqual(seen,['generativelanguage.googleapis.com','api.groq.com','openrouter.ai'])
        self.assertNotIn('secret-key',stream.getvalue()+response.text)
        self.assertNotIn(NOTE,stream.getvalue()+response.text)

    def test_source_storage_failure_returns_safe_error_and_does_not_call_ai(self):
        from sqlalchemy.orm import Session
        with patch.object(Session, 'commit', side_effect=SQLAlchemyError(NOTE + ' secret-key')):
            response = self.submit()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'detail':'Check-in could not be saved. Please try again.'})
        self.ai.assert_not_awaited()
        self.assertNotIn(NOTE, response.text)
        with self.Session() as db:
            self.assertEqual(db.query(models.Assessment).count(), 0)
            self.assertEqual(db.query(models.AIAnalysis).count(), 0)

    def test_real_checkin_analysis_independent_of_development_endpoint_switch(self):
        with patch.dict(os.environ, {'AI_TEST_ENDPOINT_ENABLED':'false'}):
            response = self.submit()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['ai_analysis']['status'], 'completed')
        self.ai.assert_awaited_once()

    def test_result_storage_error_preserves_source_and_marks_failed(self):
        counter={'commits':0}
        from sqlalchemy.orm import Session
        original=Session.commit
        def commit(db):
            counter['commits']+=1
            if counter['commits']==2: raise SQLAlchemyError('sensitive internal storage detail')
            return original(db)
        with patch.object(Session,'commit',commit):
            response=self.submit()
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['ai_analysis']['status'],'failed')
        with self.Session() as db:
            self.assertEqual(db.query(models.Assessment).one().note,NOTE)
            row=db.query(models.AIAnalysis).one()
            self.assertEqual(row.status,'failed');self.assertIsNone(row.distress_score)

    def test_persistent_result_storage_outage_exposes_pending(self):
        counter={'commits':0}
        from sqlalchemy.orm import Session
        original=Session.commit
        def commit(db):
            counter['commits']+=1
            if counter['commits']>=2: raise SQLAlchemyError('storage detail')
            return original(db)
        with patch.object(Session,'commit',commit):
            response=self.submit()
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['ai_analysis']['status'],'pending')
        with self.Session() as db:
            self.assertEqual(db.query(models.Assessment).one().note,NOTE)
            row=db.query(models.AIAnalysis).one()
            self.assertEqual(row.status,'pending');self.assertIsNone(row.distress_score)

    def test_existing_case_and_dashboard_routes_still_work(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(self.client.get('/api/victim/dashboard',headers=self.headers()).status_code,200)
        response=self.client.get('/api/cases',headers=self.headers(3,'counsellor'))
        self.assertEqual(response.status_code,200)
        self.assertEqual([case['caseId'] for case in response.json()],['CASE-10'])
        response=self.client.get('/api/cases/CASE-20',headers=self.headers(3,'counsellor'))
        self.assertEqual(response.status_code,404)


class MigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_backend()

    def test_existing_schema_upgrade_is_additive_and_repeatable(self):
        engine=create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        # Reconstruct the existing core schema without the newly added note column.
        from sqlalchemy import MetaData
        metadata=MetaData()
        for name in ('users','cases','assessments'):
            table=Base.metadata.tables[name].to_metadata(metadata)
            if name=='assessments':
                table._columns.remove(table.c.note)
        metadata.create_all(engine)
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users (id,name,email,password_hash,role) VALUES (1,'Test','test@example.com','hash','victim')"))
            conn.execute(text("INSERT INTO cases (id,case_id,victim_id,risk_level,assigned_counsellor,last_assessment,intervention_status,district,state) VALUES (10,'OLD',1,'Low','Test','old','old','x','x')"))
            conn.execute(text("INSERT INTO assessments (id,case_id,mood,anxiety,sleep,hopelessness,social_withdrawal,self_harm_thoughts,distress_score,risk_level,created_at) VALUES (1,10,1,1,1,1,1,1,25,'Moderate','old')"))
        self.assertNotIn('note',[c['name'] for c in inspect(engine).get_columns('assessments')])
        upgrade(engine);upgrade(engine)
        with engine.connect() as conn:
            row=conn.execute(text('SELECT id,distress_score,note FROM assessments')).one()
            self.assertEqual(tuple(row),(1,25,None))
        self.assertIn('ai_analyses',inspect(engine).get_table_names())
        self.assertTrue(any(c['column_names']==['assessment_id'] for c in inspect(engine).get_unique_constraints('ai_analyses')))
        self.assertEqual(len(inspect(engine).get_foreign_keys('ai_analyses')),4)  # Prompt 3 adds the message source FK.

    def test_fresh_database_upgrade(self):
        engine=create_engine('sqlite://');self.addCleanup(engine.dispose)
        upgrade(engine);upgrade(engine)
        self.assertTrue({'users','cases','assessments','ai_analyses'}.issubset(inspect(engine).get_table_names()))


if __name__=='__main__':
    unittest.main()
