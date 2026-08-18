"""
Tanvelo Model Context Protocol (MCP) Server
Exposes 5 core memory operations to MCP-compatible AI clients (Cursor, Claude Code, Codex CLI, Agy CLI, etc.):
- save_memory
- search_memory
- get_context
- forget_memory
- list_memories
"""

import json
import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy import select
from mcp.server.mcpserver import MCPServer

from app.database import async_session_factory, init_db
from app.models.user import User
from app.models.api_key import ApiKey
from app.schemas.memory import (
    MemorySaveRequest,
    MemorySearchRequest,
    MemoryContextRequest,
    MemoryForgetRequest
)
from app.services.auth_service import validate_api_key, create_user_and_api_key
from app.services.memory_service import memory_service

logger = logging.getLogger("tanvelo.mcp")

# Initialize MCP Server instance
mcp_server = MCPServer(
    name="tanvelo-memory",
    instructions="Universal long-term memory layer. Use save_memory to persist facts/preferences, get_context or search_memory to retrieve them, and forget_memory to delete invalidated facts."
)


async def get_or_create_mcp_user() -> User:
    """
    Resolves the authenticated user for the MCP session.
    Checks TANVELO_API_KEY environment variable first;
    if absent, gets or provisions a local default user for zero-config CLI setup.
    """
    await init_db()
    api_key_env = os.getenv("TANVELO_API_KEY")

    async with async_session_factory() as db:
        if api_key_env:
            user = await validate_api_key(db, api_key_env)
            if user:
                return user
            logger.warning("Provided TANVELO_API_KEY is invalid. Falling back to default MCP user.")

        # Find or create default local MCP user
        stmt = select(User).where(User.email == "mcp-client@tanvelo.local")
        res = await db.execute(stmt)
        user = res.scalars().first()

        if not user:
            user, _, _ = await create_user_and_api_key(
                db=db,
                email="mcp-client@tanvelo.local",
                key_name="Default MCP Client Key"
            )

        return user


@mcp_server.tool(
    name="save_memory",
    description="Store important information, user preferences, project facts, architecture decisions, or goals into long-term memory."
)
async def save_memory(
    content: str,
    type: Optional[str] = None
) -> str:
    """
    Store an important piece of information.
    Input:
      content: The fact, preference, or context to store (e.g. 'Tanvelo uses FastAPI and Supabase')
      type: Optional category ('project_fact', 'preference', 'decision', 'temporary', etc.)
    """
    user = await get_or_create_mcp_user()
    req = MemorySaveRequest(
        content=content,
        type=type,
        source="mcp"
    )

    async with async_session_factory() as db:
        res = await memory_service.save_memory(
            db=db,
            user_id=user.id,
            request=req
        )

        output: Dict[str, Any] = {
            "success": res.success,
            "memory_id": res.memory_id or "",
            "action": res.action,
            "message": res.message
        }
        if res.stored_memories:
            output["stored"] = [
                {
                    "id": m.id,
                    "content": m.content,
                    "type": m.type,
                    "importance": round(m.importance, 2)
                }
                for m in res.stored_memories
            ]
        return json.dumps(output, indent=2)


@mcp_server.tool(
    name="search_memory",
    description="Find memories relevant to a natural language query using semantic vector search and hybrid ranking."
)
async def search_memory(
    query: str,
    limit: int = 5
) -> str:
    """
    Find memories relevant to a query.
    Input:
      query: The search term or question (e.g. 'Tanvelo backend')
      limit: Maximum number of memories to return (default: 5)
    """
    user = await get_or_create_mcp_user()
    async with async_session_factory() as db:
        res = await memory_service.search_memories(
            db=db,
            user_id=user.id,
            query=query,
            limit=limit
        )

        memories_data = [
            {
                "id": m.id,
                "content": m.content,
                "type": m.type,
                "importance": round(m.importance, 2),
                "similarity": round(m.similarity or 0.0, 2)
            }
            for m in res.memories
        ]

        return json.dumps({"memories": memories_data}, indent=2)


@mcp_server.tool(
    name="get_context",
    description="Retrieve the most useful memories and preferences formatted as concise context for the current task."
)
async def get_context(
    query: str,
    limit: int = 5
) -> str:
    """
    Retrieve concise context that the AI can directly use for current task.
    Input:
      query: Task description or prompt (e.g. 'authentication implementation')
      limit: Max memories to assemble (default: 5)
    """
    user = await get_or_create_mcp_user()
    async with async_session_factory() as db:
        res = await memory_service.get_context(
            db=db,
            user_id=user.id,
            query=query,
            limit=limit
        )

        if not res.context:
            return "No relevant memories found in Tanvelo for this context."

        return res.context


@mcp_server.tool(
    name="forget_memory",
    description="Delete or invalidate a memory by ID or by natural language description (e.g. 'Forget that I prefer Python')."
)
async def forget_memory(
    memory_id: Optional[str] = None,
    query: Optional[str] = None
) -> str:
    """
    Delete or invalidate a memory.
    Input:
      memory_id: Exact memory ID to delete (e.g. 'mem_123')
      query: Natural language description of what to forget
    """
    user = await get_or_create_mcp_user()
    async with async_session_factory() as db:
        res = await memory_service.forget_memory(
            db=db,
            user_id=user.id,
            memory_id=memory_id,
            query=query
        )

        return json.dumps({
            "success": res.success,
            "message": res.message,
            "forgotten_ids": res.forgotten_ids
        }, indent=2)


@mcp_server.tool(
    name="list_memories",
    description="List stored memories belonging to the authenticated user."
)
async def list_memories(
    limit: int = 20
) -> str:
    """
    List memories belonging to the authenticated user.
    Input:
      limit: Max number of memories to return (default: 20)
    """
    user = await get_or_create_mcp_user()
    async with async_session_factory() as db:
        res = await memory_service.list_memories(
            db=db,
            user_id=user.id,
            limit=limit
        )

        memories_data = [
            {
                "id": m.id,
                "content": m.content,
                "type": m.type,
                "importance": round(m.importance, 2),
                "created_date": m.created_at.isoformat(),
                "updated_date": m.updated_at.isoformat(),
                "expiration_date": m.expires_at.isoformat() if m.expires_at else None
            }
            for m in res.memories
        ]

        return json.dumps({
            "total": res.total,
            "memories": memories_data
        }, indent=2)
