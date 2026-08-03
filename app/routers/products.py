from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import OrderItem, Product, PurchaseOrderItem, QuoteItem
from app.schemas import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


def _get_product_or_404(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product


@router.get("/low-stock", response_model=list[ProductOut])
def low_stock(
    response: Response,
    threshold: int = Query(10, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = select(Product).where(Product.stock_qty < threshold)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total)
    products = db.execute(stmt.order_by(Product.stock_qty).limit(limit)).scalars().all()
    return products


@router.get("/categories", response_model=list[str])
def list_categories(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Product.category).where(Product.category.is_not(None)).distinct().order_by(Product.category)
    ).scalars().all()
    return rows


@router.post("", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    existing = db.execute(select(Product).where(Product.name == payload.name)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Product name already exists")

    product = Product(**payload.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Product name already exists") from None
    db.refresh(product)
    return product


@router.get("", response_model=list[ProductOut])
def list_products(
    response: Response,
    q: str | None = Query(default=None, description="filter by name"),
    category: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    stmt = select(Product)
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%"))
    if category:
        stmt = stmt.where(Product.category == category)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total)

    rows = db.execute(stmt.order_by(Product.id).offset(skip).limit(limit)).scalars().all()
    return rows


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return _get_product_or_404(db, product_id)


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    product = _get_product_or_404(db, product_id)
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        duplicate = db.execute(select(Product).where(Product.name == updates["name"])).scalar_one_or_none()
        if duplicate is not None and duplicate.id != product.id:
            raise HTTPException(status_code=400, detail="Product name already exists")

    for field, value in updates.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


def _referenced_elsewhere(db: Session, product_id: int) -> bool:
    for model in (OrderItem, QuoteItem, PurchaseOrderItem):
        if db.execute(select(model.id).where(model.product_id == product_id).limit(1)).scalar_one_or_none():
            return True
    return False


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = _get_product_or_404(db, product_id)
    if _referenced_elsewhere(db, product_id):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a product that appears on an existing order, quote, or purchase order",
        )
    db.delete(product)
    db.commit()
