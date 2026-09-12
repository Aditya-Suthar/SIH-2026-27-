"""Persist an existing check-in's AI result after its source transaction commits."""
import asyncio
from datetime import datetime, timezone, timedelta
import json
import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import ai_service, models
from .case_state import ensure_indicator, update_from_analysis

logger = logging.getLogger(__name__)
RESULT_FIELDS = ('distress_score', 'risk_level', 'emotions', 'requires_attention', 'reason', 'provider')


def fail_abandoned_analyses(db: Session) -> int:
    """Operator/scheduler maintenance, never invoked by GET.

    Providers have a combined 30-second deadline; ten minutes allows ample
    headroom before treating an interrupted worker as failed. The conditional
    update preserves every completed/failed result, even with concurrent workers.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    values = {name:None for name in RESULT_FIELDS}
    values.update(status='failed', finished_at=datetime.now(timezone.utc))
    changed = db.query(models.AIAnalysis).filter(
        models.AIAnalysis.status == 'pending', models.AIAnalysis.created_at < cutoff,
    ).update(values, synchronize_session=False)
    db.commit()
    return changed


def analyze_saved_check_in(db: Session, analysis_id: int, note: str) -> str:
    """Called in FastAPI's sync endpoint worker, never its event loop.

    No DB transaction is held during the external call. The source and a pending
    row are already durable. Return an honest status even if result storage fails.
    """
    values = None
    try:
        result = asyncio.run(ai_service.analyze_distress(note))
        payload = result.model_dump() if isinstance(result, BaseModel) else result
        result = ai_service.DistressResult.model_validate(payload)
        # Defense at the persistence boundary, including cross-field consistency.
        ai_service.parse_indicators(json.dumps(result.model_dump(exclude={'provider'})))
        values = result.model_dump()
    except ai_service.AIServiceUnavailable:
        logger.warning('ai_check_in category=service_unavailable')
    except Exception:
        # An unexpected AI failure must not invalidate an already-saved check-in.
        # Never log exception repr/traceback: it can contain text or credentials.
        logger.warning('ai_check_in category=invalid_or_failed_analysis')

    status = 'completed' if values is not None else 'failed'
    try:
        row = db.query(models.AIAnalysis).filter_by(id=analysis_id).with_for_update().populate_existing().first()
        if row is None:
            raise ValueError('Missing pending record')
        if row.status != 'pending':
            return row.status
        for name in RESULT_FIELDS:
            setattr(row, name, values[name] if values is not None else None)
        row.status = status
        row.finished_at = datetime.now(timezone.utc)
        if status == 'completed':
            db.flush()
            case = db.get(models.Case, row.case_id)
            if case is None:
                raise ValueError('Missing analysis case')
            update_from_analysis(case, row)
            ensure_indicator(db, case)
        db.commit()
        return status
    except Exception:
        db.rollback()
        logger.warning('ai_check_in category=result_storage_failed')
        # Try a clean failure update. If DB is still unavailable the committed
        # pending row remains an explicit incomplete analysis, never a fake score.
        try:
            row = db.get(models.AIAnalysis, analysis_id)
            if row is not None and row.status == 'pending':
                for name in RESULT_FIELDS:
                    setattr(row, name, None)
                row.status = 'failed'
                row.finished_at = datetime.now(timezone.utc)
                db.commit()
                return 'failed'
        except Exception:
            db.rollback()
            logger.warning('ai_check_in category=failure_state_storage_failed')
        return 'pending'
