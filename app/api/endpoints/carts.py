from fastapi import APIRouter, HTTPException, Depends
from app.models.cart import Cart, CartItem, CartItemResponse, CartResponse, CartUpsert
from app.core.security import get_current_user
from app.models.product import ProductBase
from app.models.user import UserResponse
from app.db.mongodb import MongoDB
from bson import ObjectId
from datetime import datetime, timezone
from decimal import Decimal

router = APIRouter()


@router.get("/", response_model=CartResponse)
async def get_cart(current_user: UserResponse = Depends(get_current_user)):
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
    if cart["items"]:
        cart_items = []
        async for product in db.products.find(
            {"_id": {"$in": [ObjectId(item["product_id"]) for item in cart["items"]]}}
        ):
            cart_item = next(
                (
                    item
                    for item in cart["items"]
                    if item["product_id"] == str(product["_id"])
                ),
                None,
            )
            if cart_item:
                cart_items.append(
                    CartItemResponse(
                        product_id=str(product["_id"]),
                        quantity=cart_item["quantity"],
                        name=product["name"],
                        price=Decimal(str(product["price"])),
                        image=product["images"][0] if product.get("images") else None,
                        stock=product["stock"],
                    )
                )
        return CartResponse(
            user_id=current_user.id, items=cart_items, updated_at=cart["updated_at"]
        )
    else:
        return CartResponse(
            user_id=current_user.id, items=[], updated_at=cart["updated_at"]
        )


@router.put("/")
async def upsert_cart(
    cart_upsert: CartUpsert, current_user: UserResponse = Depends(get_current_user)
):
    """Update or insert cart items"""
    db = MongoDB.get_db()
    cart = await db.carts.find_one_and_update(
        {"user_id": current_user.id},
        {
            "$set": {
                "items": [item.model_dump() for item in cart_upsert.items],
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
        return_document=True,
    )
    if cart["items"]:
        cart_items = []
        async for product in db.products.find(
            {"_id": {"$in": [ObjectId(item["product_id"]) for item in cart["items"]]}}
        ):
            cart_item = next(
                (
                    item
                    for item in cart["items"]
                    if item["product_id"] == str(product["_id"])
                ),
                None,
            )
            if cart_item:
                cart_items.append(
                    CartItemResponse(
                        product_id=str(product["_id"]),
                        quantity=cart_item["quantity"],
                        name=product["name"],
                        price=Decimal(str(product["price"])),
                        image=product["images"][0] if product.get("images") else None,
                        stock=product["stock"],
                    )
                )
        return CartResponse(
            user_id=current_user.id, items=cart_items, updated_at=cart["updated_at"]
        )
    else:
        return CartResponse(
            user_id=current_user.id, items=[], updated_at=cart["updated_at"]
        )
