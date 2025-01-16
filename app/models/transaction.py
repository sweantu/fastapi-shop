from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
from datetime import datetime
from typing import Optional
from decimal import Decimal
from bson.decimal128 import Decimal128
from enum import Enum


class TransactionType(str, Enum):
    DEPOSIT = "deposit"  # Add money to balance
    WITHDRAW = "withdraw"  # Remove money from balance
    PAYMENT = "payment"  # Payment for order
    REFUND = "refund"  # Refund from order


class TransactionStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Transaction(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    user_id: str
    type: TransactionType
    amount: Decimal
    balance: Decimal  # Balance after transaction
    status: TransactionStatus
    description: Optional[str] = None
    reference_id: Optional[str] = None  # For order_id, payment_id etc.
    created_at: datetime
    updated_at: Optional[datetime] = None

    @field_validator("amount", "balance", mode="before")
    def validate_decimal(cls, v):
        if isinstance(v, Decimal128):
            v = str(v)
        return Decimal(str(v)).quantize(Decimal("0.01"))


class TransactionCreate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: TransactionType
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = None
    reference_id: Optional[str] = None

    @field_validator("amount")
    def validate_amount(cls, v):
        return Decimal(str(v)).quantize(Decimal("0.01"))
