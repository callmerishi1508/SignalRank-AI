"""
Export engine.

Produces the organizer-compliant submission CSV from a ranked list.
Format per submission_spec.md: candidate_id, rank, score, reasoning
Exactly 100 rows, ranks 1-100, score non-increasing, UTF-8.

The debug JSON export is enriched with skill breakdowns, career snippets,
matched/missing JD skills, and a confidence label — used by the Streamlit UI.
"""

import csv
import json
import os
from pathlib import Path
from typing import List, Dict, Set

# Synonyms for each display-facing JD skill label.
# A candidate "has" a label if any of their skill names (lowercased) appear
# in the corresponding synonym set. This prevents false-positive "missing"
# labels for candidates whose skills use equivalent but differently-named terms
# (e.g. FAISS covers both "Embeddings" and "Semantic Search").
_JD_SKILL_SYNONYMS: Dict[str, Set[str]] = {
    "Python":               {"python"},
    "FAISS":                {"faiss"},
    "NLP":                  {"nlp", "natural language processing"},
    "Ranking":              {"ranking", "reranking", "re-ranking", "learning to rank", "ltr", "ndcg", "mrr", "recommendation", "recommender"},
    "Embeddings":           {"embeddings", "embedding", "faiss", "vector search", "dense retrieval", "sentence transformers", "sentence-transformers", "ann"},
    "Semantic Search":      {"semantic search", "vector search", "faiss", "dense retrieval", "ann", "hybrid search"},
    "Machine Learning":     {"machine learning", "deep learning", "ml", "ai", "artificial intelligence", "transformer", "bert", "neural", "pytorch", "tensorflow"},
    "sentence-transformers":{"sentence transformers", "sentence-transformers", "transformers", "bert", "embeddings"},
    "RAG":                  {"rag", "retrieval augmented generation", "retrieval-augmented generation"},
    "Elasticsearch":        {"elasticsearch", "opensearch", "elastic"},
    "Learning to Rank":     {"learning to rank", "ltr", "ranking", "reranking", "re-ranking", "ndcg"},
    "Information Retrieval":{"information retrieval", "ir", "bm25", "hybrid search", "faiss", "dense retrieval"},
    "Dense Retrieval":      {"dense retrieval", "faiss", "ann", "embeddings", "vector search"},
}

# Flat set used for matched-skill detection (candidate skills that map to any JD requirement)
_REQUIRED_SKILLS: Set[str] = set().union(*_JD_SKILL_SYNONYMS.values())

_PRODUCTION_KEYWORDS: Set[str] = {
    "deployed", "production", "serving", "served", "shipped", "launched",
    "scale", "million", "billion", "real users", "latency", "throughput",
    "qps", "tps", "p99", "a/b test", "ab test", "online experiment",
    "end-to-end", "ranking system", "retrieval system", "search system",
    "recommendation system", "real-time", "online inference",
}


