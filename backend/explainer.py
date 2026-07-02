"""
Reasoning generation.

Produces a recruiter-quality 2-4 sentence justification for each candidate.
Explanations are evidence-driven: they cite specific career history, skills,
and behavioral signals — never vague phrases like 'strong fit' or 'high potential'.

Five narrative styles are chosen based on the candidate's dominant scoring signal,
so the output varies meaningfully across candidates rather than repeating a template.
"""

from datetime import date, datetime
from typing import Dict, List, Optional, Set, Tuple
import re

from backend.constants import REFERENCE_DATE

# Core JD signals used for evidence extraction (subset of jd_parser constants)
_REQUIRED_SKILLS: Set[str] = {
    "embeddings", "embedding", "faiss", "semantic search", "vector search",
    "dense retrieval", "nlp", "natural language processing",
    "information retrieval", "ranking", "reranking", "re-ranking",
    "learning to rank", "ltr", "sentence transformers", "sentence-transformers",
    "python", "machine learning", "deep learning", "transformer", "bert",
    "rag", "retrieval augmented generation", "llm", "large language model",
    "pinecone", "weaviate", "elasticsearch", "opensearch",
    "ndcg", "mrr", "a/b testing", "recommendation", "recommender",
    "hybrid search", "bm25", "vector database", "ann",
}

_PRODUCTION_KEYWORDS: Set[str] = {
    "deployed", "production", "serving", "served", "shipped", "launched",
    "scale", "million", "billion", "real users", "latency", "throughput",
    "qps", "tps", "p99", "p95", "a/b test", "ab test", "online experiment",
    "end-to-end", "ranking system", "retrieval system", "search system",
    "recommendation system", "real-time", "online inference", "index refresh",
}

_ML_TITLE_TOKENS: Set[str] = {
    "ml", "ai", "nlp", "search", "ranking", "retrieval", "scientist",
    "machine learning", "research", "applied", "recommendation",
}


def _parse_date(value) -> Optional[date]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except (ValueError, TypeError):
        return None


def _days_since(d: Optional[date]) -> int:
    if d is None:
        return 9999
    return max(0, (REFERENCE_DATE - d).days)


def _activity_phrase(sig: Dict) -> str:
    last = _parse_date(sig.get("last_active_date"))
    d = _days_since(last)
    otw = sig.get("open_to_work_flag", False)
    notice = sig.get("notice_period_days")
    rrr = sig.get("recruiter_response_rate", -1)

    activity = ""
    if d < 3:
        activity = "active today"
    elif d < 8:
        activity = "active this week"
    elif d < 30:
        weeks = d // 7
        activity = f"active {weeks}w ago"

    notice_str = ""
    if notice is not None:
        if notice <= 7:
            notice_str = "immediate joiner"
        elif notice <= 15:
            notice_str = f"short notice: {notice} days"
        elif notice <= 25:
            notice_str = f"short {notice}-day notice"
        elif notice <= 30:
            notice_str = f"{notice}-day notice"
        else:
            notice_str = f"{notice}-day notice period"

    parts = [p for p in [activity, "open to work" if otw else "", notice_str] if p]
    response = ""
    if isinstance(rrr, (int, float)) and rrr >= 0.90:
        response = f"exceptional {rrr:.0%} response rate"
    elif isinstance(rrr, (int, float)) and rrr >= 0.80:
        response = f"{rrr:.0%} response rate"
    elif isinstance(rrr, (int, float)) and 0 <= rrr < 0.20:
        response = f"low response rate ({rrr:.0%})"
    if response:
        parts.append(response)
    # Recruiter demand signal — surface high demand as a trust signal
    saved = sig.get("saved_by_recruiters_30d")
    if isinstance(saved, (int, float)) and saved >= 8:
        parts.append(f"saved by {int(saved)} recruiters this month")
    return ", ".join(parts)


def _top_jd_skills(skills: List[Dict], n: int = 4) -> List[Dict]:
    """Return top N skills prioritizing JD-matched ones, sorted by proficiency then endorsements."""
    order = {"expert": 0, "advanced": 1, "intermediate": 2, "beginner": 3}
    jd_matched = [s for s in skills if s.get("name", "").lower() in _REQUIRED_SKILLS]
    other = [s for s in skills if s.get("name", "").lower() not in _REQUIRED_SKILLS]
    ranked = sorted(jd_matched, key=lambda s: (order.get(s.get("proficiency", "beginner"), 3), -s.get("endorsements", 0)))
    ranked += sorted(other, key=lambda s: (order.get(s.get("proficiency", "beginner"), 3), -s.get("endorsements", 0)))
    return ranked[:n]


