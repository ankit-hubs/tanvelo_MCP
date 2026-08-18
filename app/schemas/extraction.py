"""
Extraction Schema for NVIDIA Nemotron Nano 8B Output
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field

MemoryType = Literal[
    "preference",
    "project_fact",
    "technical_fact",
    "decision",
    "personal_fact",
    "task",
    "goal",
    "conversation_summary",
    "temporary"
]


class ExtractedMemoryItem(BaseModel):
    content: str = Field(description="The normalized, self-contained statement to remember")
    type: str = Field(default="project_fact", description="Category of memory")
    importance: float = Field(default=0.7, ge=0.0, le=1.0, description="Estimated long-term importance score from 0.0 to 1.0")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence in this extraction from 0.0 to 1.0")
    expires: bool = Field(default=False, description="Whether this information is temporary")
    expires_in_hours: Optional[float] = Field(default=None, description="Hours until expiration if expires=True")
    reason: Optional[str] = Field(default=None, description="Short rationale for why this is worth storing or ignoring")


class MemoryExtractionResponse(BaseModel):
    should_store: bool = Field(description="True if the input contains information worthy of long-term storage, False otherwise")
    memories: List[ExtractedMemoryItem] = Field(default_factory=list, description="List of candidate memories to store")
    raw_response: Optional[str] = None
