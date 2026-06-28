"""
Tests for backend/candidate_parser.py (Phase 2).
Run with: python -m pytest tests/test_candidate_parser.py -v
"""

import sys
import json
import tempfile
from pathlib import Path
from datetime import date

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.candidate_parser import (
    parse_candidate,
    load_candidates,
    load_candidates_list,
    CandidateProfile,
    REFERENCE_DATE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_minimal_raw(candidate_id="CAND_0000001") -> dict:
    return {
        "candidate_id": candidate_id,
        "profile": {
            "anonymized_name": "Test User",
            "current_title": "Senior ML Engineer",
            "headline": "ML engineer with NLP focus",
            "summary": "Built ranking systems at scale using FAISS and transformers.",
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
                "title": "Senior ML Engineer",
                "start_date": "2022-01-01",
                "end_date": None,
                "duration_months": 29,
                "is_current": True,
                "industry": "Technology",
                "company_size": "51-200",
                "description": "Built production NLP ranking system. Deployed FAISS at 10M scale.",
            },
            {
                "company": "TCS",
                "title": "Software Engineer",
                "start_date": "2020-01-01",
                "end_date": "2021-12-31",
                "duration_months": 24,
                "is_current": False,
                "industry": "IT Services",
                "company_size": "10001+",
                "description": "Backend development using Java.",
            },
        ],
        "education": [
            {
                "institution": "IIT Bombay",
                "degree": "B.Tech",
                "field_of_study": "Computer Science",
                "start_year": 2016,
                "end_year": 2020,
                "grade": "8.5",
                "tier": "tier_1",
            }
        ],
        "skills": [
            {"name": "Python", "proficiency": "expert", "endorsements": 120, "duration_months": 60},
            {"name": "FAISS", "proficiency": "advanced", "endorsements": 40, "duration_months": 24},
            {"name": "NLP", "proficiency": "advanced", "endorsements": 55, "duration_months": 36},
        ],
        "redrob_signals": {
            "last_active_date": "2026-06-20",
            "open_to_work_flag": True,
            "recruiter_response_rate": 0.85,
            "notice_period_days": 30,
            "github_activity_score": 72,
            "interview_completion_rate": 0.90,
        },
        "certifications": [],
    }


def make_consulting_heavy_raw(candidate_id="CAND_0000002") -> dict:
    raw = make_minimal_raw(candidate_id)
    raw["career_history"] = [
        {
            "company": "TCS",
            "title": "ML Engineer",
            "start_date": "2018-01-01",
            "end_date": None,
            "duration_months": 100,
            "is_current": True,
            "industry": "IT Services",
            "company_size": "10001+",
            "description": "Consulting ML work.",
        }
    ]
    return raw


def make_inactive_raw(candidate_id="CAND_0000003") -> dict:
    raw = make_minimal_raw(candidate_id)
    raw["redrob_signals"]["last_active_date"] = "2025-06-01"  # ~390 days ago
    return raw


# ---------------------------------------------------------------------------
# Test 1: parse_candidate returns CandidateProfile
# ---------------------------------------------------------------------------
def test_parse_returns_candidate_profile():
    raw = make_minimal_raw()
    cp = parse_candidate(raw)
    assert isinstance(cp, CandidateProfile)
    assert cp.candidate_id == "CAND_0000001"


# ---------------------------------------------------------------------------
# Test 2: Scalar fields extracted correctly
# ---------------------------------------------------------------------------
def test_scalar_fields_extracted():
    raw = make_minimal_raw()
    cp = parse_candidate(raw)
    assert cp.current_title == "Senior ML Engineer"
    assert cp.location == "Pune"
    assert cp.country == "India"
    assert abs(cp.years_of_experience - 6.0) < 1e-6


# ---------------------------------------------------------------------------
# Test 3: Skill names normalized to lowercase
# ---------------------------------------------------------------------------
def test_skill_names_lowercase():
    raw = make_minimal_raw()
    cp = parse_candidate(raw)
    assert "python" in cp.skill_names_lower
    assert "faiss" in cp.skill_names_lower
    assert "nlp" in cp.skill_names_lower
    # No uppercase
    assert all(n == n.lower() for n in cp.skill_names_lower)


