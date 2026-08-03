"""Seed a large synthetic demo dataset (no external data files required).

Targets (as requested):
  - 576 customers, all with unique emails
  - 57+ suppliers
  - products split across 4 categories (Home Appliances, Furniture,
    Mobile Appliances, Home Decor), 10-13 products each, with pricing
  - 607 orders: 78 completed, 20 pending, remainder split across
    processing / shipped / delivered / cancelled
  - every order totals at least $100 (its "payment" amount), and total
    order-item rows comfortably exceed 100
  - total revenue (sum of non-cancelled order items) of at least $50,000
  - at least 7 products left in a low-stock state (stock_qty < 10, the
    threshold the API and UI already use)
  - `po_reference` on every order is left null, to be filled in later

Orders are placed through the real API (TestClient -> POST /orders) so
stock decrement and oversell prevention are exercised exactly like a real
client would. Status and created_at are then backfilled directly against
the DB for orders that aren't cancelled (that doesn't touch stock/atomicity);
cancelled orders go through the real POST /orders/{id}/cancel endpoint
instead, since that one actually returns stock and must stay correct.
"""

import itertools
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Category, Customer, Order, OrderStatus, Product, Supplier, User, UserRole
from app.security import hash_password

RANDOM_SEED = 42
ADMIN_EMAIL = "admin@inventory.com"
ADMIN_PASSWORD = "admin123"

NUM_CUSTOMERS = 576
NUM_SUPPLIERS = 57
NUM_ORDERS = 607
STATUS_TARGETS = {
    OrderStatus.PENDING: 20,
    OrderStatus.COMPLETED: 78,
    OrderStatus.CANCELLED: 50,
    OrderStatus.PROCESSING: 153,
    OrderStatus.SHIPPED: 153,
    OrderStatus.DELIVERED: 153,
}
assert sum(STATUS_TARGETS.values()) == NUM_ORDERS

MIN_ORDER_TOTAL = 100.0
LOW_STOCK_THRESHOLD = 10
LOW_STOCK_POOL_PER_CATEGORY = 3  # -> 12 products seeded low, comfortably over the "at least 7" ask

CATEGORIES = {
    "Home Appliances": {
        "price_range": (40, 900),
        "products": [
            "Refrigerator 300L", "Microwave Oven 25L", "Washing Machine 7kg",
            "Air Conditioner 1.5 Ton", "Electric Kettle 1.7L", "Vacuum Cleaner Pro",
            "Dishwasher Compact", "Water Purifier RO", "Ceiling Fan 48in",
            "Toaster 2-Slice", "Blender 600W", "Induction Cooktop", "Air Fryer 5L",
        ],
    },
    "Furniture": {
        "price_range": (70, 1600),
        "products": [
            "3-Seater Sofa", "Queen Size Bed", "Dining Table Set 6-Seater",
            "Office Chair Ergonomic", "Bookshelf 5-Tier", "Wardrobe 3-Door",
            "Coffee Table Glass", "Recliner Chair", "Bunk Bed Wooden",
            "TV Console Unit", "Study Desk", "Bar Stool Set",
        ],
    },
    "Mobile Appliances": {
        "price_range": (15, 1300),
        "products": [
            "Smartphone 128GB", "Smartphone 256GB Pro", "Wireless Earbuds",
            "Power Bank 20000mAh", "Phone Case Premium", "Screen Protector Tempered Glass",
            "Bluetooth Speaker Portable", "Smartwatch Fitness", "Fast Charger 65W",
            "USB-C Cable 2m", "Tablet 10in", "Car Phone Mount", "Wireless Charging Pad",
        ],
    },
    "Home Decor": {
        "price_range": (8, 320),
        "products": [
            "Wall Clock Modern", "Table Lamp Ceramic", "Area Rug 5x7",
            "Wall Art Canvas Set", "Decorative Vase", "Throw Pillow Set",
            "Curtain Panel Pair", "Scented Candle Set", "Photo Frame Collage",
            "Indoor Plant Pot", "Mirror Wall Round",
        ],
    },
}

BIZ_ADJECTIVES = [
    "Summit", "Blue Ridge", "Northgate", "Silverline", "Union", "Golden State",
    "Metro", "Coastal", "Highland", "Riverside", "Prairie", "Lakeside", "Vanguard",
    "Cornerstone", "Redwood", "Ironwood", "Copperfield", "Sterling", "Harborview",
    "Crestline", "Fairmount", "Brookfield", "Cedarpoint", "Milestone", "Northfield",
    "Bayline", "Granite", "Meridian", "Pinecrest", "Westgate",
]
BIZ_NOUNS = [
    "Retail Group", "Traders", "Mart", "Enterprises", "Holdings", "Ventures",
    "Partners", "Solutions", "Systems", "Supply Co", "Outlets", "Depot", "Hub",
    "Collective", "Industries", "Corp", "Networks", "Distribution", "Logistics",
    "Wholesale", "Imports", "Exports", "Merchants", "Works", "Goods Co",
]

