from math import ceil
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Literal, Optional, Union
from app.models.order import (
    OrderBase,
    OrderCreate,
    OrderUpdate,
    OrderStatus,
    PaymentStatus,
    OrderSummary,
)
from app.models.product import ProductStatus
from app.models.user import UserResponse
from app.core.security import get_current_user
from app.services.order import OrderService
from app.services.product import ProductService
from datetime import datetime

router = APIRouter()


@router.post("/", response_model=OrderBase)
async def create_order(
    order_data: OrderCreate,
    current_user: UserResponse = Depends(get_current_user),
    order_service: OrderService = Depends(),
    product_service: ProductService = Depends(),
):
    """Create a new order"""
    # Validate products existence and stock
    product_ids = [item.product_id for item in order_data.items]
    products = await product_service.get_products_by_ids(product_ids)

    return await order_service.create_order(current_user.id, order_data, products)


@router.get("/", response_model=dict)
async def get_orders(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    status: Optional[Union[OrderStatus, Literal[""]]] = Query(
        None, description="Order status filter"
    ),
    payment_status: Optional[Union[PaymentStatus, Literal[""]]] = Query(
        None, description="Payment status filter"
    ),
    sort_by: Optional[str] = Query("created_at", description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    current_user: UserResponse = Depends(get_current_user),
    order_service: OrderService = Depends(),
):
    """Get user's orders with pagination and filtering"""
    orders, total = await order_service.get_orders(
        user_id=current_user.id,
        skip=(page - 1) * size,
        limit=size,
        status=status,
        payment_status=payment_status,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return {
        "items": orders,
        "total": total,
        "page": page,
        "size": size,
        "pages": ceil(total / size),
        "sort_by": sort_by,
        "sort_order": sort_order,
    }


@router.get("/{order_id}", response_model=OrderBase)
async def get_order(
    order_id: str,
    current_user: UserResponse = Depends(get_current_user),
    order_service: OrderService = Depends(),
):
    """Get order details"""
    return await order_service.get_order_by_id(order_id, current_user.id)


@router.put("/{order_id}", response_model=OrderBase)
async def update_order(
    order_id: str,
    order_data: OrderUpdate,
    current_user: UserResponse = Depends(get_current_user),
    order_service: OrderService = Depends(),
):
    """Update order
    Users can only update certain fields and only if order is in certain states
    """
    # Get current order to check status
    current_order = await order_service.get_order_by_id(order_id, current_user.id)

    # Validate status transitions
    if order_data.status:
        # Users can only cancel pending orders
        if order_data.status == OrderStatus.CANCELLED:
            if current_order.status != OrderStatus.PENDING:
                raise HTTPException(
                    status_code=400, detail="Can only cancel pending orders"
                )
        else:
            raise HTTPException(status_code=403, detail="Users can only cancel orders")

    return await order_service.update_order(order_id, order_data, current_user.id)
