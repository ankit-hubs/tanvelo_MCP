"""
Core Memory Orchestration Service
Coordinates extraction, embedding, duplicate resolution, persistence, context generation,
updating, statistics, bulk operations, export, and expiration cleanup.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory, generate_memory_id
from app.schemas.memory import (
    MemorySaveRequest,
    MemorySaveResponse,
    MemoryUpdateRequest,
    MemoryBulkSaveRequest,
    MemoryBulkSaveResponse,
    MemorySearchResponse,
    MemoryContextResponse,
    MemoryForgetResponse,
    MemoryListResponse,
    MemoryStatsResponse,
    MemoryExportResponse,
    MemoryCleanupResponse,
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

    async def update_memory(
        self,
        db: AsyncSession,
        user_id: str,
        memory_id: str,
        request: MemoryUpdateRequest
    ) -> Optional[MemoryRecord]:
        """Updates specific fields of an existing memory."""
        stmt = select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id)
        res = await db.execute(stmt)
        mem = res.scalars().first()
        if not mem:
            return None

        now_utc = datetime.now(timezone.utc)
        if request.content is not None:
            mem.content = request.content
            mem.embedding = await embedding_service.get_embedding(request.content)
        if request.type is not None:
            mem.type = request.type
        if request.importance is not None:
            mem.importance = request.importance
        if request.expires_in_hours is not None:
            mem.expires_at = now_utc + timedelta(hours=request.expires_in_hours)

        mem.updated_at = now_utc
        await db.commit()
        await db.refresh(mem)
        return self._to_record(mem)

    async def bulk_save_memories(
        self,
        db: AsyncSession,
        user_id: str,
        request: MemoryBulkSaveRequest
    ) -> MemoryBulkSaveResponse:
        """Processes and stores a batch of memories in sequence."""
        created_count = 0
        updated_count = 0
        ignored_count = 0
        results: List[MemorySaveResponse] = []

        for item_req in request.memories:
            res = await self.save_memory(db=db, user_id=user_id, request=item_req)
            results.append(res)
            if res.action == "created":
                created_count += 1
            elif res.action == "updated":
                updated_count += 1
            else:
                ignored_count += 1

        return MemoryBulkSaveResponse(
            total_processed=len(request.memories),
            created=created_count,
            updated=updated_count,
            ignored=ignored_count,
            results=results
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
        project_id: Optional[str] = None,
        max_characters: int = 4000
    ) -> MemoryContextResponse:
        """Retrieves top memories and formats them as a clean Markdown context block with budgeting."""
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

        lines = ["### [Tanvelo Long-Term Memory Context]"]
        total_len = len(lines[0])
        included_records: List[MemoryRecord] = []

        for r in records:
            line = f"- **[{r.type}]**: {r.content} *(importance: {r.importance:.2f})*"
            if total_len + len(line) + 1 > max_characters:
                break
            lines.append(line)
            total_len += len(line) + 1
            included_records.append(r)

        context_str = "\n".join(lines)

        return MemoryContextResponse(
            context=context_str,
            memories=included_records,
            count=len(included_records)
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
            clean_query = query.strip()
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
        project_id: Optional[str] = None,
        memory_type: Optional[str] = None
    ) -> MemoryListResponse:
        """Lists active memories for the user."""
        memories, total = await retrieval_service.get_all_active_memories(
            db=db,
            user_id=user_id,
            limit=limit,
            offset=offset,
            project_id=project_id,
            memory_type=memory_type
        )
        records = [self._to_record(m) for m in memories]
        return MemoryListResponse(
            memories=records,
            total=total,
            limit=limit,
            offset=offset
        )

    async def get_stats(self, db: AsyncSession, user_id: str) -> MemoryStatsResponse:
        """Returns statistics for authenticated user's memory repository."""
        stats = await retrieval_service.get_memory_statistics(db=db, user_id=user_id)
        return MemoryStatsResponse(**stats)

    async def export_memories(
        self,
        db: AsyncSession,
        user_id: str,
        format: str = "json",
        project_id: Optional[str] = None
    ) -> MemoryExportResponse:
        """Exports user memories in JSON or Markdown format."""
        memories, total = await retrieval_service.get_all_active_memories(
            db=db,
            user_id=user_id,
            limit=10000,
            offset=0,
            project_id=project_id
        )
        records = [self._to_record(m) for m in memories]
        now_utc = datetime.now(timezone.utc)

        if format.lower() == "markdown":
            lines = [f"# Tanvelo Memory Export", f"- Exported At: {now_utc.isoformat()}", f"- Total Memories: {total}", ""]
            for r in records:
                proj_tag = f" `[{r.project_id}]`" if r.project_id else ""
                lines.append(f"- **[{r.type}]**{proj_tag}: {r.content} *(importance: {r.importance:.2f})*")
            content_str = "\n".join(lines)
        else:
            export_payload = [r.model_dump(mode="json") for r in records]
            content_str = json.dumps(export_payload, indent=2, default=str)

        return MemoryExportResponse(
            format=format.lower(),
            total=total,
            exported_at=now_utc,
            content=content_str
        )

    async def cleanup_expired(self, db: AsyncSession, user_id: Optional[str] = None) -> MemoryCleanupResponse:
        """Purges expired memories from storage."""
        count = await retrieval_service.delete_expired_memories(db=db, user_id=user_id)
        return MemoryCleanupResponse(
            deleted_count=count,
            message=f"Successfully purged {count} expired memory record(s)."
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
