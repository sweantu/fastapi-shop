from .base import Migration


class CreateTransactionsMigration(Migration):
    version = "20250113_002_create_transactions"
    description = "Create transactions collection and indexes"

    @classmethod
    async def up(cls, db):
        """
        Create transactions collection and indexes
        """
        # Create indexes
        await db.transactions.create_index("user_id")
        await db.transactions.create_index("created_at")
        await db.transactions.create_index([("user_id", 1), ("created_at", -1)])
        await db.transactions.create_index("reference_id")
        await db.transactions.create_index([("user_id", 1), ("type", 1), ("status", 1)])

    @classmethod
    async def down(cls, db):
        """
        Drop transactions collection
        """
        await db.transactions.drop()
