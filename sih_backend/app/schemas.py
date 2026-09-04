from pydantic import BaseModel, EmailStr


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