SUPPLIER_ADJECTIVES = [
    "Northern", "Southern", "Eastern", "Western", "Central", "Pacific", "Atlantic",
    "Continental", "National", "Regional", "Apex", "Titan", "Premier", "Elite",
    "Reliable", "Precision", "Global", "United", "Allied", "Frontier",
]
SUPPLIER_NOUNS = [
    "Supply Co", "Wholesale", "Distributors", "Trading Co", "Logistics",
    "Sourcing Group", "Import Export", "Materials Inc", "Procurement Partners",
    "Industrial Supply",
]

CITY_STATE = [
    ("Austin", "TX"), ("Denver", "CO"), ("Columbus", "OH"), ("Raleigh", "NC"),
    ("Portland", "OR"), ("Nashville", "TN"), ("Phoenix", "AZ"), ("Atlanta", "GA"),
    ("Minneapolis", "MN"), ("Kansas City", "MO"), ("Sacramento", "CA"), ("Tampa", "FL"),
    ("Charlotte", "NC"), ("Indianapolis", "IN"), ("Salt Lake City", "UT"),
    ("Milwaukee", "WI"), ("Albuquerque", "NM"), ("Louisville", "KY"), ("Omaha", "NE"),
    ("Boise", "ID"), ("Richmond", "VA"), ("Tucson", "AZ"), ("Spokane", "WA"),
    ("Baton Rouge", "LA"), ("Des Moines", "IA"),
]
STREET_NAMES = [
    "Main St", "Oak Ave", "Maple Dr", "Industrial Pkwy", "Commerce Blvd",
    "Market St", "Highland Rd", "Broadway", "Elm St", "Riverside Dr",
]
EMAIL_DOMAINS = ["gmail.com", "outlook.com", "bizmail.com", "corpmail.com", "yourbiz.com"]

STATUS_CREATED_AT_DAYS_AGO = {
    OrderStatus.PENDING: (0, 5),
    OrderStatus.PROCESSING: (2, 12),
    OrderStatus.SHIPPED: (6, 25),
    OrderStatus.DELIVERED: (15, 70),
    OrderStatus.COMPLETED: (30, 200),
    OrderStatus.CANCELLED: (1, 100),
}


class ProductInfo(NamedTuple):
    id: int
    price: float
    stock_qty: int


class CustomerInfo(NamedTuple):
    id: int
    name: str


def slugify(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "" for ch in name)


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed_categories(db) -> None:
    db.add_all(Category(name=name) for name in CATEGORIES)
    db.commit()


def seed_products(db) -> list[ProductInfo]:
    """Returns the orderable pool (low-stock-by-design products are excluded
    so they aren't immediately drained back above the threshold)."""
    orderable_objs = []
    for category, cfg in CATEGORIES.items():
        lo, hi = cfg["price_range"]
        names = cfg["products"]
        low_stock_names = set(random.sample(names, LOW_STOCK_POOL_PER_CATEGORY))
        for name in names:
            price = round(random.uniform(lo, hi), 2)
            if name in low_stock_names:
                stock_qty = random.randint(0, 9)
            else:
                stock_qty = random.randint(20, 300)
            product = Product(name=name, category=category, price=price, stock_qty=stock_qty)
            db.add(product)
            if name not in low_stock_names:
                orderable_objs.append(product)
    db.commit()
    return [ProductInfo(id=p.id, price=p.price, stock_qty=p.stock_qty) for p in orderable_objs]


def seed_suppliers(db) -> None:
    combos = list(itertools.product(SUPPLIER_ADJECTIVES, SUPPLIER_NOUNS))
    random.shuffle(combos)
    suppliers = []
    for i in range(NUM_SUPPLIERS):
        adj, noun = combos[i % len(combos)]
        city, state = random.choice(CITY_STATE)
        suppliers.append(Supplier(name=f"{adj} {noun}", city=city, state=state))
    db.add_all(suppliers)
    db.commit()


def seed_customers(db) -> list[CustomerInfo]:
    combos = list(itertools.product(BIZ_ADJECTIVES, BIZ_NOUNS))
    random.shuffle(combos)
    customers = []
    for i in range(NUM_CUSTOMERS):
        adj, noun = combos[i % len(combos)]
        name = f"{adj} {noun}"
        domain = random.choice(EMAIL_DOMAINS)
        email = f"{slugify(adj)}.{slugify(noun)}{i}@{domain}"
        city, state = random.choice(CITY_STATE)
        street_num = random.randint(100, 9999)
        street = random.choice(STREET_NAMES)
        phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
        customer = Customer(
            name=name,
            email=email,
            phone=phone,
            address=f"{street_num} {street}, {city}, {state}",
            password_hash=None,
        )
        db.add(customer)
        customers.append(customer)
    db.commit()
    return [CustomerInfo(id=c.id, name=c.name) for c in customers]


