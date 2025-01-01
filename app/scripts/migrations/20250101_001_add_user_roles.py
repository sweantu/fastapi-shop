from .base import Migration
from datetime import datetime, timezone


class AddUserRolesMigration(Migration):
    version = "20250101_001_add_user_roles"
    description = "Add user roles and soft delete"

    @classmethod
    async def up(cls, db):
        # Update existing users with new fields
        await db.users.update_many(
            {"role": {"$exists": False}},
            {
                "$set": {
                    "role": "user",
                    "deleted_at": None,
                }
            },
        )

        # Create admin if not exists
        admin = await db.users.find_one({"role": "admin"})
        if not admin:
            from app.core.security import hash_password

            admin_user = {
                "username": "admin",
                "password": hash_password("123456"),
                "email": "admin@example.com",
                "name": "Admin User",
                "role": "admin",
                "created_at": datetime.now(timezone.utc),
                "updated_at": None,
                "deleted_at": None,
            }
            await db.users.insert_one(admin_user)

    @classmethod
    async def down(cls, db):
        # Remove roles and soft delete
        await db.users.update_many(
            {},
            {
                "$unset": {
                    "role": "",
                    "deleted_at": "",
                }
            },
        )

        # remove admin
        await db.users.delete_one({"username": "admin"})
