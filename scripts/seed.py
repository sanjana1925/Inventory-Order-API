"""Drop and recreate all tables, then seed a small set of products.

Orders are left for the API to create — seeding orders here would bypass the
stock-decrement logic the API exists to enforce.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models import Product

PRODUCTS = [
    {"name": "Wireless Mouse", "price": 24.99, "stock_qty": 50},
    {"name": "Mechanical Keyboard", "price": 89.99, "stock_qty": 30},
    {"name": "USB-C Hub", "price": 39.99, "stock_qty": 5},
    {"name": "27in Monitor", "price": 249.99, "stock_qty": 12},
    {"name": "Webcam 1080p", "price": 59.99, "stock_qty": 0},
    {"name": "Laptop Stand", "price": 34.99, "stock_qty": 8},
]


def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        db.add_all(Product(**p) for p in PRODUCTS)
        db.commit()
    finally:
        db.close()

    print(f"Seeded {len(PRODUCTS)} products.")


if __name__ == "__main__":
    seed()
