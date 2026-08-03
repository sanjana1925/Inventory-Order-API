from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Customer, Order, OrderItem, OrderStatus, Product

router = APIRouter(prefix="/reports", tags=["reports"])


def _revenue_stmt():
    return (
        select(func.coalesce(func.sum(OrderItem.quantity * OrderItem.unit_price), 0))
        .select_from(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.status != OrderStatus.CANCELLED)
    )


@router.get("/low-stock")
def low_stock_report(threshold: int = Query(10, ge=0), limit: int = Query(50, ge=1, le=1000), db: Session = Depends(get_db)):
    products = (
        db.execute(
            select(Product)
            .where(Product.stock_qty < threshold)
            .order_by(Product.stock_qty)
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        {"id": p.id, "name": p.name, "category": p.category, "stock_qty": p.stock_qty, "price": p.price}
        for p in products
    ]


@router.get("/inventory")
def inventory_report(db: Session = Depends(get_db)):
    total_products = db.scalar(select(func.count(Product.id))) or 0
    low_stock_count = db.scalar(select(func.count(Product.id)).where(Product.stock_qty < 10)) or 0
    total_units = db.scalar(select(func.coalesce(func.sum(Product.stock_qty), 0))) or 0
    inventory_value = db.scalar(select(func.coalesce(func.sum(Product.stock_qty * Product.price), 0))) or 0
    return {
        "total_products": total_products,
        "low_stock_count": low_stock_count,
        "total_units": total_units,
        "inventory_value": round(inventory_value, 2),
    }


@router.get("/sales")
def sales_report(db: Session = Depends(get_db)):
    total_orders = db.scalar(select(func.count(Order.id))) or 0
    total_revenue = db.scalar(_revenue_stmt()) or 0
    status_rows = db.execute(select(Order.status, func.count(Order.id)).group_by(Order.status)).all()
    return {
        "total_orders": total_orders,
        "total_revenue": round(total_revenue, 2),
        "orders_by_status": {status.value: count for status, count in status_rows},
    }


@router.get("/overview")
def overview_report(db: Session = Depends(get_db)):
    total_products = db.scalar(select(func.count(Product.id))) or 0
    total_customers = db.scalar(select(func.count(Customer.id))) or 0
    total_orders = db.scalar(select(func.count(Order.id))) or 0
    low_stock_count = db.scalar(select(func.count(Product.id)).where(Product.stock_qty < 10)) or 0
    total_units = db.scalar(select(func.coalesce(func.sum(Product.stock_qty), 0))) or 0
    inventory_value = db.scalar(select(func.coalesce(func.sum(Product.stock_qty * Product.price), 0))) or 0
    total_revenue = db.scalar(_revenue_stmt()) or 0
    status_rows = db.execute(select(Order.status, func.count(Order.id)).group_by(Order.status)).all()
    return {
        "total_products": total_products,
        "total_customers": total_customers,
        "total_orders": total_orders,
        "low_stock_count": low_stock_count,
        "total_units": total_units,
        "inventory_value": round(inventory_value, 2),
        "total_revenue": round(total_revenue, 2),
        "orders_by_status": {status.value: count for status, count in status_rows},
    }


@router.get("/top-products")
def top_products_report(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    stmt = (
        select(
            Product.id,
            Product.name,
            Product.category,
            func.sum(OrderItem.quantity).label("units_sold"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.status != OrderStatus.CANCELLED)
        .group_by(Product.id, Product.name, Product.category)
        .order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "category": r.category,
            "units_sold": int(r.units_sold),
            "revenue": round(r.revenue, 2),
        }
        for r in rows
    ]


@router.get("/top-customers")
def top_customers_report(limit: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    stmt = (
        select(
            Order.customer_name,
            func.count(func.distinct(Order.id)).label("orders"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
        )
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(Order.status != OrderStatus.CANCELLED)
        .group_by(Order.customer_name)
        .order_by(func.sum(OrderItem.quantity * OrderItem.unit_price).desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        {"customer_name": r.customer_name, "orders": r.orders, "revenue": round(r.revenue, 2)}
        for r in rows
    ]


@router.get("/revenue-trend")
def revenue_trend_report(db: Session = Depends(get_db)):
    month = func.strftime("%Y-%m", Order.created_at).label("month")
    stmt = (
        select(
            month,
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue"),
            func.count(func.distinct(Order.id)).label("orders"),
        )
        .select_from(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.status != OrderStatus.CANCELLED)
        .group_by(month)
        .order_by(month)
    )
    rows = db.execute(stmt).all()
    return [{"month": r.month, "revenue": round(r.revenue, 2), "orders": r.orders} for r in rows]


@router.get("/category-mix")
def category_mix_report(db: Session = Depends(get_db)):
    category = func.coalesce(Product.category, "Uncategorized").label("category")
    stmt = (
        select(
            category,
            func.count(Product.id).label("product_count"),
            func.sum(Product.stock_qty).label("total_units"),
            func.sum(Product.stock_qty * Product.price).label("inventory_value"),
        )
        .group_by(category)
        .order_by(func.sum(Product.stock_qty * Product.price).desc())
    )
    rows = db.execute(stmt).all()
    return [
        {
            "category": r.category,
            "product_count": r.product_count,
            "total_units": int(r.total_units or 0),
            "inventory_value": round(r.inventory_value or 0, 2),
        }
        for r in rows
    ]
