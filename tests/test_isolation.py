"""
Tests for Strict Tenant User Data Isolation (PRD Section 28)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.memory import MemorySaveRequest
from app.services.memory_service import memory_service


@pytest.mark.asyncio
async def test_user_data_isolation(db_session: AsyncSession, user_a: dict, user_b: dict):
    """
    Mandatory Security Requirement:
    User A must never retrieve or manipulate User B's memories.
    """
    user_a_id = user_a["user"].id
    user_b_id = user_b["user"].id

    # 1. User A saves private memory
    req_a = MemorySaveRequest(content="Remember that User A proprietary secret token is SECRET_KEY_9999.")
    res_a = await memory_service.save_memory(db=db_session, user_id=user_a_id, request=req_a)
    assert res_a.success is True
    mem_a_id = res_a.memory_id

    # 2. User B searches for User A's secret
    search_b = await memory_service.search_memories(
        db=db_session,
        user_id=user_b_id,
        query="proprietary secret token SECRET_KEY_9999"
    )
    # User B must find NOTHING
    assert len(search_b.memories) == 0

    # 3. User B requests context
    ctx_b = await memory_service.get_context(
        db=db_session,
        user_id=user_b_id,
        query="secret token"
    )
    assert "SECRET_KEY_9999" not in ctx_b.context
    assert len(ctx_b.memories) == 0

    # 4. User B attempts to delete User A's memory ID
    forget_attempt = await memory_service.forget_memory(
        db=db_session,
        user_id=user_b_id,
        memory_id=mem_a_id
    )
    assert forget_attempt.success is False

    # 5. User A can still retrieve their own memory
    search_a = await memory_service.search_memories(
        db=db_session,
        user_id=user_a_id,
        query="proprietary secret token"
    )
    assert len(search_a.memories) == 1
    assert search_a.memories[0].id == mem_a_id
