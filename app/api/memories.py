"""
Memories REST API Endpoints
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.memory import Memory
from app.api.auth import get_current_user
from app.schemas.memory import (
    MemorySaveRequest,
    MemorySaveResponse,
    MemorySearchRequest,
    MemorySearchResponse,
    MemoryContextRequest,
    MemoryContextResponse,
    MemoryForgetRequest,
    MemoryForgetResponse,
    MemoryListResponse,
    MemoryRecord
)
from app.services.memory_service import memory_service

router = APIRouter(prefix="/v1", tags=["Memories"])


@router.post("/memories", response_model=MemorySaveResponse, status_code=status.HTTP_200_OK)
async def save_memory(
    request: MemorySaveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Evaluates, extracts, and stores or updates long-term memory.
    """
    return await memory_service.save_memory(
        db=db,
        user_id=user.id,
        request=request
    )


@router.get("/memories", response_model=MemoryListResponse)
async def list_memories(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    type: Optional[str] = Query(None, alias="type"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists active memories for the authenticated user.
    """
    return await memory_service.list_memories(
        db=db,
        user_id=user.id,
        limit=limit,
        offset=offset,
        memory_type=type
    )


@router.get("/memories/{memory_id}", response_model=MemoryRecord)
async def get_memory_by_id(
    memory_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a single memory by ID scoped to the authenticated user.
    """
    stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user.id)
    res = await db.execute(stmt)
    mem = res.scalars().first()
    if not mem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory '{memory_id}' not found."
        )
    return memory_service._to_record(mem)


@router.delete("/memories/{memory_id}", response_model=MemoryForgetResponse)
async def delete_memory_by_id(
    memory_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes or invalidates a memory by ID.
    """
    return await memory_service.forget_memory(
        db=db,
        user_id=user.id,
        memory_id=memory_id
    )


@router.post("/search", response_model=MemorySearchResponse)
async def search_memories(
    request: MemorySearchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Searches memories using semantic vector search and hybrid ranking.
    """
    return await memory_service.search_memories(
        db=db,
        user_id=user.id,
        query=request.query,
        limit=request.limit or 5,
        project_id=request.project_id,
        memory_type=request.memory_type
    )


@router.post("/context", response_model=MemoryContextResponse)
async def get_context(
    request: MemoryContextRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves most relevant memories formatted as markdown for AI prompt injection.
    """
    return await memory_service.get_context(
        db=db,
        user_id=user.id,
        query=request.query,
        limit=request.limit or 5,
        project_id=request.project_id
    )


@router.post("/forget", response_model=MemoryForgetResponse)
async def forget_memory(
    request: MemoryForgetRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Natural language or ID-based memory forget endpoint.
    """
    return await memory_service.forget_memory(
        db=db,
        user_id=user.id,
        memory_id=request.memory_id,
        query=request.query
    )
