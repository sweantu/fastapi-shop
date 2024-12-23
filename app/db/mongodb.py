from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


class MongoDB:
    client: AsyncIOMotorClient = None

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        if cls.client is None:
            cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
        return cls.client

    @classmethod
    def get_db(cls):
        return cls.client[settings.DB_NAME]

    @classmethod
    async def connect_db(cls):
        cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
        try:
            await cls.client.admin.command("ping")
            print("Successfully connected to MongoDB")
        except Exception as e:
            print(f"Could not connect to MongoDB: {e}")
            raise e

    @classmethod
    async def close_db(cls):
        if cls.client is not None:
            cls.client.close()
