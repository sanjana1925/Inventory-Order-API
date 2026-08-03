from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus, Supplier
from app.schemas import PurchaseOrderCreate, PurchaseOrderItemOut, PurchaseOrderOut

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])


def _serialize(po: PurchaseOrder) -> PurchaseOrderOut:
    items_out = [
        PurchaseOrderItemOut(
            product_id=item.product_id,
            product_name=item.product.name,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
        )
        for item in po.items
    ]
    return PurchaseOrderOut(
        id=po.id,
        supplier_id=po.supplier_id,
        supplier_name=po.supplier.name,
        status=po.status,
        created_at=po.created_at,
        received_at=po.received_at,
        items=items_out,
        total_cost=sum(i.quantity * i.unit_cost for i in items_out),
    )


def _get_or_404(db: Session, po_id: int) -> PurchaseOrder:
    po = db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id)
        .options(selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product), selectinload(PurchaseOrder.supplier))
    ).scalar_one_or_none()
    if po is None:
        raise HTTPException(status_code=404, detail=f"Purchase order {po_id} not found")
    return po


@router.post("", response_model=PurchaseOrderOut, status_code=201)
def create_purchase_order(payload: PurchaseOrderCreate, db: Session = Depends(get_db)):
    supplier = db.get(Supplier, payload.supplier_id)
    if supplier is None:
        raise HTTPException(status_code=400, detail="Unknown supplier")

    po = PurchaseOrder(
        supplier_id=payload.supplier_id,
        status=PurchaseOrderStatus.ORDERED,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    for line in payload.items:
        po.items.append(PurchaseOrderItem(product_id=line.product_id, quantity=line.quantity, unit_cost=line.unit_cost))

    db.add(po)
    db.commit()
    return _serialize(_get_or_404(db, po.id))


@router.get("", response_model=list[PurchaseOrderOut])
def list_purchase_orders(
    response: Response,
    status: PurchaseOrderStatus | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    count_stmt = select(func.count(PurchaseOrder.id))
    if status is not None:
        count_stmt = count_stmt.where(PurchaseOrder.status == status)
    total = db.scalar(count_stmt)
    response.headers["X-Total-Count"] = str(total)

    stmt = select(PurchaseOrder).options(
        selectinload(PurchaseOrder.items).selectinload(PurchaseOrderItem.product), selectinload(PurchaseOrder.supplier)
    )
    if status is not None:
        stmt = stmt.where(PurchaseOrder.status == status)
    stmt = stmt.order_by(PurchaseOrder.id.desc()).offset(skip).limit(limit)

    rows = db.execute(stmt).scalars().all()
    return [_serialize(po) for po in rows]


@router.get("/{po_id}", response_model=PurchaseOrderOut)
def get_purchase_order(po_id: int, db: Session = Depends(get_db)):
    return _serialize(_get_or_404(db, po_id))


@router.post("/{po_id}/receive", response_model=PurchaseOrderOut)
def receive_purchase_order(po_id: int, db: Session = Depends(get_db)):
    po = _get_or_404(db, po_id)
    if po.status == PurchaseOrderStatus.RECEIVED:
        raise HTTPException(status_code=400, detail="Purchase order already received")

    for item in po.items:
        item.product.stock_qty += item.quantity

    po.status = PurchaseOrderStatus.RECEIVED
    po.received_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return _serialize(_get_or_404(db, po_id))
