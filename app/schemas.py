from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import OrderStatus, PurchaseOrderStatus, QuoteStatus, SupportStatus, UserRole


class ProductCreate(BaseModel):
    name: str = Field(min_length=1)
    category: str | None = None
    price: float = Field(gt=0)
    stock_qty: int = Field(ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    category: str | None = None
    price: float | None = Field(default=None, gt=0)
    stock_qty: int | None = Field(default=None, ge=0)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str | None = None
    price: float
    stock_qty: int


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


# --- Customers (business accounts) -----------------------------------------

class CustomerCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    phone: str | None = None
    address: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    phone: str | None = None
    address: str | None = None


class CustomerSignup(BaseModel):
    name: str = Field(min_length=1, description="Company / contact name")
    email: EmailStr
    password: str = Field(min_length=6)
    phone: str | None = None
    address: str | None = None


class CustomerLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class DeliveryAddressCreate(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    address: str = Field(min_length=1, max_length=255)
    is_default: bool = False


class DeliveryAddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    address: str
    is_default: bool


# --- Orders ------------------------------------------------------------------

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1)
    customer_id: int | None = None
    po_reference: str | None = None
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
    customer_id: int | None = None
    po_reference: str | None = None
    created_at: datetime
    status: OrderStatus
    items: list[OrderItemOut]
    total: float


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


# --- Quotes --------------------------------------------------------------

class QuoteItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class QuoteCreate(BaseModel):
    customer_name: str = Field(min_length=1)
    customer_id: int | None = None
    items: list[QuoteItemCreate] = Field(min_length=1)


class QuoteItemPricing(BaseModel):
    product_id: int
    quoted_unit_price: float = Field(gt=0)


class QuotePriceUpdate(BaseModel):
    items: list[QuoteItemPricing] = Field(min_length=1)


class QuoteItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    quantity: int
    quoted_unit_price: float | None = None


class QuoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    customer_id: int | None = None
    status: QuoteStatus
    created_at: datetime
    order_id: int | None = None
    items: list[QuoteItemOut]


# --- Procurement: suppliers & purchase orders -------------------------------

class SupplierCreate(BaseModel):
    name: str = Field(min_length=1)
    city: str | None = None
    state: str | None = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    city: str | None = None
    state: str | None = None


class PurchaseOrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
    unit_cost: float = Field(gt=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    items: list[PurchaseOrderItemCreate] = Field(min_length=1)


class PurchaseOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    quantity: int
    unit_cost: float


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int
    supplier_name: str
    status: PurchaseOrderStatus
    created_at: datetime
    received_at: datetime | None = None
    items: list[PurchaseOrderItemOut]
    total_cost: float


# --- Support -----------------------------------------------------------------

class SupportMessageCreate(BaseModel):
    customer_name: str = Field(min_length=1)
    customer_id: int | None = None
    email: EmailStr
    subject: str = Field(min_length=1, max_length=150)
    message: str = Field(min_length=1, max_length=2000)


class SupportMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    customer_id: int | None = None
    email: str
    subject: str
    message: str
    status: SupportStatus
    created_at: datetime


# --- Notifications -------------------------------------------------------

class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    audience: str
    message: str
    level: str
    order_id: int | None = None
    created_at: datetime


# --- Admin/staff users ---------------------------------------------------

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    role: UserRole = UserRole.STAFF


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    id: int
    email: str
    role: UserRole


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6)
