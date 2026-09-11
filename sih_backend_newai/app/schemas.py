from typing import Annotated
from pydantic import BaseModel, EmailStr, StringConstraints, field_validator


class VictimDashboardOut(BaseModel):
    caseId: str
    riskLevel: str
    distressScore: int
    assignedCounsellor: str
    caseStage: str


class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str


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

    class Config:
        from_attributes = True

class AssessmentCreate(BaseModel):
    mood: int
    anxiety: int
    sleep: int
    hopelessness: int
    social_withdrawal: int
    self_harm_thoughts: int
    note: Annotated[str, StringConstraints(strict=True, max_length=4000)] | None = None

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value):
        if value is None:
            return None
        return value.strip() or None
