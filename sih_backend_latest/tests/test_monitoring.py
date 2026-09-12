"""Prompt 3: deterministic rules, case messaging, monitoring, reviews and migration."""
from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from pathlib import Path
from uuid import uuid4
import tempfile
import unittest
from unittest.mock import patch
import json

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.monitoring_rules import trend, prioritize

NOW = datetime(2026,9,10,12,tzinfo=timezone.utc)
GOOD = dict(distress_score=78,risk_level='critical',emotions=['fear'],requires_attention=True,
            reason='The message expresses distress.',provider='gemini')


def points(scores, spacing=1):
    return [SimpleNamespace(id=i+1,distress_score=score,status='completed',risk_level='critical' if score>=75 else 'high' if score>=50 else 'medium' if score>=25 else 'low',
                            requires_attention=score>=50,created_at=NOW-timedelta(days=(len(scores)-1-i)*spacing)) for i,score in enumerate(scores)]


class RuleTests(unittest.TestCase):
    def test_insufficient_one_or_same_day(self):
        self.assertEqual(trend(points([70]),NOW)['state'],'insufficient_data')
        self.assertEqual(trend(points([30,45,61,78],spacing=0),NOW)['state'],'insufficient_data')
        self.assertEqual(trend([],NOW)['state'],'insufficient_data')

    def test_worsening_and_improving(self):
        self.assertEqual(trend(points([30,36,42],spacing=2),NOW)['state'],'worsening')
        self.assertEqual(trend(points([78,65,50,35]),NOW)['state'],'improving')

    def test_rapid_and_stable_examples(self):
        self.assertEqual(trend(points([30,45,61,78]),NOW)['state'],'rapidly_worsening')
        self.assertEqual(trend(points([70,69,71]),NOW)['state'],'stable')
        rising=prioritize(points([30,45,61,78]),NOW)
        steady=prioritize(points([70,69,71]),NOW)
        self.assertEqual(rising['category'],'URGENT');self.assertEqual(steady['category'],'HIGH')
        self.assertGreater(rising['score'],steady['score'])

    def test_failed_null_irregular_and_future_points(self):
        rows=points([30,40,55],spacing=3)
        rows.extend([SimpleNamespace(id=10,status='failed',distress_score=None,created_at=NOW),
                     SimpleNamespace(id=11,status='completed',distress_score=None,created_at=NOW)])
        result=trend(list(reversed(rows)),NOW)
        self.assertEqual(result['state'],'worsening')
        self.assertAlmostEqual(result['slope_per_day'],4.17,places=2)
        rows.append(SimpleNamespace(id=12,status='completed',distress_score=100,risk_level='critical',requires_attention=True,created_at=NOW+timedelta(days=1)))
        self.assertEqual(trend(rows,NOW),result)

    def test_attention_priority_and_no_data(self):
        rows=points([35,35,35]);baseline=prioritize(rows,NOW)
        rows[-1].requires_attention=True
        flagged=prioritize(rows,NOW)
        self.assertEqual(flagged['score']-baseline['score'],12)
        self.assertTrue(flagged['alerts'])
        empty=prioritize([],NOW)
        self.assertIsNone(empty['score']);self.assertEqual(empty['category'],'UNASSESSED')

    def test_bursts_do_not_create_repeated_high_days(self):
        result=prioritize(points([90]*10,spacing=0),NOW)
        self.assertEqual(result['recent_high_days'],1)
        self.assertEqual(result['trend']['state'],'insufficient_data')

    def test_stale_is_not_current_stability(self):
        rows=points([70,69,71])
        for row in rows: row.created_at-=timedelta(days=30)
        result=prioritize(rows,NOW)
        self.assertTrue(result['stale']);self.assertEqual(result['trend']['state'],'insufficient_data')


class ChatMonitoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global models, Base, get_db, app, create_access_token, ai_service
        with patch('sqlalchemy.create_engine',return_value=create_engine('sqlite://')):
            from app.main import app
        from app import models, ai_service
        from app.database import Base, get_db
        from app.auth import create_access_token

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.engine=create_engine('sqlite:///'+str(Path(self.temp.name)/'db.sqlite'),connect_args={'check_same_thread':False})
        @event.listens_for(self.engine,'connect')
        def fk(conn,_): conn.execute('PRAGMA foreign_keys=ON')
        self.addCleanup(self.engine.dispose);Base.metadata.create_all(self.engine)
        self.Session=sessionmaker(bind=self.engine)
        with self.Session.begin() as db:
            for uid,role in ((1,'victim'),(2,'victim'),(3,'counsellor'),(4,'counsellor'),(5,'authority')):
                db.add(models.User(id=uid,name=f'Test {uid}',email=f'test{uid}@example.com',password_hash='test-only',role=role))
            db.flush()
            for cid,vid,counsellor in ((10,1,3),(20,2,4)):
                db.add(models.Case(id=cid,case_id=f'CASE-{cid}',victim_id=vid,assigned_counsellor_id=counsellor,
                    assigned_counsellor='Assigned counsellor',risk_level='Low',last_assessment='Never',intervention_status='Pending',district='Test',state='Test'))
        def db_override():
            with self.Session() as db: yield db
        app.dependency_overrides[get_db]=db_override
        self.addCleanup(app.dependency_overrides.pop,get_db,None)
        self.client=TestClient(app);self.client.__enter__();self.addCleanup(self.client.__exit__,None,None,None)
        self.mock=patch('app.ai_service.analyze_distress',return_value=ai_service.DistressResult(**GOOD));self.ai=self.mock.start();self.addCleanup(self.mock.stop)

    def headers(self,uid=1,role='victim'):
        return {'Authorization':'Bearer '+create_access_token({'user_id':uid,'role':role})}

    def send(self,content='I feel afraid and cannot sleep.',uid=1,role='victim',case='CASE-10',key=None):
        return self.client.post(f'/api/cases/{case}/messages',json={'content':content,'client_message_id':key or str(uuid4())},headers=self.headers(uid,role))

    def detail(self,uid=3,role='counsellor',case='CASE-10',indicator_id=None):
        suffix = f'?indicator_id={indicator_id}' if indicator_id is not None else ''
        return self.client.get(f'/api/cases/{case}/monitoring{suffix}',headers=self.headers(uid,role))

    def test_selected_indicators_keep_historical_scores_separate_from_current_state(self):
        with self.Session.begin() as db:
            case = db.get(models.Case, 10)
            first = models.Assessment(case_id=10,mood=2,anxiety=2,sleep=0,hopelessness=4,
                social_withdrawal=0,self_harm_thoughts=0,distress_score=66,risk_level='High',
                created_at='2026-09-12T19:03:08+00:00')
            second = models.Assessment(case_id=10,mood=2,anxiety=2,sleep=0,hopelessness=3,
                social_withdrawal=0,self_harm_thoughts=4,distress_score=48,risk_level='Critical',
                created_at='2026-09-12T20:03:18+00:00')
            db.add_all((first,second)); db.flush()
            db.add_all((
                models.MonitoringIndicator(case_id=10,source='questionnaire',assessment_id=first.id,
                    severity='HIGH',fingerprint=f'authoritative:questionnaire:{first.id}',
                    reason='Current authoritative risk is High (66/100).',current_score=66,
                    created_at=datetime(2026,9,12,19,3,8,tzinfo=timezone.utc)),
                models.MonitoringIndicator(case_id=10,source='questionnaire',assessment_id=second.id,
                    severity='URGENT',fingerprint=f'authoritative:questionnaire:{second.id}',
                    reason='Critical safety override triggered by the questionnaire response.',current_score=48,
                    created_at=datetime(2026,9,12,20,3,18,tzinfo=timezone.utc)),
            )); db.flush()
            indicator_ids = [row.id for row in db.query(models.MonitoringIndicator).order_by(models.MonitoringIndicator.id)]
            case.risk_level='Critical'; case.latest_distress_score=48; case.latest_risk_source='questionnaire'
            case.latest_state_at=datetime(2026,9,12,20,3,18,tzinfo=timezone.utc)
            case.latest_assessment_id=second.id

        with self.Session() as db:
            before = db.query(models.MonitoringIndicator).count()
        high = self.detail(5,'authority',indicator_id=indicator_ids[0])
        critical = self.detail(5,'authority',indicator_id=indicator_ids[1])
        self.assertEqual(high.status_code,200,high.text); self.assertEqual(critical.status_code,200,critical.text)
        self.assertEqual((high.json()['selected_evidence']['id'],high.json()['selected_evidence']['score_snapshot']),
                         (indicator_ids[0],66))
        self.assertEqual((critical.json()['selected_evidence']['id'],critical.json()['selected_evidence']['score_snapshot']),
                         (indicator_ids[1],48))
        self.assertEqual(high.json()['current_score'],48); self.assertEqual(critical.json()['current_score'],48)
        self.assertTrue(critical.json()['selected_evidence']['safety_override'])
        self.assertEqual(critical.json()['selected_evidence']['triggering_rule'],
                         'Critical safety override triggered by the questionnaire response.')
        self.client.get('/api/monitoring/indicators',headers=self.headers(5,'authority'))
        with self.Session() as db: self.assertEqual(db.query(models.MonitoringIndicator).count(),before)

    def test_victim_chat_saved_before_analysis_and_linked(self):
        async def analyze(message):
            with self.Session() as db:
                saved=db.query(models.CaseMessage).one();row=db.query(models.AIAnalysis).one()
                self.assertEqual(saved.content,message)
                self.assertEqual((row.message_id,row.case_id,row.victim_id,row.assessment_id),(saved.id,10,1,None))
                self.assertEqual(row.status,'pending')
            return ai_service.DistressResult(**GOOD)
        self.ai.side_effect=analyze
        response=self.send();self.assertEqual(response.status_code,200,response.text)
        self.ai.assert_awaited_once()
        history=self.client.get('/api/cases/CASE-10/ai-analyses',headers=self.headers()).json()['items']
        self.assertEqual(history[0]['source_type'],'message')
        self.assertEqual(history[0]['distress_score'],78)
        self.assertIsNotNone(history[0]['message_id'])

    def test_questionnaire_and_ai_are_separate_and_null_safety_state_is_preserved(self):
        self.send()
        with self.Session.begin() as db:
            a=models.Assessment(case_id=10,mood=0,anxiety=0,sleep=0,hopelessness=0,
                social_withdrawal=0,self_harm_thoughts=4,distress_score=None,risk_level='Critical',
                created_at=datetime.now(timezone.utc).isoformat())
            db.add(a);db.flush()
            from app.case_state import update_from_assessment
            update_from_assessment(db.get(models.Case,10),a)
        result=self.detail().json()
        self.assertIsNone(result['current_score'])
        self.assertEqual(result['current_source'],'questionnaire')
        self.assertIsNone(result['current_questionnaire']['score'])
        self.assertTrue(result['current_questionnaire']['safety_override'])
        self.assertEqual(result['latest_analysis']['distress_score'],78)
        self.assertNotIn('note',result['current_questionnaire'])

    def test_alert_gets_are_read_only_and_scope_is_enforced(self):
        self.send()
        with self.Session() as db:
            before=[(r.id,r.current_score,r.reviewed_at) for r in db.query(models.MonitoringIndicator)]
            indicator_id=before[0][0]
        for _ in range(2):
            for path in ('/api/support-requests','/api/monitoring/indicators','/api/monitoring/summary'):
                self.assertEqual(self.client.get(path,headers=self.headers(5,'authority')).status_code,200)
        self.assertEqual(self.detail(4,indicator_id=indicator_id).status_code,404)
        self.assertEqual(self.detail(1,'victim',indicator_id=indicator_id).status_code,403)
        with self.Session() as db:
            self.assertEqual(before,[(r.id,r.current_score,r.reviewed_at) for r in db.query(models.MonitoringIndicator)])
        response=self.client.post(f'/api/monitoring/indicators/{indicator_id}/review',headers=self.headers(5,'authority'))
        self.assertEqual(response.json()['reviewed_indicator_id'],indicator_id)
        self.assertTrue(self.detail(5,'authority',indicator_id=indicator_id).json()['selected_evidence']['reviewed'])

    def test_abandoned_pending_maintenance_preserves_success_and_active_attempts(self):
        self.send()
        with self.Session.begin() as db:
            for key,minutes in (('old',20),('active',1)):
                msg=models.CaseMessage(case_id=10,victim_id=1,sender_id=1,sender_role='victim',
                    client_message_id=str(uuid4()),content='Isolated test message')
                db.add(msg);db.flush()
                db.add(models.AIAnalysis(case_id=10,victim_id=1,message_id=msg.id,status='pending',
                    created_at=datetime.now(timezone.utc)-timedelta(minutes=minutes)))
        from app.ai_workflow import fail_abandoned_analyses
        with self.Session() as db:
            self.assertEqual(fail_abandoned_analyses(db),1)
            self.assertEqual(fail_abandoned_analyses(db),0)
            rows=db.query(models.AIAnalysis).order_by(models.AIAnalysis.id).all()
            self.assertEqual([r.status for r in rows],['completed','failed','pending'])
            self.assertEqual(rows[0].distress_score,78)
            self.assertIsNone(rows[1].distress_score)

    def test_counsellor_and_trivial_messages_not_analyzed(self):
        self.assertEqual(self.send('How are you feeling?',3,'counsellor').status_code,200)
        for content in ('hi','okay','thanks','Thank you!','👍','...'):
            self.assertEqual(self.send(content).status_code,200)
        self.ai.assert_not_awaited()
        self.send('help');self.ai.assert_awaited_once()

    def test_failure_and_malformed_result_do_not_lose_message(self):
        self.ai.side_effect=ai_service.AIServiceUnavailable()
        response=self.send();self.assertEqual(response.status_code,200)
        self.ai.side_effect=None;self.ai.return_value={'bad':'output'}
        self.assertEqual(self.send('A second meaningful message.').status_code,200)
        with self.Session() as db:
            self.assertEqual(db.query(models.CaseMessage).count(),2)
            for row in db.query(models.AIAnalysis):
                self.assertEqual(row.status,'failed');self.assertIsNone(row.distress_score)

    def test_retry_is_idempotent_no_duplicate_analysis(self):
        key=str(uuid4())
        first=self.send(key=key);again=self.send(key=key)
        self.assertEqual(first.json()['message']['id'],again.json()['message']['id'])
        self.assertTrue(again.json()['replayed']);self.ai.assert_awaited_once()
        self.assertEqual(self.send('Changed content',key=key).status_code,409)
        with self.Session() as db:
            self.assertEqual(db.query(models.AIAnalysis).count(),1)
            with self.assertRaises(IntegrityError):
                row=db.query(models.AIAnalysis).one()
                db.add(models.AIAnalysis(message_id=row.message_id,case_id=10,victim_id=1,status='pending'));db.commit()

    def test_chat_and_monitoring_authorization(self):
        self.send()
        for uid,role,expected in ((1,'victim',200),(2,'victim',404),(3,'counsellor',200),(4,'counsellor',404),(5,'authority',403)):
            self.assertEqual(self.client.get('/api/cases/CASE-10/messages',headers=self.headers(uid,role)).status_code,expected)
        self.assertEqual(self.send(uid=4,role='counsellor').status_code,404)
        self.assertEqual(self.detail(4).status_code,404)
        self.assertEqual(self.detail(1,'victim').status_code,403)
        self.assertEqual(self.client.get('/api/cases/CASE-10/ai-analyses',headers=self.headers(2)).status_code,404)
        self.assertEqual(self.client.get('/api/cases/CASE-10/ai-analyses',headers=self.headers(4,'counsellor')).status_code,404)
        items=self.client.get('/api/monitoring/cases',headers=self.headers(3,'counsellor')).json()['items']
        self.assertEqual([x['case_id'] for x in items],['CASE-10'])

    def test_invalid_input_and_spoofed_identity_rejected(self):
        for value in ('','   ','x'*4001): self.assertEqual(self.send(value).status_code,422)
        response=self.client.post('/api/cases/CASE-10/messages',json={'content':'test text','client_message_id':str(uuid4()),'victim_id':2},headers=self.headers())
        self.assertEqual(response.status_code,422);self.ai.assert_not_awaited()

    def test_history_pagination_and_sender_distinction(self):
        self.send('hello');self.send('hello',3,'counsellor');self.send('okay')
        page=self.client.get('/api/cases/CASE-10/messages?limit=2',headers=self.headers()).json()
        self.assertTrue(page['has_more']);self.assertEqual([x['sender_role'] for x in page['items']],['counsellor','victim'])
        earlier=self.client.get(f"/api/cases/CASE-10/messages?before_id={page['items'][0]['id']}",headers=self.headers()).json()
        self.assertEqual(len(earlier['items']),1);self.assertFalse(earlier['has_more'])

    def test_review_authorization_and_new_signal_reopens(self):
        self.send();before=self.detail().json();aid=before['latest_analysis']['id']
        self.assertTrue(before['needs_review'])
        for uid,role,expected in ((1,'victim',403),(4,'counsellor',404),(5,'authority',403)):
            response=self.client.post('/api/cases/CASE-10/ai-review',json={'analysis_id':aid},headers=self.headers(uid,role))
            self.assertEqual(response.status_code,expected)
        for _ in range(2):
            response=self.client.post('/api/cases/CASE-10/ai-review',json={'analysis_id':aid},headers=self.headers(3,'counsellor'))
            self.assertEqual(response.status_code,200)
        self.assertFalse(self.detail().json()['needs_review'])
        self.send('Another message describing persistent fear.')
        after=self.detail().json();self.assertTrue(after['needs_review']);self.assertIsNone(after['review'])
        with self.Session() as db:
            self.assertEqual(db.query(models.AnalysisReview).count(),1)
            self.assertEqual(db.query(models.AIAnalysis).count(),2)

    def test_reviews_cross_case_and_failed_analysis_rejected(self):
        self.send(uid=2,case='CASE-20')
        with self.Session() as db: other=db.query(models.AIAnalysis).one().id
        self.assertEqual(self.client.post('/api/cases/CASE-10/ai-review',json={'analysis_id':other},headers=self.headers(3,'counsellor')).status_code,404)
        self.ai.side_effect=ai_service.AIServiceUnavailable();self.send()
        with self.Session() as db: failed=db.query(models.AIAnalysis).filter_by(case_id=10).one().id
        self.assertEqual(self.client.post('/api/cases/CASE-10/ai-review',json={'analysis_id':failed},headers=self.headers(3,'counsellor')).status_code,409)

    def test_authority_summary_aggregates_and_read_does_not_call_ai(self):
        self.send();self.ai.reset_mock()
        response=self.client.get('/api/monitoring/summary',headers=self.headers(5,'authority'))
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['risk_distribution']['critical'],1)
        self.assertEqual(response.json()['risk_distribution']['unassessed'],1)
        self.assertEqual(response.json()['unreviewed_urgent'],1)
        self.assertNotIn('content',response.text);self.assertNotIn('reason',response.text)
        self.detail();self.client.get('/api/monitoring/cases',headers=self.headers(3,'counsellor'))
        self.ai.assert_not_awaited()

    def test_questionnaire_state_drives_cases_summary_queue_and_acknowledgement(self):
        critical = dict(mood=4, anxiety=4, sleep=4, hopelessness=4,
                        social_withdrawal=4, self_harm_thoughts=4, note=None)
        response = self.client.post('/api/victim/assessment', json=critical, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)

        cases = self.client.get('/api/cases', headers=self.headers(5, 'authority')).json()
        case = next(row for row in cases if row['caseId'] == 'CASE-10')
        self.assertEqual(case['riskLevel'], 'Critical')

        summary = self.client.get('/api/monitoring/summary', headers=self.headers(5, 'authority')).json()
        self.assertEqual(summary['risk_distribution']['critical'], 1)
        queue = self.client.get('/api/monitoring/cases', headers=self.headers(5, 'authority')).json()['items']
        current = next(row for row in queue if row['case_id'] == 'CASE-10')
        self.assertEqual((current['current_risk'], current['current_score'], current['category']),
                         ('critical', 100, 'URGENT'))
        self.assertTrue(current['needs_review'])

        indicators = self.client.get('/api/monitoring/indicators', headers=self.headers(5, 'authority')).json()['items']
        indicator = next(row for row in indicators if row['case_id'] == 'CASE-10')
        reviewed = self.client.post(f"/api/monitoring/indicators/{indicator['id']}/review",
                                    headers=self.headers(5, 'authority'))
        self.assertEqual(reviewed.status_code, 200)
        remaining = self.client.get('/api/monitoring/indicators', headers=self.headers(5, 'authority')).json()['items']
        self.assertNotIn('CASE-10', [row['case_id'] for row in remaining])
        after = self.client.get('/api/cases', headers=self.headers(5, 'authority')).json()
        self.assertEqual(next(row for row in after if row['caseId'] == 'CASE-10')['riskLevel'], 'Critical')

    def test_moderate_questionnaire_is_assessed_in_distribution(self):
        moderate = dict(mood=1, anxiety=1, sleep=1, hopelessness=1,
                        social_withdrawal=1, self_harm_thoughts=1, note=None)
        response = self.client.post('/api/victim/assessment', json=moderate, headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        summary = self.client.get('/api/monitoring/summary', headers=self.headers(5, 'authority')).json()
        self.assertEqual(summary['risk_distribution']['medium'], 1)
        self.assertEqual(summary['risk_distribution']['unassessed'], 1)

    def test_failed_latest_retains_success_without_fabrication(self):
        self.send();self.ai.side_effect=ai_service.AIServiceUnavailable();self.send('Another distress message.')
        detail=self.detail().json();self.assertEqual(detail['latest_attempt_status'],'failed')
        self.assertEqual(detail['latest_analysis']['distress_score'],78)
        self.assertIn('Analysis failed', detail['latest_attempt']['error_message'])
        self.assertIsNone(detail['latest_attempt']['distress_score'])
        self.assertEqual([x['status'] for x in detail['history']],['completed','failed'])
        empty=self.detail(4,case='CASE-20').json()
        self.assertIsNone(empty['score']);self.assertIsNone(empty['latest_analysis'])
        self.assertEqual(empty['category'],'UNASSESSED')

    def test_questionnaire_source_is_read_when_projection_is_missing(self):
        response = self.client.post('/api/victim/assessment', json=dict(
            mood=1, anxiety=1, sleep=1, hopelessness=1, social_withdrawal=1,
            self_harm_thoughts=1, note=None), headers=self.headers())
        self.assertEqual(response.status_code, 200)
        with self.Session() as db:
            case = db.get(models.Case, 10)
            case.latest_distress_score = None
            case.latest_risk_source = None
            case.latest_state_at = None
            db.commit()
        detail = self.detail().json()
        self.assertEqual(detail['current_source'], 'questionnaire')
        self.assertEqual(detail['current_score'], detail['questionnaire_score'])
        self.assertIsNotNone(detail['questionnaire_score'])
        self.assertIsNone(detail['latest_analysis'])
        self.assertEqual(detail['latest_attempt_status'], 'none')

    def test_mixed_sources_in_same_history(self):
        response=self.client.post('/api/victim/assessment',json=dict(mood=1,anxiety=1,sleep=1,hopelessness=1,social_withdrawal=1,self_harm_thoughts=1,note='I feel very scared.'),headers=self.headers())
        self.assertEqual(response.status_code,200);self.send()
        history=self.client.get('/api/cases/CASE-10/ai-analyses',headers=self.headers()).json()['items']
        self.assertEqual([x['source_type'] for x in history],['assessment','message'])

    def test_prompt3_migration_preserves_prompt2_history(self):
        from app.migrate_ai_prompt3 import upgrade
        engine=create_engine('sqlite://');self.addCleanup(engine.dispose)
        for table in (models.User.__table__,models.Case.__table__,models.Assessment.__table__): table.create(engine)
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE ai_analyses (id INTEGER PRIMARY KEY, assessment_id INTEGER NOT NULL UNIQUE REFERENCES assessments(id), case_id INTEGER NOT NULL REFERENCES cases(id), victim_id INTEGER NOT NULL REFERENCES users(id), status VARCHAR(16) NOT NULL, distress_score INTEGER, risk_level VARCHAR(16), emotions JSON, requires_attention BOOLEAN, reason VARCHAR(400), provider VARCHAR(16), created_at DATETIME NOT NULL, finished_at DATETIME)"))
            conn.execute(text("INSERT INTO users (id,name,email,password_hash,role) VALUES (1,'Test','a@example.com','hash','victim')"))
            conn.execute(text("INSERT INTO cases (id,case_id,victim_id,risk_level,assigned_counsellor,last_assessment,intervention_status,district,state) VALUES (10,'OLD',1,'Low','Test','old','old','x','x')"))
            conn.execute(text("INSERT INTO assessments (id,case_id,mood,anxiety,sleep,hopelessness,social_withdrawal,self_harm_thoughts,distress_score,risk_level,created_at) VALUES (1,10,1,1,1,1,1,1,25,'Moderate','old')"))
            conn.execute(text("INSERT INTO ai_analyses (id,assessment_id,case_id,victim_id,status,distress_score,risk_level,emotions,requires_attention,reason,provider,created_at,finished_at) VALUES (1,1,10,1,'completed',65,'high','[\"fear\"]',1,'Fear expressed','groq','2026-09-01 12:00:00','2026-09-01 12:00:01')"))
        upgrade(engine);upgrade(engine)
        with engine.connect() as conn:
            self.assertEqual(tuple(conn.execute(text('SELECT id,assessment_id,message_id,distress_score FROM ai_analyses')).one()),(1,1,None,65))
        self.assertTrue(next(c for c in inspect(engine).get_columns('ai_analyses') if c['name']=='assessment_id')['nullable'])
        with sessionmaker(bind=engine).begin() as db:
            message=models.CaseMessage(case_id=10,victim_id=1,sender_id=1,sender_role='victim',client_message_id=str(uuid4()),content='New meaningful message')
            db.add(message);db.flush()
            db.add(models.AIAnalysis(message_id=message.id,case_id=10,victim_id=1,status='pending'))
        with engine.connect() as conn: self.assertEqual(conn.scalar(text('SELECT count(*) FROM ai_analyses')),2)


if __name__=='__main__': unittest.main()
