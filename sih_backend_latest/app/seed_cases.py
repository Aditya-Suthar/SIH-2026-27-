"""
Development seed script for GET /api/cases testing.

WHAT THIS DOES
- Ensures three demo counsellor accounts exist (get-or-create, so it's safe
  to run more than once).
- Generates ~45 fully fictional cases distributed across those counsellors:
    Counsellor A -> 10 cases
    Counsellor B -> 20 cases
    Counsellor C -> 15 cases
- Uses deterministic case_id values and skips any case_id that already
  exists, so re-running this script does not create duplicates.

WHAT THIS DOES NOT DO
- No new API endpoint.
- No changes to authentication logic (it reuses the existing password
  hashing context from app.auth).
- No frontend changes.

HOW TO RUN
From the `sih_backend` directory (the one containing the `app` folder and
requirements.txt), with your virtualenv active and Postgres reachable:

    python -m app.seed_cases

Run it again any time — it will not duplicate users or cases.
"""

import random

from .database import SessionLocal, engine, Base
from .auth import pwd_context
from . import models

# Make sure tables (including the new district/state/assigned_counsellor_id
# columns) exist before we try to seed. NOTE: if you already had a `cases`
# table from before this change, create_all() will NOT add the new columns
# to it -- you need to drop that old table once first. See the chat message
# for the exact command.
Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Demo counsellor accounts (fictional). Fixed password so it's easy to log
# into Swagger and test filtering per counsellor.
# ---------------------------------------------------------------------------
DEMO_PASSWORD = "Counsellor@123"

COUNSELLORS = [
    {"key": "A", "name": "Dr. Meera Sharma", "email": "counsellor.a@example.com", "count": 10},
    {"key": "B", "name": "Dr. Arjun Verma", "email": "counsellor.b@example.com", "count": 20},
    {"key": "C", "name": "Dr. Priya Nair", "email": "counsellor.c@example.com", "count": 15},
]

RISK_LEVELS = ["Critical", "High", "Moderate", "Low"]

INTERVENTION_STATUS_BY_RISK = {
    "Critical": ["Immediate Action", "Under Observation"],
    "High": ["Under Observation", "Pending Review"],
    "Moderate": ["Routine Follow-up", "Pending Review"],
    "Low": ["Routine Follow-up", "Case Closed"],
}

LAST_ASSESSMENT_OPTIONS = [
    "Today", "Yesterday", "2 days ago", "3 days ago",
    "1 week ago", "2 weeks ago", "3 weeks ago",
]

# A handful of districts/states so location-based filtering can be added
# later. All fictional pairings, not tied to any real case.
LOCATIONS = [
    ("Kurukshetra", "Haryana"),
    ("Rohtak", "Haryana"),
    ("Panipat", "Haryana"),
    ("Gurugram", "Haryana"),
    ("Ambala", "Haryana"),
    ("Ludhiana", "Punjab"),
    ("Amritsar", "Punjab"),
    ("Patiala", "Punjab"),
    ("Jaipur", "Rajasthan"),
    ("Udaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"),
    ("Kanpur", "Uttar Pradesh"),
    ("Shimla", "Himachal Pradesh"),
    ("Dehradun", "Uttarakhand"),
    ("Chandigarh", "Chandigarh"),
]


def get_or_create_counsellor(db, name: str, email: str) -> models.User:
    user = db.query(models.User).filter(models.User.email == email).first()
    if user:
        return user

    user = models.User(
        name=name,
        email=email,
        password_hash=pwd_context.hash(DEMO_PASSWORD),
        role="counsellor",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_cases_for_counsellor(db, counsellor: models.User, key: str, count: int):
    created = 0
    skipped = 0

    for i in range(1, count + 1):
        case_id = f"SAH-{key}-{i:04d}"

        exists = db.query(models.Case).filter(
            models.Case.case_id == case_id
        ).first()

        if exists:
            skipped += 1
            continue

        risk_level = random.choice(RISK_LEVELS)
        district, state = random.choice(LOCATIONS)

        case = models.Case(
            case_id=case_id,
            risk_level=risk_level,
            assigned_counsellor=counsellor.name,
            assigned_counsellor_id=counsellor.id,
            last_assessment=random.choice(LAST_ASSESSMENT_OPTIONS),
            intervention_status=random.choice(
                INTERVENTION_STATUS_BY_RISK[risk_level]
            ),
            district=district,
            state=state,
        )

        db.add(case)
        created += 1

    db.commit()
    return created, skipped


def main():
    db = SessionLocal()

    try:
        print("Seeding demo counsellor accounts...")
        counsellor_users = {}

        for c in COUNSELLORS:
            user = get_or_create_counsellor(db, c["name"], c["email"])
            counsellor_users[c["key"]] = user
            print(f"  Counsellor {c['key']}: {c['name']} <{c['email']}> (id={user.id})")

        print("\nSeeding fictional cases...")
        total_created = 0
        total_skipped = 0

        for c in COUNSELLORS:
            user = counsellor_users[c["key"]]
            created, skipped = seed_cases_for_counsellor(
                db, user, c["key"], c["count"]
            )
            total_created += created
            total_skipped += skipped
            print(
                f"  Counsellor {c['key']} ({user.name}): "
                f"{created} created, {skipped} already existed"
            )

        print(
            f"\nDone. {total_created} new cases created, "
            f"{total_skipped} already present (skipped)."
        )
        print(f"\nDemo login password for all seeded counsellors: {DEMO_PASSWORD}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
