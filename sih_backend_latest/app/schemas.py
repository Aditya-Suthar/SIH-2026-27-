from datetime import date
from typing import Annotated
from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, Field, field_validator


class VictimDashboardOut(BaseModel):
    caseId: str
    riskLevel: str
    distressScore: int | None
    historicalScore: float | None = None
    recentTrend: str | None = None
    recentScores: list[dict] = Field(default_factory=list)
    assignedCounsellor: str
    caseStage: str
    dateOfBirth: date | None = None


class UserRegister(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    email: EmailStr
    password: Annotated[str, StringConstraints(min_length=8, max_length=72)]
    role: str
    date_of_birth: date | None = None


    @field_validator("password")
    @classmethod
    def password_bytes(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must fit within 72 UTF-8 bytes")
        return value

    @field_validator("date_of_birth")
    @classmethod
    def supported_birth_date(cls, value):
        if value is None:
            return None
        from .questionnaire_engine import age_on
        if not 13 <= age_on(value) <= 120:
            raise ValueError("Victim age must be between 13 and 120")
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
    victimName: str
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


class VictimProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date_of_birth: date

    @field_validator("date_of_birth")
    @classmethod
    def supported_birth_date(cls, value):
        from .questionnaire_engine import age_on
        if not 13 <= age_on(value) <= 120:
            raise ValueError("Victim age must be between 13 and 120")
        return value


class QuestionnaireSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questionnaire_id: str = Field(min_length=36, max_length=36)
    answers: dict[str, int] = Field(default_factory=dict, max_length=20)
    note: Annotated[str, StringConstraints(strict=True, max_length=4000)] | None = None

    @field_validator("note")
    @classmethod
    def normalize_questionnaire_note(cls, value):
        return value.strip() or None if value is not None else None


class QuestionnaireSafetySignal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questionnaire_id: str = Field(min_length=36, max_length=36)
    question_id: str = Field(pattern=r"^Q\d{3}$")
    answer: int
