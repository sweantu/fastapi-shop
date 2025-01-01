import asyncio
import importlib
import os
from datetime import datetime, timezone
from app.db.mongodb import MongoDB

# List of migrations in order
MIGRATIONS = [
    "20250101_001_add_user_roles.AddUserRolesMigration",
    "20250101_002_add_user_indexes.AddUserIndexesMigration",
]


async def run_migrations():
    try:
        await MongoDB.connect_db()
        db = MongoDB.get_db()

        # Create migrations collection if it doesn't exist
        if "migrations" not in await db.list_collection_names():
            await db.create_collection("migrations")
            await db.migrations.create_index("version", unique=True)

        for migration_path in MIGRATIONS:
            # Import migration class
            module_path, class_name = migration_path.rsplit(".", 1)
            module = importlib.import_module(f"app.scripts.migrations.{module_path}")
            migration_class = getattr(module, class_name)

            # Check if migration has been run
            if not await db.migrations.find_one({"version": migration_class.version}):
                print(
                    f"Running migration {migration_class.version}: {migration_class.description}"
                )

                try:
                    # Run migration
                    await migration_class.up(db)

                    # Record successful migration
                    await db.migrations.insert_one(
                        {
                            "version": migration_class.version,
                            "description": migration_class.description,
                            "executed_at": datetime.now(timezone.utc),
                        }
                    )
                    print(f"Completed migration {migration_class.version}")
                except Exception as e:
                    print(f"Error in migration {migration_class.version}: {str(e)}")
                    raise e
            else:
                print(
                    f"Skipping migration {migration_class.version} (already executed)"
                )

    except Exception as e:
        print(f"Migration error: {str(e)}")
        raise e
    finally:
        await MongoDB.close_db()


if __name__ == "__main__":
    asyncio.run(run_migrations())
