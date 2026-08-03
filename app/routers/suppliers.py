from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Supplier
from app.schemas import SupplierCreate, SupplierOut

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=list[SupplierOut])
def list_suppliers(
    response: Response,
    q: str | None = Query(default=None, description="filter by name"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = select(Supplier)
    if q:
        stmt = stmt.where(Supplier.name.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total)

    rows = db.execute(stmt.order_by(Supplier.name).offset(skip).limit(limit)).scalars().all()
    return rows


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db)):
    supplier = Supplier(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail=f"Supplier {supplier_id} not found")
    db.delete(supplier)
    db.commit()
