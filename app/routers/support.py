from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SupportMessage, SupportStatus
from app.schemas import SupportMessageCreate, SupportMessageOut

router = APIRouter(prefix="/support", tags=["support"])


@router.post("", response_model=SupportMessageOut, status_code=201)
def create_support_message(payload: SupportMessageCreate, db: Session = Depends(get_db)):
    message = SupportMessage(
        **payload.model_dump(),
        status=SupportStatus.OPEN,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("", response_model=list[SupportMessageOut])
def list_support_messages(
    status: SupportStatus | None = None,
    customer: str | None = Query(default=None, description="admin search: fuzzy match on customer name"),
    customer_id: int | None = Query(default=None, description="exact match: use for a client's own messages"),
    db: Session = Depends(get_db),
):
    stmt = select(SupportMessage)
    if status is not None:
        stmt = stmt.where(SupportMessage.status == status)
    if customer:
        stmt = stmt.where(SupportMessage.customer_name.ilike(f"%{customer}%"))
    if customer_id is not None:
        stmt = stmt.where(SupportMessage.customer_id == customer_id)
    return db.execute(stmt.order_by(SupportMessage.id.desc())).scalars().all()


@router.post("/{message_id}/close", response_model=SupportMessageOut)
def close_support_message(message_id: int, db: Session = Depends(get_db)):
    message = db.get(SupportMessage, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail=f"Support message {message_id} not found")
    message.status = SupportStatus.CLOSED
    db.commit()
    db.refresh(message)
    return message
