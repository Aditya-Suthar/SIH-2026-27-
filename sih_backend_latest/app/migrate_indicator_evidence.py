"""Link indicators to source records and repair partial-score duplicates."""
import re

from sqlalchemy import inspect, text

from . import models
from .database import engine, SessionLocal
from .migrate_questionnaire_v2 import upgrade as prior_upgrade


QUESTIONNAIRE_FINGERPRINT = re.compile(r"^authoritative:questionnaire:(\d+)(?::.*)?$")


def add_columns(bind):
    with bind.begin() as connection:
        tables = set(inspect(connection).get_table_names())
        if "monitoring_indicators" in tables:
            columns = {column["name"] for column in inspect(connection).get_columns("monitoring_indicators")}
            if "assessment_id" not in columns:
                connection.execute(text("ALTER TABLE monitoring_indicators ADD COLUMN assessment_id INTEGER"))
        # PostgreSQL can make the partial safety-state distinction explicit on
        # upgraded databases. Fresh SQLite databases use the nullable model.
        if connection.dialect.name == "postgresql" and "assessments" in tables:
            connection.execute(text("ALTER TABLE assessments ALTER COLUMN distress_score DROP NOT NULL"))


def repair(bind):
    with bind.connect() as connection:
        if "monitoring_indicators" not in inspect(connection).get_table_names():
            return
    session = SessionLocal(bind=bind)
    try:
        questionnaire_rows = session.query(models.MonitoringIndicator).filter_by(source="questionnaire").order_by(
            models.MonitoringIndicator.case_id, models.MonitoringIndicator.id
        ).all()
        grouped = {}
        for row in questionnaire_rows:
            match = QUESTIONNAIRE_FINGERPRINT.match(row.fingerprint or "")
            if row.assessment_id is None and match:
                assessment_id = int(match.group(1))
                assessment = session.get(models.Assessment, assessment_id)
                if assessment is not None and assessment.case_id == row.case_id:
                    row.assessment_id = assessment_id
            if row.assessment_id is not None:
                grouped.setdefault((row.case_id, row.assessment_id), []).append(row)

        for (_, assessment_id), rows in grouped.items():
            assessment = session.get(models.Assessment, assessment_id)
            if assessment is None:
                continue
            matching = [row for row in rows if row.current_score == assessment.distress_score]
            keep = max(matching or rows, key=lambda row: row.id)
            for row in rows:
                if row is not keep:
                    session.delete(row)
            session.flush()
            keep.current_score = assessment.distress_score
            keep.fingerprint = f"authoritative:questionnaire:{assessment.id}"
            if keep.severity == "URGENT" and assessment.self_harm_thoughts >= 3:
                keep.reason = "Critical safety override triggered by the questionnaire response."
            else:
                score = f" ({assessment.distress_score}/100)" if assessment.distress_score is not None else ""
                keep.reason = f"Current authoritative risk is {assessment.risk_level}{score}."

        for row in session.query(models.MonitoringIndicator).filter_by(source="text_ai"):
            if row.analysis_id is not None:
                row.fingerprint = f"authoritative:text_ai:{row.analysis_id}"
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def upgrade(bind):
    # The previous migration's backfill imports the current model, so an old
    # indicators table needs this additive column before that code can query it.
    add_columns(bind)
    repair(bind)
    prior_upgrade(bind)
    models.Base.metadata.create_all(bind)
    add_columns(bind)
    repair(bind)


if __name__ == "__main__":
    upgrade(engine)
    print("Monitoring evidence schema ready; source links and snapshots repaired.")
