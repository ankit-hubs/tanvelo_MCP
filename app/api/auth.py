"""
Authentication Router and User Resolution Dependency
Provides API key creation, verification, listing, revocation, and user introspection.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User
from app.models.api_key import ApiKey
from app.models.memory import Memory
from app.schemas.auth import ApiKeyCreate, ApiKeyResponse, ApiKeyListItem, ApiKeyRevokeResponse, UserInfo
from app.services.auth_service import (
    create_user_and_api_key,
    validate_api_key,
    list_user_api_keys,
    revoke_user_api_key
)

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


async def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key_query: Optional[str] = Query(None, alias="api_key"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extracts and authenticates API key from Authorization header, X-API-Key header, or query param.
    """
    token = None
    if auth_header and auth_header.credentials:
        token = auth_header.credentials
    elif x_api_key:
        token = x_api_key
    elif api_key_query:
        token = api_key_query

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Tanvelo API Key. Provide via 'Authorization: Bearer tv_live_...' or 'X-API-Key: tv_live_...' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await validate_api_key(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked Tanvelo API Key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post("/keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(request: ApiKeyCreate, db: AsyncSession = Depends(get_db)):
    """Generates a new Tanvelo API key for a user/tool."""
    user, key_model, raw_key = await create_user_and_api_key(
        db=db,
        email=request.email,
        key_name=request.name
    )

    return ApiKeyResponse(
        api_key=raw_key,
        key_id=key_model.id,
        user_id=user.id,
        name=key_model.name,
        created_at=key_model.created_at
    )


@router.get("/keys", response_model=List[ApiKeyListItem])
async def list_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lists all API keys belonging to authenticated user with masked display."""
    return await list_user_api_keys(db=db, user_id=user.id)


@router.delete("/keys/{key_id}", response_model=ApiKeyRevokeResponse)
async def revoke_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Revokes an active API key."""
    revoked = await revoke_user_api_key(db=db, user_id=user.id, key_id=key_id)
    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active API key '{key_id}' not found or already revoked."
        )
    return ApiKeyRevokeResponse(
        success=True,
        key_id=key_id,
        message=f"API key '{key_id}' revoked successfully."
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Returns details and active memory stats for the authenticated user."""
    keys_res = await db.execute(
        select(func.count(ApiKey.id)).where(ApiKey.user_id == user.id, ApiKey.revoked_at.is_(None))
    )
    keys_count = keys_res.scalar() or 0

    mems_res = await db.execute(
        select(func.count(Memory.id)).where(Memory.user_id == user.id)
    )
    mems_count = mems_res.scalar() or 0

    return UserInfo(
        user_id=user.id,
        email=user.email,
        created_at=user.created_at,
        active_keys_count=keys_count,
        memories_count=mems_count
    )
