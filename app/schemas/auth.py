"""
Authentication Pydantic Schemas
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class ApiKeyCreate(BaseModel):
    name: str = "Default Key"
    email: Optional[EmailStr] = None


class ApiKeyResponse(BaseModel):
    api_key: str
    key_id: str
    user_id: str
    name: str
    created_at: datetime
    message: str = "Store this API key safely. It will not be shown again."


class UserInfo(BaseModel):
    user_id: str
    email: Optional[str] = None
    created_at: datetime
    active_keys_count: int
    memories_count: int
