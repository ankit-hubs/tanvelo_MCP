"""
Memory Request and Response Pydantic Schemas
"""

from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class MemorySaveRequest(BaseModel):
    content: str = Field(description="Information or context to remember")
    type: Optional[str] = Field(default=None, description="Optional memory type (preference, project_fact, technical_fact, etc.)")
    importance: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Optional manual importance score")
    project_id: Optional[str] = Field(default=None, description="Optional project identifier for scoping")
    source: Optional[str] = Field(default="mcp", description="Origin of memory, e.g. 'mcp:cursor', 'mcp:claude-code'")
    force_store: bool = Field(default=False, description="Bypass LLM evaluation and store directly")


class MemoryRecord(BaseModel):
    id: str
    user_id: str
    content: str
    type: str
    importance: float
    confidence: float
    source: str
    project_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    similarity: Optional[float] = None
    hybrid_score: Optional[float] = None


class MemorySaveResponse(BaseModel):
    success: bool
    action: Literal["created", "updated", "ignored"]
    memory_id: Optional[str] = None
    stored_memories: List[MemoryRecord] = Field(default_factory=list)
    message: Optional[str] = None


class MemorySearchRequest(BaseModel):
    query: str = Field(description="Search query to find relevant memories")
    limit: Optional[int] = Field(default=5, ge=1, le=50, description="Max number of memories to return")
    project_id: Optional[str] = Field(default=None, description="Filter by project ID")
    memory_type: Optional[str] = Field(default=None, description="Filter by memory type")


class MemorySearchResponse(BaseModel):
    memories: List[MemoryRecord]
    total_found: int


class MemoryContextRequest(BaseModel):
    query: str = Field(description="Current task or query to assemble relevant context for")
    limit: Optional[int] = Field(default=5, ge=1, le=50, description="Max memories in context")
    project_id: Optional[str] = Field(default=None, description="Filter by project ID")


class MemoryContextResponse(BaseModel):
    context: str = Field(description="Concise, structured markdown memory context ready for AI prompt injection")
    memories: List[MemoryRecord]
    count: int


class MemoryForgetRequest(BaseModel):
    memory_id: Optional[str] = Field(default=None, description="ID of specific memory to delete (e.g. 'mem_123')")
    query: Optional[str] = Field(default=None, description="Natural language description of what to forget (e.g. 'Forget that Tanvelo uses Supabase')")


class MemoryForgetResponse(BaseModel):
    success: bool
    message: str
    forgotten_ids: List[str] = Field(default_factory=list)


class MemoryListResponse(BaseModel):
    memories: List[MemoryRecord]
    total: int
    limit: int
    offset: int
