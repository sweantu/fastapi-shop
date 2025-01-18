from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from app.models.user import UserResponse, UserRole, UserUpdateByAdmin, UserBase
from app.core.security import get_current_admin
from app.core.validators import ObjectIdParam
from app.services.user import UserService
from enum import Enum

router = APIRouter()


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


@router.get("/", response_model=dict)
async def get_users(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    role: Optional[UserRole] = Query(None, description="User role"),
    search: Optional[str] = Query(None, description="Search term"),
    sort_by: Optional[str] = Query(
        None, description="Field to sort by (e.g., username, created_at)"
    ),
    sort_order: SortOrder = Query(
        SortOrder.ASC, description="Sort order (asc or desc)"
    ),
    admin: UserBase = Depends(get_current_admin),
    user_service: UserService = Depends(),
):
    """Get all users with pagination and filters"""
    try:
        # Get users with pagination and filters
        users, total = await user_service.get_users(
            skip=(page - 1) * size,
            limit=size,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            role=role,
        )

        # Calculate pagination info
        total_pages = (total + size - 1) // size
        # Prepare response
        return {
            "items": [UserResponse.model_validate(user.model_dump()) for user in users],
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


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: ObjectIdParam,
    admin: UserBase = Depends(get_current_admin),
    user_service: UserService = Depends(),
):
    """Get user by ID"""
    user = await user_service.get_user_by_id(str(user_id))
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: ObjectIdParam,
    user_data: UserUpdateByAdmin,
    admin: UserBase = Depends(get_current_admin),
    user_service: UserService = Depends(),
):
    """Update user data by admin"""
    updated_user = await user_service.update_user(str(user_id), user_data)
    return updated_user


@router.delete("/{user_id}")
async def delete_user(
    user_id: ObjectIdParam,
    admin: UserBase = Depends(get_current_admin),
    user_service: UserService = Depends(),
):
    """Soft delete user"""
    success = await user_service.soft_delete_user(str(user_id))
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User deleted successfully"}
