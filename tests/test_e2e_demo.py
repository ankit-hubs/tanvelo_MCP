"""
End-to-End Test for the 7-Step Hackathon Demo Story (PRD Section 38)
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
async def test_complete_hackathon_demo_flow():
    """
    Step 1 — Connect: MCP initialized
    Step 2 — Save: AI Tool A saves 'Remember that Tanvelo uses FastAPI, Supabase and pgvector.'
    Step 3 — Verify: Memory stored in Tanvelo
    Step 4 & 5 — Switch AI & Retrieve: AI Tool B calls get_context('What technology stack am I using for Tanvelo?')
    Step 6 — Answer: Context contains FastAPI, Supabase, pgvector
    Step 7 — Forget: AI Tool B calls forget_memory('Forget that Tanvelo uses Supabase')
    """
    # Step 2: Save via AI Tool A
    save_raw = await save_memory(
        content="Remember that Tanvelo uses FastAPI, Supabase and pgvector.",
        type="project_fact"
    )
    save_res = json.loads(save_raw)
    assert save_res["success"] is True
    assert save_res["action"] in ["created", "updated"]
    saved_mem_id = save_res["memory_id"]

    # Step 3: Verify in list_memories
    list_raw = await list_memories()
    list_res = json.loads(list_raw)
    assert any("FastAPI" in m["content"] for m in list_res["memories"])

    # Step 4 & 5: AI Tool B retrieves context without repeating input
    context_output = await get_context(query="What technology stack am I using for Tanvelo?")
    assert "FastAPI" in context_output
    assert "Supabase" in context_output or "pgvector" in context_output

    # Step 7: Forget memory
    forget_raw = await forget_memory(query="Forget that Tanvelo uses Supabase")
    forget_res = json.loads(forget_raw)
    assert forget_res["success"] is True

    # Confirm Supabase memory is no longer retrieved
    search_raw = await search_memory(query="Tanvelo database Supabase")
    search_res = json.loads(search_raw)
    assert not any("Supabase" in m["content"] for m in search_res["memories"])
