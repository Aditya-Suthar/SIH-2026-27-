"""Run once before workers: python -m app.migrate_ai_prompt3. Preserves history."""
from sqlalchemy import inspect, text, MetaData
from .database import engine
from . import models
from .migrate_ai_prompt2 import upgrade as upgrade_prompt2


def upgrade(bind):
    if {'users', 'cases', 'assessments'}.issubset(inspect(bind).get_table_names()):
        models.CaseMessage.__table__.create(bind, checkfirst=True)
    upgrade_prompt2(bind)
    with bind.begin() as conn:
        models.CaseMessage.__table__.create(conn, checkfirst=True)
        columns = {c['name'] for c in inspect(conn).get_columns('ai_analyses')}
        if 'message_id' not in columns:
            if conn.dialect.name == 'postgresql':
                conn.execute(text('ALTER TABLE ai_analyses ALTER COLUMN assessment_id DROP NOT NULL'))
                conn.execute(text('ALTER TABLE ai_analyses ADD COLUMN message_id INTEGER UNIQUE REFERENCES case_messages(id)'))
                conn.execute(text('ALTER TABLE ai_analyses ADD CONSTRAINT ck_ai_source CHECK ((assessment_id IS NOT NULL AND message_id IS NULL) OR (assessment_id IS NULL AND message_id IS NOT NULL))'))
            elif conn.dialect.name == 'sqlite':
                # SQLite needs a table rebuild to relax NOT NULL. Copy before drop.
                meta = MetaData()
                for table in models.Base.metadata.sorted_tables:
                    if table.name not in ('ai_analyses', 'analysis_reviews'):
                        table.to_metadata(meta)
                replacement = models.AIAnalysis.__table__.to_metadata(meta, name='ai_analyses_prompt3_new')
                replacement.indexes.clear()  # Old named indexes exist until old table is dropped.
                replacement.create(conn)
                names = ', '.join(sorted(columns))
                conn.execute(text(f'INSERT INTO ai_analyses_prompt3_new ({names}) SELECT {names} FROM ai_analyses'))
                conn.execute(text('DROP TABLE ai_analyses'))
                conn.execute(text('ALTER TABLE ai_analyses_prompt3_new RENAME TO ai_analyses'))
                for index in models.AIAnalysis.__table__.indexes:
                    index.create(conn)
            else:
                raise RuntimeError('Unsupported database dialect')
        models.AnalysisReview.__table__.create(conn, checkfirst=True)


if __name__ == '__main__':
    try:
        upgrade(engine)
    except Exception:
        raise SystemExit('Prompt 3 migration failed. Check connectivity and migration permissions.') from None
    print('Prompt 3 schema ready. Existing messages and AI history preserved.')
