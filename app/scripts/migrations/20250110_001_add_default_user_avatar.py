from .base import Migration


class AddDefaultUserAvatarMigration(Migration):
    version = "20250110_001_add_default_user_avatar"
    description = "Add default user avatar"

    @classmethod
    async def up(cls, db):
        """
        Add avatar field with default null to all users that don't have it
        """
        await db.users.update_many(
            {"avatar": {"$exists": False}}, {"$set": {"avatar": None}}
        )

    @classmethod
    async def down(cls, db):
        """
        Remove avatar field from all users
        """
        await db.users.update_many(
            {"avatar": {"$exists": True}}, {"$unset": {"avatar": ""}}
        )
