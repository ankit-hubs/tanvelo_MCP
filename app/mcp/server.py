"""
Tanvelo Model Context Protocol (MCP) Server
Exposes enterprise memory operations to MCP-compatible AI clients (Cursor, Claude Code, Codex CLI, Agy CLI, Windsurf):
- save_memory
- search_memory
- get_context
- forget_memory
- list_memories
- update_memory
- get_memory_stats
- cleanup_expired_memories
- export_memories
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
    MemoryUpdateRequest,
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
    instructions="Universal long-term memory layer. Use save_memory to persist facts/preferences, get_context or search_memory to retrieve them, update_memory to modify them, and forget_memory to delete invalidated facts."
)


async def get_or_create_mcp_user() -> User:
    """
    Resolves the authenticated user for the MCP session.
    Checks TANVELO_API_KEY environment variable first;
    if absent, provisions or fetches a default local user for zero-config CLI setup.
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
    description="AUTONOMOUS MEMORY STORAGE: Automatically stores and categorizes important project facts, architecture decisions, database configurations, coding conventions, or user preferences into Tanvelo. Call automatically whenever durable knowledge is shared, without requiring explicit user instructions."
)
async def save_memory(
    content: str,
    type: Optional[str] = None,
    importance: Optional[float] = None,
    project_id: Optional[str] = None,
    force_store: bool = False
) -> str:
    """
    Store an important piece of information.
    Input:
      content: The fact, preference, or context to store (e.g. 'Tanvelo uses FastAPI and Supabase')
      type: Optional category ('project_fact', 'preference', 'decision', 'temporary', etc.)
      importance: Optional manual importance score (0.0 to 1.0)
      project_id: Optional project identifier for multi-project scoping
      force_store: Set to True to bypass LLM evaluation and store directly
    """
    user = await get_or_create_mcp_user()
    req = MemorySaveRequest(
        content=content,
        type=type,
        importance=importance,
        project_id=project_id,
        force_store=force_store,
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
                    "importance": round(m.importance, 2),
                    "project_id": m.project_id
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
    limit: int = 5,
    project_id: Optional[str] = None,
    type: Optional[str] = None
) -> str:
    """
    Find memories relevant to a query.
    Input:
      query: The search term or question (e.g. 'Tanvelo backend')
      limit: Maximum number of memories to return (default: 5)
      project_id: Filter by project identifier
      type: Filter by memory category
    """
    user = await get_or_create_mcp_user()
    async with async_session_factory() as db:
        res = await memory_service.search_memories(
            db=db,
            user_id=user.id,
            query=query,
            limit=limit,
            project_id=project_id,
            memory_type=type
        )

        memories_data = [
            {
                "id": m.id,
                "content": m.content,
                "type": m.type,
                "project_id": m.project_id,
                "importance": round(m.importance, 2),
                "similarity": round(m.similarity or 0.0, 2)
            }
            for m in res.memories
        ]

        return json.dumps({"memories": memories_data, "total_found": res.total_found}, indent=2)


@mcp_server.tool(
    name="get_context",
    description="PRE-FLIGHT CONTEXT RETRIEVAL: Call this tool FIRST before answering any user query or generating code. Retrieves relevant project architecture decisions, technical conventions, database setups, and developer preferences from Tanvelo long-term memory."
)
async def get_context(
    query: str,
    limit: int = 5,
    project_id: Optional[str] = None,
    max_characters: int = 4000
) -> str:
    """
    Retrieve concise context that the AI can directly use for current task.
    Input:
      query: Task description or prompt (e.g. 'authentication implementation')
      limit: Max memories to assemble (default: 5)
      project_id: Optional project identifier
      max_characters: Maximum character budget for returned context (default: 4000)
    """
    user = await get_or_create_mcp_user()
    async with async_session_factory() as db:
        res = await memory_service.get_context(
            db=db,
            user_id=user.id,
            query=query,
            limit=limit,
            project_id=project_id,
            max_characters=max_characters
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
    limit: int = 20,
    offset: int = 0,
    project_id: Optional[str] = None,
    type: Optional[str] = None
) -> str:
    """
    List memories belonging to the authenticated user.
    Input:
      limit: Max number of memories to return (default: 20)
      offset: Pagination offset (default: 0)
      project_id: Filter by project identifier
      type: Filter by memory category
    """
    user = await get_or_create_mcp_user()
    async with async_session_factory() as db:
        res = await memory_service.list_memories(
            db=db,
            user_id=user.id,
            limit=limit,
            offset=offset,
            project_id=project_id,
            memory_type=type
        )

        memories_data = [
            {
                "id": m.id,
                "content": m.content,
                "type": m.type,
                "project_id": m.project_id,
                "importance": round(m.importance, 2),
                "created_date": m.created_at.isoformat(),
                "updated_date": m.updated_at.isoformat(),
                "expiration_date": m.expires_at.isoformat() if m.expires_at else None
            }
            for m in res.memories
        ]

        return json.dumps({
            "total": res.total,
            "limit": res.limit,
            "offset": res.offset,
            "memories": memories_data
        }, indent=2)


