"""
Tests for Hybrid Ranking Algorithm (PRD Section 23)
"""

from datetime import datetime, timezone, timedelta
import pytest
from app.models.memory import Memory, generate_memory_id
from app.services.ranking_service import RankingService


def test_ranking_formula_calculation():
    """
    Test direct score calculation: 0.60 * Sim + 0.25 * Imp + 0.15 * Rec
    """
    ranking = RankingService(w_sim=0.60, w_imp=0.25, w_rec=0.15)
    now = datetime.now(timezone.utc)

    # Score for sim=1.0, imp=1.0, rec=1.0 (now) -> 0.60 + 0.25 + 0.15 = 1.0
    score_perfect = ranking.compute_hybrid_score(similarity=1.0, importance=1.0, timestamp=now)
    assert score_perfect == 1.0

    # Score for sim=0.8, imp=0.4, rec=1.0 -> 0.60*0.8 (0.48) + 0.25*0.4 (0.10) + 0.15*1.0 (0.15) = 0.73
    score_mid = ranking.compute_hybrid_score(similarity=0.8, importance=0.4, timestamp=now)
    assert pytest.approx(score_mid, 0.01) == 0.73


def test_ranking_importance_tie_breaker():
    """
    When similarity is equal, higher importance must rank first.
    """
    ranking = RankingService()
    now = datetime.now(timezone.utc)

    mem_high_imp = Memory(
        id=generate_memory_id(),
        user_id="u1",
        content="Important architectural rule",
        type="decision",
        importance=0.95,
        confidence=1.0,
        created_at=now,
        updated_at=now
    )

    mem_low_imp = Memory(
        id=generate_memory_id(),
        user_id="u1",
        content="Minor note",
        type="temporary",
        importance=0.20,
        confidence=1.0,
        created_at=now,
        updated_at=now
    )

    # Both have equal similarity 0.85
    candidates = [(mem_low_imp, 0.85), (mem_high_imp, 0.85)]
    ranked = ranking.rank_memories(candidates, top_k=2)

    # High importance item should be first
    assert ranked[0][0].id == mem_high_imp.id
    assert ranked[1][0].id == mem_low_imp.id
    assert ranked[0][2] > ranked[1][2]  # Higher hybrid score