def _skill_names(skills: List[Dict], n: int = 4) -> List[str]:
    return [s["name"] for s in _top_jd_skills(skills, n) if s.get("name")]


def _best_production_entry(career_history: List[Dict]) -> Tuple[str, str, str]:
    """Return (company, title, best_sentence) for the entry with most production signals."""
    best_entry = None
    best_score = 0
    for entry in career_history:
        desc = (entry.get("description") or "").lower()
        score = sum(1 for kw in _PRODUCTION_KEYWORDS if kw in desc)
        if score > best_score:
            best_score = score
            best_entry = entry

    if not best_entry or best_score == 0:
        return "", "", ""

    desc = best_entry.get("description", "").strip()
    # Strip trailing punctuation so callers can safely append their own
    raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", desc) if s.strip()]
    sentences = [s.rstrip(".!?") for s in raw_sentences]

    best_sentence, best_sc, best_i = "", 0, 0
    for i, sent in enumerate(sentences):
        sc = sum(1 for kw in _PRODUCTION_KEYWORDS if kw in sent.lower())
        if sc > best_sc:
            best_sc, best_sentence, best_i = sc, sent, i

    if not best_sentence:
        best_sentence = desc.rstrip(".!?")[:160].rsplit(" ", 1)[0]

    # Extend with the next sentence if there is room
    if best_i + 1 < len(sentences):
        follow = sentences[best_i + 1]
        combined = best_sentence + ". " + follow
        if len(combined) <= 210:
            best_sentence = combined
        elif len(best_sentence) > 160:
            best_sentence = best_sentence[:160].rsplit(" ", 1)[0] + "…"

    return best_entry.get("company", ""), best_entry.get("title", ""), best_sentence


def _ml_entries(career_history: List[Dict]) -> List[Dict]:
    return [
        e for e in career_history
        if any(kw in (e.get("title") or "").lower() for kw in _ML_TITLE_TOKENS)
    ]


def _skill_phrase(top_skills: List[Dict]) -> str:
    """Build a natural skill phrase with proficiency detail for the top 2."""
    parts = []
    for i, s in enumerate(top_skills[:3]):
        name = s.get("name", "")
        prof = s.get("proficiency", "")
        end = s.get("endorsements", 0)
        if i < 2 and prof in ("expert", "advanced") and end > 80:
            parts.append(f"{name} ({prof}, {end} endorsements)")
        else:
            parts.append(name)
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + f" and {parts[-1]}"


# ─────────────────────────────────────────────────────────────────────────────
# Narrative generators (one per dominant signal type)
# ─────────────────────────────────────────────────────────────────────────────

def _production_led(candidate: Dict, components: Dict) -> str:
    """Lead with current role, then production evidence, then unique signals."""
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    sig = candidate.get("redrob_signals", {})

    company, role, snippet = _best_production_entry(career)
    yoe = float(profile.get("years_of_experience", 0))
    current_title = profile.get("current_title", "")
    current_co = profile.get("current_company", "")
    top = _top_jd_skills(skills, 4)

    # Lead with current role (always unique per candidate)
    if current_title and current_co:
        s1 = f"{current_title} at {current_co} ({yoe:.0f}y ML/AI experience)."
    else:
        s1 = f"{yoe:.0f} years of production ML/AI engineering experience."

    # Production evidence from past (may overlap across candidates — present as support)
    if snippet and company:
        if current_co and company.lower() == current_co.lower():
            s2 = f"Production track record: {snippet[0].lower() + snippet[1:]}."
        else:
            s2 = (f"At {company} ({role}), demonstrated production impact: "
                  f"{snippet[0].lower() + snippet[1:]}.")
    else:
        s2 = ""

    skill_str = _skill_phrase(top)
    if skill_str:
        s3 = (f"Brings {yoe:.0f}y ML/AI depth; strongest in {skill_str}."
              if yoe >= 8 else f"Technical depth in {skill_str}.")
    else:
        s3 = f"{yoe:.0f}-year ML/AI engineering track record." if yoe >= 8 else ""

    avail = _activity_phrase(sig)
    s4 = f"Currently {avail}." if avail else ""

    return " ".join(p for p in [s1, s2, s3, s4] if p)


