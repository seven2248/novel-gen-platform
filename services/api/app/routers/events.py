"""
Event log query API.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from services.api.app.models.event_log import EventLog
router = APIRouter(prefix="/events", tags=["events"])


def get_session():
    raise RuntimeError("Session not configured. Ensure session dependency is overridden in tests.")


@router.get("")
def list_events(
    project_id: str = Query(..., description="Project ID to filter events"),
    correlation_id: str | None = Query(None, description="Filter by correlation ID"),
    limit: int = Query(100, ge=1, le=1000, description="Max events to return"),
    session: Session = Depends(get_session),
) -> list[dict]:
    """
    Query event logs for a project, optionally filtered by correlation_id.

    Returns events ordered by id descending (most recent first).
    """
    try:
        if correlation_id:
            events = session.exec(
                select(EventLog)
                .where(
                    EventLog.project_id == project_id,
                    EventLog.correlation_id == correlation_id,
                )
                .order_by(EventLog.id.desc())
                .limit(limit)
            ).all()
        else:
            events = session.exec(
                select(EventLog)
                .where(EventLog.project_id == project_id)
                .order_by(EventLog.id.desc())
                .limit(limit)
            ).all()
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Database error") from exc

    return [e.to_dict() for e in events]
