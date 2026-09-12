from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean, JSON, Date, DateTime, Float, CheckConstraint, Index, UniqueConstraint
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
    # Optional for legacy accounts; required before a victim starts questionnaire v2.
    date_of_birth = Column(Date, nullable=True)


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

    # One authoritative current distress/risk projection. Source records remain
    # immutable in assessments/ai_analyses; these columns only identify which
    # latest successful observation every dashboard should display.
    latest_distress_score = Column(Integer, nullable=True)
    latest_risk_source = Column(String(32), nullable=True)
    latest_state_at = Column(DateTime(timezone=True), nullable=True)
    # Logical source IDs. Kept without database FKs to avoid circular core-table
    # dependencies during additive upgrades of legacy schemas.
    latest_assessment_id = Column(Integer, nullable=True)
    latest_analysis_id = Column(Integer, nullable=True)
    legacy_risk_level = Column(String(20), nullable=True)

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


class QuestionnaireSession(Base):
    """Versioned adaptive selection and derived answers; legacy assessments remain intact."""
    __tablename__ = "questionnaire_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('pending','followup','completed')", name="ck_questionnaire_status"),
        Index("ix_questionnaire_victim_history", "victim_id", "created_at", "id"),
    )
    id = Column(String(36), primary_key=True)
    victim_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=True, unique=True)
    questionnaire_version = Column(String(16), nullable=False)
    scoring_version = Column(String(16), nullable=False)
    age_group = Column(String(8), nullable=False)
    selected_question_ids = Column(JSON, nullable=False)
    triggered_follow_up_ids = Column(JSON, nullable=False, default=list)
    answers = Column(JSON, nullable=False, default=dict)
    domain_scores = Column(JSON, nullable=True)
    questionnaire_score = Column(Float, nullable=True)
    safety_flags = Column(JSON, nullable=False, default=list)
    explanation = Column(JSON, nullable=True)
    status = Column(String(16), nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)


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
        CheckConstraint('(assessment_id IS NOT NULL AND message_id IS NULL) OR (assessment_id IS NULL AND message_id IS NOT NULL)', name='ck_ai_source'),
        Index('ix_ai_case_history', 'case_id', 'created_at', 'id'),
    )

    id = Column(Integer, primary_key=True)
    assessment_id = Column(Integer, ForeignKey('assessments.id'), nullable=True, unique=True)
    message_id = Column(Integer, ForeignKey('case_messages.id'), nullable=True, unique=True)
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


    @property
    def source_type(self):
        return 'message' if self.message_id is not None else 'assessment'


class CaseMessage(Base):
    __tablename__ = 'case_messages'
    __table_args__ = (
        UniqueConstraint('sender_id', 'client_message_id', name='uq_message_retry'),
        CheckConstraint("sender_role IN ('victim', 'counsellor')", name='ck_message_sender'),
        Index('ix_message_case_order', 'case_id', 'id'),
    )
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=False)
    victim_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    sender_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    sender_role = Column(String(16), nullable=False)
    client_message_id = Column(String(36), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class AnalysisReview(Base):
    __tablename__ = 'analysis_reviews'
    __table_args__ = (UniqueConstraint('analysis_id', 'reviewer_id', name='uq_analysis_reviewer'),)
    id = Column(Integer, primary_key=True)
    analysis_id = Column(Integer, ForeignKey('ai_analyses.id'), nullable=False)
    reviewer_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class MonitoringIndicator(Base):
    """Auditable, deduplicated human-review signal; never a support request."""
    __tablename__ = 'monitoring_indicators'
    __table_args__ = (UniqueConstraint('case_id', 'fingerprint', name='uq_monitoring_indicator_event'),
                      Index('ix_monitoring_indicator_queue', 'case_id', 'reviewed_at', 'created_at'))
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=False)
    source = Column(String(32), nullable=False)  # questionnaire, questionnaire_trend, text_ai
    severity = Column(String(16), nullable=False)
    fingerprint = Column(String(160), nullable=False)
    reason = Column(String(500), nullable=False)
    current_score = Column(Integer, nullable=True)
    trend = Column(String(32), nullable=True)
    analysis_id = Column(Integer, ForeignKey('ai_analyses.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    reviewed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)


class SupportSession(Base):
    __tablename__ = 'support_sessions'
    __table_args__ = (CheckConstraint("status IN ('Requested','Confirmed','Completed','Cancelled')", name='ck_session_status'),)
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=False, index=True)
    victim_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    counsellor_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=45)
    status = Column(String(16), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class SupportRequest(Base):
    __tablename__ = 'support_requests'
    __table_args__ = (CheckConstraint("status IN ('Open','Reviewed','Resolved')", name='ck_request_status'),)
    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey('cases.id'), nullable=False, index=True)
    victim_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    kind = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, default='Open')
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    reviewed_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
