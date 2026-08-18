"""
Memory Retrieval Service
Handles pgvector similarity search, expiration filtering, and tenant isolation.
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.services.embedding_service import embedding_service
from app.services.ranking_service import ranking_service


class RetrievalService:
    async def search_memories(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        limit: int = 5,
        project_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        min_similarity: float = 0.0
    ) -> List[Tuple[Memory, float, float]]:
        """
        Executes semantic vector search scoped to user_id, filters expired memories,
        and applies hybrid ranking.
        Returns: List of (Memory, similarity, hybrid_score).
        """
        # Generate embedding for search query
        query_embedding = await embedding_service.get_embedding(query)

        # Build base filter: user isolation + active (not expired)
        now_utc = datetime.now(timezone.utc)
        conditions = [
            Memory.user_id == user_id,
            or_(Memory.expires_at.is_(None), Memory.expires_at > now_utc)
        ]

        if project_id:
            conditions.append(Memory.project_id == project_id)
        if memory_type:
            conditions.append(Memory.type == memory_type)

        stmt = select(Memory).where(and_(*conditions))
        result = await db.execute(stmt)
        memories: List[Memory] = list(result.scalars().all())

        if not memories:
            return []

        # Compute cosine similarity for each memory
        scored: List[Tuple[Memory, float]] = []
        for mem in memories:
            if mem.embedding is not None:
                sim = embedding_service.cosine_similarity(query_embedding, mem.embedding)
            else:
                sim = 0.0

            if sim >= min_similarity:
                scored.append((mem, sim))

        # Apply hybrid ranking
        ranked = ranking_service.rank_memories(scored, top_k=limit)
        return ranked

    async def get_all_active_memories(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        memory_type: Optional[str] = None
    ) -> Tuple[List[Memory], int]:
        """
        Lists all unexpired memories for the authenticated user.
        """
        now_utc = datetime.now(timezone.utc)
        conditions = [
            Memory.user_id == user_id,
            or_(Memory.expires_at.is_(None), Memory.expires_at > now_utc)
        ]
        if memory_type:
            conditions.append(Memory.type == memory_type)

        # Count total
        stmt_all = select(Memory).where(and_(*conditions)).order_by(Memory.created_at.desc())
        result_all = await db.execute(stmt_all)
        all_items = list(result_all.scalars().all())
        total = len(all_items)

        # Paginate
        paginated = all_items[offset:offset + limit]
        return paginated, total


retrieval_service = RetrievalService()