def seed_admin(db) -> None:
    db.add(User(email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD), role=UserRole.ADMIN))
    db.commit()


def build_status_sequence() -> list[OrderStatus]:
    sequence = []
    for status, count in STATUS_TARGETS.items():
        sequence.extend([status] * count)
    random.shuffle(sequence)
    return sequence


def random_created_at(status: OrderStatus) -> datetime:
    lo, hi = STATUS_CREATED_AT_DAYS_AGO[status]
    days_ago = random.randint(lo, hi)
    return datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))


def build_order_items(stock: dict[int, int], orderable: list[ProductInfo]) -> list[dict]:
    """Pick 1-4 line items against the in-memory stock tracker, topping up
    quantity/items until the order totals at least MIN_ORDER_TOTAL."""
    items: list[dict] = []
    total = 0.0
    available = [p for p in orderable if stock[p.id] > 0]
    if not available:
        return items

    for _ in range(random.randint(1, 4)):
        available = [p for p in orderable if stock[p.id] > 0 and p.id not in {i["product_id"] for i in items}]
        if not available:
            break
        product = random.choice(available)
        qty = random.randint(1, min(5, stock[product.id]))
        items.append({"product_id": product.id, "quantity": qty})
        stock[product.id] -= qty
        total += qty * product.price

    while total < MIN_ORDER_TOTAL:
        candidates = [i for i in items if stock[i["product_id"]] > 0]
        if not candidates:
            break
        line = random.choice(candidates)
        product = next(p for p in orderable if p.id == line["product_id"])
        line["quantity"] += 1
        stock[product.id] -= 1
        total += product.price

    return items


def seed_orders(client: TestClient, customers: list[CustomerInfo], orderable: list[ProductInfo]) -> None:
    stock = {p.id: p.stock_qty for p in orderable}
    statuses = build_status_sequence()

    placed = []  # (order_id, target_status)
    for status in statuses:
        customer = random.choice(customers)
        items = build_order_items(stock, orderable)
        if not items:
            continue  # pool exhausted; skip rather than force an oversell
        resp = client.post(
            "/orders",
            json={"customer_name": customer.name, "customer_id": customer.id, "items": items},
        )
        resp.raise_for_status()
        placed.append((resp.json()["id"], status))

    db = SessionLocal()
    try:
        for order_id, status in placed:
            if status == OrderStatus.CANCELLED:
                client.post(f"/orders/{order_id}/cancel").raise_for_status()
                continue
            order = db.get(Order, order_id)
            order.status = status
            order.created_at = random_created_at(status)
        db.commit()
    finally:
        db.close()

    print(f"Placed {len(placed)}/{NUM_ORDERS} orders (some may be skipped if stock ran out).")


def print_summary(db) -> None:
    from sqlalchemy import func, select

    from app.models import OrderItem

    total_customers = db.scalar(select(func.count(Customer.id)))
    total_suppliers = db.scalar(select(func.count(Supplier.id)))
    total_products = db.scalar(select(func.count(Product.id)))
    total_orders = db.scalar(select(func.count(Order.id)))
    total_items = db.scalar(select(func.count(OrderItem.id)))
    low_stock = db.scalar(select(func.count(Product.id)).where(Product.stock_qty < LOW_STOCK_THRESHOLD))
    revenue = db.scalar(
        select(func.coalesce(func.sum(OrderItem.quantity * OrderItem.unit_price), 0))
        .select_from(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.status != OrderStatus.CANCELLED)
    )
    status_counts = dict(db.execute(select(Order.status, func.count(Order.id)).group_by(Order.status)).all())

    print("\n--- Seed summary ---")
    print(f"customers: {total_customers}")
    print(f"suppliers: {total_suppliers}")
    print(f"products:  {total_products} (low stock <{LOW_STOCK_THRESHOLD}: {low_stock})")
    print(f"orders:    {total_orders}")
    print(f"order_items: {total_items}")
    print(f"revenue (non-cancelled): ${revenue:,.2f}")
    for status, count in sorted(status_counts.items(), key=lambda kv: kv[0].value):
        print(f"  {status.value}: {count}")


def main():
    random.seed(RANDOM_SEED)
    reset_db()

    db = SessionLocal()
    try:
        seed_categories(db)
        orderable = seed_products(db)
        seed_suppliers(db)
        customers = seed_customers(db)
        seed_admin(db)
    finally:
        db.close()

    client = TestClient(app)
    seed_orders(client, customers, orderable)

    db = SessionLocal()
    try:
        print_summary(db)
    finally:
        db.close()

    print(f"\nAdmin login: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")


if __name__ == "__main__":
    main()
