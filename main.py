from typing import Union
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection settings from environment variables
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://admin:password@localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "fastapi-shop")

# Create a database client
client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to MongoDB when the app starts
    global client
    client = AsyncIOMotorClient(MONGODB_URL)
    try:
        # Verify the connection
        await client.admin.command("ping")
        print("Successfully connected to MongoDB")
    except Exception as e:
        print(f"Could not connect to MongoDB: {e}")
        raise e
    yield
    # Close MongoDB connection when the app stops
    if client is not None:
        client.close()


app = FastAPI(lifespan=lifespan)


# Helper function to get database
def get_database():
    return client[DB_NAME]


@app.get("/")
async def read_root():
    # Example of using MongoDB
    db = get_database()
    count = await db.test_collection.count_documents({})
    return {"Hello": "World", "documents_count": count}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


# Example of a MongoDB operation
@app.post("/items/")
async def create_item(name: str):
    db = get_database()
    result = await db.test_collection.insert_one({"name": name})
    return {"id": str(result.inserted_id), "name": name}
