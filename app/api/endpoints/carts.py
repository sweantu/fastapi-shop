from fastapi import APIRouter, HTTPException, Depends
from app.models.cart import (
    CartBase,
    CartItemBase,
    CartItemResponse,
    CartResponse,
    CartUpsert,
)
from app.core.security import get_current_user
from app.models.product import ProductBase
from app.models.user import UserBase, UserResponse
from app.db.mongodb import MongoDB
from bson import ObjectId
from datetime import datetime, timezone
from decimal import Decimal

from app.services.cart import CartService
from app.services.product import ProductService
from app.utils.cart import build_cart_response

router = APIRouter()


@router.get("/", response_model=CartResponse)
async def get_cart(
    current_user: UserBase = Depends(get_current_user),
    cart_service: CartService = Depends(),
    product_service: ProductService = Depends(),
):
    """Get user's cart"""
    cart = await cart_service.get_cart(current_user.id)
    products = await product_service.get_products_by_ids(
        [item.product_id for item in cart.items]
    )
    return build_cart_response(cart, products)


@router.put("/")
async def upsert_cart(
    cart_upsert: CartUpsert,
    current_user: UserResponse = Depends(get_current_user),
    cart_service: CartService = Depends(),
    product_service: ProductService = Depends(),
):
    """Update or insert cart items"""
    # Validate product existence and stock
    product_ids = [item.product_id for item in cart_upsert.items]
    products = await product_service.get_products_by_ids(product_ids)

    # Create product lookup dict
    product_map = {str(p.id): p for p in products}

    # Validate all products exist and have sufficient stock
    for item in cart_upsert.items:
        product = product_map.get(item.product_id)
        if not product:
            raise HTTPException(
                status_code=404, detail=f"Product not found: {item.product_id}"
            )
        if product.stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product: {product.name}",
            )

    # Update cart
    cart = await cart_service.upsert_cart(current_user.id, cart_upsert)

    # Build response with product details
    return build_cart_response(cart, products)
