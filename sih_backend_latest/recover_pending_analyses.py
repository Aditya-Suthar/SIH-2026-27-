"""Run once per minute by the deployment scheduler. No scores are generated."""
import json
from app.database import SessionLocal, engine
from app.ai_workflow import fail_abandoned_analyses

if __name__ == '__main__':
    try:
        if engine.url.get_backend_name() != 'postgresql':
            raise RuntimeError('Cloud PostgreSQL required')
        with SessionLocal() as db:
            print(json.dumps({'abandoned_attempts_marked_failed':fail_abandoned_analyses(db)}))
    except Exception as exc:
        print(json.dumps({'maintenance_error':type(exc).__name__}))
        raise SystemExit(1) from None