def _skills_led(candidate: Dict, components: Dict) -> str:
    """Lead with rare or deep skill combination."""
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    sig = candidate.get("redrob_signals", {})

    yoe = float(profile.get("years_of_experience", 0))
    current_title = profile.get("current_title", "")
    current_co = profile.get("current_company", "")
    top = _top_jd_skills(skills, 5)

    skill_str = _skill_phrase(top)
    rest = ", ".join(s["name"] for s in top[2:]) if len(top) > 2 else ""
    extra = f", also covers {rest}" if rest else ""

    s1 = (f"Rare technical depth: {skill_str}{extra} — "
          f"combined with {yoe:.0f} years of hands-on ML/AI engineering "
          f"at {current_co or 'a product company'}.")

    company, _, snippet = _best_production_entry(career)
    if snippet:
        s2 = f"Production track record at {company}: {snippet[0].lower() + snippet[1:]}." if company else f"Production evidence: {snippet[0].lower() + snippet[1:]}."
    else:
        ml_cos = list({e.get("company") for e in _ml_entries(career) if e.get("company")})[:2]
        s2 = f"ML engineering background across {' and '.join(ml_cos)}." if ml_cos else ""

    avail = _activity_phrase(sig)
    s3 = f"Availability: {avail}." if avail else ""

    return " ".join(p for p in [s1, s2, s3] if p)


def _career_arc_led(candidate: Dict, components: Dict) -> str:
    """Lead with career trajectory across companies."""
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    sig = candidate.get("redrob_signals", {})

    yoe = float(profile.get("years_of_experience", 0))
    current_title = profile.get("current_title", "")
    current_co = profile.get("current_company", "")
    ml_roles = _ml_entries(career)

    if len(ml_roles) >= 2:
        earliest = ml_roles[-1]
        latest = ml_roles[0]
        s1 = (f"Consistent ML/AI career arc: {earliest.get('title', 'early ML role')} at {earliest.get('company', '')} "
              f"→ {latest.get('title', current_title)} at {latest.get('company', current_co)}, "
              f"spanning {yoe:.0f} years of focused ML engineering.")
    else:
        s1 = f"{yoe:.0f}-year ML/AI career, currently {current_title} at {current_co}."

    company, _, snippet = _best_production_entry(career)
    top_names = _skill_names(skills, 3)
    if snippet and top_names:
        s2 = f"Production evidence present; key skills include {', '.join(top_names)}."
    elif top_names:
        s2 = f"Key technical skills: {', '.join(top_names)}."
    else:
        s2 = ""

    avail = _activity_phrase(sig)
    s3 = f"Currently {avail}." if avail else ""

    return " ".join(p for p in [s1, s2, s3] if p)


def _availability_led(candidate: Dict, components: Dict) -> str:
    """Lead with strong behavioral availability — used when behavioral is the differentiator."""
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    sig = candidate.get("redrob_signals", {})

    current_title = profile.get("current_title", "")
    current_co = profile.get("current_company", "")
    yoe = float(profile.get("years_of_experience", 0))
    notice = sig.get("notice_period_days")
    otw = sig.get("open_to_work_flag", False)
    rrr = sig.get("recruiter_response_rate", -1)
    github = sig.get("github_activity_score", 0)

    if notice is not None and notice <= 15:
        avail_str = f"immediately available ({notice}-day notice)"
    elif notice is not None and notice <= 30:
        avail_str = f"available on short notice ({notice} days)"
    else:
        avail_str = "actively searching"

    open_str = ", openly seeking new opportunities" if otw else ""
    s1 = f"{yoe:.0f}-year {current_title.lower() or 'ML engineer'} at {current_co}, {avail_str}{open_str}."

    company, _, snippet = _best_production_entry(career)
    top_names = _skill_names(skills, 4)
    if snippet:
        s2 = f"Technical credentials: {snippet[0].lower() + snippet[1:] if snippet else ''}."
    elif top_names:
        s2 = f"Technical profile covers {', '.join(top_names)}."
    else:
        s2 = ""

    signals = []
    if isinstance(rrr, (int, float)) and rrr >= 0.80:
        signals.append(f"{rrr:.0%} recruiter response rate")
    if github > 70:
        signals.append(f"strong GitHub activity ({github:.0f}/100)")
    s3 = f"Strong recruiter signals: {', '.join(signals)}." if signals else ""

    return " ".join(p for p in [s1, s2, s3] if p)


