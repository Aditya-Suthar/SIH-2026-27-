"""Add/backfill the authoritative case state without changing source history."""
from sqlalchemy import inspect, text

from .database import engine, SessionLocal
from . import models
from .case_state import current_state, ensure_indicator, update_from_analysis, update_from_assessment, utc
from .migrate_ai_prompt3 import upgrade as prior_upgrade


COLUMNS = {
    "latest_distress_score": "INTEGER",
    "latest_risk_source": "VARCHAR(32)",
    "latest_state_at": "TIMESTAMP WITH TIME ZONE",
    "latest_assessment_id": "INTEGER",
    "latest_analysis_id": "INTEGER",
    "legacy_risk_level": "VARCHAR(20)",
}


def add_columns(bind):
    with bind.begin() as connection:
        existing = {column["name"] for column in inspect(connection).get_columns("cases")}
        for name, sql_type in COLUMNS.items():
            if name not in existing:
                if connection.dialect.name == "sqlite" and sql_type == "TIMESTAMP WITH TIME ZONE":
                    sql_type = "DATETIME"
                connection.execute(text(f"ALTER TABLE cases ADD COLUMN {name} {sql_type}"))


def newest_source(db, case):
    assessment = db.query(models.Assessment).filter_by(case_id=case.id).order_by(
        models.Assessment.id.desc()
    ).first()
    analysis = db.query(models.AIAnalysis).filter_by(case_id=case.id, status="completed").filter(
        models.AIAnalysis.distress_score.is_not(None), models.AIAnalysis.risk_level.is_not(None)
    ).order_by(models.AIAnalysis.created_at.desc(), models.AIAnalysis.id.desc()).first()
    assessment_time = utc(assessment.created_at) if assessment else None
    analysis_time = utc(analysis.finished_at or analysis.created_at) if analysis else None
    if analysis is not None and (assessment_time is None or analysis_time >= assessment_time):
        return "analysis", analysis
    if assessment is not None:
        return "assessment", assessment
    return None, None


def backfill(bind):
    session = SessionLocal(bind=bind)
    try:
        for case in session.query(models.Case).order_by(models.Case.id):
            if case.legacy_risk_level is None:
                case.legacy_risk_level = case.risk_level
            if case.latest_risk_source is None:
                kind, source = newest_source(session, case)
                if kind == "analysis":
                    update_from_analysis(case, source)
                elif kind == "assessment":
                    update_from_assessment(case, source)
                else:
                    # Preserve the pre-existing case value as an explicit legacy
                    # current state. No score or timestamp is invented.
                    state = current_state(case)
                    if state["risk"] is not None:
                        case.latest_risk_source = "legacy_case"
            session.flush()
            ensure_indicator(session, case)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upgrade(bind):
    prior_upgrade(bind)
    models.Base.metadata.create_all(bind)
    add_columns(bind)
    backfill(bind)


if __name__ == "__main__":
    try:
        upgrade(engine)
    except Exception:
        raise SystemExit("Case-state migration failed. Check connectivity and migration permissions.") from None
    print("Authoritative case state ready. Existing assessments, AI history and legacy risk values preserved.")
