from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone
from app.models.user import User, UserRole, UserUpdate
from app.core.security import get_token, verify_admin, verify_token
from app.db.mongodb import MongoDB
from bson import ObjectId
from app.core.validators import ObjectIdParam
from math import ceil
from enum import Enum

router = APIRouter()


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


# Get all users with pagination and filters
@router.get("/", response_model=dict)
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    role: Optional[UserRole] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query(
        None, description="Field to sort by (e.g., username, created_at)"
    ),
    sort_order: SortOrder = Query(
        SortOrder.ASC, description="Sort order (asc or desc)"
    ),
    admin: str = Depends(verify_admin),
):
    db = MongoDB.get_db()
    query = {}

    # Apply filters
    if role:
        query["role"] = role
    if search:
        query["$or"] = [
            {"username": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"name": {"$regex": search, "$options": "i"}},
        ]

    try:
        # Get total count
        total = await db.users.count_documents(query)

        # Calculate pagination
        total_pages = ceil(total / size)
        skip = (page - 1) * size

        # Prepare sort
        sort_options = {}
        if sort_by:
            # Convert id to _id for MongoDB
            if sort_by == "id":
                sort_by = "_id"
            sort_options[sort_by] = 1 if sort_order == SortOrder.ASC else -1

        # Get paginated and sorted users
        cursor = db.users.find(query)

        # Apply sort if specified
        if sort_options:
            cursor = cursor.sort(list(sort_options.items()))

        # Apply pagination
        cursor = cursor.skip(skip).limit(size)

        # Process results
        users = []
        async for user in cursor:
            user["id"] = str(user.pop("_id"))
            users.append(user)

        # Prepare response
        return {
            "items": users,
            "total": total,
            "page": page,
            "size": size,
            "pages": total_pages,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }

    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=400, detail=f"Invalid sort field: {sort_by}"
            )
        raise HTTPException(status_code=500, detail=f"Error fetching users: {str(e)}")


# Get user by ID
@router.get("/{user_id}", response_model=User)
async def get_user(user_id: ObjectIdParam, admin: str = Depends(verify_admin)):
    db = MongoDB.get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user["id"] = str(user.pop("_id"))
    return user


# Update user
@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: ObjectIdParam,
    user_data: UserUpdate,
    admin: str = Depends(verify_admin),
):
    db = MongoDB.get_db()

    update_data = user_data.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc)

    result = await db.users.find_one_and_update(
        {"_id": ObjectId(user_id)}, {"$set": update_data}, return_document=True
    )

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    result["id"] = str(result.pop("_id"))
    return result


# Soft delete user
@router.delete("/{user_id}")
async def delete_user(
    user_id: ObjectIdParam,
    admin: str = Depends(verify_admin),
):
    db = MongoDB.get_db()
    result = await db.users.find_one_and_update(
        {"_id": ObjectId(user_id)},
        {"$set": {"deleted_at": datetime.now(timezone.utc)}},
        return_document=True,
    )

    if not result:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User deleted successfully"}
