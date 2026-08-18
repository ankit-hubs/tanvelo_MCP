"""
Authentication and API Key Service
"""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.api_key import ApiKey


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

    # Update last_used_at timestamp asynchronously
    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return user
