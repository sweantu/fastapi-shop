from .base import Migration
from datetime import datetime


class AddUserIndexesMigration(Migration):
    version = "20250101_002_add_user_indexes"
    description = "Add indexes for user collection"

    @classmethod
    async def up(cls, db):
        # Create indexes
        await db.users.create_index("username", unique=True)
        await db.users.create_index("email", unique=True)

    @classmethod
    async def down(cls, db):
        # Drop indexes
        await db.users.drop_index("username_1")
        await db.users.drop_index("email_1")
