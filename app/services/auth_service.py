"""
Authentication and API Key Service
Handles secure SHA-256 key hashing, tenant validation, key issuance, listing, and revocation.
"""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.api_key import ApiKey
from app.schemas.auth import ApiKeyListItem


def generate_api_key() -> str:
    """Generate a high-entropy Tanvelo live API key."""
    return f"tv_live_{secrets.token_hex(24)}"


def hash_api_key(api_key: str) -> str:
    """Return SHA-256 hash of API key for secure storage."""
    return hashlib.sha256(api_key.strip().encode("utf-8")).hexdigest()


async def create_user_and_api_key(
    db: AsyncSession,
    email: Optional[str] = None,
    key_name: str = "Default Key"
) -> Tuple[User, ApiKey, str]:
    """
    Creates a new user (or links to existing email) and issues a new API key.
    Returns (user, api_key_model, raw_api_key).
    """
    user = None
    if email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()

    if not user:
        user = User(email=email)
        db.add(user)
        await db.flush()

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    api_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        name=key_name,
        created_at=datetime.now(timezone.utc)
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(user)
    await db.refresh(api_key)

    return user, api_key, raw_key


async def validate_api_key(db: AsyncSession, raw_key: str) -> Optional[User]:
    """
    Validates a raw API key and returns the associated User if valid, active, and not revoked.
    """
    if not raw_key or not raw_key.startswith("tv_"):
        return None

    key_hash = hash_api_key(raw_key)
    query = (
        select(ApiKey, User)
        .join(User, ApiKey.user_id == User.id)
        .where(
            ApiKey.key_hash == key_hash,
            ApiKey.revoked_at.is_(None)
        )
    )
    result = await db.execute(query)
    row = result.first()
    if not row:
        return None

    api_key, user = row

    # Update last_used_at timestamp
    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return user


async def list_user_api_keys(db: AsyncSession, user_id: str) -> List[ApiKeyListItem]:
    """Lists all API keys for user with masked presentation."""
    stmt = (
        select(ApiKey)
        .where(ApiKey.user_id == user_id)
        .order_by(ApiKey.created_at.desc())
    )
    res = await db.execute(stmt)
    keys = res.scalars().all()

    items = []
    for k in keys:
        masked = f"tv_live_...{k.key_hash[:8]}"
        items.append(
            ApiKeyListItem(
                id=k.id,
                name=k.name,
                masked_key=masked,
                created_at=k.created_at,
                last_used_at=k.last_used_at,
                is_active=(k.revoked_at is None)
            )
        )
    return items


async def revoke_user_api_key(db: AsyncSession, user_id: str, key_id: str) -> bool:
    """Revokes a specific API key belonging to user."""
    stmt = (
        update(ApiKey)
        .where(ApiKey.id == key_id, ApiKey.user_id == user_id, ApiKey.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    res = await db.execute(stmt)
    await db.commit()
    return (res.rowcount or 0) > 0
