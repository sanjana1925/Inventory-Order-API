from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import OrderStatus


class ProductCreate(BaseModel):
    name: str
    price: float = Field(gt=0)
    stock_qty: int = Field(ge=0)


class ProductUpdate(BaseModel):
    name: str | None = None
    price: float | None = Field(default=None, gt=0)
    stock_qty: int | None = Field(default=None, ge=0)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: float
    stock_qty: int


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_name: str
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    line_total: float


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    created_at: datetime
    status: OrderStatus
    items: list[OrderItemOut]
    total: float
