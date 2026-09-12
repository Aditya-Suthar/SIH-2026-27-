"""Add questionnaire v2 storage without changing historical assessments."""
from sqlalchemy import inspect, text

from . import models
from .database import engine
from .migrate_case_state import upgrade as prior_upgrade


def upgrade(bind):
    prior_upgrade(bind)
    with bind.begin() as connection:
        user_columns = {column["name"] for column in inspect(connection).get_columns("users")}
        if "date_of_birth" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN date_of_birth DATE"))
        models.QuestionnaireSession.__table__.create(connection, checkfirst=True)


if __name__ == "__main__":
    upgrade(engine)
    print("Questionnaire v2 schema ready. Existing assessments were preserved.")
