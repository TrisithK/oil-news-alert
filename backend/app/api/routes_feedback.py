"""Submit useful / noise / missed feedback on an alert."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import Alert, User
from app.schemas.api import FeedbackIn, FeedbackOut
from worker.alerting.feedback import record_feedback

router = APIRouter(prefix="/api", tags=["feedback"])


@router.post("/feedback", response_model=FeedbackOut, status_code=201)
def post_feedback(
    payload: FeedbackIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FeedbackOut:
    if db.get(Alert, payload.alert_id) is None:
        raise HTTPException(status_code=404, detail="alert not found")
    try:
        feedback = record_feedback(
            db, alert_id=payload.alert_id, label=payload.label, user_id=user.id, note=payload.note
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FeedbackOut(
        id=feedback.id,
        alert_id=feedback.alert_id,
        label=feedback.label,
        note=feedback.note,
        created_at=feedback.created_at,
    )
