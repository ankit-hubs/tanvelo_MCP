"""
Duplicate Memory Detection and Resolution Service
Detects semantically equivalent memories using cosine similarity threshold (>= 0.90)
and updates existing records to prevent context fragmentation.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.memory import Memory
from app.services.embedding_service import embedding_service

logger = logging.getLogger("tanvelo.duplicate")


class DuplicateService:
    def __init__(self, threshold: float = settings.DUPLICATE_SIMILARITY_THRESHOLD):
        self.threshold = threshold

    async def find_duplicate(
        self,
        db: AsyncSession,
        user_id: str,
        candidate_embedding: List[float],
        project_id: Optional[str] = None
    ) -> Tuple[Optional[Memory], float]:
        """
        Searches for an existing active memory belonging to user_id that has
        cosine similarity >= self.threshold.
        Returns: (duplicate_memory_or_none, max_similarity).
        """
        now_utc = datetime.now(timezone.utc)
        conditions = [
            Memory.user_id == user_id,
            or_(Memory.expires_at.is_(None), Memory.expires_at > now_utc)
        ]
        if project_id:
            conditions.append(Memory.project_id == project_id)

        stmt = select(Memory).where(and_(*conditions))
        result = await db.execute(stmt)
        existing_memories: List[Memory] = list(result.scalars().all())

        best_match: Optional[Memory] = None
        max_sim: float = 0.0

        for mem in existing_memories:
            if mem.embedding is not None:
                sim = embedding_service.cosine_similarity(candidate_embedding, mem.embedding)
                if sim > max_sim:
                    max_sim = sim
                    if sim >= self.threshold:
                        best_match = mem

        return best_match, max_sim


duplicate_service = DuplicateService()
