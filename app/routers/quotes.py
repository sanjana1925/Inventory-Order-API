from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import Order, OrderItem, OrderStatus, Product, Quote, QuoteItem, QuoteStatus
from app.schemas import QuoteCreate, QuoteItemOut, QuoteOut, QuotePriceUpdate

router = APIRouter(prefix="/quotes", tags=["quotes"])


def _serialize(quote: Quote) -> QuoteOut:
    items_out = [
        QuoteItemOut(
            product_id=item.product_id,
            product_name=item.product.name,
            quantity=item.quantity,
            quoted_unit_price=item.quoted_unit_price,
        )
        for item in quote.items
    ]
    return QuoteOut(
        id=quote.id,
        customer_name=quote.customer_name,
        customer_id=quote.customer_id,
        status=quote.status,
        created_at=quote.created_at,
        order_id=quote.order_id,
        items=items_out,
    )


def _get_or_404(db: Session, quote_id: int) -> Quote:
    quote = db.execute(
        select(Quote)
        .where(Quote.id == quote_id)
        .options(selectinload(Quote.items).selectinload(QuoteItem.product))
    ).scalar_one_or_none()
    if quote is None:
        raise HTTPException(status_code=404, detail=f"Quote {quote_id} not found")
    return quote


@router.post("", response_model=QuoteOut, status_code=201)
def request_quote(payload: QuoteCreate, db: Session = Depends(get_db)):
    product_ids = {line.product_id for line in payload.items}
    known_ids = set(db.execute(select(Product.id).where(Product.id.in_(product_ids))).scalars().all())
    unknown = product_ids - known_ids
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown product id(s): {sorted(unknown)}")

    quote = Quote(
        customer_name=payload.customer_name,
        customer_id=payload.customer_id,
        status=QuoteStatus.REQUESTED,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    for line in payload.items:
        quote.items.append(QuoteItem(product_id=line.product_id, quantity=line.quantity))

    db.add(quote)
    db.commit()
    return _serialize(_get_or_404(db, quote.id))


@router.get("", response_model=list[QuoteOut])
def list_quotes(
    customer: str | None = Query(default=None, description="admin search: fuzzy match on customer name"),
    customer_id: int | None = Query(default=None, description="exact match: use for a client's own quotes"),
    status: QuoteStatus | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Quote).options(selectinload(Quote.items).selectinload(QuoteItem.product))
    if customer:
        stmt = stmt.where(Quote.customer_name.ilike(f"%{customer}%"))
    if customer_id is not None:
        stmt = stmt.where(Quote.customer_id == customer_id)
    if status is not None:
        stmt = stmt.where(Quote.status == status)
    rows = db.execute(stmt.order_by(Quote.id.desc())).scalars().all()
    return [_serialize(q) for q in rows]


@router.get("/{quote_id}", response_model=QuoteOut)
def get_quote(quote_id: int, db: Session = Depends(get_db)):
    return _serialize(_get_or_404(db, quote_id))


@router.patch("/{quote_id}/price", response_model=QuoteOut, dependencies=[Depends(get_current_user)])
def price_quote(quote_id: int, payload: QuotePriceUpdate, db: Session = Depends(get_db)):
    quote = _get_or_404(db, quote_id)
    if quote.status != QuoteStatus.REQUESTED:
        raise HTTPException(status_code=400, detail=f"Quote is '{quote.status.value}', not awaiting pricing")

    prices_by_product = {p.product_id: p.quoted_unit_price for p in payload.items}
    missing = {item.product_id for item in quote.items} - set(prices_by_product)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing price for product id(s): {sorted(missing)}")

    for item in quote.items:
        item.quoted_unit_price = prices_by_product[item.product_id]
    quote.status = QuoteStatus.QUOTED

    db.commit()
    return _serialize(_get_or_404(db, quote_id))


@router.post("/{quote_id}/reject", response_model=QuoteOut, dependencies=[Depends(get_current_user)])
def reject_quote(quote_id: int, db: Session = Depends(get_db)):
    quote = _get_or_404(db, quote_id)
    if quote.status not in (QuoteStatus.REQUESTED, QuoteStatus.QUOTED):
        raise HTTPException(status_code=400, detail=f"Quote is already '{quote.status.value}'")
    quote.status = QuoteStatus.REJECTED
    db.commit()
    return _serialize(_get_or_404(db, quote_id))


@router.post("/{quote_id}/convert", response_model=QuoteOut)
def convert_quote(quote_id: int, db: Session = Depends(get_db)):
    """Turn an admin-priced quote into a real purchase order (Order), at the
    negotiated prices rather than the live product price."""
    quote = _get_or_404(db, quote_id)
    if quote.status != QuoteStatus.QUOTED:
        raise HTTPException(status_code=400, detail=f"Quote is '{quote.status.value}', not ready to convert")

    product_ids = [item.product_id for item in quote.items]
    products_by_id = {p.id: p for p in db.execute(select(Product).where(Product.id.in_(product_ids))).scalars().all()}

    problems = [
        {"product_id": item.product_id, "requested": item.quantity, "available": products_by_id[item.product_id].stock_qty}
        for item in quote.items
        if products_by_id[item.product_id].stock_qty < item.quantity
    ]
    if problems:
        raise HTTPException(status_code=400, detail={"message": "insufficient stock to convert quote", "problems": problems})

    order = Order(
        customer_name=quote.customer_name,
        customer_id=quote.customer_id,
        po_reference=f"quote-{quote.id}",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        status=OrderStatus.PENDING,
    )
    for item in quote.items:
        product = products_by_id[item.product_id]
        order.items.append(OrderItem(product_id=product.id, quantity=item.quantity, unit_price=item.quoted_unit_price))
        product.stock_qty -= item.quantity

    db.add(order)
    db.flush()
    quote.order_id = order.id
    quote.status = QuoteStatus.CONVERTED
    db.commit()
    return _serialize(_get_or_404(db, quote_id))
