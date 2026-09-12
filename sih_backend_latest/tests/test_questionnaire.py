"""Question bank, deterministic adaptation, scoring, and additive-storage tests."""
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import models
from app.database import Base
from app.database import get_db
from app.auth import get_current_user
from app.questionnaire import router
from app.migrate_questionnaire_v2 import upgrade
from app.question_bank import ALL_AGES, BY_ID, CORE_IDS, QUESTIONS, SAFETY_IDS
from app.questionnaire_engine import age_group, answer_severity, score_answers, select_questions, triggered_followups


def neutral_answers(questions):
    return {q.id:(1 if q.reverse_scored and q.response_type in ("yes_no","safety_yes_no") else
                     4 if q.reverse_scored else 0) for q in questions}


class QuestionnaireEngineTests(unittest.TestCase):
    def test_bank_integrity_and_counts(self):
        self.assertEqual((len(QUESTIONS), len(BY_ID)), (150, 150))
        self.assertEqual(len(set(q.id for q in QUESTIONS)), 150)
        self.assertEqual(len({q.domain for q in QUESTIONS}), 25)
        self.assertTrue(all(parent in BY_ID for q in QUESTIONS for parent in q.follow_up_for))
        self.assertEqual(len(SAFETY_IDS), 9)
        self.assertTrue(all(set(q.age_groups) == set(ALL_AGES) for q in QUESTIONS if q.id in SAFETY_IDS))
        self.assertGreater(len(set(Counter(q.domain for q in QUESTIONS).values())), 1)

    def test_age_boundaries(self):
        today = date(2026, 9, 12)
        cases = [(date(2010,9,13),"13-17"),(date(2008,9,12),"18-24"),
                 (date(1982,9,12),"25-44"),(date(1967,9,12),"45-59"),(date(1966,9,12),"60+")]
        for dob, expected in cases: self.assertEqual(age_group(dob,today), expected)

    def test_every_age_has_short_core_safe_selection(self):
        for group in ALL_AGES:
            selected = select_questions(group, victim_id=7)
            self.assertEqual(len(selected), 12)
            self.assertTrue(set(CORE_IDS) <= {q.id for q in selected})
            self.assertTrue(all(group in q.age_groups for q in selected))

    def test_age_context_selection(self):
        adolescent = select_questions("13-17", victim_id=1)
        young = select_questions("18-24", victim_id=1)
        adult = select_questions("25-44", victim_id=1)
        older = select_questions("60+", victim_id=1)
        self.assertTrue(all("13-17" in q.age_groups for q in adolescent))
        self.assertTrue(all("18-24" in q.age_groups for q in young))
        self.assertTrue(all("25-44" in q.age_groups for q in adult))
        self.assertTrue(all("60+" in q.age_groups for q in older))
        self.assertNotEqual({q.id for q in adolescent}, {q.id for q in older})

    def test_repeated_checkin_rotation(self):
        first = select_questions("25-44", victim_id=2)
        history = [SimpleNamespace(selected_question_ids=[q.id for q in first], domain_scores={})]
        second = select_questions("25-44", history, victim_id=2)
        first_optional = {q.id for q in first} - set(CORE_IDS)
        second_optional = {q.id for q in second} - set(CORE_IDS)
        self.assertNotEqual(first_optional, second_optional)

    def test_elevated_domain_priority(self):
        history = [SimpleNamespace(selected_question_ids=[], domain_scores={"trauma":90})]
        selected = select_questions("25-44", history, victim_id=3)
        self.assertIn("trauma", {q.domain for q in selected})

    def test_safety_followups_and_escalation(self):
        followups = triggered_followups({"Q064":1}, CORE_IDS)
        self.assertTrue(followups)
        self.assertTrue(all(q.critical for q in followups))
        result = score_answers({"Q001":0,"Q006":0,"Q009":0,"Q057":0,"Q064":1,"Q073":1})
        self.assertIn("Q064", result["safety_flags"])
        self.assertEqual(result["risk_level"], "Critical")

    def test_inability_to_stay_safe_is_critical(self):
        result = score_answers({"Q066":0})
        self.assertEqual((result["safety_flags"], result["risk_level"]), (["Q066"], "Critical"))

    def test_reverse_scoring(self):
        protective = BY_ID["Q073"]
        self.assertEqual(answer_severity(protective, 1), 0)
        self.assertEqual(answer_severity(protective, 0), 4)
        self.assertEqual(score_answers({"Q073":1})["domain_scores"]["social_support"], 0)

    def test_domain_normalization_is_weighted_not_answer_average(self):
        result = score_answers({"Q001":4,"Q002":0})
        # weights 3 and 2: 12 / 20 = 60%, not the simple 50% answer average.
        self.assertEqual(result["domain_scores"]["mood"], 60.0)

    def test_optional_skips_and_invalid_answers(self):
        self.assertEqual(score_answers({"Q001":2})["questionnaire_score"], 50.0)
        with self.assertRaises(ValueError): score_answers({"Q001":5})
        with self.assertRaises(ValueError): score_answers({"Q999":0})

    def test_age_never_changes_score(self):
        answers = {"Q001":3,"Q009":2,"Q057":1,"Q073":1}
        expected = score_answers(answers)
        for group in ALL_AGES:
            self.assertEqual(score_answers(answers)["questionnaire_score"], expected["questionnaire_score"])


