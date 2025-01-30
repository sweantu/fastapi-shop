from .base import Migration


class AddUserGoogleIdMigration(Migration):
    version = "20250130_001_add_user_google_id"
    description = "Add user google id"

    @classmethod
    async def up(cls, db):
        """
        Add user google id
        """
        # Create indexes
        await db.users.create_index("google_id")

    @classmethod
    async def down(cls, db):
        """
        Drop user google id
        """
        # Drop indexes
        await db.users.drop_index("google_id")
