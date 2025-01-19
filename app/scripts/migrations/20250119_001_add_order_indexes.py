from .base import Migration


class AddOrderIndexesMigration(Migration):
    version = "20250119_001_add_order_indexes"
    description = "Add order indexes"

    @classmethod
    async def up(cls, db):
        """
        Add order indexes
        """
        # Create indexes
        await db.orders.create_index("user_id")
        await db.orders.create_index("created_at")
        await db.orders.create_index("status")
        await db.orders.create_index("payment_status")
        await db.orders.create_index(
            [("user_id", 1), ("status", 1), ("created_at", -1)]
        )

    @classmethod
    async def down(cls, db):
        """
        Drop order indexes
        """
        # Drop all non-default indexes
        await db.orders.drop_indexes()
        # Note: This keeps the default _id index
