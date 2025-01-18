from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import get_current_user
from app.models.transaction import (
    TransactionCreate,
    TransactionStatus,
    TransactionType,
    TransactionBase,
)
from app.models.user import UserResponse
from app.services.transaction import TransactionService
from app.services.user import UserService
from decimal import Decimal
from typing import List, Literal, Optional, Union

router = APIRouter()


@router.post("/deposit", response_model=TransactionBase)
async def deposit_money(
    amount: Decimal,
    description: str | None = None,
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(),
    user_service: UserService = Depends(),
):
    """Deposit money to user balance"""
    CURRENT_BALANCE = current_user.balance
    transaction_data = TransactionCreate(
        type=TransactionType.DEPOSIT, amount=amount, description=description
    )

    try:
        # Update user balance first (atomic operation)
        await user_service.update_balance(
            user_id=current_user.id,
            current_balance=CURRENT_BALANCE,
            amount=amount,
            operation="add",
        )

        # Insert transaction
        return await transaction_service.create_transaction(
            transaction_data=transaction_data,
            user_id=current_user.id,
            current_balance=CURRENT_BALANCE,
        )

    except Exception as e:
        # Log the error here
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")


@router.post("/withdraw", response_model=TransactionBase)
async def withdraw_money(
    amount: Decimal,
    description: str | None = None,
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(),
    user_service: UserService = Depends(),
):
    """Withdraw money from user balance"""
    CURRENT_BALANCE = current_user.balance
    transaction_data = TransactionCreate(
        type=TransactionType.WITHDRAW, amount=amount, description=description
    )

    try:
        # Update user balance first (atomic operation)
        await user_service.update_balance(
            user_id=current_user.id,
            current_balance=CURRENT_BALANCE,
            amount=amount,
            operation="subtract",
        )

        # Insert transaction
        return await transaction_service.create_transaction(
            transaction_data=transaction_data,
            user_id=current_user.id,
            current_balance=CURRENT_BALANCE,
        )

    except Exception as e:
        # Log the error here
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")


@router.get("/", response_model=dict)
async def get_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    transaction_type: Optional[Union[TransactionType, Literal[""]]] = Query(
        None, description="Transaction type"
    ),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    min_amount: Optional[Decimal] = Query(None, ge=0, description="Minimum amount"),
    max_amount: Optional[Decimal] = Query(None, ge=0, description="Maximum amount"),
    status: Optional[Union[TransactionStatus, Literal[""]]] = Query(
        None, description="Transaction status"
    ),
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(),
):
    """Get user's transaction history with pagination, filtering and sorting"""
    try:
        # Get transactions with pagination and filters
        transactions, total = await transaction_service.get_user_transactions(
            user_id=current_user.id,
            skip=(page - 1) * size,
            limit=size,
            transaction_type=transaction_type,
            sort_by=sort_by,
            sort_order=sort_order,
            min_amount=min_amount,
            max_amount=max_amount,
            status=status,
        )

        # Calculate total pages
        total_pages = (total + size - 1) // size

        return {
            "items": transactions,
            "total": total,
            "page": page,
            "size": size,
            "pages": total_pages,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }

    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=400, detail=f"Invalid sort field: {sort_by}"
            )
        raise HTTPException(
            status_code=500, detail=f"Error fetching transactions: {str(e)}"
        )
