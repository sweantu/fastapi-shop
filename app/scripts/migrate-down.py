import asyncio
import importlib
import os
from datetime import datetime
from app.db.mongodb import MongoDB

# List of migrations in order
MIGRATIONS = []


async def run_migrations_down():
    try:
        await MongoDB.connect_db()
        db = MongoDB.get_db()

        if "migrations" not in await db.list_collection_names():
            raise Exception("Migrations collection not found")

        for migration_path in MIGRATIONS:
            # Import migration class
            module_path, class_name = migration_path.rsplit(".", 1)
            module = importlib.import_module(f"app.scripts.migrations.{module_path}")
            migration_class = getattr(module, class_name)

            if await db.migrations.find_one({"version": migration_class.version}):
                print(
                    f"Running migration down {migration_class.version}: {migration_class.description}"
                )

                try:
                    # Run migration
                    await migration_class.down(db)

                    # Record successful migration
                    await db.migrations.delete_one({"version": migration_class.version})
                    print(f"Completed migration down {migration_class.version}")
                except Exception as e:
                    print(
                        f"Error in migration down {migration_class.version}: {str(e)}"
                    )
                    raise e
            else:
                # migration not found
                print(f"Migration down {migration_class.version} not found")

    except Exception as e:
        print(f"Migration error: {str(e)}")
        raise e
    finally:
        await MongoDB.close_db()


if __name__ == "__main__":
    asyncio.run(run_migrations_down())
