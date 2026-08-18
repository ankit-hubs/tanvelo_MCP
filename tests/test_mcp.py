"""
Tests for Model Context Protocol (MCP) Server Tools
"""

import json
import pytest
from app.mcp.server import (
    save_memory,
    search_memory,
    get_context,
    forget_memory,
    list_memories
)


@pytest.mark.asyncio
async def test_mcp_save_and_retrieve_tool():
    """
    Test MCP tools: save_memory -> search_memory -> get_context -> forget_memory -> list_memories
    """
    # 1. save_memory
    save_raw = await save_memory(
        content="Tanvelo is configured with FastAPI backend and pgvector vector search.",
        type="project_fact"
    )
    save_data = json.loads(save_raw)
    assert save_data["success"] is True
    assert save_data["action"] in ["created", "updated"]
    mem_id = save_data["memory_id"]
    assert mem_id != ""

    # 2. search_memory
    search_raw = await search_memory(query="What backend does Tanvelo use?")
    search_data = json.loads(search_raw)
    assert len(search_data["memories"]) >= 1
    assert "FastAPI" in search_data["memories"][0]["content"]

    # 3. get_context
    ctx_raw = await get_context(query="Tanvelo backend stack")
    assert "FastAPI" in ctx_raw
    assert "pgvector" in ctx_raw

    # 4. list_memories
    list_raw = await list_memories(limit=10)
    list_data = json.loads(list_raw)
    assert list_data["total"] >= 1

    # 5. forget_memory
    for item in save_data.get("stored", [{"id": mem_id}]):
        forget_raw = await forget_memory(memory_id=item["id"])
        forget_data = json.loads(forget_raw)
        assert forget_data["success"] is True

    # 6. Verify search after forget
    search_after_raw = await search_memory(query="What backend does Tanvelo use?")
    search_after_data = json.loads(search_after_raw)
    assert len(search_after_data["memories"]) == 0
