from .base import Migration


class AddCartIndexesMigration(Migration):
    version = "20250111_001_add_cart_indexes"
    description = "Add indexes to carts collection"

    @classmethod
    async def up(cls, db):
        """
        Create indexes on carts collection
        """
        # Create unique index
        await db.carts.create_index("user_id", unique=True, background=True)

    @classmethod
    async def down(cls, db):
        """
        Remove indexes from carts collection
        """
        await db.carts.drop_index("user_id_1")
