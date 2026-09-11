from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, JSON, DateTime, CheckConstraint, Index
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

    # Optional check-in text; stored once on its original assessment.
    note = Column(Text, nullable=True)


class AIAnalysis(Base):
    """One immutable historical result per submitted text check-in.

    Pending is committed with the source, before external inference starts.
    No source text, keys, provider payloads or exception details are duplicated.
    """
    __tablename__ = 'ai_analyses'
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed', 'failed')", name='ck_ai_status'),
        CheckConstraint('distress_score >= 0 AND distress_score <= 100', name='ck_ai_score'),
        CheckConstraint("risk_level IN ('low', 'medium', 'high', 'critical')", name='ck_ai_risk'),
        CheckConstraint("provider IN ('gemini', 'groq', 'openrouter')", name='ck_ai_provider'),
        CheckConstraint("(status = 'completed' AND distress_score IS NOT NULL "
                        "AND risk_level IS NOT NULL AND emotions IS NOT NULL "
                        "AND requires_attention IS NOT NULL AND reason IS NOT NULL "
                        "AND provider IS NOT NULL AND finished_at IS NOT NULL) OR "
                        "(status IN ('pending', 'failed') AND distress_score IS NULL "
                        "AND risk_level IS NULL AND emotions IS NULL "
                        "AND requires_attention IS NULL AND reason IS NULL AND provider IS NULL)",
                        name='ck_ai_result_state'),
        Index('ix_ai_case_history', 'case_id', 'created_at', 'id'),
    )

    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey('assessments.id'), nullable=False, unique=True)
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=False)
    victim_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    status = Column(String(16), nullable=False, default='pending')
    distress_score = Column(Integer, nullable=True)
    risk_level = Column(String(16), nullable=True)
    emotions = Column(JSON(none_as_null=True), nullable=True)
    requires_attention = Column(Boolean, nullable=True)
    reason = Column(String(400), nullable=True)
    provider = Column(String(16), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False,
                        default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime(timezone=True), nullable=True)
