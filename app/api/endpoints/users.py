from fastapi import APIRouter, HTTPException, Depends
from datetime import timedelta, timezone
from app.models.user import UserCreate, User, Token, UserLogin, UserUpdate
from app.core.security import (
    get_current_user,
    verify_password,
    create_access_token,
    hash_password,
    verify_token,
)
from app.db.mongodb import MongoDB
from app.core.config import settings
from datetime import datetime
from bson import Decimal128, ObjectId
from app.models.transaction import TransactionCreate, TransactionType, Transaction
from app.services.transaction import TransactionService
from decimal import Decimal
from typing import List

router = APIRouter()


@router.post("/register", response_model=User)
async def register_user(user_data: UserCreate):
    db = MongoDB.get_db()

    if await db.users.find_one({"username": user_data.username}):
        raise HTTPException(status_code=400, detail="Username already registered")

    if await db.users.find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")

    user_dict = user_data.model_dump()
    user_dict.update(
        {
            "password": hash_password(user_dict["password"]),
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
            "deleted_at": None,
            "balance": Decimal128("0.00"),
        }
    )

    result = await db.users.insert_one(user_dict)
    created_user = await db.users.find_one({"_id": result.inserted_id})
    created_user["id"] = str(created_user.pop("_id"))

    return created_user


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    db = MongoDB.get_db()

    user = await db.users.find_one({"username": user_data.username})
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    if not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def read_users_me(user: User = Depends(get_current_user)):
    return user


@router.put("/me", response_model=User)
async def update_current_user(
    user_data: UserUpdate, user: User = Depends(get_current_user)
):
    db = MongoDB.get_db()
    update_data = user_data.model_dump(exclude_unset=True)

    # Validate avatar URL if provided
    if user_data.avatar is not None:
        if user_data.avatar and not user_data.avatar.startswith(
            settings.AWS_BUCKET_URL
        ):
            raise HTTPException(status_code=400, detail="Invalid avatar URL")

    update_data["updated_at"] = datetime.now(timezone.utc)

    result = await db.users.find_one_and_update(
        {"username": user.username}, {"$set": update_data}, return_document=True
    )

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    result["id"] = str(result.pop("_id"))
    return result


@router.post("/deposit", response_model=Transaction)
async def deposit_money(
    amount: Decimal,
    description: str | None = None,
    current_user: User = Depends(get_current_user),
    transaction_service: TransactionService = Depends(),
):
    """
    Deposit money to user balance
    """
    transaction_data = TransactionCreate(
        type=TransactionType.DEPOSIT, amount=amount, description=description
    )

    return await transaction_service.create_transaction(
        user_id=current_user.id, transaction_data=transaction_data
    )


@router.post("/withdraw", response_model=Transaction)
async def withdraw_money(
    amount: Decimal,
    description: str | None = None,
    current_user: User = Depends(get_current_user),
    transaction_service: TransactionService = Depends(),
):
    """
    Withdraw money from user balance
    """
    transaction_data = TransactionCreate(
        type=TransactionType.WITHDRAW, amount=amount, description=description
    )

    return await transaction_service.create_transaction(
        user_id=current_user.id, transaction_data=transaction_data
    )


@router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    skip: int = 0,
    limit: int = 50,
    transaction_type: TransactionType | None = None,
    current_user: User = Depends(get_current_user),
    transaction_service: TransactionService = Depends(),
):
    """
    Get user's transaction history
    """
    return await transaction_service.get_user_transactions(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        transaction_type=transaction_type,
    )