class QuestionnaireMigrationTests(unittest.TestCase):
    def test_migration_is_additive_idempotent_and_preserves_assessment(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = create_engine("sqlite:///" + str(Path(directory)/"migration.db"))
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            with Session.begin() as db:
                db.add(models.User(id=1,name="Legacy",email="legacy@example.com",password_hash="x",role="victim"))
                db.add(models.Case(id=1,case_id="LEGACY-1",victim_id=1,risk_level="Low",
                    assigned_counsellor="Not Assigned",last_assessment="Never",
                    intervention_status="Pending",district="",state=""))
                db.add(models.Assessment(id=1,case_id=1,mood=1,anxiety=1,sleep=1,hopelessness=1,
                    social_withdrawal=1,self_harm_thoughts=0,distress_score=21,risk_level="Low",created_at="2026-01-01T00:00:00+00:00"))
            upgrade(engine); upgrade(engine)
            self.assertIn("date_of_birth", {c["name"] for c in inspect(engine).get_columns("users")})
            self.assertIn("questionnaire_sessions", inspect(engine).get_table_names())
            with Session() as db: self.assertEqual(db.get(models.Assessment,1).distress_score,21)
            engine.dispose()


class QuestionnaireApiTests(unittest.TestCase):
    def test_note_after_safety_signal_is_saved_and_failure_is_durable(self):
        from app.ai_service import AIServiceUnavailable
        payload = self.client.get('/api/victim/questionnaire').json()
        self.client.post('/api/victim/questionnaire/safety-signal', json={
            'questionnaire_id':payload['questionnaire_id'], 'question_id':'Q064', 'answer':1})
        answers = neutral_answers([BY_ID[q['id']] for q in payload['questions']])
        answers['Q064'] = 1
        with patch('app.ai_service.analyze_distress', new=AsyncMock(side_effect=AIServiceUnavailable())) as analyze:
            response = self.client.post('/api/victim/questionnaire/submit', json={
                'questionnaire_id':payload['questionnaire_id'], 'answers':answers, 'note':'  I feel worried.  '})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['ai_analysis']['status'], 'failed')
        analyze.assert_awaited_once_with('I feel worried.')
        with self.Session() as db:
            assessment = db.query(models.Assessment).one()
            analysis = db.query(models.AIAnalysis).one()
            self.assertEqual(assessment.note, 'I feel worried.')
            self.assertEqual((analysis.assessment_id, analysis.case_id, analysis.victim_id), (assessment.id, 1, 1))
            self.assertIsNone(analysis.distress_score)

    def test_completed_submission_retry_returns_same_analysis(self):
        payload = self.client.get('/api/victim/questionnaire').json()
        request = {'questionnaire_id':payload['questionnaire_id'],
                   'answers':neutral_answers([BY_ID[q['id']] for q in payload['questions']]),
                   'note':'I feel worried.'}
        result = dict(distress_score=30, risk_level='medium', emotions=['worry'],
                      requires_attention=False, reason='Worry is expressed.', provider='groq')
        with patch('app.ai_service.analyze_distress', new=AsyncMock(return_value=result)) as analyze:
            first = self.client.post('/api/victim/questionnaire/submit', json=request)
            second = self.client.post('/api/victim/questionnaire/submit', json=request)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(first.json()['ai_analysis'], second.json()['ai_analysis'])
        self.assertEqual(first.json()['ai_analysis']['status'], 'completed')
        self.assertEqual(analyze.await_count, 1)
        with self.Session() as db:
            self.assertEqual(db.query(models.Assessment).count(), 1)
            self.assertEqual(db.query(models.AIAnalysis).count(), 1)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.engine = create_engine("sqlite:///" + str(Path(self.temp.name)/"api.db"), connect_args={"check_same_thread":False})
        Base.metadata.create_all(self.engine); self.Session = sessionmaker(bind=self.engine)
        with self.Session.begin() as db:
            db.add(models.User(id=1,name="Victim",email="v@example.com",password_hash="x",role="victim",date_of_birth=date(2003,1,1)))
            db.add(models.Case(id=1,case_id="CASE-1",victim_id=1,risk_level="Low",assigned_counsellor="Not Assigned",
                last_assessment="Never",intervention_status="Pending",district="",state=""))
        application = FastAPI(); application.include_router(router)
        def database():
            with self.Session() as db: yield db
        application.dependency_overrides[get_db] = database
        application.dependency_overrides[get_current_user] = lambda:{"user_id":1,"role":"victim"}
        self.client = TestClient(application); self.client.__enter__()
        self.addCleanup(self.client.__exit__,None,None,None); self.addCleanup(self.engine.dispose)

    def test_get_submit_followup_and_persistence(self):
        offered = self.client.get("/api/victim/questionnaire")
        self.assertEqual(offered.status_code,200,offered.text)
        payload = offered.json(); self.assertEqual((payload["age_group"],len(payload["questions"])),("18-24",12))
        immediate = self.client.post("/api/victim/questionnaire/safety-signal",json={
            "questionnaire_id":payload["questionnaire_id"],"question_id":"Q064","answer":1})
        self.assertEqual(immediate.status_code,200,immediate.text); self.assertTrue(immediate.json()["recorded"])
        with self.Session() as db:
            self.assertEqual(db.get(models.Case,1).risk_level,"Critical")
            self.assertEqual(db.query(models.Assessment).count(),1)
        answers = {}
        for question in payload["questions"]:
            answers[question["id"]] = 1 if question["response_type"] in ("yes_no","safety_yes_no") and question["reverse_scored"] else 0
        answers["Q064"] = 1
        first = self.client.post("/api/victim/questionnaire/submit",json={"questionnaire_id":payload["questionnaire_id"],"answers":answers})
        self.assertEqual(first.status_code,200,first.text); body=first.json()
        self.assertEqual(body["risk_level"],"Critical"); self.assertFalse(body["complete"])
        followup_answers = {q["id"]:(1 if q["reverse_scored"] else 0) for q in body["triggered_followups"]}
        second = self.client.post("/api/victim/questionnaire/submit",json={"questionnaire_id":payload["questionnaire_id"],"answers":followup_answers})
        self.assertEqual(second.status_code,200,second.text); self.assertTrue(second.json()["complete"])
        with self.Session() as db:
            session=db.get(models.QuestionnaireSession,payload["questionnaire_id"])
            self.assertEqual(session.status,"completed"); self.assertEqual(session.safety_flags,["Q064"])
            self.assertEqual(db.query(models.Assessment).count(),1)

    def test_unselected_and_missing_core_rejected(self):
        payload=self.client.get("/api/victim/questionnaire").json()
        bad=self.client.post("/api/victim/questionnaire/submit",json={"questionnaire_id":payload["questionnaire_id"],"answers":{"Q150":4}})
        self.assertEqual(bad.status_code,422)
