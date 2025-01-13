from .base import Migration
from decimal import Decimal
from bson.decimal128 import Decimal128


class AddUserBalanceMigration(Migration):
    version = "20250113_001_add_user_balance"
    description = "Add balance field to users"

    @classmethod
    async def up(cls, db):
        """
        Add balance field with default 0.00 to all users that don't have it
        """
        await db.users.update_many(
            {"balance": {"$exists": False}}, {"$set": {"balance": Decimal128("0.00")}}
        )

    @classmethod
    async def down(cls, db):
        """
        Remove balance field from all users
        """
        await db.users.update_many(
            {"balance": {"$exists": True}}, {"$unset": {"balance": ""}}
        )
