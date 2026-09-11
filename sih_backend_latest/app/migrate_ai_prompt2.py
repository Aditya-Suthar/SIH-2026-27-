"""Additive, repeatable schema upgrade. Run: python -m app.migrate_ai_prompt2.

Run once before starting app workers. Never drops tables or modifies old scores.
Supports the project's PostgreSQL and SQLite (for isolated migration tests).
"""
from sqlalchemy import inspect, text
from .database import Base, engine
from . import models


def upgrade(bind):
    with bind.begin() as connection:
        tables = set(inspect(connection).get_table_names())
        required = {'users', 'cases', 'assessments'}
        if not tables:
            Base.metadata.create_all(bind=connection)
            return
        if not required.issubset(tables):
            raise RuntimeError('Existing core schema is incomplete; restore its migrations first.')
        columns = {col['name'] for col in inspect(connection).get_columns('assessments')}
        if 'note' not in columns:
            connection.execute(text('ALTER TABLE assessments ADD COLUMN note TEXT'))
        models.AIAnalysis.__table__.create(bind=connection, checkfirst=True)


if __name__ == '__main__':
    try:
        upgrade(engine)
    except Exception:
        # Connection exceptions can expose the existing hardcoded DB credentials.
        raise SystemExit('AI Prompt 2 migration failed. Check database connectivity and schema permissions.') from None
    print('AI Prompt 2 schema is ready. Existing assessment data is preserved.')
