from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import create_access_token
from app.database import get_db
from app.models import Customer
from app.notifications_channel import send_email
from app.schemas import (
    CustomerAuthOut,
    CustomerCreate,
    CustomerLoginRequest,
    CustomerOut,
    CustomerSignup,
    CustomerUpdate,
)
from app.security import hash_password, verify_password

router = APIRouter(prefix="/customers", tags=["customers"])


def _get_customer_or_404(db: Session, customer_id: int) -> Customer:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return customer


def _with_token(customer: Customer) -> CustomerAuthOut:
    return CustomerAuthOut(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        address=customer.address,
        access_token=create_access_token(subject=customer.id, kind="customer"),
    )


@router.post("/signup", response_model=CustomerAuthOut, status_code=201)
def signup(payload: CustomerSignup, db: Session = Depends(get_db)):
    customer = Customer(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        address=payload.address,
        password_hash=hash_password(payload.password),
    )
    db.add(customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="An account with this email already exists") from None
    db.refresh(customer)
    send_email(customer.email, "Welcome to Inventory & Order Management", f"Hi {customer.name}, your account is ready.")
    return _with_token(customer)


@router.post("/login", response_model=CustomerAuthOut)
def login(payload: CustomerLoginRequest, db: Session = Depends(get_db)):
    customer = db.execute(select(Customer).where(Customer.email == payload.email)).scalar_one_or_none()
    if customer is None or customer.password_hash is None or not verify_password(payload.password, customer.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _with_token(customer)


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Customer email already exists") from None
    db.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerOut])
def list_customers(
    response: Response,
    q: str | None = Query(default=None, description="filter by name or email"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = select(Customer)
    if q:
        stmt = stmt.where(Customer.name.ilike(f"%{q}%") | Customer.email.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total)

    rows = db.execute(stmt.order_by(Customer.id).offset(skip).limit(limit)).scalars().all()
    return rows


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    return _get_customer_or_404(db, customer_id)


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    customer = _get_customer_or_404(db, customer_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = _get_customer_or_404(db, customer_id)
    db.delete(customer)
    db.commit()
