"""
Tests for Memory Expiration Filtering (PRD Section 25)
"""

from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.memory import Memory, generate_memory_id
from app.services.embedding_service import embedding_service
from app.services.memory_service import memory_service


@pytest.mark.asyncio
async def test_expired_memory_is_not_returned(db_session: AsyncSession, user_a: dict):
    """
    Expired memories must NEVER be returned by search or context retrieval.
    """
    user_id = user_a["user"].id
    now = datetime.now(timezone.utc)

    # 1. Create already expired memory (expired 2 hours ago)
    emb_expired = await embedding_service.get_embedding("Fixing bug 404 in auth")
    expired_mem = Memory(
        id=generate_memory_id(),
        user_id=user_id,
        content="Fixing bug 404 in auth",
        type="temporary",
        importance=0.5,
        confidence=1.0,
        embedding=emb_expired,
        created_at=now - timedelta(hours=26),
        updated_at=now - timedelta(hours=26),
        expires_at=now - timedelta(hours=2)  # Expired in past
    )

    # 2. Create active memory (expires in future)
    emb_active = await embedding_service.get_embedding("Tanvelo core architecture is modular")
    active_mem = Memory(
        id=generate_memory_id(),
        user_id=user_id,
        content="Tanvelo core architecture is modular",
        type="project_fact",
        importance=0.9,
        confidence=1.0,
        embedding=emb_active,
        created_at=now,
        updated_at=now,
        expires_at=None  # Permanent
    )

    db_session.add_all([expired_mem, active_mem])
    await db_session.commit()

    # 3. Search for the expired bug topic
    search_res = await memory_service.search_memories(
        db=db_session,
        user_id=user_id,
        query="bug 404 in auth"
    )

    # Expired memory must NOT appear in search results
    returned_ids = [m.id for m in search_res.memories]
    assert expired_mem.id not in returned_ids

    # 4. Context retrieval must also exclude expired memories
    ctx_res = await memory_service.get_context(
        db=db_session,
        user_id=user_id,
        query="auth"
    )
    assert expired_mem.content not in ctx_res.context
