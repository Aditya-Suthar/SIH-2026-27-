"""Minimal current-owner identity for already-authorized case collections."""
from sqlalchemy import and_

from . import models

UNNAMED_VICTIM = "Unnamed Victim"


def victim_names(db, cases):
    """One projected outer join, regardless of case count; select only the name.

    Callers must scope cases before calling. Resolve the case owner, never an
    assessment author or assigned counsellor. Legacy/unowned cases stay visible.
    """
    ids = {case.id for case in cases}
    if not ids:
        return {}
    rows = db.query(models.Case.id, models.User.name).outerjoin(
        models.User,
        and_(models.Case.victim_id == models.User.id, models.User.role == 'victim'),
    ).filter(models.Case.id.in_(ids)).all()
    return {case_id: (name.strip() if name and name.strip() else UNNAMED_VICTIM)
            for case_id, name in rows}
