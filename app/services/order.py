from app.models.order import (
    OrderBase,
    OrderCreate,
    OrderUpdate,
    OrderAdminUpdate,
    OrderStatus,
    PaymentStatus,
    OrderSummary,
    OrderStats,
)
from app.db.mongodb import MongoDB
from fastapi import HTTPException
from datetime import datetime, timezone
from bson import ObjectId, Decimal128
from decimal import Decimal
from typing import List, Optional, Tuple
from math import ceil

from app.models.product import ProductBase, ProductStatus


class OrderService:
    def __init__(self):
        self.db = MongoDB.get_db()

    async def create_order(
        self, user_id: str, order_data: OrderCreate, products: List[ProductBase]
    ) -> OrderBase:
        """Create a new order"""
        # Prepare order data
        order_dict = order_data.model_dump()
        # Create product lookup dict
        product_map = {str(p.id): p for p in products}

        # Validate all products and update order items with current prices
        for item in order_dict["items"]:
            product = product_map.get(item["product_id"])
            if not product or product.status != ProductStatus.ACTIVE:
                raise HTTPException(
                    status_code=404, detail=f"Product not found: {item['product_id']}"
                )
            if product.stock < item["quantity"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for product: {product.name}",
                )
            # Update item with current product data
            item["price"] = Decimal128(str(product.price))
            item["name"] = product.name
            item["image"] = product.images[0] if product.images else None

        # Calculate total amount
        total_amount = sum(
            Decimal(str(item["price"])) * item["quantity"]
            for item in order_dict["items"]
        )

        # Prepare order document
        order_dict.update(
            {
                "user_id": user_id,
                "total_amount": Decimal128(str(total_amount)),
                "status": OrderStatus.PENDING,
                "payment_status": PaymentStatus.PENDING,
                "created_at": datetime.now(timezone.utc),
                "updated_at": None,
                "cancelled_at": None,
                "shipped_at": None,
                "delivered_at": None,
                "tracking_number": None,
            }
        )

        # Insert order
        result = await self.db.orders.insert_one(order_dict)
        created_order = await self.db.orders.find_one({"_id": result.inserted_id})
        created_order["id"] = str(created_order.pop("_id"))

        return OrderBase.model_validate(created_order)

    async def get_order_by_id(
        self, order_id: str, user_id: Optional[str] = None
    ) -> OrderBase:
        """Get order by ID"""
        query = {"_id": ObjectId(order_id)}
        if user_id:  # If user_id provided, ensure order belongs to user
            query["user_id"] = user_id

        order = await self.db.orders.find_one(query)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        order["id"] = str(order.pop("_id"))
        return OrderBase.model_validate(order)

    async def get_orders(
        self,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        status: Optional[OrderStatus] = None,
        payment_status: Optional[PaymentStatus] = None,
        sort_by: Optional[str] = "created_at",
        sort_order: Optional[str] = "desc",
    ) -> Tuple[List[OrderBase], int]:
        """Get orders with pagination and filtering"""
        # Build query
        query = {}
        if user_id:
            query["user_id"] = user_id
        if status:
            query["status"] = status
        if payment_status:
            query["payment_status"] = payment_status

        # Handle sort parameters
        sort_field = sort_by if sort_by else "created_at"
        sort_direction = -1 if sort_order == "desc" else 1

        # Get total count
        total = await self.db.orders.count_documents(query)

        # Get orders
        cursor = self.db.orders.find(query)
        cursor = cursor.sort(sort_field, sort_direction)
        cursor = cursor.skip(skip).limit(limit)

        orders = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            orders.append(OrderBase.model_validate(doc))

        return orders, total

    async def update_order(
        self,
        order_id: str,
        order_data: OrderUpdate | OrderAdminUpdate,
        user_id: Optional[str] = None,
    ) -> OrderBase:
        """Update order"""
        # Get existing order
        query = {"_id": ObjectId(order_id)}
        if user_id:  # If user_id provided, ensure order belongs to user
            query["user_id"] = user_id

        order = await self.db.orders.find_one(query)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Prepare update data
        update_data = order_data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")

        # Add timestamps based on status changes
        if "status" in update_data:
            update_data["updated_at"] = datetime.now(timezone.utc)
            if update_data["status"] == OrderStatus.CANCELLED:
                update_data["cancelled_at"] = datetime.now(timezone.utc)
            elif update_data["status"] == OrderStatus.SHIPPED:
                update_data["shipped_at"] = datetime.now(timezone.utc)
            elif update_data["status"] == OrderStatus.DELIVERED:
                update_data["delivered_at"] = datetime.now(timezone.utc)

        # Update order
        updated_order = await self.db.orders.find_one_and_update(
            query, {"$set": update_data}, return_document=True
        )

        if not updated_order:
            raise HTTPException(status_code=404, detail="Order not found")

        updated_order["id"] = str(updated_order.pop("_id"))
        return OrderBase.model_validate(updated_order)

    async def get_order_stats(self, user_id: Optional[str] = None) -> OrderStats:
        """Get order statistics"""
        match_stage = {} if user_id is None else {"$match": {"user_id": user_id}}

        pipeline = [
            match_stage,
            {
                "$group": {
                    "_id": None,
                    "total_orders": {"$sum": 1},
                    "total_amount": {"$sum": "$total_amount"},
                    "pending_orders": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", OrderStatus.PENDING]}, 1, 0]
                        }
                    },
                    "completed_orders": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", OrderStatus.DELIVERED]}, 1, 0]
                        }
                    },
                    "cancelled_orders": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", OrderStatus.CANCELLED]}, 1, 0]
                        }
                    },
                }
            },
        ]

        result = await self.db.orders.aggregate(pipeline).to_list(1)
        if not result:
            return OrderStats(
                total_orders=0,
                total_amount=Decimal("0"),
                pending_orders=0,
                completed_orders=0,
                cancelled_orders=0,
                average_order_amount=Decimal("0"),
            )

        stats = result[0]
        total_orders = stats["total_orders"]
        total_amount = Decimal(str(stats["total_amount"]))

        return OrderStats(
            total_orders=total_orders,
            total_amount=total_amount,
            pending_orders=stats["pending_orders"],
            completed_orders=stats["completed_orders"],
            cancelled_orders=stats["cancelled_orders"],
            average_order_amount=(
                total_amount / total_orders if total_orders > 0 else Decimal("0")
            ),
        )

    async def update_order_payment_status(
        self, order_id: str, payment_status: PaymentStatus, transaction_id: str = None
    ) -> None:
        """Update order payment status"""
        update_data = {
            "payment_status": payment_status,
            "updated_at": datetime.now(timezone.utc),
        }
        if transaction_id:
            update_data["transaction_id"] = transaction_id

        result = await self.db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {"$set": update_data},
        )

        if result.modified_count == 0:
            raise HTTPException(
                status_code=400, detail="Failed to update payment status"
            )

    async def update_order_status(self, order_id: str, status: OrderStatus) -> None:
        """Update order status"""
        result = await self.db.orders.update_one(
            {"_id": ObjectId(order_id)},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
        )

        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to update order status")
