from bson.decimal128 import Decimal128
from pydantic import BaseModel, Field, field_validator, field_serializer, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


class ProductStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


class ProductCreate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    price: Decimal = Field(..., ge=0)
    stock: int = Field(..., ge=0)
    sku: str = Field(..., min_length=3, max_length=50)
    category: str = Field(..., min_length=1)
    tags: List[str] = Field(default=[])
    images: List[str] = Field(default=[])
    status: ProductStatus = Field(default=ProductStatus.DRAFT)

    @field_validator("price")
    def validate_price(cls, v):
        return Decimal(str(v)).quantize(Decimal("0.01"))

    @field_validator("images")
    def validate_images(cls, v):
        if len(v) > 10:
            raise ValueError("Maximum 10 images allowed per product")
        return v

    @field_serializer("price")
    def serialize_price(self, price: Decimal) -> Decimal128:
        return Decimal128(str(price))


class Product(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    name: str
    description: str
    price: Decimal
    stock: int
    sku: str
    category: str
    tags: List[str]
    images: List[str]
    status: ProductStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    @field_validator("price", mode="before")
    def validate_price(cls, v):
        # Convert Decimal128 to string before validation
        if isinstance(v, Decimal128):
            v = str(v)
        return Decimal(str(v)).quantize(Decimal("0.01"))


class ProductUpdate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    price: Optional[Decimal] = Field(None, ge=0)
    stock: Optional[int] = Field(None, ge=0)
    sku: Optional[str] = Field(None, min_length=3, max_length=50)
    category: Optional[str] = Field(None, min_length=1)
    tags: Optional[List[str]] = None
    images: Optional[List[str]] = None
    status: Optional[ProductStatus] = None

    @field_validator("price")
    def validate_price(cls, v):
        if v is not None:
            return Decimal(str(v)).quantize(Decimal("0.01"))
        return v

    @field_validator("images")
    def validate_images(cls, v):
        if v is not None and len(v) > 10:
            raise ValueError("Maximum 10 images allowed per product")
        return v

    @field_serializer("price")
    def serialize_price(self, price: Optional[Decimal]) -> Optional[Decimal128]:
        if price is not None:
            return Decimal128(str(price))
        return None
