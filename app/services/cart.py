from app.models.cart import CartBase, CartUpsert, CartItemResponse, CartResponse
from app.db.mongodb import MongoDB
from fastapi import HTTPException
from datetime import datetime, timezone
from bson import ObjectId, Decimal128
from decimal import Decimal
from typing import List, Optional


class CartService:
    def __init__(self):
        self.db = MongoDB.get_db()

    async def get_cart(self, user_id: str) -> CartBase:
        """Get user's cart with product details"""
        # Get cart or create if doesn't exist
        cart = await self.db.carts.find_one({"user_id": user_id})
        if not cart:
            cart = {
                "user_id": user_id,
                "items": [],
                "updated_at": datetime.now(timezone.utc),
            }
            await self.db.carts.insert_one(cart)

        return CartBase(**cart)

    async def upsert_cart(self, user_id: str, cart_data: CartUpsert) -> CartBase:
        """Update or insert cart items"""

        # Update cart
        cart = await self.db.carts.find_one_and_update(
            {"user_id": user_id},
            {
                "$set": {
                    "items": [item.model_dump() for item in cart_data.items],
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
            return_document=True,
        )
        return CartBase(**cart)

    async def clear_cart(self, user_id: str) -> bool:
        """Clear all items from user's cart"""
        result = await self.db.carts.find_one_and_update(
            {"user_id": user_id},
            {"$set": {"items": [], "updated_at": datetime.now(timezone.utc)}},
            return_document=True,
        )
        return bool(result)

    async def validate_cart(self, user_id: str) -> bool:
        """Validate cart items stock availability"""
        cart = await self.db.carts.find_one({"user_id": user_id})
        if not cart or not cart["items"]:
            return True

        product_ids = [ObjectId(item["product_id"]) for item in cart["items"]]
        async for product in self.db.products.find({"_id": {"$in": product_ids}}):
            cart_item = next(
                (
                    item
                    for item in cart["items"]
                    if item["product_id"] == str(product["_id"])
                ),
                None,
            )
            if cart_item and product["stock"] < cart_item["quantity"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for product: {product['name']}",
                )

        return True
