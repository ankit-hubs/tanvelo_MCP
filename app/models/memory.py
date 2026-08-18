"""
Memory SQLAlchemy Model
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base, VectorType
from app.config import settings


def generate_memory_id() -> str:
    return f"mem_{uuid.uuid4().hex[:12]}"


class Memory(Base):
    __tablename__ = "memories"

    id = Column(String(64), primary_key=True, default=generate_memory_id)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    type = Column(String(64), nullable=False, default="project_fact", index=True)
    importance = Column(Float, nullable=False, default=0.5)
    confidence = Column(Float, nullable=False, default=1.0)
    source = Column(String(64), nullable=False, default="mcp")
    project_id = Column(String(128), nullable=True, index=True)
    embedding = Column(VectorType(settings.EMBEDDING_DIMENSION), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

    user = relationship("User", back_populates="memories")
