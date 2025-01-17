from fastapi import APIRouter, HTTPException, Depends
from datetime import timedelta
from app.models.user import UserCreate, UserResponse, Token, UserLogin, UserUpdate
from app.core.security import get_current_user, create_access_token
from app.core.config import settings
from app.services.user import UserService
from app.utils.auth import verify_password

router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, user_service: UserService = Depends()):
    """Register a new user"""
    return await user_service.create_user(user_data)


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, user_service: UserService = Depends()):
    """Login user and return access token"""
    try:
        user = await user_service.get_user_by_username(user_data.username)
    except HTTPException:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    if not verify_password(user_data.password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: UserResponse = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: UserResponse = Depends(get_current_user),
    user_service: UserService = Depends(),
):
    """Update current user information"""
    # Validate avatar URL if provided
    if user_data.avatar is not None:
        if user_data.avatar and not user_data.avatar.startswith(
            settings.AWS_BUCKET_URL
        ):
            raise HTTPException(status_code=400, detail="Invalid avatar URL")

    return await user_service.update_user(current_user.id, user_data)
