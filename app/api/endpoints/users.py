from fastapi import APIRouter, HTTPException, Depends
from datetime import timedelta

import httpx
from app.models.user import (
    UserCreate,
    UserCreateByGoogle,
    UserResponse,
    Token,
    UserLogin,
    UserUpdate,
)
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

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

SCOPES = "openid email profile"


@router.get("/google-oauth/login")
def login_with_google():
    """Redirects the user to Google's OAuth 2.0 consent screen."""
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{GOOGLE_AUTH_URL}?{'&'.join(f'{k}={v}' for k,v in params.items())}"

    return {"auth_url": auth_url}


@router.get("/google-oauth/callback")
async def auth_callback(code: str, user_service: UserService = Depends()):
    """Handles the OAuth callback and exchanges the authorization code for an access token."""
    async with httpx.AsyncClient() as client:
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        token_response = await client.post(GOOGLE_TOKEN_URL, data=token_data)
        token_json = token_response.json()

        if "access_token" not in token_json:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")

        access_token = token_json["access_token"]

        # Fetch user info
        headers = {"Authorization": f"Bearer {access_token}"}
        user_response = await client.get(GOOGLE_USERINFO_URL, headers=headers)
        user_info = user_response.json()

        try:
            user = await user_service.get_user_by_google_id(user_info["id"])
        except HTTPException:
            user = None

        if user is None:
            user = await user_service.create_user_by_google(
                UserCreateByGoogle(
                    google_id=user_info["id"],
                    email=user_info["email"],
                    name=user_info["name"],
                    avatar=user_info["picture"],
                )
            )
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
