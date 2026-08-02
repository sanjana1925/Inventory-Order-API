from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Order, OrderItem, OrderStatus, Product
from app.schemas import OrderCreate, OrderItemOut, OrderOut

router = APIRouter(prefix="/orders", tags=["orders"])


def _serialize_order(order: Order) -> OrderOut:
    items_out = [
        OrderItemOut(
            product_id=item.product_id,
            product_name=item.product.name,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.quantity * item.unit_price,
        )
        for item in order.items
    ]
    return OrderOut(
        id=order.id,
        customer_name=order.customer_name,
        created_at=order.created_at,
        status=order.status,
        items=items_out,
        total=sum(item.line_total for item in items_out),
    )


@router.post("", response_model=OrderOut, status_code=201)
def place_order(payload: OrderCreate, db: Session = Depends(get_db)):
    requested_qty: dict[int, int] = {}
    for line in payload.items:
        requested_qty[line.product_id] = requested_qty.get(line.product_id, 0) + line.quantity

    products = db.execute(
        select(Product).where(Product.id.in_(requested_qty.keys()))
    ).scalars().all()
    products_by_id = {p.id: p for p in products}

    problems = []
    for product_id, qty in requested_qty.items():
        product = products_by_id.get(product_id)
        if product is None:
            problems.append({"product_id": product_id, "error": "product not found"})
        elif product.stock_qty < qty:
            problems.append(
                {
                    "product_id": product_id,
                    "product_name": product.name,
                    "error": "insufficient stock",
                    "requested": qty,
                    "available": product.stock_qty,
                }
            )
    if problems:
        raise HTTPException(status_code=400, detail={"message": "order rejected", "problems": problems})

    order = Order(
        customer_name=payload.customer_name,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        status=OrderStatus.PENDING,
    )
    for line in payload.items:
        product = products_by_id[line.product_id]
        order.items.append(
            OrderItem(product_id=product.id, quantity=line.quantity, unit_price=product.price)
        )

    for product_id, qty in requested_qty.items():
        products_by_id[product_id].stock_qty -= qty

    db.add(order)
    db.commit()
    db.refresh(order)
    return _serialize_order(order)


@router.get("", response_model=list[OrderOut])
def list_orders(db: Session = Depends(get_db)):
    orders = db.execute(select(Order).order_by(Order.id)).scalars().all()
    return [_serialize_order(order) for order in orders]


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return _serialize_order(order)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail=f"Order {order_id} is already cancelled")

    for item in order.items:
        item.product.stock_qty += item.quantity
    order.status = OrderStatus.CANCELLED

    db.commit()
    db.refresh(order)
    return _serialize_order(order)
