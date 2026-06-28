"""
Tests for backend/retrieval.py (Phase 3).

Strategy: tests use the TF-IDF path (no heavy model required) unless
sentence-transformers + faiss-cpu are installed, in which case embedding
path tests also run.

Run with: python -m pytest tests/test_retrieval.py -v
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from typing import List, Optional

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.candidate_parser import CandidateProfile, parse_candidate
from backend.config_loader import load_config, reset_cache
from backend.retrieval import (
    RetrievalResult,
    SemanticRetriever,
    _rrf_merge,
    _title_safety_ids,
    _EmbeddingCache,
)
from backend.jd_parser import JD_PROFILE

# Check optional deps
try:
    import faiss  # noqa
    import sentence_transformers  # noqa
    _EMBEDDING_OK = True
except ImportError:
    _EMBEDDING_OK = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_config():
    reset_cache()
    yield
    reset_cache()


def _make_profile(
    candidate_id: str,
    title: str = "Senior ML Engineer",
    description: str = "Built NLP ranking system using FAISS and transformers.",
    skills: Optional[List[str]] = None,
) -> CandidateProfile:
    if skills is None:
        skills = ["Python", "FAISS", "NLP", "Transformers"]
    raw = {
        "candidate_id": candidate_id,
        "profile": {
            "current_title": title,
            "headline": f"{title} — AI/ML expert",
            "summary": "Deep ML background with production deployment experience.",
            "location": "Pune",
            "country": "India",
            "years_of_experience": 6.0,
            "current_company": "StartupCo",
            "current_company_size": "51-200",
            "current_industry": "Technology",
        },
        "career_history": [
            {
                "company": "StartupCo",
                "title": title,
                "start_date": "2020-01-01",
                "end_date": None,
                "duration_months": 77,
                "is_current": True,
                "industry": "Technology",
                "company_size": "51-200",
                "description": description,
            }
        ],
        "education": [
            {
                "institution": "IIT Bombay",
                "degree": "B.Tech",
                "field_of_study": "Computer Science",
                "start_year": 2014,
                "end_year": 2018,
                "grade": None,
                "tier": "tier_1",
            }
        ],
        "skills": [{"name": s, "proficiency": "advanced", "endorsements": 50, "duration_months": 24} for s in skills],
        "redrob_signals": {
            "last_active_date": "2026-06-20",
            "open_to_work_flag": True,
            "recruiter_response_rate": 0.80,
            "notice_period_days": 30,
            "github_activity_score": 60,
            "interview_completion_rate": 0.85,
        },
        "certifications": [],
    }
    return parse_candidate(raw)


def _make_unrelated_profile(candidate_id: str) -> CandidateProfile:
    return _make_profile(
        candidate_id,
        title="HR Manager",
        description="Managed recruitment processes. No technical background.",
        skills=["Communication", "Recruitment", "Excel"],
    )


def _make_pool(n_ml: int = 10, n_unrelated: int = 10) -> List[CandidateProfile]:
    pool = []
    for i in range(n_ml):
        pool.append(_make_profile(f"CAND_{i:07d}"))
    for i in range(n_unrelated):
        pool.append(_make_unrelated_profile(f"CAND_{n_ml + i:07d}"))
    return pool


# ---------------------------------------------------------------------------
# Unit tests: RRF merge
# ---------------------------------------------------------------------------

def test_rrf_merge_basic():
    list1 = ["A", "B", "C", "D"]
    list2 = ["B", "A", "D", "C"]
    result = _rrf_merge([list1, list2], k=60, top_n=4)
    # B appears early in both lists → should be ranked high
    assert result[0] in ("A", "B")
    assert set(result) == {"A", "B", "C", "D"}


def test_rrf_merge_single_list():
    ranked = ["X", "Y", "Z"]
    result = _rrf_merge([ranked], k=60, top_n=3)
    assert result == ["X", "Y", "Z"]


def test_rrf_merge_top_n_limits_output():
    result = _rrf_merge([["A", "B", "C", "D", "E"]], k=60, top_n=3)
    assert len(result) == 3


def test_rrf_merge_deduplicates():
    list1 = ["A", "B"]
    list2 = ["A", "C"]  # A appears in both
    result = _rrf_merge([list1, list2], k=60, top_n=3)
    assert result.count("A") == 1


# ---------------------------------------------------------------------------
# Unit tests: title safety net
# ---------------------------------------------------------------------------

def test_title_safety_net_includes_tier1():
    profiles = _make_pool(n_ml=3, n_unrelated=3)
    ml_ids = {p.candidate_id for p in profiles if "ml" in p.current_title.lower() or "ai" in p.current_title.lower()}
    safety = _title_safety_ids(profiles, JD_PROFILE)
    # All ML Engineer profiles should be in safety set
    for cid in ml_ids:
        assert cid in safety, f"{cid} should be in safety set"


def test_title_safety_net_excludes_hr():
    hr_profiles = [_make_unrelated_profile(f"CAND_{i:07d}") for i in range(5)]
    safety = _title_safety_ids(hr_profiles, JD_PROFILE)
    assert len(safety) == 0, "HR Manager titles should not be in safety set"


# ---------------------------------------------------------------------------
# Integration tests: SemanticRetriever (TF-IDF path)
# ---------------------------------------------------------------------------

def _make_tfidf_config():
    """Force TF-IDF backend regardless of whether FAISS is available."""
    import yaml
    from backend.config_loader import ScoringConfig, _validate

    cfg_path = Path(__file__).parent.parent / "config" / "scoring.yaml"
    data = yaml.safe_load(cfg_path.read_text())
    data["semantic"]["backend"] = "tfidf"
    data["semantic"]["rrf"]["enabled"] = False
    _validate(data)
    return ScoringConfig(data)


def test_retriever_tfidf_returns_result():
    cfg = _make_tfidf_config()
    profiles = _make_pool(n_ml=10, n_unrelated=10)
    retriever = SemanticRetriever(config=cfg, jd=JD_PROFILE)
    retriever.fit(profiles)
    result = retriever.retrieve(profiles)

    assert isinstance(result, RetrievalResult)
    assert result.backend_used == "tfidf"
    assert len(result.profiles) > 0


def test_retriever_tfidf_returns_all_candidates():
    cfg = _make_tfidf_config()
    profiles = _make_pool(n_ml=5, n_unrelated=5)
    retriever = SemanticRetriever(config=cfg)
    retriever.fit(profiles)
    result = retriever.retrieve(profiles)
    # TF-IDF scores all candidates
    assert len(result.profiles) == 10


def test_retriever_ml_candidates_score_higher():
    cfg = _make_tfidf_config()
    profiles = _make_pool(n_ml=5, n_unrelated=5)

    ml_ids = {p.candidate_id for p in profiles[:5]}
    unrelated_ids = {p.candidate_id for p in profiles[5:]}

    retriever = SemanticRetriever(config=cfg)
    retriever.fit(profiles)
    result = retriever.retrieve(profiles)

    ml_sims = [result.similarities.get(cid, 0.0) for cid in ml_ids]
    unrelated_sims = [result.similarities.get(cid, 0.0) for cid in unrelated_ids]

    assert sum(ml_sims) / len(ml_sims) > sum(unrelated_sims) / len(unrelated_sims), (
        "ML candidates should have higher TF-IDF similarity than HR Managers"
    )


def test_retriever_similarities_in_range():
    cfg = _make_tfidf_config()
    profiles = _make_pool(n_ml=5, n_unrelated=5)
    retriever = SemanticRetriever(config=cfg)
    retriever.fit(profiles)
    result = retriever.retrieve(profiles)
    for cid, sim in result.similarities.items():
        assert 0.0 <= sim <= 1.0, f"{cid}: similarity {sim} out of [0,1]"


def test_retriever_retrieve_without_fit_raises():
    cfg = _make_tfidf_config()
    retriever = SemanticRetriever(config=cfg)
    profiles = _make_pool(n_ml=3, n_unrelated=3)
    with pytest.raises(RuntimeError):
        retriever.retrieve(profiles)


def test_fit_and_retrieve_convenience():
    cfg = _make_tfidf_config()
    profiles = _make_pool(n_ml=5, n_unrelated=5)
    retriever = SemanticRetriever(config=cfg)
    result = retriever.fit_and_retrieve(profiles)
    assert isinstance(result, RetrievalResult)
    assert len(result.profiles) > 0


# ---------------------------------------------------------------------------
# Integration tests: embedding path (skip if not installed)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EMBEDDING_OK, reason="sentence-transformers/faiss-cpu not installed")
def test_retriever_embedding_returns_result():
    cfg = load_config()
    profiles = _make_pool(n_ml=10, n_unrelated=10)
    retriever = SemanticRetriever(config=cfg)
    retriever.fit(profiles)
    result = retriever.retrieve(profiles)
    assert isinstance(result, RetrievalResult)
    assert result.backend_used in ("embedding", "embedding+rrf")
    assert len(result.profiles) > 0


@pytest.mark.skipif(not _EMBEDDING_OK, reason="sentence-transformers/faiss-cpu not installed")
def test_retriever_embedding_pool_size():
    cfg = load_config()
    profiles = _make_pool(n_ml=5, n_unrelated=5)
    retriever = SemanticRetriever(config=cfg)
    result = retriever.fit_and_retrieve(profiles, min_pool_size=5)
    assert len(result.profiles) >= 5


@pytest.mark.skipif(not _EMBEDDING_OK, reason="sentence-transformers/faiss-cpu not installed")
def test_retriever_embedding_cache(tmp_path):
    """Second run with same source file should load from cache."""
    import json

    cfg = load_config()
    import yaml
    from backend.config_loader import ScoringConfig, _validate

    cfg_path = Path(__file__).parent.parent / "config" / "scoring.yaml"
    data = yaml.safe_load(cfg_path.read_text())
    data["semantic"]["embedding"]["cache"]["path"] = str(tmp_path / "cache")
    _validate(data)
    cfg = ScoringConfig(data)

    profiles = _make_pool(n_ml=5, n_unrelated=5)

    # Write fake source file
    source_file = tmp_path / "candidates.jsonl"
    source_file.write_text(
        "\n".join(json.dumps(p.raw) for p in profiles)
    )

    retriever1 = SemanticRetriever(config=cfg)
    retriever1.fit(profiles, source_path=source_file)

    retriever2 = SemanticRetriever(config=cfg)
    retriever2.fit(profiles, source_path=source_file)

    # Both should succeed; second run uses cache
    result2 = retriever2.retrieve(profiles)
    assert isinstance(result2, RetrievalResult)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_retriever_single_candidate():
    cfg = _make_tfidf_config()
    profiles = [_make_profile("CAND_0000001")]
    retriever = SemanticRetriever(config=cfg)
    result = retriever.fit_and_retrieve(profiles)
    assert len(result.profiles) == 1


def test_retriever_result_has_timing():
    cfg = _make_tfidf_config()
    profiles = _make_pool(n_ml=3, n_unrelated=3)
    retriever = SemanticRetriever(config=cfg)
    result = retriever.fit_and_retrieve(profiles)
    assert result.retrieval_time_sec >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
