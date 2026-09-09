from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from passlib.context import CryptContext

import jwt
from datetime import datetime, timedelta, timezone

from .database import get_db
from . import models, schemas

router = APIRouter()
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

SECRET_KEY = "change-this-later"
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
        raise HTTPException(
            status_code=403,
            detail="Public registration is available for victim accounts only."
        )

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
        role="victim"
    )

    db.add(new_user)
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