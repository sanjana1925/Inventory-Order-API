from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, DeliveryAddress
from app.schemas import DeliveryAddressCreate, DeliveryAddressOut

router = APIRouter(prefix="/customers/{customer_id}/addresses", tags=["addresses"])


def _get_customer_or_404(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return customer


@router.get("", response_model=list[DeliveryAddressOut])
def list_addresses(customer_id: int, db: Session = Depends(get_db)):
    _get_customer_or_404(db, customer_id)
    return db.execute(
        select(DeliveryAddress).where(DeliveryAddress.customer_id == customer_id).order_by(DeliveryAddress.id)
    ).scalars().all()


@router.post("", response_model=DeliveryAddressOut, status_code=201)
def add_address(customer_id: int, payload: DeliveryAddressCreate, db: Session = Depends(get_db)):
    _get_customer_or_404(db, customer_id)

    if payload.is_default:
        db.execute(
            DeliveryAddress.__table__.update()
            .where(DeliveryAddress.customer_id == customer_id)
            .values(is_default=False)
        )

    address = DeliveryAddress(customer_id=customer_id, **payload.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


@router.delete("/{address_id}", status_code=204)
def delete_address(customer_id: int, address_id: int, db: Session = Depends(get_db)):
    address = db.execute(
        select(DeliveryAddress).where(DeliveryAddress.id == address_id, DeliveryAddress.customer_id == customer_id)
    ).scalar_one_or_none()
    if address is None:
        raise HTTPException(status_code=404, detail="Address not found")
    db.delete(address)
    db.commit()