# ---------------------------------------------------------------------------
# Test 4: days_since_active computed correctly
# ---------------------------------------------------------------------------
def test_days_since_active_recent():
    raw = make_minimal_raw()
    cp = parse_candidate(raw)
    # last_active_date = 2026-06-20, reference = 2026-06-25
    assert cp.days_since_active == 5


def test_days_since_active_inactive():
    raw = make_inactive_raw()
    cp = parse_candidate(raw)
    assert cp.days_since_active > 300  # ~390 days


def test_days_since_active_missing():
    raw = make_minimal_raw()
    del raw["redrob_signals"]["last_active_date"]
    cp = parse_candidate(raw)
    assert cp.days_since_active == -1


# ---------------------------------------------------------------------------
# Test 5: Consulting fraction computed correctly
# ---------------------------------------------------------------------------
def test_consulting_fraction():
    raw = make_consulting_heavy_raw()
    cp = parse_candidate(raw)
    assert abs(cp.consulting_fraction - 1.0) < 1e-6, (
        f"Expected consulting_fraction=1.0, got {cp.consulting_fraction}"
    )


def test_mixed_career_consulting_fraction():
    raw = make_minimal_raw()
    cp = parse_candidate(raw)
    # 24 consulting months out of 53 total (29 + 24)
    expected = 24.0 / 53.0
    assert abs(cp.consulting_fraction - expected) < 0.01


# ---------------------------------------------------------------------------
# Test 6: ML fraction computed (career with ML title)
# ---------------------------------------------------------------------------
def test_ml_fraction_with_ml_title():
    raw = make_minimal_raw()
    cp = parse_candidate(raw)
    # "Senior ML Engineer" is an ML title — 29 months
    assert cp.ml_fraction > 0.0


# ---------------------------------------------------------------------------
# Test 7: profile_text contains key content
# ---------------------------------------------------------------------------
def test_profile_text_contains_key_signals():
    raw = make_minimal_raw()
    cp = parse_candidate(raw)
    text_lower = cp.profile_text.lower()
    assert "senior ml engineer" in text_lower
    assert "ranking" in text_lower or "faiss" in text_lower
    assert "python" in text_lower


# ---------------------------------------------------------------------------
# Test 8: raw dict is preserved for backwards compat
# ---------------------------------------------------------------------------
def test_raw_dict_preserved():
    raw = make_minimal_raw()
    cp = parse_candidate(raw)
    assert cp.raw is raw


# ---------------------------------------------------------------------------
# Test 9: Missing candidate_id raises ValueError
# ---------------------------------------------------------------------------
def test_missing_candidate_id_raises():
    raw = make_minimal_raw()
    del raw["candidate_id"]
    with pytest.raises(ValueError, match="candidate_id"):
        parse_candidate(raw)


# ---------------------------------------------------------------------------
# Test 10: load_candidates_list reads a JSONL file correctly
# ---------------------------------------------------------------------------
def test_load_candidates_list():
    records = [make_minimal_raw(f"CAND_{i:07d}") for i in range(1, 6)]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
        tmp_path = fh.name

    try:
        profiles = load_candidates_list(tmp_path)
        assert len(profiles) == 5
        ids = [p.candidate_id for p in profiles]
        assert "CAND_0000001" in ids
        assert "CAND_0000005" in ids
    finally:
        import os
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Test 11: Malformed lines are skipped when skip_invalid=True
# ---------------------------------------------------------------------------
def test_malformed_lines_skipped():
    good_record = json.dumps(make_minimal_raw("CAND_0000001"))
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as fh:
        fh.write(good_record + "\n")
        fh.write("not json at all\n")
        fh.write('{"candidate_id": null, "profile": {}}\n')  # missing id
        tmp_path = fh.name

    try:
        profiles = load_candidates_list(tmp_path, skip_invalid=True)
        assert len(profiles) == 1
        assert profiles[0].candidate_id == "CAND_0000001"
    finally:
        import os
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Test 12: Honeypot state defaults to False
# ---------------------------------------------------------------------------
def test_honeypot_defaults_to_false():
    cp = parse_candidate(make_minimal_raw())
    assert cp.is_honeypot is False
    assert cp.honeypot_reasons == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