def export_csv(ranked_results: List[Dict], output_path: str) -> None:
    """
    Write the top 100 ranked candidates to a submission CSV.

    Args:
        ranked_results: List of result dicts, already sorted by final_score descending.
        output_path: Where to write the CSV.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    top100 = ranked_results[:100]

    # Enforce monotonically non-increasing scores (floating point safety)
    prev_score = top100[0]["final_score"] if top100 else 1.0
    for row in top100:
        row["final_score"] = min(row["final_score"], prev_score)
        prev_score = row["final_score"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for rank_idx, result in enumerate(top100, start=1):
            cid = result["candidate_id"]
            score = round(result["final_score"], 6)
            reasoning = result.get("reasoning", "")
            reasoning = reasoning.replace("\n", " ").replace("\r", " ").strip()
            writer.writerow([cid, rank_idx, score, reasoning])


def _enrich_candidate(candidate: Dict, components: Dict) -> Dict:
    """Extract UI-facing fields from the raw candidate and scoring components."""
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    edu = candidate.get("education", [])
    sig = candidate.get("redrob_signals", {})

    # Skills: top 8 sorted by proficiency then endorsements
    order = {"expert": 0, "advanced": 1, "intermediate": 2, "beginner": 3}
    sorted_skills = sorted(
        skills,
        key=lambda s: (order.get(s.get("proficiency", "beginner"), 3), -s.get("endorsements", 0)),
    )
    top_skills = [
        {
            "name": s.get("name", ""),
            "proficiency": s.get("proficiency", ""),
            "endorsements": s.get("endorsements", 0),
            "duration_months": s.get("duration_months", 0),
        }
        for s in sorted_skills[:8]
    ]

    # Matched JD skills
    candidate_skill_lower = {s.get("name", "").lower() for s in skills}
    matched_skills = [
        s.get("name") for s in sorted_skills
        if s.get("name", "").lower() in _REQUIRED_SKILLS
    ][:6]

    # Missing key JD skills — a skill is only "missing" if the candidate has
    # none of its synonyms, preventing false positives like showing
    # "Machine Learning" as missing for an engineer who has PyTorch and FAISS.
    missing_skills = [
        label for label, synonyms in _JD_SKILL_SYNONYMS.items()
        if not synonyms.intersection(candidate_skill_lower)
    ][:4]

    # Career snippets: up to 2 entries with highest production signal density
    scored_entries = []
    for entry in career:
        desc = (entry.get("description") or "").lower()
        prod_count = sum(1 for kw in _PRODUCTION_KEYWORDS if kw in desc)
        scored_entries.append((prod_count, entry))
    scored_entries.sort(key=lambda x: -x[0])

    career_snippets = []
    for count, entry in scored_entries[:2]:
        desc = (entry.get("description") or "").strip()
        if desc:
            short = desc[:200].rsplit(" ", 1)[0] + ("…" if len(desc) > 200 else "")
            career_snippets.append({
                "company": entry.get("company", ""),
                "title": entry.get("title", ""),
                "snippet": short,
                "has_production_evidence": count > 0,
            })

    # Education
    education_snapshot = {}
    if edu:
        e0 = edu[0]
        education_snapshot = {
            "degree": e0.get("degree", ""),
            "field": e0.get("field_of_study", ""),
            "institution": e0.get("institution", ""),
            "tier": e0.get("tier", ""),
        }

    # Confidence label
    final_score = components.get("final_score", 0)
    penalty = components.get("penalty", 0)
    title_score = components.get("title_role", 0)
    if final_score >= 0.82 and penalty < 0.10 and title_score >= 0.70:
        confidence = "High"
    elif final_score >= 0.60 and penalty < 0.30:
        confidence = "Medium"
    else:
        confidence = "Low"

    # Rule-based score (before semantic blend)
    rule_score = round(
        components.get("title_role", 0) * 0.25
        + components.get("skill_match", 0) * 0.20
        + components.get("production_evidence", 0) * 0.15
        + components.get("behavioral", 0) * 0.15
        + components.get("experience_fit", 0) * 0.10
        + components.get("domain_fit", 0) * 0.10
        + components.get("location", 0) * 0.05,
        4,
    )

    return {
        "headline": profile.get("headline", ""),
        "summary_snippet": (profile.get("summary") or "")[:200].strip(),
        "skills_snapshot": top_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "career_snippets": career_snippets,
        "education_snapshot": education_snapshot,
        "confidence": confidence,
        "rule_based_score": rule_score,
        "redrob_signals_snapshot": {
            "last_active_date": sig.get("last_active_date"),
            "open_to_work_flag": sig.get("open_to_work_flag", False),
            "recruiter_response_rate": sig.get("recruiter_response_rate"),
            "notice_period_days": sig.get("notice_period_days"),
            "github_activity_score": sig.get("github_activity_score"),
            "interview_completion_rate": sig.get("interview_completion_rate"),
            "github_url": sig.get("github_url"),
            "expected_salary_range_inr_lpa": sig.get("expected_salary_range_inr_lpa"),
        },
    }


def export_json(ranked_results: List[Dict], output_path: str) -> None:
    """
    Write full ranked results with component breakdowns to JSON.
    Includes enriched UI fields for the Streamlit dashboard.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    output = []
    for rank_idx, result in enumerate(ranked_results[:100], start=1):
        components = result.get("components", {})
        safe_components = {
            k: v for k, v in components.items()
            if k != "behavioral_sub" and isinstance(v, (int, float, str, bool, list))
        }
        behavioral_sub = components.get("behavioral_sub", {})
        candidate = result.get("candidate", {})
        profile = candidate.get("profile", {})

        # Inject final_score into components for confidence computation
        components_with_score = dict(components)
        components_with_score["final_score"] = result.get("final_score", 0)

        enriched = _enrich_candidate(candidate, components_with_score)

        output.append({
            "rank": rank_idx,
            "candidate_id": result["candidate_id"],
            "final_score": round(result["final_score"], 6),
            "reasoning": result.get("reasoning", ""),
            "scores": {
                "title_role": round(components.get("title_role", 0), 4),
                "skill_match": round(components.get("skill_match", 0), 4),
                "production_evidence": round(components.get("production_evidence", 0), 4),
                "behavioral": round(components.get("behavioral", 0), 4),
                "experience_fit": round(components.get("experience_fit", 0), 4),
                "domain_fit": round(components.get("domain_fit", 0), 4),
                "location": round(components.get("location", 0), 4),
                # semantic_similarity covers both embedding and TF-IDF backends
                "tfidf_similarity": round(
                    components.get("semantic_similarity",
                    components.get("tfidf_similarity", 0)), 4
                ),
                "penalty": round(components.get("penalty", 0), 4),
            },
            "behavioral_breakdown": {k: round(v, 4) for k, v in behavioral_sub.items()},
            "penalty_reasons": components.get("penalty_reasons", []),
            "is_honeypot": result.get("is_honeypot", False),
            "profile_snapshot": {
                "current_title": profile.get("current_title", ""),
                "years_of_experience": profile.get("years_of_experience", 0),
                "location": profile.get("location", ""),
                "current_company": profile.get("current_company", ""),
                "current_industry": profile.get("current_industry", ""),
            },
            # Enriched fields for Streamlit UI
            "confidence": enriched["confidence"],
            "rule_based_score": enriched["rule_based_score"],
            "headline": enriched["headline"],
            "summary_snippet": enriched["summary_snippet"],
            "skills_snapshot": enriched["skills_snapshot"],
            "matched_skills": enriched["matched_skills"],
            "missing_skills": enriched["missing_skills"],
            "career_snippets": enriched["career_snippets"],
            "education_snapshot": enriched["education_snapshot"],
            "redrob_signals_snapshot": enriched["redrob_signals_snapshot"],
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
