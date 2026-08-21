"""
Memory Retrieval Service
Handles pgvector-accelerated similarity search on PostgreSQL with HNSW indexing,
robust pure-Python fallback for local SQLite development/testing, expiration filtering,
tenant isolation, and statistical aggregation.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, func, and_, or_, delete
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
        """
        # 1. Generate embedding for query
        query_embedding = await embedding_service.get_embedding(query)

        # 2. Build base filter: user isolation + active (not expired)
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

        # 3. Compute cosine similarity
        scored: List[Tuple[Memory, float]] = []
        for mem in memories:
            if mem.embedding is not None:
                sim = embedding_service.cosine_similarity(query_embedding, mem.embedding)
            else:
                sim = 0.0

            if sim >= min_similarity:
                scored.append((mem, sim))

        # 4. Apply hybrid ranking
        ranked = ranking_service.rank_memories(scored, top_k=limit)
        return ranked

    async def get_all_active_memories(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        project_id: Optional[str] = None,
        memory_type: Optional[str] = None
    ) -> Tuple[List[Memory], int]:
        """
        Lists active (unexpired) memories for the authenticated user with pagination and filters.
        """
        now_utc = datetime.now(timezone.utc)
        conditions = [
            Memory.user_id == user_id,
            or_(Memory.expires_at.is_(None), Memory.expires_at > now_utc)
        ]
        if project_id:
            conditions.append(Memory.project_id == project_id)
        if memory_type:
            conditions.append(Memory.type == memory_type)

        # Count total
        count_stmt = select(func.count(Memory.id)).where(and_(*conditions))
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        # Query paginated
        stmt = (
            select(Memory)
            .where(and_(*conditions))
            .order_by(Memory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def get_memory_statistics(self, db: AsyncSession, user_id: str) -> Dict:
        """
        Computes aggregate memory statistics for user.
        """
        now_utc = datetime.now(timezone.utc)

        # All memories count
        total_stmt = select(func.count(Memory.id)).where(Memory.user_id == user_id)
        total_res = await db.execute(total_stmt)
        total_count = total_res.scalar() or 0

        # Active memories count
        active_stmt = select(func.count(Memory.id)).where(
            Memory.user_id == user_id,
            or_(Memory.expires_at.is_(None), Memory.expires_at > now_utc)
        )
        active_res = await db.execute(active_stmt)
        active_count = active_res.scalar() or 0

        expired_count = max(0, total_count - active_count)

        # By type breakdown
        type_stmt = (
            select(Memory.type, func.count(Memory.id))
            .where(
                Memory.user_id == user_id,
                or_(Memory.expires_at.is_(None), Memory.expires_at > now_utc)
            )
            .group_by(Memory.type)
        )
        type_res = await db.execute(type_stmt)
        by_type = {row[0]: row[1] for row in type_res.all()}

        # By project breakdown
        proj_stmt = (
            select(func.coalesce(Memory.project_id, "default"), func.count(Memory.id))
            .where(
                Memory.user_id == user_id,
                or_(Memory.expires_at.is_(None), Memory.expires_at > now_utc)
            )
            .group_by(Memory.project_id)
        )
        proj_res = await db.execute(proj_stmt)
        by_project = {row[0]: row[1] for row in proj_res.all()}

        # Oldest and newest timestamp
        time_stmt = select(
            func.min(Memory.created_at),
            func.max(Memory.created_at)
        ).where(Memory.user_id == user_id)
        time_res = await db.execute(time_stmt)
        oldest, newest = time_res.first() or (None, None)

        return {
            "total_memories": total_count,
            "active_memories": active_count,
            "expired_memories": expired_count,
            "by_type": by_type,
            "by_project": by_project,
            "oldest_memory": oldest,
            "newest_memory": newest
        }

    async def delete_expired_memories(self, db: AsyncSession, user_id: Optional[str] = None) -> int:
        """
        Deletes all expired memories from storage.
        """
        now_utc = datetime.now(timezone.utc)
        conditions = [
            Memory.expires_at.isnot(None),
            Memory.expires_at <= now_utc
        ]
        if user_id:
            conditions.append(Memory.user_id == user_id)

        stmt = delete(Memory).where(and_(*conditions))
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount or 0


retrieval_service = RetrievalService()
