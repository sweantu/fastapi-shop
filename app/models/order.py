from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from decimal import Decimal
from enum import Enum
from bson import Decimal128


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class OrderItemBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    product_id: str = Field(..., min_length=24, max_length=24)
    quantity: int = Field(..., gt=0)
    price: Decimal  # Price at time of order
    name: str  # Product name at time of order
    image: Optional[str] = None

    @field_validator("price", mode="before")
    def validate_price(cls, v):
        # Convert Decimal128 to string before validation
        if isinstance(v, Decimal128):
            v = str(v)
        return Decimal(str(v)).quantize(Decimal("0.01"))


class OrderBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    user_id: str
    items: List[OrderItemBase]
    total_amount: Decimal
    shipping_address: str
    note: Optional[str] = None
    status: OrderStatus
    payment_status: PaymentStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    tracking_number: Optional[str] = None

    @field_validator("total_amount", mode="before")
    def validate_price(cls, v):
        # Convert Decimal128 to string before validation
        if isinstance(v, Decimal128):
            v = str(v)
        return Decimal(str(v)).quantize(Decimal("0.01"))


class OrderItemCreate(BaseModel):
    product_id: str = Field(
        ..., min_length=24, max_length=24, pattern="^[0-9a-fA-F]{24}$"
    )
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")


class OrderCreate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: List[OrderItemCreate] = Field(..., min_items=1)
    shipping_address: str = Field(..., min_length=10)
    note: Optional[str] = None

    @field_validator("items")
    def validate_unique_products(cls, items):
        product_ids = [item.product_id for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Duplicate products in order")
        return items


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    note: Optional[str] = None


class OrderAdminUpdate(OrderUpdate):
    shipping_address: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None


class OrderSummary(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    total_amount: Decimal
    status: OrderStatus
    payment_status: PaymentStatus
    created_at: datetime
    items_count: int = Field(..., description="Number of items in order")

    @field_validator("total_amount")
    def validate_total(cls, v):
        if v is not None:
            return Decimal(str(v)).quantize(Decimal("0.01"))
        return v


class OrderStats(BaseModel):
    total_orders: int
    total_amount: Decimal
    pending_orders: int
    completed_orders: int
    cancelled_orders: int
    average_order_amount: Decimal

    @field_validator("total_amount", "average_order_amount")
    def validate_amounts(cls, v):
        if v is not None:
            return Decimal(str(v)).quantize(Decimal("0.01"))
        return v
