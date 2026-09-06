from sqlalchemy import Column, Integer, String, ForeignKey
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )

    password_hash = Column(String(255), nullable=False)

    role = Column(String(20), nullable=False)


class Case(Base):

    victim_id = Column(
    Integer,
    ForeignKey("users.id"),
    nullable=True,
    index=True,
)
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(String(50), unique=True, index=True, nullable=False)

    risk_level = Column(String(20), nullable=False)

    assigned_counsellor = Column(String(100), nullable=False)

    # Stable reference to the counsellor's user record, used for filtering.
    # assigned_counsellor (above) stays as the free-text display name so
    # existing response formatting doesn't change; this new column is what
    # makes "cases assigned to the logged-in counsellor" reliable instead of
    # matching on a name string.
    assigned_counsellor_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    last_assessment = Column(String(50), nullable=False)

    intervention_status = Column(String(100), nullable=False)

    district = Column(String(100), nullable=False)

    state = Column(String(100), nullable=False)

class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)

    case_id = Column(
        Integer,
        ForeignKey("cases.id"),
        nullable=False,
        index=True,
    )

    mood = Column(Integer, nullable=False)
    anxiety = Column(Integer, nullable=False)
    sleep = Column(Integer, nullable=False)
    hopelessness = Column(Integer, nullable=False)
    social_withdrawal = Column(Integer, nullable=False)
    self_harm_thoughts = Column(Integer, nullable=False)

    distress_score = Column(Integer, nullable=False)

    risk_level = Column(String(20), nullable=False)

    created_at = Column(String(50), nullable=False)