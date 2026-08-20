from fastapi import FastAPI

from app.database import Base, engine
from app.routers import (
    addresses,
    categories,
    customers,
    favorites,
    notifications,
    orders,
    products,
    purchase_orders,
    quotes,
    reports,
    suppliers,
    support,
    users,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Inventory & Order Management API")

app.include_router(products.router)
app.include_router(categories.router)
app.include_router(customers.router)
app.include_router(addresses.router)
app.include_router(orders.router)
app.include_router(quotes.router)
app.include_router(suppliers.router)
app.include_router(purchase_orders.router)
app.include_router(support.router)
app.include_router(notifications.router)
app.include_router(users.router)
app.include_router(reports.router)
app.include_router(favorites.router)


@app.get("/")
def health():
    return {"message": "Inventory & Order Management API is running. See /docs for endpoints."}
