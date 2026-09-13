"""Current-owner names, minimal disclosure and constant-query case reads."""
from datetime import datetime, timedelta, timezone
import unittest

from sqlalchemy import event
import test_monitoring as t


class CaseIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        t.ChatMonitoringTests.setUpClass()

    setUp = t.ChatMonitoringTests.setUp
    headers = t.ChatMonitoringTests.headers

    def get(self, path, uid=5, role='authority'):
        return self.client.get(path, headers=self.headers(uid, role))

    def test_case_list_and_detail_resolve_current_owner_not_counsellor(self):
        with self.Session.begin() as db:
            db.get(t.models.User, 1).name = '  Aditya Suthar  '
            db.get(t.models.User, 2).name = 'Second Victim'
        rows = self.get('/api/cases').json()
        self.assertEqual({r['caseId']: r['victimName'] for r in rows},
                         {'CASE-10': 'Aditya Suthar', 'CASE-20': 'Second Victim'})
        self.assertEqual(self.get('/api/cases/CASE-10').json()['victimName'], 'Aditya Suthar')
        self.assertEqual(set(rows[0]), {'caseId', 'victimName', 'riskLevel', 'assignedCounsellor',
                                      'lastAssessment', 'interventionStatus', 'district', 'state'})
        # Existing non-identity fields keep their values.
        self.assertEqual(rows[0]['assignedCounsellor'], 'Assigned counsellor')
        self.assertEqual(rows[0]['lastAssessment'], 'Never')
        self.assertEqual(rows[0]['interventionStatus'], 'Pending')
        with self.Session.begin() as db:
            db.get(t.models.Case, 10).victim_id = 2
        self.assertEqual(self.get('/api/cases/CASE-10').json()['victimName'], 'Second Victim')

    def test_blank_unowned_and_nonvictim_owner_use_fallback(self):
        with self.Session.begin() as db:
            db.get(t.models.User, 1).name = ' \t '
            db.get(t.models.Case, 20).victim_id = None
        self.assertEqual([r['victimName'] for r in self.get('/api/cases').json()],
                         ['Unnamed Victim', 'Unnamed Victim'])
        with self.Session.begin() as db:
            db.get(t.models.Case, 10).victim_id = 3
        self.assertEqual(self.get('/api/cases/CASE-10').json()['victimName'], 'Unnamed Victim')
        self.assertTrue(all(r['victim_name'] == 'Unnamed Victim'
                            for r in self.get('/api/monitoring/cases').json()['items']))

    def test_counsellor_scope_and_unauthorized_requests_do_not_disclose_names(self):
        rows = self.get('/api/cases', 3, 'counsellor').json()
        self.assertEqual([(r['caseId'], r['victimName']) for r in rows], [('CASE-10', 'Test 1')])
        for path in ['/api/cases/CASE-20', '/api/cases/CASE-20/monitoring']:
            response = self.get(path, 3, 'counsellor')
            self.assertEqual(response.status_code, 404)
            self.assertNotIn('Test 2', response.text)
        for path in ['/api/cases', '/api/monitoring/cases', '/api/monitoring/indicators']:
            response = self.get(path, 1, 'victim')
            self.assertEqual(response.status_code, 403)
            self.assertNotIn('victimName', response.text)
            self.assertNotIn('victim_name', response.text)
            self.assertEqual(self.get(path, 999, 'authority').status_code, 401)
            self.assertIn(self.client.get(path).status_code, (401, 403))
        self.assertEqual(self.get('/api/cases', 3, 'authority').status_code, 401)

    def test_monitoring_and_indicators_include_only_scoped_owner_name(self):
        answers = {key: 3 for key in ('mood', 'anxiety', 'sleep', 'hopelessness',
                                     'social_withdrawal', 'self_harm_thoughts')}
        response = self.client.post('/api/victim/assessment', headers=self.headers(), json=answers)
        self.assertEqual(response.status_code, 200)
        for path in ['/api/monitoring/cases', '/api/monitoring/indicators']:
            response = self.get(path, 3, 'counsellor')
            rows = response.json()['items']
            self.assertEqual([(r['case_id'], r['victim_name']) for r in rows], [('CASE-10', 'Test 1')])
            for field in ('email', 'password_hash', 'date_of_birth', 'phone'):
                self.assertNotIn(field, response.text)
        self.assertEqual(self.get('/api/monitoring/indicators', 4, 'counsellor').json()['items'], [])
        detail = self.get('/api/cases/CASE-10/monitoring', 3, 'counsellor').json()
        self.assertEqual(detail['victim_name'], 'Test 1')
        self.assertEqual(detail['category'], 'URGENT')
        summary = self.get('/api/monitoring/summary')
        self.assertNotIn('victim_name', summary.text)
        self.assertNotIn('Test 1', summary.text)

    def test_staff_support_and_session_lists_show_name_without_expanding_victim_payload(self):
        self.assertEqual(self.client.post('/api/support-requests', headers=self.headers(),
                                         json={'kind': 'Support'}).status_code, 200)
        self.assertEqual(self.client.post('/api/sessions', headers=self.headers(), json={
            'case_id': 'CASE-10', 'starts_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }).status_code, 200)
        for path in ['/api/support-requests', '/api/sessions']:
            self.assertEqual(self.get(path).json()['items'][0]['victim_name'], 'Test 1')
            self.assertEqual(self.get(path, 3, 'counsellor').json()['items'][0]['victim_name'], 'Test 1')
            self.assertEqual(self.get(path, 4, 'counsellor').json()['items'], [])
            self.assertEqual(self.get(path, 2, 'victim').json()['items'], [])
            self.assertNotIn('victim_name', self.get(path, 1, 'victim').text)

    def test_identity_query_projects_only_name_and_handles_empty_collection(self):
        from app.case_identity import victim_names
        statements = []
        def record(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)
        with self.Session() as db:
            cases = db.query(t.models.Case).all()
            event.listen(self.engine, 'before_cursor_execute', record)
            try:
                self.assertEqual(victim_names(db, []), {})
                self.assertEqual(statements, [])
                self.assertEqual(victim_names(db, cases), {10: 'Test 1', 20: 'Test 2'})
            finally:
                event.remove(self.engine, 'before_cursor_execute', record)
        self.assertEqual(len(statements), 1)
        projection = statements[0].split('FROM')[0].lower()
        self.assertIn('users.name', projection)
        for field in ('email', 'password_hash', 'date_of_birth'):
            self.assertNotIn(field, projection)

    def test_query_count_does_not_grow_with_cases(self):
        def count_reads(path):
            statements = []
            def record(conn, cursor, statement, parameters, context, executemany):
                if statement.lstrip().upper().startswith('SELECT'):
                    statements.append(statement)
            event.listen(self.engine, 'before_cursor_execute', record)
            try:
                response = self.get(path)
                self.assertEqual(response.status_code, 200, response.text)
            finally:
                event.remove(self.engine, 'before_cursor_execute', record)
            return len(statements)
        paths = ['/api/cases', '/api/monitoring/cases', '/api/monitoring/indicators']
        before = {path: count_reads(path) for path in paths}
        with self.Session.begin() as db:
            for cid in range(30, 50):
                db.add(t.models.Case(id=cid, case_id=f'CASE-{cid}', victim_id=1,
                    assigned_counsellor_id=3, assigned_counsellor='Assigned counsellor',
                    risk_level='Low', last_assessment='Never', intervention_status='Pending',
                    district='', state=''))
        for path in paths:
            self.assertEqual(count_reads(path), before[path], path)
