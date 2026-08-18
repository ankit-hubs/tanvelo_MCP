"""
Core Memory Orchestration Service
Coordinates extraction, embedding, duplicate resolution, persistence, context generation, and deletion.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory, generate_memory_id
from app.schemas.memory import (
    MemorySaveRequest,
    MemorySaveResponse,
    MemorySearchResponse,
    MemoryContextResponse,
    MemoryForgetResponse,
    MemoryListResponse,
    MemoryRecord
)
from app.services.extraction_service import extraction_service
from app.services.embedding_service import embedding_service
from app.services.retrieval_service import retrieval_service
from app.services.duplicate_service import duplicate_service

logger = logging.getLogger("tanvelo.memory")


class MemoryService:
    async def save_memory(
        self,
        db: AsyncSession,
        user_id: str,
        request: MemorySaveRequest
    ) -> MemorySaveResponse:
        """
        Orchestrates memory processing: Extraction -> Validation -> Embedding -> Duplicate Check -> Store/Update/Ignore.
        """
        # Step 1: Memory Extraction & Importance Evaluation
        extraction = await extraction_service.extract_memories(
            raw_text=request.content,
            manual_type=request.type,
            manual_importance=request.importance,
            force_store=request.force_store
        )

        if not extraction.should_store or not extraction.memories:
            return MemorySaveResponse(
                success=True,
                action="ignored",
                memory_id=None,
                stored_memories=[],
                message="Information evaluated as low-value, transient, or excluded by user instruction."
            )

        stored_records: List[MemoryRecord] = []
        overall_action = "created"
        primary_memory_id = None

        now_utc = datetime.now(timezone.utc)

        for item in extraction.memories:
            # Step 2: Generate Vector Embedding
            emb = await embedding_service.get_embedding(item.content)

            # Step 3: Duplicate Detection
            dup_memory, sim = await duplicate_service.find_duplicate(
                db=db,
                user_id=user_id,
                candidate_embedding=emb,
                project_id=request.project_id
            )

            # Calculate Expiration Date
            expires_at = None
            if item.expires:
                hours = item.expires_in_hours or 24.0
                expires_at = now_utc + timedelta(hours=hours)

            if dup_memory:
                # Update existing memory in-place
                logger.info(f"Duplicate detected (similarity={sim:.2f}) for '{item.content[:40]}...'. Updating memory {dup_memory.id}.")
                dup_memory.content = item.content
                dup_memory.type = item.type
                dup_memory.importance = max(dup_memory.importance, item.importance)
                dup_memory.confidence = item.confidence
                dup_memory.embedding = emb
                dup_memory.updated_at = now_utc
                if expires_at:
                    dup_memory.expires_at = expires_at

                await db.commit()
                await db.refresh(dup_memory)

                overall_action = "updated"
                primary_memory_id = dup_memory.id
                stored_records.append(self._to_record(dup_memory, similarity=sim))
            else:
                # Create brand new memory
                new_mem_id = generate_memory_id()
                new_mem = Memory(
                    id=new_mem_id,
                    user_id=user_id,
                    content=item.content,
                    type=item.type,
                    importance=item.importance,
                    confidence=item.confidence,
                    source=request.source or "mcp",
                    project_id=request.project_id,
                    embedding=emb,
                    created_at=now_utc,
                    updated_at=now_utc,
                    expires_at=expires_at
                )
                db.add(new_mem)
                await db.commit()
                await db.refresh(new_mem)

                if not primary_memory_id:
                    primary_memory_id = new_mem.id
                stored_records.append(self._to_record(new_mem, similarity=1.0))

        return MemorySaveResponse(
            success=True,
            action=overall_action,
            memory_id=primary_memory_id,
            stored_memories=stored_records,
            message=f"Memory successfully {overall_action}."
        )

    async def search_memories(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        limit: int = 5,
        project_id: Optional[str] = None,
        memory_type: Optional[str] = None
    ) -> MemorySearchResponse:
        """Finds relevant memories using semantic similarity and hybrid ranking."""
        ranked_results = await retrieval_service.search_memories(
            db=db,
            user_id=user_id,
            query=query,
            limit=limit,
            project_id=project_id,
            memory_type=memory_type
        )

        records = [
            self._to_record(mem, similarity=sim, hybrid_score=h_score)
            for mem, sim, h_score in ranked_results
        ]

        return MemorySearchResponse(
            memories=records,
            total_found=len(records)
        )

    async def get_context(
        self,
        db: AsyncSession,
        user_id: str,
        query: str,
        limit: int = 5,
        project_id: Optional[str] = None
    ) -> MemoryContextResponse:
        """Retrieves top memories and formats them as a clean Markdown context block."""
        ranked_results = await retrieval_service.search_memories(
            db=db,
            user_id=user_id,
            query=query,
            limit=limit,
            project_id=project_id
        )

        records = [
            self._to_record(mem, similarity=sim, hybrid_score=h_score)
            for mem, sim, h_score in ranked_results
        ]

        if not records:
            return MemoryContextResponse(
                context="",
                memories=[],
                count=0
            )

        # Build clean markdown context for AI tool prompt injection
        lines = ["### [Tanvelo Long-Term Memory Context]"]
        for r in records:
            lines.append(f"- **[{r.type}]**: {r.content} *(importance: {r.importance:.2f})*")

        context_str = "\n".join(lines)

        return MemoryContextResponse(
            context=context_str,
            memories=records,
            count=len(records)
        )

    async def forget_memory(
        self,
        db: AsyncSession,
        user_id: str,
        memory_id: Optional[str] = None,
        query: Optional[str] = None
    ) -> MemoryForgetResponse:
        """
        Deletes a specific memory by ID or by semantic query match (e.g. 'Forget that Tanvelo uses Supabase').
        """
        deleted_ids: List[str] = []

        if memory_id:
            # Delete exact memory ID scoped to authenticated user
            stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
            res = await db.execute(stmt)
            mem = res.scalars().first()
            if mem:
                await db.delete(mem)
                await db.commit()
                deleted_ids.append(memory_id)
                return MemoryForgetResponse(
                    success=True,
                    message=f"Memory '{memory_id}' forgotten successfully.",
                    forgotten_ids=deleted_ids
                )
            else:
                return MemoryForgetResponse(
                    success=False,
                    message=f"Memory '{memory_id}' not found.",
                    forgotten_ids=[]
                )

        if query:
            # Search for closest matches to delete
            clean_query = query.strip()
            # Strip prefixes like "Forget that..."
            for prefix in ["forget that", "forget", "delete memory about", "remove"]:
                if clean_query.lower().startswith(prefix):
                    clean_query = clean_query[len(prefix):].strip()

            ranked = await retrieval_service.search_memories(
                db=db,
                user_id=user_id,
                query=clean_query,
                limit=5,
                min_similarity=0.0
            )

            if ranked:
                # Find matching memories by similarity or significant word overlap
                query_words = set(w.lower() for w in clean_query.split() if len(w) > 3)
                for mem, sim, _ in ranked:
                    mem_words = set(w.lower() for w in mem.content.split())
                    has_overlap = bool(query_words & mem_words)
                    if sim >= 0.50 or clean_query.lower() in mem.content.lower() or has_overlap:
                        deleted_ids.append(mem.id)
                        await db.delete(mem)

                if deleted_ids:
                    await db.commit()
                    return MemoryForgetResponse(
                        success=True,
                        message=f"Successfully forgotten {len(deleted_ids)} related memory(s).",
                        forgotten_ids=deleted_ids
                    )

            return MemoryForgetResponse(
                success=False,
                message=f"No matching memories found to forget for query: '{query}'.",
                forgotten_ids=[]
            )

        return MemoryForgetResponse(
            success=False,
            message="Either 'memory_id' or 'query' must be provided.",
            forgotten_ids=[]
        )

    async def list_memories(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
        memory_type: Optional[str] = None
    ) -> MemoryListResponse:
        """Lists active memories for the user."""
        memories, total = await retrieval_service.get_all_active_memories(
            db=db,
            user_id=user_id,
            limit=limit,
            offset=offset,
            memory_type=memory_type
        )
        records = [self._to_record(m) for m in memories]
        return MemoryListResponse(
            memories=records,
            total=total,
            limit=limit,
            offset=offset
        )

    @staticmethod
    def _to_record(
        mem: Memory,
        similarity: Optional[float] = None,
        hybrid_score: Optional[float] = None
    ) -> MemoryRecord:
        return MemoryRecord(
            id=mem.id,
            user_id=mem.user_id,
            content=mem.content,
            type=mem.type,
            importance=mem.importance,
            confidence=mem.confidence,
            source=mem.source,
            project_id=mem.project_id,
            created_at=mem.created_at,
            updated_at=mem.updated_at,
            expires_at=mem.expires_at,
            similarity=similarity,
            hybrid_score=hybrid_score
        )


memory_service = MemoryService()
