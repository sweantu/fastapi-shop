from app.models.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserUpdateByAdmin,
    UserRole,
)
from app.db.mongodb import MongoDB
from fastapi import HTTPException
from datetime import datetime, timezone
from bson import ObjectId, Decimal128
from decimal import Decimal
from typing import List, Optional
from app.core.security import hash_password
from math import ceil


class UserService:
    def __init__(self):
        self.db = MongoDB.get_db()

    async def create_user(self, user_data: UserCreate) -> UserBase:
        """Create a new user"""
        # Check existing username/email
        if await self.db.users.find_one({"username": user_data.username}):
            raise HTTPException(status_code=400, detail="Username already registered")

        if await self.db.users.find_one({"email": user_data.email}):
            raise HTTPException(status_code=400, detail="Email already registered")

        # Prepare user data
        user_dict = user_data.model_dump()
        user_dict.update(
            {
                "password": hash_password(user_dict["password"]),
                "created_at": datetime.now(timezone.utc),
                "updated_at": None,
                "deleted_at": None,
                "balance": Decimal128("0.00"),
            }
        )

        # Insert user
        result = await self.db.users.insert_one(user_dict)
        created_user = await self.db.users.find_one({"_id": result.inserted_id})
        created_user["id"] = str(created_user.pop("_id"))

        return UserBase.model_validate(created_user)

    async def get_user_by_id(self, user_id: str) -> UserBase:
        """Get user by ID"""
        user = await self.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user["id"] = str(user.pop("_id"))
        return UserBase.model_validate(user)

    async def get_user_by_username(self, username: str) -> UserBase:
        """Get user by username"""
        user = await self.db.users.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user["id"] = str(user.pop("_id"))
        return UserBase.model_validate(user)

    async def update_user(self, user_id: str, user_data: UserUpdate) -> UserBase:
        """Update user data"""
        update_data = user_data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")

        update_data["updated_at"] = datetime.now(timezone.utc)

        result = await self.db.users.find_one_and_update(
            {"_id": ObjectId(user_id)}, {"$set": update_data}, return_document=True
        )

        if not result:
            raise HTTPException(status_code=404, detail="User not found")

        result["id"] = str(result.pop("_id"))
        return UserBase.model_validate(result)

    async def update_balance(
        self, user_id: str, amount: Decimal, operation: str = "add"
    ) -> UserBase:
        """Update user balance (add or subtract)"""
        if operation not in ["add", "subtract"]:
            raise ValueError("Invalid operation. Use 'add' or 'subtract'")

        amount = Decimal(str(amount)).quantize(Decimal("0.01"))
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be positive")

        update_result = await self.db.users.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {
                "$inc": {
                    "balance": Decimal128(
                        str(amount if operation == "add" else -amount)
                    )
                },
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
            return_document=True,
        )

        if not update_result:
            raise HTTPException(status_code=404, detail="User not found")

        update_result["id"] = str(update_result.pop("_id"))
        return UserBase.model_validate(update_result)

    async def soft_delete_user(self, user_id: str) -> bool:
        """Soft delete a user"""
        result = await self.db.users.find_one_and_update(
            {"_id": ObjectId(user_id)},
            {"$set": {"deleted_at": datetime.now(timezone.utc)}},
            return_document=True,
        )
        return bool(result)

    async def get_users(
        self,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: Optional[str] = None,
        role: Optional[UserRole] = None,
    ) -> tuple[List[UserBase], int]:
        """Get users with pagination and filtering"""
        # Build query
        query = {"deleted_at": None}
        if search:
            query["$or"] = [
                {"username": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"name": {"$regex": search, "$options": "i"}},
            ]
        if role:
            query["role"] = role

        # Get total count
        total = await self.db.users.count_documents(query)

        # Get users
        cursor = self.db.users.find(query)
        cursor = cursor.sort(sort_by, -1 if sort_order == "desc" else 1)
        cursor = cursor.skip(skip).limit(limit)

        users = []
        async for doc in cursor:
            doc["id"] = str(doc.pop("_id"))
            users.append(UserBase.model_validate(doc))

        return users, total
