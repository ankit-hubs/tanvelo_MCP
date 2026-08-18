"""
Tests for Memory Extraction and Importance Decision Engine (PRD Tests 1, 2, 3, 4)
"""

import pytest
from app.services.extraction_service import extraction_service


@pytest.mark.asyncio
async def test_extraction_test_1_project_fact():
    """
    PRD Test 1: Important project fact
    Input: "Tanvelo uses FastAPI."
    Expected: should_store = true, type = project_fact
    """
    res = await extraction_service.extract_memories("Tanvelo uses FastAPI.")
    assert res.should_store is True
    assert len(res.memories) >= 1
    mem = res.memories[0]
    assert mem.type == "project_fact"
    assert "FastAPI" in mem.content
    assert mem.importance >= 0.8
    assert mem.expires is False


@pytest.mark.asyncio
async def test_extraction_test_2_explicit_remember():
    """
    PRD Test 2: Explicit remember
    Input: "Remember that I prefer Python."
    Expected: should_store = true, type = preference
    """
    res = await extraction_service.extract_memories("Remember that I prefer Python.")
    assert res.should_store is True
    assert len(res.memories) >= 1
    mem = res.memories[0]
    assert mem.type == "preference"
    assert "Python" in mem.content
    assert mem.importance >= 0.75


@pytest.mark.asyncio
async def test_extraction_test_3_casual_conversation():
    """
    PRD Test 3: Casual conversation
    Input: "Hello, how are you?"
    Expected: should_store = false
    """
    res = await extraction_service.extract_memories("Hello, how are you?")
    assert res.should_store is False
    assert len(res.memories) == 0


@pytest.mark.asyncio
async def test_extraction_test_4_temporary_information():
    """
    PRD Test 4: Temporary information
    Input: "I'm fixing authentication today."
    Expected: type = temporary, expires = true, expires_in_hours > 0
    """
    res = await extraction_service.extract_memories("I'm fixing authentication today.")
    assert res.should_store is True
    assert len(res.memories) >= 1
    mem = res.memories[0]
    assert mem.type in ["temporary", "task"]
    assert mem.expires is True
    assert mem.expires_in_hours is not None
    assert mem.expires_in_hours > 0


@pytest.mark.asyncio
async def test_extraction_explicit_do_not_remember():
    """
    Explicit negative instruction: "Don't remember this conversation."
    Expected: should_store = false
    """
    res = await extraction_service.extract_memories("Don't remember this conversation, it is confidential.")
    assert res.should_store is False
    assert len(res.memories) == 0
