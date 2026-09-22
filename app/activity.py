from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Notification


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def notify(db: Session, audience: str, message: str, level: str = "info", order_id: int | None = None) -> None:
    """Added to the session but not committed — callers include it in
    whatever transaction is already in progress."""
    db.add(Notification(audience=audience, message=message, level=level, order_id=order_id, created_at=_now()))
