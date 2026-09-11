"""Demo-critical onboarding, assignment, scheduling and support authorization."""
from datetime import datetime, timezone, timedelta
import unittest
import test_monitoring as t

class OperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):t.ChatMonitoringTests.setUpClass()
    setUp=t.ChatMonitoringTests.setUp
    headers=t.ChatMonitoringTests.headers
    def test_public_signup_only_victim_and_case_created(self):
        body={'name':'New user','email':'new@example.com','password':'test-password-only','role':'authority'}
        self.assertEqual(self.client.post('/register',json=body).status_code,403)
        body['role']='victim';response=self.client.post('/register',json=body)
        self.assertEqual(response.status_code,200,response.text)
        with self.Session() as db:self.assertEqual(db.query(t.models.Case).filter_by(victim_id=response.json()['id']).count(),1)
        login=self.client.post('/login',json={k:body[k] for k in ('email','password','role')})
        self.assertEqual(login.status_code,200)
        response=self.client.get('/api/victim/dashboard',headers={'Authorization':'Bearer '+login.json()['access_token']})
        self.assertIsNone(response.json()['distressScore'])
    def test_assessment_ranges_and_live_account(self):
        body={k:0 for k in ['mood','anxiety','sleep','hopelessness','social_withdrawal','self_harm_thoughts']};body['mood']=5
        self.assertEqual(self.client.post('/api/victim/assessment',headers=self.headers(),json=body).status_code,422)
        self.assertEqual(self.client.get('/api/users',headers=self.headers(999,'authority')).status_code,401)
    def test_assignment_authorization_and_real_directory(self):
        path='/api/cases/CASE-10/assignment'
        for uid,role in [(1,'victim'),(3,'counsellor')]:self.assertEqual(self.client.patch(path,headers=self.headers(uid,role),json={'counsellor_id':4}).status_code,403)
        self.assertEqual(self.client.patch(path,headers=self.headers(5,'authority'),json={'counsellor_id':1}).status_code,422)
        self.assertEqual(self.client.patch(path,headers=self.headers(5,'authority'),json={'counsellor_id':4,'status':'Follow-up pending'}).status_code,200)
        self.assertEqual(self.client.get('/api/cases/CASE-10',headers=self.headers(3,'counsellor')).status_code,404)
        self.assertEqual(self.client.get('/api/counsellors',headers=self.headers(5,'authority')).json()['items'][1]['assigned_cases'],2)
    def test_support_request_idempotency_and_scope(self):
        first=self.client.post('/api/support-requests',json={'kind':'Threat report'},headers=self.headers()).json()
        second=self.client.post('/api/support-requests',json={'kind':'Threat report'},headers=self.headers()).json()
        self.assertEqual(first,second)
        self.assertEqual(self.client.get('/api/support-requests',headers=self.headers(4,'counsellor')).json()['items'],[])
        path=f"/api/support-requests/{first['id']}"
        self.assertEqual(self.client.patch(path,headers=self.headers(),json={'status':'Reviewed'}).status_code,403)
        self.assertEqual(self.client.patch(path,headers=self.headers(4,'counsellor'),json={'status':'Reviewed'}).status_code,404)
        self.assertEqual(self.client.patch(path,headers=self.headers(3,'counsellor'),json={'status':'Reviewed'}).status_code,200)
        row=self.client.get('/api/support-requests',headers=self.headers()).json()['items'][0]
        self.assertEqual(row['reviewed_by'],3);self.assertIsNotNone(row['reviewed_at'])
    def book(self):
        return self.client.post('/api/sessions',headers=self.headers(),json={'case_id':'CASE-10','starts_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()})
    def test_booking_confirmation_overlap_and_scope(self):
        r=self.book();self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['status'],'Requested')
        self.assertEqual(self.book().status_code,409)
        path=f"/api/sessions/{r.json()['id']}"
        self.assertEqual(self.client.patch(path,headers=self.headers(),json={'status':'Confirmed'}).status_code,403)
        self.assertEqual(self.client.patch(path,headers=self.headers(4,'counsellor'),json={'status':'Confirmed'}).status_code,404)
        self.assertEqual(self.client.patch(path,headers=self.headers(3,'counsellor'),json={'status':'Confirmed'}).status_code,200)
        self.assertEqual(self.client.patch(path,headers=self.headers(3,'counsellor'),json={'status':'Completed'}).status_code,409)
        self.assertEqual(self.client.get('/api/sessions',headers=self.headers(2,'victim')).json()['items'],[])
        self.assertEqual(self.client.patch(path,headers=self.headers(),json={'status':'Cancelled'}).status_code,200)
    def test_booking_rejects_spoof_and_past(self):
        for body in [{'case_id':'CASE-20','starts_at':(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()},{'case_id':'CASE-10','starts_at':'2020-01-01T12:00:00+00:00'}]:
            self.assertIn(self.client.post('/api/sessions',headers=self.headers(),json=body).status_code,[404,422])
    def test_reassignment_cancels_old_appointments(self):
        self.book()
        self.client.patch('/api/cases/CASE-10/assignment',headers=self.headers(5,'authority'),json={'counsellor_id':4})
        self.assertEqual(self.client.get('/api/sessions',headers=self.headers()).json()['items'][0]['status'],'Cancelled')
    def test_legacy_victim_onboarding_idempotent(self):
        with self.Session.begin() as db:db.add(t.models.User(id=8,name='Legacy',email='legacy@example.com',role='victim',password_hash='unused'))
        a=self.client.post('/api/victim/case',headers=self.headers(8)).json();b=self.client.post('/api/victim/case',headers=self.headers(8)).json();self.assertEqual(a,b)
