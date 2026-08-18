"""
Hybrid Ranking Service
Combines Semantic Vector Similarity (0.60), Importance (0.25), and Recency (0.15).
"""

import math
from datetime import datetime, timezone
from typing import List, Tuple
from app.config import settings
from app.models.memory import Memory


class RankingService:
    def __init__(
        self,
        w_sim: float = settings.RANKING_WEIGHT_SIMILARITY,
        w_imp: float = settings.RANKING_WEIGHT_IMPORTANCE,
        w_rec: float = settings.RANKING_WEIGHT_RECENCY,
        half_life_days: float = 30.0
    ):
        self.w_sim = w_sim
        self.w_imp = w_imp
        self.w_rec = w_rec
        self.half_life_days = half_life_days

    def compute_recency_score(self, dt: datetime) -> float:
        """
        Computes exponential decay recency score in [0.0, 1.0].
        Score = 1.0 when created/updated now.
        """
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        delta_seconds = max(0.0, (now - dt).total_seconds())
        delta_days = delta_seconds / 86400.0

        # Exponential decay: e^(-delta_days / 30.0)
        recency = math.exp(-delta_days / self.half_life_days)
        return max(0.0, min(1.0, recency))

    def compute_hybrid_score(
        self,
        similarity: float,
        importance: float,
        timestamp: datetime
    ) -> float:
        """
        Final Score = w_sim * Similarity + w_imp * Importance + w_rec * Recency
        """
        sim_clamped = max(0.0, min(1.0, similarity))
        imp_clamped = max(0.0, min(1.0, importance))
        rec = self.compute_recency_score(timestamp)

        score = (self.w_sim * sim_clamped) + (self.w_imp * imp_clamped) + (self.w_rec * rec)
        return round(score, 4)

    def rank_memories(
        self,
        scored_memories: List[Tuple[Memory, float]],
        top_k: int = 5
    ) -> List[Tuple[Memory, float, float]]:
        """
        Ranks memories using the hybrid formula.
        Input: List of (Memory, cosine_similarity)
        Returns: Sorted List of (Memory, cosine_similarity, hybrid_score)
        """
        ranked = []
        for mem, sim in scored_memories:
            ts = mem.updated_at or mem.created_at
            h_score = self.compute_hybrid_score(
                similarity=sim,
                importance=mem.importance,
                timestamp=ts
            )
            ranked.append((mem, sim, h_score))

        # Sort descending by hybrid_score, breaking ties by similarity
        ranked.sort(key=lambda x: (x[2], x[1]), reverse=True)
        return ranked[:top_k]


ranking_service = RankingService()
