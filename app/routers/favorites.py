from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Favorite, Product
from app.schemas import FavoriteCreate, FavoriteOut

router = APIRouter(prefix="/favorites", tags=["favorites"])


def _serialize(favorite: Favorite) -> FavoriteOut:
    return FavoriteOut(
        id=favorite.id,
        customer_id=favorite.customer_id,
        product_id=favorite.product_id,
        product_name=favorite.product.name,
        list_name=favorite.list_name,
        created_at=favorite.created_at,
    )


@router.post("", response_model=FavoriteOut, status_code=201)
def add_favorite(payload: FavoriteCreate, db: Session = Depends(get_db)):
    if db.get(Product, payload.product_id) is None:
        raise HTTPException(status_code=400, detail=f"Product {payload.product_id} not found")

    favorite = Favorite(
        customer_id=payload.customer_id,
        product_id=payload.product_id,
        list_name=payload.list_name,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(favorite)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Product is already saved in that list") from None
    db.refresh(favorite, attribute_names=["product"])
    return _serialize(favorite)


@router.get("", response_model=list[FavoriteOut])
def list_favorites(
    response: Response,
    customer_id: int = Query(...),
    list_name: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(Favorite).where(Favorite.customer_id == customer_id)
    if list_name:
        stmt = stmt.where(Favorite.list_name == list_name)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    response.headers["X-Total-Count"] = str(total)

    stmt = stmt.options(selectinload(Favorite.product)).order_by(Favorite.id.desc()).offset(skip).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [_serialize(f) for f in rows]


@router.get("/lists", response_model=list[str])
def list_favorite_lists(customer_id: int = Query(...), db: Session = Depends(get_db)):
    """Distinct list_name values for a customer — lets the UI show 'which lists do I have'."""
    return db.execute(
        select(Favorite.list_name)
        .where(Favorite.customer_id == customer_id)
        .distinct()
        .order_by(Favorite.list_name)
    ).scalars().all()


@router.delete("/{favorite_id}", status_code=204)
def delete_favorite(favorite_id: int, db: Session = Depends(get_db)):
    favorite = db.get(Favorite, favorite_id)
    if favorite is None:
        raise HTTPException(status_code=404, detail=f"Favorite {favorite_id} not found")
    db.delete(favorite)
    db.commit()
