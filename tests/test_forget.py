"""
Tests for Explicit Forget (PRD Test 5)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.memory import MemorySaveRequest
from app.services.memory_service import memory_service


@pytest.mark.asyncio
async def test_forget_test_5_explicit_forget_by_query(db_session: AsyncSession, user_a: dict):
    """
    PRD Test 5: Explicit forget
    Input: "Forget that I prefer Python."
    Expected: Memory removed or invalidated, never returned by subsequent search.
    """
    user_id = user_a["user"].id

    # 1. First, save the memory
    save_req = MemorySaveRequest(content="Remember that I prefer Python.")
    save_res = await memory_service.save_memory(db=db_session, user_id=user_id, request=save_req)
    assert save_res.success is True
    assert save_res.action == "created"

    # 2. Verify search finds it
    search_res = await memory_service.search_memories(db=db_session, user_id=user_id, query="What language do I prefer?")
    assert len(search_res.memories) >= 1
    assert "Python" in search_res.memories[0].content

    # 3. Explicit forget
    forget_res = await memory_service.forget_memory(
        db=db_session,
        user_id=user_id,
        query="Forget that I prefer Python"
    )
    assert forget_res.success is True
    assert len(forget_res.forgotten_ids) >= 1

    # 4. Confirm search no longer finds it
    search_after = await memory_service.search_memories(db=db_session, user_id=user_id, query="What language do I prefer?")
    assert len(search_after.memories) == 0


@pytest.mark.asyncio
async def test_forget_by_memory_id(db_session: AsyncSession, user_a: dict):
    """
    Test deleting a memory by exact memory_id.
    """
    user_id = user_a["user"].id

    save_req = MemorySaveRequest(content="Tanvelo uses FastAPI and pgvector.")
    save_res = await memory_service.save_memory(db=db_session, user_id=user_id, request=save_req)
    mem_id = save_res.memory_id
    assert mem_id is not None

    forget_res = await memory_service.forget_memory(
        db=db_session,
        user_id=user_id,
        memory_id=mem_id
    )
    assert forget_res.success is True
    assert mem_id in forget_res.forgotten_ids

    # Subsequent search should return 0 results
    search_after = await memory_service.search_memories(db=db_session, user_id=user_id, query="Tanvelo database backend")
    assert len(search_after.memories) == 0
