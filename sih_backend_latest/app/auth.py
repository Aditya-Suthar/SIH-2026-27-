from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext

import os
import secrets
import logging
import jwt
from datetime import datetime, timedelta, timezone

from .database import get_db
from . import models, schemas

router = APIRouter()
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

SECRET_KEY = os.getenv("JWT_SECRET", "")
if not SECRET_KEY:
    if os.getenv("APP_ENV") == "production":
        raise RuntimeError("JWT_SECRET is required in production")
    SECRET_KEY = secrets.token_urlsafe(48)
    logging.getLogger(__name__).warning("Using an ephemeral local JWT secret; configure JWT_SECRET for persistent sessions.")
elif len(SECRET_KEY.encode()) < 32:
    raise RuntimeError("JWT_SECRET must contain at least 32 bytes")
ALGORITHM = "HS256"
security = HTTPBearer()


def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=60)

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

def require_role(required_role: str):
    def role_checker(
        current_user: dict = Depends(get_current_user)
    ):
        if current_user.get("role") != required_role:
            raise HTTPException(
                status_code=403,
                detail="Access forbidden for this role"
            )

        return current_user

    return role_checker

@router.get("/victim/test")
def victim_test(
    current_user: dict = Depends(require_role("victim"))
):
    return {
        "message": "Victim access granted",
        "user": current_user
    }

@router.get("/counsellor/test")
def counsellor_test(
    current_user: dict = Depends(require_role("counsellor"))
):
    return {
        "message": "Counsellor access granted",
        "user": current_user
    }


@router.get("/authority/test")
def authority_test(
    current_user: dict = Depends(require_role("authority"))
):
    return {
        "message": "Authority access granted",
        "user": current_user
    }

@router.post("/register")
def register_user(
    data: schemas.UserRegister,
    db: Session = Depends(get_db)
):
    if data.role != "victim":
        raise HTTPException(403, "Public registration is victim-only")

    existing_user = db.query(models.User).filter(
        models.User.email == data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    new_user = models.User(
        name=data.name,
        email=data.email,
        password_hash=pwd_context.hash(data.password),
        role=data.role
    )

    db.add(new_user)
    db.flush()
    from .operations import new_victim_case
    new_victim_case(db, new_user.id)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "id": new_user.id,
        "email": new_user.email,
        "role": new_user.role
    }


@router.post("/login")
def login_user(
    data: schemas.UserLogin,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.email == data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not pwd_context.verify(
        data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if user.role != data.role:
        raise HTTPException(
            status_code=403,
            detail="Invalid role"
        )

    access_token = create_access_token({
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "name": user.name,
        "email": user.email,
        "role": user.role
    }