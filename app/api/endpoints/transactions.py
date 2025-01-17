from fastapi import APIRouter, Depends
from app.core.security import get_current_user
from app.models.transaction import TransactionCreate, TransactionType, Transaction
from app.models.user import UserResponse
from app.services.transaction import TransactionService
from decimal import Decimal
from typing import List

router = APIRouter()


@router.post("/deposit", response_model=Transaction)
async def deposit_money(
    amount: Decimal,
    description: str | None = None,
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(),
):
    """Deposit money to user balance"""
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
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(),
):
    """Withdraw money from user balance"""
    transaction_data = TransactionCreate(
        type=TransactionType.WITHDRAW, amount=amount, description=description
    )

    return await transaction_service.create_transaction(
        user_id=current_user.id, transaction_data=transaction_data
    )


@router.get("/", response_model=List[Transaction])
async def get_transactions(
    skip: int = 0,
    limit: int = 50,
    transaction_type: TransactionType | None = None,
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(),
):
    """Get user's transaction history"""
    return await transaction_service.get_user_transactions(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        transaction_type=transaction_type,
    )
