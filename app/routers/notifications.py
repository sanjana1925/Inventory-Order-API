from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification
from app.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    audience: str = Query(..., pattern="^(admin|client)$"),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(Notification)
        .where(Notification.audience == audience)
        .order_by(Notification.id.desc())
        .limit(limit)
    ).scalars().all()
    return rows
