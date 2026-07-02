"""
Candidate normalization layer.

Parses raw JSONL dicts into CandidateProfile dataclasses with:
  - pre-computed derived fields (days_since_active, career fractions, etc.)
  - normalized skill/title lookups
  - pre-built profile_text for embedding and TF-IDF

The raw dict is retained as .raw so existing scorer.py code continues to work
during the phased refactoring.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from backend.constants import REFERENCE_DATE

_CONSULTING_TOKENS: frozenset = frozenset({
    "tcs", "tata consultancy", "tata consultancy services",
    "infosys", "wipro", "accenture", "cognizant",
    "cognizant technology solutions", "capgemini",
    "hcl", "hcl technologies", "tech mahindra",
    "hexaware", "mphasis", "l&t infotech", "ltimindtree",
    "mindtree", "niit technologies", "kpit",
})

_ML_TITLE_TOKENS: frozenset = frozenset({
    "ml engineer", "machine learning engineer",
    "ai engineer", "artificial intelligence engineer",
    "nlp engineer", "nlp scientist", "natural language",
    "search engineer", "ranking engineer",
    "recommendation engineer", "retrieval engineer",
    "applied scientist", "applied ml", "applied ai",
    "research engineer", "research scientist",
    "information retrieval",
    "senior data scientist", "staff data scientist", "principal data scientist",
    "senior ml", "staff ml", "principal ml", "lead ml",
    "senior ai", "staff ai", "principal ai",
    "mlops engineer", "data scientist",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except (ValueError, TypeError):
        return None


def _parse_year(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _months_between(start: date, end: date) -> float:
    return max(0.0, (end - start).days / 30.44)


def _is_consulting_firm(company_name: str) -> bool:
    name_lower = company_name.lower().strip()
    return any(tok in name_lower for tok in _CONSULTING_TOKENS)


def _has_ml_title(title: str) -> bool:
    title_lower = title.lower()
    return any(tok in title_lower for tok in _ML_TITLE_TOKENS)


# ---------------------------------------------------------------------------
# CandidateProfile dataclass
# ---------------------------------------------------------------------------

@dataclass
class CandidateProfile:
    """
    Normalized representation of one candidate record.

    Carries both the raw dict (for backwards-compat with existing scorer.py)
    and pre-computed derived fields used by the retrieval and ranking layers.
    """

    # Identity
    candidate_id: str

    # Original dict — passed through to existing scorer.py
    raw: Dict

    # Core profile fields (extracted for convenience)
    current_title: str
    headline: str
    summary: str
    location: str
    country: str
    years_of_experience: float

    # Structured sub-objects
    career_history: List[Dict]
    skills: List[Dict]
    education: List[Dict]
    redrob_signals: Dict
    certifications: List[Dict]

    # Derived / computed
    skill_names_lower: List[str]        # lowercase skill names
    days_since_active: int              # -1 if last_active_date absent
    career_months_total: float
    career_months_consulting: float
    career_months_ml: float
    consulting_fraction: float          # consulting / total
    ml_fraction: float                  # ml / total

    # Combined text for embedding & TF-IDF vectorisation
    profile_text: str

    # Honeypot state — populated externally by honeypot.detect_honeypot()
    is_honeypot: bool = False
    honeypot_reasons: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Build profile_text
# ---------------------------------------------------------------------------

def _build_profile_text(raw: Dict) -> str:
    """
    Concatenate the most signal-rich text fields for semantic embedding.

    Order matters for sentence-transformers: more important signals first.
    """
    parts: List[str] = []
    profile = raw.get("profile", {})

    # Current role context
    title = str(profile.get("current_title", "")).strip()
    if title:
        parts.append(title)
        parts.append(title)  # repeat for weighting boost

    headline = str(profile.get("headline", "")).strip()
    if headline:
        parts.append(headline)

    summary = str(profile.get("summary", "")).strip()
    if summary:
        parts.append(summary)

    # Career descriptions (most information-dense field)
    for job in raw.get("career_history", []):
        job_title = str(job.get("title", "")).strip()
        if job_title:
            parts.append(job_title)
        desc = str(job.get("description", "")).strip()
        if desc:
            parts.append(desc)

    # Skills
    skill_names = [
        str(s.get("name", "")).strip() if isinstance(s, dict) else str(s).strip()
        for s in raw.get("skills", [])
    ]
    skill_names = [n for n in skill_names if n]
    if skill_names:
        parts.append("Skills: " + ", ".join(skill_names))

    # Education
    for edu in raw.get("education", []):
        fos = str(edu.get("field_of_study", "")).strip()
        deg = str(edu.get("degree", "")).strip()
        if fos or deg:
            parts.append(f"{deg} {fos}".strip())

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Career fraction computation
# ---------------------------------------------------------------------------

def _compute_career_fractions(
    career: List[Dict],
) -> Tuple[float, float, float]:
    """
    Return (total_months, consulting_months, ml_months).
    Months are measured from career entries; overlapping periods counted once
    via the raw duration_months field (organizer-provided, trusted).
    """
    total = 0.0
    consulting = 0.0
    ml = 0.0

    for job in career:
        dur = float(job.get("duration_months", 0) or 0)
        company = str(job.get("company", ""))
        title = str(job.get("title", ""))

        total += dur
        if _is_consulting_firm(company):
            consulting += dur
        if _has_ml_title(title):
            ml += dur

    return total, consulting, ml


# ---------------------------------------------------------------------------
# Main parse function
# ---------------------------------------------------------------------------

def parse_candidate(raw: Dict) -> CandidateProfile:
    """
    Convert a raw JSONL dict into a CandidateProfile.

    Raises ValueError if candidate_id is missing.
    """
    cid = raw.get("candidate_id")
    if not cid:
        raise ValueError(f"candidate_id missing in record: {str(raw)[:120]}")

    # Normalize string skills to dicts so all downstream code can safely call .get()
    if raw.get("skills"):
        raw["skills"] = [
            s if isinstance(s, dict) else {"name": str(s)}
            for s in raw["skills"]
        ]

    profile_dict = raw.get("profile", {})
    career = raw.get("career_history", [])
    skills = raw.get("skills", [])
    education = raw.get("education", [])
    signals = raw.get("redrob_signals", {})
    certs = raw.get("certifications", [])

    # --- Scalar extractions ---
    current_title = str(profile_dict.get("current_title", "")).strip()
    headline = str(profile_dict.get("headline", "")).strip()
    summary = str(profile_dict.get("summary", "")).strip()
    location = str(profile_dict.get("location", "")).strip()
    country = str(profile_dict.get("country", "")).strip()

    try:
        yoe = float(profile_dict.get("years_of_experience", 0) or 0)
    except (ValueError, TypeError):
        yoe = 0.0

    # --- Skill names ---
    skill_names_lower = [
        (str(s.get("name", "")).lower().strip() if isinstance(s, dict) else str(s).lower().strip())
        for s in skills
        if (s.get("name") if isinstance(s, dict) else s)
    ]

    # --- Days since active ---
    last_active_raw = signals.get("last_active_date")
    last_active = _parse_date(last_active_raw)
    if last_active:
        days_since_active = (REFERENCE_DATE - last_active).days
    else:
        days_since_active = -1

    # --- Career fractions ---
    total_months, consulting_months, ml_months = _compute_career_fractions(career)
    consulting_frac = consulting_months / total_months if total_months > 0 else 0.0
    ml_frac = ml_months / total_months if total_months > 0 else 0.0

    # --- Profile text for embedding ---
    profile_text = _build_profile_text(raw)

    return CandidateProfile(
        candidate_id=cid,
        raw=raw,
        current_title=current_title,
        headline=headline,
        summary=summary,
        location=location,
        country=country,
        years_of_experience=yoe,
        career_history=career,
        skills=skills,
        education=education,
        redrob_signals=signals,
        certifications=certs if certs else [],
        skill_names_lower=skill_names_lower,
        days_since_active=days_since_active,
        career_months_total=total_months,
        career_months_consulting=consulting_months,
        career_months_ml=ml_months,
        consulting_fraction=consulting_frac,
        ml_fraction=ml_frac,
        profile_text=profile_text,
    )


# ---------------------------------------------------------------------------
# JSONL loader
# ---------------------------------------------------------------------------

def load_candidates(
    path: "Union[str, Path]",
    skip_invalid: bool = True,
) -> Iterator[CandidateProfile]:
    """
    Stream CandidateProfile objects from a JSONL file.

    Args:
        path: Path to candidates.jsonl
        skip_invalid: If True, log and skip malformed lines instead of raising.

    Yields:
        CandidateProfile for each valid record.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Candidates file not found: {path}")

    errors = 0
    parsed = 0

    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
                yield parse_candidate(raw)
                parsed += 1
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                errors += 1
                if not skip_invalid:
                    raise
                if errors <= 10:  # suppress repetitive noise beyond first 10
                    print(f"[candidate_parser] skip line {line_no}: {exc}")

    if errors:
        print(
            f"[candidate_parser] loaded {parsed} candidates, skipped {errors} invalid lines"
        )


def load_candidates_list(
    path: "Union[str, Path]",
    skip_invalid: bool = True,
) -> List[CandidateProfile]:
    """Convenience wrapper that returns a list (loads entire file into memory)."""
    return list(load_candidates(path, skip_invalid=skip_invalid))
