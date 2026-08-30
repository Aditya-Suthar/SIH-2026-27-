from pydantic import BaseModel, EmailStr
from pydantic import BaseModel


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


class CaseOut(BaseModel):
    caseId: str
    riskLevel: str
    assignedCounsellor: str
    lastAssessment: str
    interventionStatus: str

    class Config:
        from_attributes = True

    class VictimDashboardOut(BaseModel):
        caseId: str
        riskLevel: str
        distressScore: int
        assignedCounsellor: str
        caseStage: str