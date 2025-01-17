from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings
from app.models.user import UserBase, UserRole
from app.services.user import UserService

oauth2_scheme = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_token(token: HTTPAuthorizationCredentials = Depends(oauth2_scheme)) -> str:
    return token.credentials


async def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")


async def get_current_user(
    token: str = Depends(get_token), user_service: UserService = Depends()
) -> UserBase:
    username = await verify_token(token)
    user = await user_service.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# Admin middleware
async def get_current_admin(
    user: UserBase = Depends(get_current_user),
) -> UserBase:
    if not user or user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Not authorized to access admin resources"
        )
    return user
