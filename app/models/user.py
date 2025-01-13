from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ConfigDict,
    field_serializer,
    field_validator,
)
from datetime import datetime
from typing import Optional
from enum import Enum
from decimal import Decimal
from bson.decimal128 import Decimal128


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    role: UserRole = UserRole.USER  # Default role for new users
    avatar: Optional[str] = None

class User(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    username: str
    name: str
    email: EmailStr
    avatar: Optional[str] = None
    balance: Decimal = Field(default=Decimal("0.00"), ge=0)
    role: UserRole
    created_at: datetime
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

    @field_validator("balance", mode="before")
    def validate_balance(cls, v):
        if isinstance(v, Decimal128):
            v = str(v)
        return Decimal(str(v)).quantize(Decimal("0.01"))


class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


class UserUpdate(BaseModel):

    name: Optional[str] = Field(None, min_length=2)
    avatar: Optional[str] = None


class UserUpdateByAdmin(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: Optional[str] = Field(None, min_length=2)
    avatar: Optional[str] = None
    balance: Optional[Decimal] = Field(None, ge=0)

    @field_validator("balance")
    def validate_balance(cls, v):
        if v is not None:
            return Decimal(str(v)).quantize(Decimal("0.01"))
        return v

    @field_serializer("balance")
    def serialize_balance(self, balance: Decimal) -> Decimal128:
        return Decimal128(str(balance))
