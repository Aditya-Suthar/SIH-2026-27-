"""Safely seed idempotent questionnaire history for three existing demo victims.

Dry-run is the default. Pass --execute to commit the exact proposed records.
This utility never creates users, cases, or AIAnalysis rows and never edits or
deletes an existing Assessment.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from . import models
from .cases import calculate_distress_score, historical_distress
from .database import SessionLocal, engine
from .schemas import AssessmentCreate


SEED_VERSION = "SYNTHETIC_DEMO_HISTORY_V1"
ADVISORY_LOCK_KEY = 26094001


@dataclass(frozen=True)
class DemoPlan:
    trend: str
    email: str
    case_id: str
    answers: tuple[tuple[int, int, int, int, int, int], ...]


PLANS = (
    DemoPlan(
        "RISING",
        "victim10@sahas.demo",
        "SAH-8839C2090E8C",
        ((1, 1, 1, 1, 1, 1), (2, 2, 2, 2, 1, 1), (3, 3, 2, 2, 2, 2)),
    ),
    DemoPlan(
        "FALLING",
        "victim11@sahas.demo",
        "SAH-9D0CC12642A6",
        ((4, 4, 4, 3, 2, 1), (3, 3, 2, 2, 2, 2), (2, 2, 2, 2, 1, 1)),
    ),
    DemoPlan(
        "STABLE",
        "victim14@sahas.demo",
        "SAH-DD11F3E02A3E",
        ((2, 2, 2, 2, 1, 1), (2, 2, 2, 2, 2, 1), (2, 2, 2, 2, 1, 1)),
    ),
)


def marker(plan: DemoPlan, number: int) -> str:
    return f"{SEED_VERSION}:{plan.trend}:{number}"


def assessment_input(values: tuple[int, int, int, int, int, int]) -> AssessmentCreate:
    return AssessmentCreate(
        mood=values[0], anxiety=values[1], sleep=values[2], hopelessness=values[3],
        social_withdrawal=values[4], self_harm_thoughts=values[5], note=None,
    )


def normalized_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=value.tzinfo or timezone.utc).astimezone(timezone.utc)


def expected_rows(plan: DemoPlan, anchor: datetime) -> list[dict]:
    rows: list[dict] = []
    chronological_scores: list[int] = []
    for index, values in enumerate(plan.answers, start=1):
        data = assessment_input(values)
        # calculate_distress_score expects prior history newest-to-oldest.
        history = [{"score": score, "created_at": "synthetic"}
                   for score in reversed(chronological_scores)]
        score, risk, _ = calculate_distress_score(data, history)
        rows.append({
            "marker": marker(plan, index),
            "created_at": anchor + timedelta(hours=24 * (index - 1)),
            "values": values,
            "score": score,
            "risk": risk,
        })
        chronological_scores.append(score)
    return rows


def row_matches(row: models.Assessment, expected: dict) -> bool:
    actual_values = (
        row.mood, row.anxiety, row.sleep, row.hopelessness,
        row.social_withdrawal, row.self_harm_thoughts,
    )
    try:
        actual_time = normalized_utc(datetime.fromisoformat(row.created_at.replace("Z", "+00:00")))
    except (AttributeError, TypeError, ValueError):
        return False
    return (
        row.note == expected["marker"]
        and actual_values == expected["values"]
        and row.distress_score == expected["score"]
        and row.risk_level == expected["risk"]
        and actual_time == expected["created_at"]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Commit missing records; default is dry-run.")
    args = parser.parse_args()

    if engine.dialect.name != "postgresql":
        raise SystemExit("REFUSED: this seed utility only runs against configured PostgreSQL.")

    mode = "EXECUTE" if args.execute else "DRY-RUN"
    total_missing = 0
    summaries: list[tuple[models.Case, dict, list[dict]]] = []

    with SessionLocal() as db:
        with db.begin():
            db.execute(text("select pg_advisory_xact_lock(:key)"), {"key": ADVISORY_LOCK_KEY})
            database_now = normalized_utc(db.execute(text("select current_timestamp")).scalar_one())

            for plan in PLANS:
                user = db.query(models.User).filter_by(email=plan.email, role="victim").one_or_none()
                if user is None or user.name != f"Demo Victim {plan.email[6:8]}":
                    raise SystemExit(f"REFUSED: exact demo victim identity mismatch for {plan.email}.")
                case = db.query(models.Case).filter_by(victim_id=user.id, case_id=plan.case_id).one_or_none()
                if case is None:
                    raise SystemExit(f"REFUSED: exact case identity mismatch for {plan.email}.")

                existing = db.query(models.Assessment).filter_by(case_id=case.id).order_by(models.Assessment.id).all()
                allowed_markers = {marker(plan, number) for number in range(1, 4)}
                foreign = [row for row in existing if row.note not in allowed_markers]
                if foreign:
                    raise SystemExit(
                        f"REFUSED: {plan.email} / {plan.case_id} has {len(foreign)} non-seed assessment(s)."
                    )
                by_marker = {row.note: row for row in existing}
                if len(by_marker) != len(existing):
                    raise SystemExit(f"REFUSED: duplicate seed markers already exist for {plan.email}.")

                if existing:
                    first = by_marker.get(marker(plan, 1))
                    if first is None:
                        raise SystemExit(f"REFUSED: partial seed lacks the first anchor for {plan.email}.")
                    anchor = normalized_utc(datetime.fromisoformat(first.created_at.replace("Z", "+00:00")))
                else:
                    anchor = database_now - timedelta(hours=72)

                expected = expected_rows(plan, anchor)
                missing: list[dict] = []
                for item in expected:
                    found = by_marker.get(item["marker"])
                    if found is None:
                        missing.append(item)
                    elif not row_matches(found, item):
                        raise SystemExit(f"REFUSED: existing marker content differs: {item['marker']}.")

                total_missing += len(missing)
                summaries.append((case, expected[-1], expected))
                print(f"{plan.trend}: {user.name} | {plan.email} | {case.case_id}")
                for item in expected:
                    action = "INSERT" if item in missing else "EXISTS"
                    print(
                        f"  {action} {item['marker']} | {item['created_at'].isoformat()} | "
                        f"answers={item['values']} | score={item['score']} | risk={item['risk']}"
                    )

                if args.execute:
                    for item in missing:
                        values = item["values"]
                        db.add(models.Assessment(
                            case_id=case.id,
                            mood=values[0], anxiety=values[1], sleep=values[2],
                            hopelessness=values[3], social_withdrawal=values[4],
                            self_harm_thoughts=values[5], distress_score=item["score"],
                            risk_level=item["risk"], created_at=item["created_at"].isoformat(),
                            note=item["marker"],
                        ))

            if args.execute:
                db.flush()
                # Mirror only the normal assessment submission's case summary updates.
                for case, latest, _ in summaries:
                    case.risk_level = latest["risk"]
                    case.last_assessment = latest["created_at"].strftime("%Y-%m-%d %H:%M")

                ai_count = db.query(models.AIAnalysis).filter(
                    models.AIAnalysis.case_id.in_([case.id for case, _, _ in summaries])
                ).count()
                if ai_count:
                    raise SystemExit("REFUSED: selected cases unexpectedly contain AIAnalysis records.")

        print(f"MODE={mode} missing_records={total_missing}")
        if args.execute:
            print(f"COMMITTED inserted_records={total_missing}; AIAnalysis records created=0")
        else:
            print("No database writes performed.")


if __name__ == "__main__":
    main()
