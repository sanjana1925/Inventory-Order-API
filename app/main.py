from fastapi import FastAPI

from app.database import Base, engine
from app.routers import orders, products

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Inventory & Order Management API")

app.include_router(products.router)
app.include_router(orders.router)


@app.get("/")
def health():
    return {"message": "Inventory & Order Management API is running. See /docs for endpoints."}
