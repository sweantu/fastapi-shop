from datetime import datetime
from bson import Decimal128
from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
from typing import Optional, List
from decimal import Decimal


class CartItemBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    product_id: str
    quantity: int


class CartBase(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: str
    items: List[CartItemBase] = Field(default=[])
    updated_at: Optional[datetime] = None


class CartItemUpsert(BaseModel):
    product_id: str = Field(
        ..., min_length=24, max_length=24, pattern="^[0-9a-fA-F]{24}$"
    )
    quantity: int = Field(..., gt=0, description="Quantity must be greater than 0")


class CartUpsert(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: List[CartItemUpsert] = Field(
        ..., description="Cart items with product_id and quantity only"
    )

    @field_validator("items")
    def validate_unique_product_ids(cls, items):
        product_ids = [item.product_id for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Duplicate product_id found in cart items")
        return items


class CartItemResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    product_id: str
    quantity: int
    name: str  # Product name for quick access
    price: Decimal  # Price at time of adding to cart
    image: Optional[str] = None  # First product image if available
    stock: int


class CartResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    user_id: str
    items: List[CartItemResponse] = Field(default=[])
    updated_at: Optional[datetime] = None
