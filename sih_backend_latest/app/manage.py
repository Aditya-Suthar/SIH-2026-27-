"""Local operator-only account provisioning; no public privileged signup."""
import argparse
from getpass import getpass
from pydantic import TypeAdapter, EmailStr
from .database import SessionLocal, engine
from .migrate_final import upgrade
from .models import User
from .auth import pwd_context
from .operations import new_victim_case

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email',required=True);parser.add_argument('--name',required=True)
    parser.add_argument('--role',required=True,choices=['victim','counsellor','authority'])
    args=parser.parse_args();email=TypeAdapter(EmailStr).validate_python(args.email)
    password=getpass('New account password (8–72 characters): ')
    if not 8<=len(password)<=72 or len(password.encode())>72:raise SystemExit('Invalid password length')
    if password!=getpass('Confirm password: '):raise SystemExit('Passwords differ')
    upgrade(engine)
    with SessionLocal.begin() as db:
        if db.query(User).filter_by(email=email).first():raise SystemExit('Account already exists; no changes made')
        user=User(name=args.name[:100],email=email,role=args.role,password_hash=pwd_context.hash(password));db.add(user);db.flush()
        if args.role=='victim':new_victim_case(db,user.id)
    print('Account created.')

if __name__=='__main__':main()