def _balanced(candidate: Dict, components: Dict) -> str:
    """Balanced summary when no single signal dominates."""
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    sig = candidate.get("redrob_signals", {})

    yoe = float(profile.get("years_of_experience", 0))
    current_title = profile.get("current_title", "")
    current_co = profile.get("current_company", "")
    top_names = _skill_names(skills, 4)
    prod_score = components.get("production_evidence", 0)

    if prod_score >= 0.5:
        prod_note = "with demonstrated production deployment experience"
    else:
        prod_note = "primarily in research or prototyping contexts"

    s1 = f"{current_title} at {current_co} ({yoe:.0f}y) — {prod_note}."

    skill_str = ", ".join(top_names) if top_names else ""
    s2 = f"Core skills: {skill_str}." if skill_str else ""

    avail = _activity_phrase(sig)
    s3 = f"{avail.capitalize()}." if avail else ""

    return " ".join(p for p in [s1, s2, s3] if p)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_reasoning(
    candidate: Dict,
    components: Dict,
    rank: int,
    is_honeypot: bool = False,
    honeypot_flags: List[str] = None,
) -> str:
    """
    Generate a recruiter-quality 2-4 sentence justification.

    Narrative style is determined by the candidate's dominant scoring signal
    so the output varies naturally rather than repeating a fixed template.
    """
    if is_honeypot:
        reason = honeypot_flags[0] if honeypot_flags else "profile inconsistency detected"
        return f"Profile flagged: {reason}. Excluded from shortlist."

    title_score = components.get("title_role", 0)
    skill_score = components.get("skill_match", 0)
    prod_score = components.get("production_evidence", 0)
    beh_score = components.get("behavioral", 0)
    penalty = components.get("penalty", 0)
    penalty_reasons = components.get("penalty_reasons", [])
    career = candidate.get("career_history", [])

    # Route to the narrative that best surfaces the candidate's value
    if prod_score >= 0.75 and title_score >= 0.65:
        text = _production_led(candidate, components)
    elif skill_score >= 0.85 and title_score >= 0.55:
        text = _skills_led(candidate, components)
    elif title_score >= 0.85 and len(_ml_entries(career)) >= 2:
        text = _career_arc_led(candidate, components)
    elif beh_score >= 0.88 and title_score >= 0.55:
        text = _availability_led(candidate, components)
    else:
        text = _balanced(candidate, components)

    # Append penalty caution if meaningful
    if penalty_reasons and penalty > 0.10:
        caution = "; ".join(penalty_reasons[:2])
        text = text.rstrip(". ") + f". Caution: {caution}."

    return text.strip()


def build_evidence_panel(candidate: Dict, components: Dict) -> Dict:
    """
    Build structured evidence for the UI explainability panel.

    Returns a dict with: matched_skills, missing_skills, career_snippets,
    top_skills, headline, education, confidence.
    """
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    edu = candidate.get("education", [])
    sig = candidate.get("redrob_signals", {})

    # Top skills (name + proficiency + endorsements)
    order = {"expert": 0, "advanced": 1, "intermediate": 2, "beginner": 3}
    top_skills = sorted(skills, key=lambda s: (order.get(s.get("proficiency", "beginner"), 3), -s.get("endorsements", 0)))[:8]

    # Matched and missing JD skills
    candidate_skill_names = {s.get("name", "").lower() for s in skills}
    matched = [s for s in top_skills if s.get("name", "").lower() in _REQUIRED_SKILLS]
    key_jd_skills = [
        "Python", "FAISS", "NLP", "Ranking", "Embeddings", "Semantic Search",
        "Machine Learning", "sentence-transformers", "RAG", "Elasticsearch",
        "Learning to Rank", "Information Retrieval",
    ]
    missing = [s for s in key_jd_skills if s.lower() not in candidate_skill_names][:4]

    # Career snippets (up to 2 best entries)
    snippets = []
    sorted_entries = sorted(
        career,
        key=lambda e: sum(1 for kw in _PRODUCTION_KEYWORDS if kw in (e.get("description") or "").lower()),
        reverse=True,
    )
    for entry in sorted_entries[:2]:
        desc = (entry.get("description") or "").strip()
        if desc:
            short = desc[:180].rsplit(" ", 1)[0] + ("…" if len(desc) > 180 else "")
            snippets.append({
                "company": entry.get("company", ""),
                "title": entry.get("title", ""),
                "snippet": short,
            })

    # Education snapshot
    education = {}
    if edu:
        e0 = edu[0]
        education = {
            "degree": e0.get("degree", ""),
            "field": e0.get("field_of_study", ""),
            "institution": e0.get("institution", ""),
            "tier": e0.get("tier", ""),
        }

    # Confidence
    final_score = components.get("final_score", components.get("score", 0))
    penalty = components.get("penalty", 0)
    if final_score >= 0.82 and penalty < 0.10:
        confidence = "High"
    elif final_score >= 0.55 and penalty < 0.30:
        confidence = "Medium"
    else:
        confidence = "Low"

    return {
        "top_skills": top_skills,
        "matched_skills": [s.get("name") for s in matched],
        "missing_skills": missing,
        "career_snippets": snippets,
        "education": education,
        "headline": profile.get("headline", ""),
        "confidence": confidence,
        "activity": _activity_phrase(sig),
    }
