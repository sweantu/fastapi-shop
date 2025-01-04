from .base import Migration


class AddProductIndexesMigration(Migration):
    version = "20250104_001_add_product_indexes"
    description = "Add indexes for product collection"

    @classmethod
    async def up(cls, db):
        # Create indexes
        await db.products.create_index("sku", unique=True)
        await db.products.create_index("name")

    @classmethod
    async def down(cls, db):
        # Drop indexes
        await db.products.drop_index("sku_1")
        await db.products.drop_index("name_1")
