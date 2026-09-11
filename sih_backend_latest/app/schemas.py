from typing import Annotated
from pydantic import BaseModel, EmailStr, StringConstraints, Field, field_validator


class VictimDashboardOut(BaseModel):
    caseId: str
    riskLevel: str
    distressScore: int | None
    assignedCounsellor: str
    caseStage: str


class UserRegister(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=8, max_length=72)]
    role: str


    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must fit within 72 UTF-8 bytes")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    role: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str

    class Config:
        from_attributes = True


class CaseOut(BaseModel):
    caseId: str
    riskLevel: str
    assignedCounsellor: str
    lastAssessment: str
    interventionStatus: str
    district: str = ""
    state: str = ""

    class Config:
        from_attributes = True

class AssessmentCreate(BaseModel):
    mood: int = Field(ge=0, le=4, strict=True)
    anxiety: int = Field(ge=0, le=4, strict=True)
    sleep: int = Field(ge=0, le=4, strict=True)
    hopelessness: int = Field(ge=0, le=4, strict=True)
    social_withdrawal: int = Field(ge=0, le=4, strict=True)
    self_harm_thoughts: int = Field(ge=0, le=4, strict=True)
    note: Annotated[str, StringConstraints(strict=True, max_length=4000)] | None = None

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value):
        if value is None:
            return None
        return value.strip() or None
