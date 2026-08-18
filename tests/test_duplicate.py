"""
Tests for Duplicate Memory Detection and Resolution (PRD Test 6)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.memory import Memory
from app.schemas.memory import MemorySaveRequest
from app.services.memory_service import memory_service


@pytest.mark.asyncio
async def test_duplicate_detection_test_6(db_session: AsyncSession, user_a: dict):
    """
    PRD Test 6: Duplicate detection
    Existing: "Tanvelo uses FastAPI."
    New: "The backend of Tanvelo is built with FastAPI."
    Expected: Update existing memory instead of creating a duplicate.
    """
    user_id = user_a["user"].id

    # 1. Save initial memory
    req1 = MemorySaveRequest(content="Tanvelo uses FastAPI.")
    res1 = await memory_service.save_memory(db=db_session, user_id=user_id, request=req1)
    assert res1.success is True
    assert res1.action == "created"
    first_mem_id = res1.memory_id

    # Count records in DB
    cnt1 = (await db_session.execute(select(func.count(Memory.id)).where(Memory.user_id == user_id))).scalar()
    assert cnt1 == 1

    # 2. Save semantically equivalent statement
    req2 = MemorySaveRequest(content="The backend of Tanvelo is built with FastAPI.")
    res2 = await memory_service.save_memory(db=db_session, user_id=user_id, request=req2)
    assert res2.success is True
    assert res2.action == "updated"
    assert res2.memory_id == first_mem_id

    # 3. Total memory count should still be 1 (in-place update, not duplicate)
    cnt2 = (await db_session.execute(select(func.count(Memory.id)).where(Memory.user_id == user_id))).scalar()
    assert cnt2 == 1
