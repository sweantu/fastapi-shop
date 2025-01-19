from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.security import get_current_user
from app.models.order import OrderStatus, PaymentStatus
from app.models.product import ProductStatus
from app.models.transaction import (
    TransactionCreate,
    TransactionDeposit,
    TransactionStatus,
    TransactionType,
    TransactionBase,
    TransactionWithdraw,
)
from app.models.user import UserResponse
from app.services.product import ProductService
from app.services.transaction import TransactionService
from app.services.user import UserService
from app.services.order import OrderService
from decimal import Decimal
from typing import Literal, Optional, Union

router = APIRouter()


@router.post("/deposit", response_model=TransactionBase)
async def deposit_money(
    transaction_deposit: TransactionDeposit,
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(),
    user_service: UserService = Depends(),
):
    """Deposit money to user balance"""
    CURRENT_BALANCE = current_user.balance
    transaction_data = TransactionCreate(
        type=TransactionType.DEPOSIT,
        amount=transaction_deposit.amount,
        description=transaction_deposit.description,
    )

    try:
        # Update user balance first (atomic operation)
        await user_service.update_balance(
            user_id=current_user.id,
            current_balance=CURRENT_BALANCE,
            amount=transaction_deposit.amount,
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
    transaction_withdraw: TransactionWithdraw,
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(),
    user_service: UserService = Depends(),
):
    """Withdraw money from user balance"""
    CURRENT_BALANCE = current_user.balance
    transaction_data = TransactionCreate(
        type=TransactionType.WITHDRAW,
        amount=transaction_withdraw.amount,
        description=transaction_withdraw.description,
    )

    try:
        # Update user balance first (atomic operation)
        await user_service.update_balance(
            user_id=current_user.id,
            current_balance=CURRENT_BALANCE,
            amount=transaction_withdraw.amount,
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
    type: Optional[Union[TransactionType, Literal[""]]] = Query(
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
            transaction_type=type,
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


@router.post("/order-payment/{order_id}", response_model=TransactionBase)
async def order_payment(
    order_id: str,
    current_user: UserResponse = Depends(get_current_user),
    transaction_service: TransactionService = Depends(),
    order_service: OrderService = Depends(),
    user_service: UserService = Depends(),
    product_service: ProductService = Depends(),
):
    """Order payment using balance"""
    CURRENT_BALANCE = current_user.balance

    # Get order details first
    order = await order_service.get_order_by_id(order_id, current_user.id)

    # Validate order status
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Order is not pending")
    if order.payment_status not in [PaymentStatus.PENDING, PaymentStatus.FAILED]:
        raise HTTPException(status_code=400, detail="Order is not pending or failed")

    # Validate user balance
    if CURRENT_BALANCE < order.total_amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")

    # Validate order items in stock
    products = await product_service.get_products_by_ids(
        [item.product_id for item in order.items]
    )
    if len(products) != len(order.items):
        raise HTTPException(status_code=400, detail="Some products not found")

    product_map = {product.id: product for product in products}
    for item in order.items:
        product = product_map.get(item.product_id)
        if product.status != ProductStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Product is not active")
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")

    transaction_data = TransactionCreate(
        type=TransactionType.PAYMENT,
        amount=order.total_amount,
        description=f"Payment for order #{order_id}",
    )

    try:
        # Update user balance first (atomic operation)
        await user_service.update_balance(
            user_id=current_user.id,
            current_balance=CURRENT_BALANCE,
            amount=order.total_amount,
            operation="subtract",
        )

        # Insert transaction
        transaction = await transaction_service.create_transaction(
            transaction_data=transaction_data,
            user_id=current_user.id,
            current_balance=CURRENT_BALANCE,
        )

        await order_service.update_order_payment_status(
            order_id, PaymentStatus.PAID, transaction.id
        )

    except Exception as e:
        # Log the error here
        await order_service.update_order_payment_status(order_id, PaymentStatus.FAILED)
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")

    try:
        # Update product stock after order payment
        await product_service.update_stock_after_order_payment(order)

        # Update order status
        await order_service.update_order_status(order_id, OrderStatus.CONFIRMED)

        return transaction

    except Exception as e:
        # Log the error here
        await order_service.update_order_status(order_id, OrderStatus.FAILED)
        raise HTTPException(status_code=500, detail=f"Transaction failed: {str(e)}")
