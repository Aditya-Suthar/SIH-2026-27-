"""Opt-in SYNTHETIC fixtures for an empty, separate SQLite demo database only."""
import os
from datetime import datetime, timezone, timedelta
from getpass import getpass
from .database import engine, SessionLocal
from .migrate_final import upgrade
from . import models
from .auth import pwd_context
from .operations import new_victim_case

def main():
    if os.getenv('APP_ENV')=='production' or engine.dialect.name!='sqlite' or 'demo' not in str(engine.url.database).lower():
        raise SystemExit('Set DATABASE_URL to a separate SQLite filename containing demo. Production is prohibited.')
    upgrade(engine)
    with SessionLocal() as db:
        if db.query(models.User).first():raise SystemExit('Database is not empty; no records changed.')
    password=getpass('Choose a demo account password (8–72 ASCII characters): ')
    if not password.isascii() or not 8<=len(password)<=72:raise SystemExit('Invalid password length/format')
    if password!=getpass('Confirm demo password: '):raise SystemExit('Passwords differ')
    hashed=pwd_context.hash(password)
    now=datetime.now(timezone.utc)-timedelta(minutes=5)
    with SessionLocal.begin() as db:
        authority=models.User(name='Demo Authority',email='authority@demo.example',role='authority',password_hash=hashed)
        counsellor=models.User(name='Demo Counsellor',email='counsellor@demo.example',role='counsellor',password_hash=hashed)
        db.add_all([authority,counsellor]);db.flush()
        for number,scores in enumerate(([30,45,61,78],[70,69,71],[78,65,50,35],[]),1):
            victim=models.User(name=f'Demo Victim {number}',email=f'victim{number}@demo.example',role='victim',password_hash=hashed);db.add(victim);db.flush()
            case=new_victim_case(db,victim.id);case.case_id=f'DEMO-{number}';case.assigned_counsellor_id=counsellor.id;case.assigned_counsellor=counsellor.name;case.intervention_status='Monitoring';db.flush()
            for i,score in enumerate(scores):
                when=now-timedelta(days=len(scores)-i-1)
                a=models.Assessment(case_id=case.id,mood=0,anxiety=0,sleep=0,hopelessness=0,social_withdrawal=0,self_harm_thoughts=0,distress_score=0,risk_level='Low',created_at=when.isoformat(),note='SYNTHETIC DEMO check-in. Not a real victim or provider response.')
                db.add(a);db.flush()
                db.add(models.AIAnalysis(assessment_id=a.id,case_id=case.id,victim_id=victim.id,status='completed',distress_score=score,risk_level='critical' if score>=75 else 'high' if score>=50 else 'medium',requires_attention=score>=50,emotions=['synthetic example'],reason='SYNTHETIC DEMO fixture, created without an AI call. Not clinical data.',provider='gemini',created_at=when,finished_at=when))
    print('Synthetic demo ready: authority@demo.example, counsellor@demo.example, victim1@demo.example through victim4@demo.example. Use the password you entered. New submissions use the real configured AI service; no mock provider is installed.')

if __name__=='__main__':main()
