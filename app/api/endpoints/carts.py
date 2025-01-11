from fastapi import APIRouter, HTTPException, Depends
from app.models.cart import Cart, CartItem, CartUpsert
from app.core.security import get_current_user
from app.models.user import User
from app.db.mongodb import MongoDB
from bson import ObjectId
from datetime import datetime, timezone
from decimal import Decimal

router = APIRouter()


@router.get("/", response_model=Cart)
async def get_cart(current_user: User = Depends(get_current_user)):
    """Get user's cart"""
    db = MongoDB.get_db()

    cart = await db.carts.find_one({"user_id": current_user.id})
    if not cart:
        # Create empty cart if doesn't exist
        cart = {
            "user_id": current_user.id,
            "items": [],
            "updated_at": datetime.now(timezone.utc),
        }
        await db.carts.insert_one(cart)
    return Cart.model_validate(cart)


@router.put("/", response_model=Cart)
async def upsert_cart(
    cart_upsert: CartUpsert, current_user: User = Depends(get_current_user)
):
    """Update or insert cart items"""
    db = MongoDB.get_db()

    cart_items = [item.model_dump() for item in cart_upsert.items]
    # Validate all products and stock
    for item in cart_items:
        product = await db.products.find_one(
            {
                "_id": ObjectId(item["product_id"]),
                "status": "active",
                "deleted_at": None,
            }
        )

        if not product:
            raise HTTPException(
                status_code=404, detail=f"Product not found: {item['product_id']}"
            )

        if product["stock"] < item["quantity"]:
            raise HTTPException(
                status_code=400,
                detail=f"Not enough stock for product: {product['name']}",
            )

        # Update item with current product info
        item["name"] = product["name"]
        item["price"] = product["price"]
        item["image"] = product["images"][0] if product.get("images") else None

    # Update cart
    cart = await db.carts.find_one_and_update(
        {"user_id": current_user.id},
        {
            "$set": {
                "items": cart_items,
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
        return_document=True,
    )

    return Cart.model_validate(cart)