@mcp_server.tool(
    name="update_memory",
    description="Update the content, category, or importance of an existing memory by ID."
)
async def update_memory(
    memory_id: str,
    content: Optional[str] = None,
    type: Optional[str] = None,
    importance: Optional[float] = None
) -> str:
    """
    Update an existing memory.
    Input:
      memory_id: ID of the memory to update
      content: New statement text
      type: New category
      importance: New importance score (0.0 to 1.0)
    """
    user = await get_or_create_mcp_user()
    req = MemoryUpdateRequest(
        content=content,
        type=type,
        importance=importance
    )
    async with async_session_factory() as db:
        updated = await memory_service.update_memory(
            db=db,
            user_id=user.id,
            memory_id=memory_id,
            request=req
        )
        if not updated:
            return json.dumps({"success": False, "message": f"Memory '{memory_id}' not found."}, indent=2)

        return json.dumps({
            "success": True,
            "memory": {
                "id": updated.id,
                "content": updated.content,
                "type": updated.type,
                "importance": round(updated.importance, 2),
                "updated_at": updated.updated_at.isoformat()
            }
        }, indent=2)


@mcp_server.tool(
    name="get_memory_stats",
    description="Retrieve statistical overview of stored memories (total counts, categories, and project breakdown)."
)
async def get_memory_stats() -> str:
    """
    Returns memory statistics for the current user.
    """
    user = await get_or_create_mcp_user()
    async with async_session_factory() as db:
        stats = await memory_service.get_stats(db=db, user_id=user.id)
        return json.dumps(stats.model_dump(mode="json"), indent=2)


@mcp_server.tool(
    name="cleanup_expired_memories",
    description="Purge all expired memories from the database."
)
async def cleanup_expired_memories() -> str:
    """
    Purges expired memories from storage.
    """
    user = await get_or_create_mcp_user()
    async with async_session_factory() as db:
        res = await memory_service.cleanup_expired(db=db, user_id=user.id)
        return json.dumps({"success": True, "deleted_count": res.deleted_count, "message": res.message}, indent=2)


@mcp_server.tool(
    name="export_memories",
    description="Export memories as formatted Markdown or JSON."
)
async def export_memories(
    format: str = "markdown",
    project_id: Optional[str] = None
) -> str:
    """
    Export all active memories.
    Input:
      format: 'markdown' or 'json' (default: 'markdown')
      project_id: Optional project filter
    """
    user = await get_or_create_mcp_user()
    async with async_session_factory() as db:
        res = await memory_service.export_memories(
            db=db,
            user_id=user.id,
            format=format,
            project_id=project_id
        )
        return res.content


@mcp_server.prompt(
    name="tanvelo_memory_protocol",
    description="Universal standard instructions for AI tools on how to interact with Tanvelo memory."
)
def tanvelo_memory_protocol() -> str:
    """Standard system instruction block that can be loaded by any MCP client."""
    return (
        "# Tanvelo Universal Memory Protocol\n"
        "1. PRE-FLIGHT RETRIEVAL: Always invoke `get_context(query=...)` first on the user prompt to retrieve relevant project memory and preferences before answering.\n"
        "2. AUTONOMOUS STORAGE: Whenever technical decisions, tech stacks, or user preferences are established, call `save_memory(content=...)` in the background.\n"
        "3. SEAMLESS UPDATES: If a prior decision changes, invoke `save_memory` or `update_memory` with the updated fact to maintain fresh, non-duplicate memory."
    )

