from .base import Migration


class AddProductImagesMigration(Migration):
    version = "20250109_001_add_product_images"
    description = "Add images to product collection"

    @classmethod
    async def up(cls, db):
        # Create indexes
        await db.products.update_many(
            {
                "images": {"$exists": False},
            },
            {"$set": {"images": []}},
        )

    @classmethod
    async def down(cls, db):
        # Remove images field from products where images is empty
        await db.products.update_many({"images": []}, {"$unset": {"images": ""}})
