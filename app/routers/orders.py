from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.activity import notify
from app.auth import get_current_user
from app.database import get_db
from app.invoice import build_invoice_pdf
from app.models import Customer, Order, OrderItem, OrderStatus, PaymentStatus, Product
from app.notifications_channel import send_email
from app.schemas import OrderCreate, OrderItemOut, OrderOut, OrderPaymentStatusUpdate, OrderStatusUpdate
from app.security import can_transition

router = APIRouter(prefix="/orders", tags=["orders"])

LOW_STOCK_THRESHOLD = 10

# Simulated checkout math — no real tax jurisdiction/carrier is involved.
TAX_RATE = 0.08
SHIPPING_FEE = 100.0
FREE_SHIPPING_THRESHOLD = 2000.0


def _customer_email(db: Session, customer_id: int | None) -> str | None:
    if customer_id is None:
        return None
    customer = db.get(Customer, customer_id)
    return customer.email if customer else None


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
    subtotal = sum(item.line_total for item in items_out)
    return OrderOut(
        id=order.id,
        customer_name=order.customer_name,
        customer_id=order.customer_id,
        po_reference=order.po_reference,
        created_at=order.created_at,
        status=order.status,
        payment_status=order.payment_status,
        items=items_out,
        total=subtotal,
        tax_amount=order.tax_amount,
        shipping_fee=order.shipping_fee,
        grand_total=subtotal + order.tax_amount + order.shipping_fee,
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

    subtotal = sum(products_by_id[pid].price * qty for pid, qty in requested_qty.items())
    tax_amount = round(subtotal * TAX_RATE, 2)
    shipping_fee = 0.0 if subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_FEE

    order = Order(
        customer_name=payload.customer_name,
        customer_id=payload.customer_id,
        po_reference=payload.po_reference,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        status=OrderStatus.PENDING,
        payment_status=PaymentStatus.UNPAID,
        tax_amount=tax_amount,
        shipping_fee=shipping_fee,
    )
    for line in payload.items:
        product = products_by_id[line.product_id]
        order.items.append(
            OrderItem(product_id=product.id, quantity=line.quantity, unit_price=product.price)
        )

    low_stock_alerts = []
    for product_id, qty in requested_qty.items():
        product = products_by_id[product_id]
        was_above_threshold = product.stock_qty >= LOW_STOCK_THRESHOLD
        product.stock_qty -= qty
        if was_above_threshold and product.stock_qty < LOW_STOCK_THRESHOLD:
            low_stock_alerts.append(product.name)

    db.add(order)
    db.flush()  # assigns order.id so notifications below can reference it

    notify(db, audience="client", message=f"Order #{order.id} placed", order_id=order.id)
    for name in low_stock_alerts:
        notify(db, audience="admin", message=f"Low stock: {name}", level="warning")

    db.commit()
    db.refresh(order)

    email = _customer_email(db, order.customer_id)
    if email:
        grand_total = subtotal + tax_amount + shipping_fee
        send_email(
            email,
            f"Order #{order.id} confirmed",
            f"Thanks for your order, {order.customer_name}. Grand total: {grand_total:,.2f} (unpaid).",
        )
    return _serialize_order(order)


@router.get("", response_model=list[OrderOut])
def list_orders(
    response: Response,
    status: OrderStatus | None = None,
    payment_status: PaymentStatus | None = None,
    customer: str | None = Query(default=None, description="admin search: fuzzy match on customer name"),
    customer_id: int | None = Query(default=None, description="exact match: use for a client's own orders"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    filters = []
    if status is not None:
        filters.append(Order.status == status)
    if payment_status is not None:
        filters.append(Order.payment_status == payment_status)
    if customer:
        filters.append(Order.customer_name.ilike(f"%{customer}%"))
    if customer_id is not None:
        filters.append(Order.customer_id == customer_id)

    count_stmt = select(func.count(Order.id))
    for f in filters:
        count_stmt = count_stmt.where(f)
    total = db.scalar(count_stmt)
    response.headers["X-Total-Count"] = str(total)

    stmt = select(Order).options(selectinload(Order.items).selectinload(OrderItem.product))
    for f in filters:
        stmt = stmt.where(f)
    stmt = stmt.order_by(Order.id.desc()).offset(skip).limit(limit)

    orders = db.execute(stmt).scalars().all()
    return [_serialize_order(order) for order in orders]


@router.get("/lookup", response_model=OrderOut)
def lookup_order(order_id: int, customer_name: str, db: Session = Depends(get_db)):
    """Public order tracking: an order id alone isn't a secret worth gatekeeping
    hard, but requiring the customer name too keeps casual ID-guessing out."""
    order = db.execute(
        select(Order)
        .where(Order.id == order_id, func.lower(Order.customer_name) == customer_name.lower())
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="No matching order found")
    return _serialize_order(order)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return _serialize_order(order)


@router.get("/{order_id}/invoice")
def download_invoice(order_id: int, db: Session = Depends(get_db)):
    order = db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    ).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    pdf_bytes = build_invoice_pdf(_serialize_order(order))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice-{order_id}.pdf"},
    )


@router.patch("/{order_id}/status", response_model=OrderOut, dependencies=[Depends(get_current_user)])
def update_order_status(order_id: int, payload: OrderStatusUpdate, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    if not can_transition(order.status, payload.status):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move order from '{order.status.value}' to '{payload.status.value}'",
        )

    if payload.status == OrderStatus.CANCELLED:
        for item in order.items:
            item.product.stock_qty += item.quantity

    order.status = payload.status
    notify(db, audience="client", message=f"Order #{order.id} is now {payload.status.value}", order_id=order.id)

    db.commit()
    db.refresh(order)

    email = _customer_email(db, order.customer_id)
    if email:
        send_email(email, f"Order #{order.id} update", f"Your order is now {payload.status.value}.")
    return _serialize_order(order)


@router.patch("/{order_id}/payment-status", response_model=OrderOut, dependencies=[Depends(get_current_user)])
def update_payment_status(order_id: int, payload: OrderPaymentStatusUpdate, db: Session = Depends(get_db)):
    """Admin override in either direction (paid<->unpaid) — separate from the
    customer-facing simulated POST /pay, which only ever goes unpaid->paid."""
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot change payment status on a cancelled order")
    if order.payment_status == payload.payment_status:
        return _serialize_order(order)

    order.payment_status = payload.payment_status
    notify(db, audience="client", message=f"Order #{order.id} payment marked {payload.payment_status.value}", order_id=order.id)

    db.commit()
    db.refresh(order)
    return _serialize_order(order)


@router.post("/{order_id}/pay", response_model=OrderOut)
def pay_order(order_id: int, db: Session = Depends(get_db)):
    """Simulated payment — flips unpaid -> paid with no real payment gateway
    involved. Stands in for a Razorpay/Stripe checkout callback."""
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot pay for a cancelled order")
    if order.payment_status == PaymentStatus.PAID:
        raise HTTPException(status_code=400, detail="Order is already paid")

    order.payment_status = PaymentStatus.PAID
    notify(db, audience="admin", message=f"Order #{order.id} was paid", order_id=order.id)

    db.commit()
    db.refresh(order)

    email = _customer_email(db, order.customer_id)
    if email:
        send_email(email, f"Payment received for order #{order.id}", "Your simulated payment was successful.")
    return _serialize_order(order)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    if not can_transition(order.status, OrderStatus.CANCELLED):
        raise HTTPException(status_code=400, detail=f"Order {order_id} can no longer be cancelled")

    for item in order.items:
        item.product.stock_qty += item.quantity
    order.status = OrderStatus.CANCELLED
    notify(db, audience="client", message=f"Order #{order.id} was cancelled", order_id=order.id)

    db.commit()
    db.refresh(order)
    return _serialize_order(order)
