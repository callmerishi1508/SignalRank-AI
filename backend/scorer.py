"""
Hybrid scoring engine.

Combines 7 rule-based scoring components with explicit penalty multipliers.
All numeric constants read from config/scoring.yaml via config_loader.
Accepts pre-computed semantic similarities from the retrieval module.

Public interfaces (backwards-compatible):
  score_candidate(candidate, jd)                     → (float, dict)
  score_candidates_bulk(candidates, jd)              → List[dict]   (legacy TF-IDF blend)
  score_candidates_bulk(candidates, jd, similarities, config)  → List[dict]  (new pipeline)
"""

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.constants import REFERENCE_DATE
from backend.jd_parser import JobProfile, JD_PROFILE

_SCALE_PATTERN = re.compile(
    r'\b(\d+[kmb]?\+?\s*(users?|requests?|qps|tps|queries|records))\b',
    re.IGNORECASE,
)

UNRELATED_TITLE_TOKENS = frozenset({
    "hr", "human resources", "recruiter", "talent acquisition",
    "content writer", "content strategist", "copywriter",
    "graphic designer", "ui designer", "ux designer",
    "marketing manager", "marketing executive", "growth manager",
    "sales executive", "sales manager", "business development",
    "account manager", "account executive",
    "operations manager", "operations executive",
    "project manager", "program manager",
    "accountant", "finance manager", "financial analyst",
    "civil engineer", "mechanical engineer", "electrical engineer",
    "customer support", "customer success", "customer service",
    "supply chain", "logistics",
    "legal", "compliance",
})


# ---------------------------------------------------------------------------
# Config access
# ---------------------------------------------------------------------------

def _load_cfg():
    from backend.config_loader import load_config
    return load_config()


def _prof_weights(cfg) -> Dict[str, float]:
    pw = cfg.scoring.skill.proficiency_weights
    return {k: float(v) for k, v in vars(pw).items()}


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    return text.lower().strip()


def _contains_any(text: str, tokens: frozenset) -> List[str]:
    text_lower = _normalise(text)
    return [tok for tok in tokens if tok in text_lower]


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except (ValueError, TypeError):
        return None


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _tier_score(value: float, thresholds: List[float], scores: List[float]) -> float:
    """
    Return scores[i] where i is the first threshold value exceeds (or equals).
    The last score is the catch-all when value exceeds all thresholds.
    """
    for threshold, score in zip(thresholds, scores):
        if value <= threshold:
            return score
    return scores[-1]


# ---------------------------------------------------------------------------
# Component 1 — Title / Role Alignment
# ---------------------------------------------------------------------------

def _score_title_role(candidate: Dict, jd: JobProfile, cfg=None) -> float:
    if cfg is None:
        cfg = _load_cfg()
    tc = cfg.scoring.title

    career = candidate.get("career_history", [])
    current_title = _normalise(candidate.get("profile", {}).get("current_title", ""))

    if not career:
        return _title_score_from_string(current_title, jd, tc)

    total_months = 0
    tier1_months = 0
    tier2_months = 0
    unrelated_months = 0

    for job in career:
        duration = max(0, int(job.get("duration_months", 0)))
        title = _normalise(job.get("title", ""))
        total_months += duration

        if _contains_any(title, jd.tier1_title_tokens):
            tier1_months += duration
        elif _contains_any(title, jd.tier2_title_tokens):
            tier2_months += duration
        elif _contains_any(title, UNRELATED_TITLE_TOKENS):
            unrelated_months += duration

    if total_months == 0:
        return _title_score_from_string(current_title, jd, tc)

    tier1_frac = tier1_months / total_months
    tier2_frac = tier2_months / total_months
    unrelated_frac = unrelated_months / total_months

    base = (
        tc.score_tier1_career_fraction * tier1_frac +
        tc.score_tier2_career_fraction * tier2_frac +
        tc.score_unrelated_career_fraction * unrelated_frac
    )

    current_boost = 0.0
    if _contains_any(current_title, jd.tier1_title_tokens):
        current_boost = tc.current_title_tier1_boost
    elif _contains_any(current_title, jd.tier2_title_tokens):
        current_boost = tc.current_title_tier2_boost

    return _clamp(base + current_boost)


def _title_score_from_string(title: str, jd: JobProfile, tc=None) -> float:
    if tc is None:
        tc = _load_cfg().scoring.title
    if _contains_any(title, jd.tier1_title_tokens):
        return tc.score_tier1_current_only
    if _contains_any(title, jd.tier2_title_tokens):
        return tc.score_tier2_current_only
    if _contains_any(title, UNRELATED_TITLE_TOKENS):
        return tc.score_unrelated_current_only
    return tc.score_unknown_current_only


# ---------------------------------------------------------------------------
# Component 2 — Skill Match
# ---------------------------------------------------------------------------

def _score_skill_match(candidate: Dict, jd: JobProfile, cfg=None) -> float:
    if cfg is None:
        cfg = _load_cfg()
    sc = cfg.scoring.skill

    prof_weights = _prof_weights(cfg)
    assessment_threshold = sc.assessment_score_threshold
    breadth_normalizer = sc.required_breadth_normalizer
    nice_cap = sc.nice_to_have_bonus_cap
    depth_cap = sc.depth_bonus_cap
    depth_months = sc.depth_bonus_months_normalizer

    skills = candidate.get("skills", [])
    assessment_scores = candidate.get("redrob_signals", {}).get("skill_assessment_scores", {})

    if not skills:
        return 0.0

    required_hits = []
    nice_hits = 0.0
    total_duration_nlp = 0.0

    for skill_obj in skills:
        if isinstance(skill_obj, str):
            skill_obj = {"name": skill_obj}
        raw_name = skill_obj.get("name", "")
        name = _normalise(raw_name)
        proficiency = _normalise(skill_obj.get("proficiency", "intermediate"))
        endorsements = int(skill_obj.get("endorsements", 0))
        duration_months = int(skill_obj.get("duration_months", 0))

        prof_w = prof_weights.get(proficiency, 0.55)
        endorse_boost = min(0.20, endorsements / 100 * 0.10)
        assessment_val = assessment_scores.get(raw_name, assessment_scores.get(name, -1))
        assess_boost = 0.10 if assessment_val >= assessment_threshold else 0.0
        trust = _clamp(prof_w + endorse_boost + assess_boost)

        matched_required = _contains_any(name, jd.required_skills)
        if matched_required:
            required_hits.append(trust)
        if _contains_any(name, jd.nice_to_have_skills):
            nice_hits += trust * 0.4
        if matched_required and duration_months > 0:
            total_duration_nlp += duration_months

    if not required_hits:
        return 0.0

    breadth = min(1.0, len(required_hits) / breadth_normalizer)
    quality = sum(required_hits) / len(required_hits)
    base_skill = 0.6 * breadth + 0.4 * quality

    nice_bonus = _clamp(nice_hits / max(1, len(skills)), 0.0, nice_cap)
    depth_bonus = _clamp(total_duration_nlp / depth_months * depth_cap, 0.0, depth_cap)

    return _clamp(base_skill + nice_bonus + depth_bonus)


# ---------------------------------------------------------------------------
# Component 3 — Experience Fit
# ---------------------------------------------------------------------------

def _score_experience_fit(candidate: Dict, jd: JobProfile, cfg=None) -> float:
    if cfg is None:
        cfg = _load_cfg()
    ec = cfg.scoring.experience

    yoe = float(candidate.get("profile", {}).get("years_of_experience", 0))
    ideal_min = jd.experience_ideal_min
    ideal_max = jd.experience_ideal_max

    if ideal_min <= yoe <= ideal_max:
        return 1.0
    if yoe < ideal_min:
        if yoe <= 0:
            return ec.score_at_zero_yoe
        fraction = yoe / ideal_min
        return _clamp(ec.underexperienced_ramp_base + ec.underexperienced_ramp_multiplier * fraction)
    excess = yoe - ideal_max
    return _clamp(1.0 - excess * ec.overqualified_penalty_per_year)


# ---------------------------------------------------------------------------
# Component 4 — Production Evidence
# ---------------------------------------------------------------------------

def _score_production_evidence(candidate: Dict, jd: JobProfile, cfg=None) -> float:
    if cfg is None:
        cfg = _load_cfg()
    pc = cfg.scoring.production_evidence

    career = candidate.get("career_history", [])
    summary = _normalise(candidate.get("profile", {}).get("summary", ""))
    all_text = summary + " " + " ".join(
        _normalise(j.get("description", "")) for j in career
    )

    if not all_text.strip():
        return pc.empty_text_default

    hits = _contains_any(all_text, jd.production_keywords)
    unique_keywords = len(set(hits))
    scale_hits = len(_SCALE_PATTERN.findall(all_text))

    base = _clamp(unique_keywords / pc.keywords_for_full_score)
    scale_bonus = _clamp(scale_hits * pc.scale_match_bonus_per_hit, 0.0, pc.scale_match_bonus_cap)
    return _clamp(base + scale_bonus)


# ---------------------------------------------------------------------------
# Component 5 — Behavioral Availability
# ---------------------------------------------------------------------------

def _score_behavioral(candidate: Dict, jd: JobProfile, cfg=None) -> Tuple[float, Dict]:
    if cfg is None:
        cfg = _load_cfg()
    sc = cfg.scoring

    sig = candidate.get("redrob_signals", {})
    if not sig:
        return sc.behavioral_missing_signals_default, {}

    bw = sc.behavioral_sub_weights
    sub_scores = {}

    # Recency
    last_active = _parse_date(sig.get("last_active_date"))
    if last_active:
        days_inactive = (REFERENCE_DATE - last_active).days
        recency = _tier_score(
            days_inactive,
            sc.behavioral_recency.thresholds_days,
            sc.behavioral_recency.scores,
        )
    else:
        recency = 0.40
    sub_scores["recency"] = recency

    # Open to work
    sub_scores["open_to_work"] = (
        1.0 if sig.get("open_to_work_flag", False)
        else sc.behavioral_open_to_work_false_score
    )

    # Recruiter response rate
    rrr = float(sig.get("recruiter_response_rate", 0.5))
    sub_scores["response_rate"] = _clamp(rrr)

    # Notice period
    notice = int(sig.get("notice_period_days", 60))
    np_score = _tier_score(
        notice,
        sc.behavioral_notice_period.thresholds_days,
        sc.behavioral_notice_period.scores,
    )
    sub_scores["notice_period"] = np_score

    # Interview completion
    icr = float(sig.get("interview_completion_rate", 0.7))
    sub_scores["interview_completion"] = _clamp(icr)

    # GitHub activity
    gh = float(sig.get("github_activity_score", -1))
    sub_scores["github_activity"] = (
        _clamp(gh / 100) if gh >= 0
        else sc.behavioral_github_missing_score
    )

    # Response speed (avg_response_time_hours — lower = faster = better)
    avg_rt = sig.get("avg_response_time_hours")
    if avg_rt is not None:
        sub_scores["response_speed"] = _tier_score(
            float(avg_rt),
            sc.behavioral_response_speed.thresholds_hours,
            sc.behavioral_response_speed.scores,
        )
    else:
        sub_scores["response_speed"] = sc.behavioral_response_speed_missing_score

    # Recruiter demand (saved_by_recruiters_30d — how many recruiters bookmarked)
    saved = sig.get("saved_by_recruiters_30d")
    if saved is not None:
        sub_scores["recruiter_demand"] = _tier_score(
            int(saved),
            sc.behavioral_recruiter_demand.thresholds,
            sc.behavioral_recruiter_demand.scores,
        )
    else:
        sub_scores["recruiter_demand"] = 0.30

    # Active job seeking (applications_submitted_30d)
    apps = sig.get("applications_submitted_30d")
    if apps is not None:
        sub_scores["active_seeking"] = _tier_score(
            int(apps),
            sc.behavioral_active_seeking.thresholds,
            sc.behavioral_active_seeking.scores,
        )
    else:
        sub_scores["active_seeking"] = 0.40

    behavioral = (
        bw.recency * sub_scores["recency"] +
        bw.open_to_work * sub_scores["open_to_work"] +
        bw.response_rate * sub_scores["response_rate"] +
        bw.response_speed * sub_scores["response_speed"] +
        bw.notice_period * sub_scores["notice_period"] +
        bw.interview_completion * sub_scores["interview_completion"] +
        bw.github_activity * sub_scores["github_activity"] +
        bw.recruiter_demand * sub_scores["recruiter_demand"] +
        bw.active_seeking * sub_scores["active_seeking"]
    )
    return _clamp(behavioral), sub_scores


# ---------------------------------------------------------------------------
# Component 6 — Domain / Company Fit
# ---------------------------------------------------------------------------

def _score_domain_fit(candidate: Dict, jd: JobProfile, cfg=None) -> float:
    if cfg is None:
        cfg = _load_cfg()
    dc = cfg.scoring.domain

    career = candidate.get("career_history", [])
    current_industry = _normalise(candidate.get("profile", {}).get("current_industry", ""))

    if not career:
        if _contains_any(current_industry, jd.preferred_industries):
            return dc.fallback_current_industry_match
        return dc.fallback_current_industry_no_match

    total_months = 0
    product_months = 0
    consulting_months = 0

    for job in career:
        duration = max(0, int(job.get("duration_months", 0)))
        company = _normalise(job.get("company", ""))
        industry = _normalise(job.get("industry", ""))
        company_size = job.get("company_size", "")

        total_months += duration
        is_consulting = bool(_contains_any(company, jd.disqualifying_firms))
        if is_consulting:
            consulting_months += duration
        elif _contains_any(industry, jd.preferred_industries):
            product_months += duration
        elif company_size in ("5001-10000", "10001+"):
            product_months += duration * dc.score_large_neutral_company_multiplier

    if total_months == 0:
        return dc.fallback_no_career

    consulting_frac = consulting_months / total_months
    product_frac = product_months / total_months
    neutral_frac = 1 - product_frac - consulting_frac

    base = (
        dc.score_product_company * product_frac +
        dc.score_unclassified * neutral_frac +
        dc.score_consulting * consulting_frac
    )
    return _clamp(base)


# ---------------------------------------------------------------------------
# Component 7 — Location Fit
# ---------------------------------------------------------------------------

def _score_location(candidate: Dict, jd: JobProfile, cfg=None) -> float:
    if cfg is None:
        cfg = _load_cfg()
    lc = cfg.scoring.location

    location = _normalise(candidate.get("profile", {}).get("location", ""))
    country = _normalise(candidate.get("profile", {}).get("country", ""))
    willing = candidate.get("redrob_signals", {}).get("willing_to_relocate", False)
    work_mode = _normalise(candidate.get("redrob_signals", {}).get("preferred_work_mode", ""))

    if _contains_any(location, jd.tier1_locations):
        return lc.score_tier1_location
    if _contains_any(location, jd.tier2_locations):
        return lc.score_tier2_location
    if willing and country == "india":
        return lc.score_willing_to_relocate_india
    if country == "india":
        return lc.score_india_default
    if work_mode in ("remote", "flexible"):
        return lc.score_remote_or_flexible
    return lc.score_other


# ---------------------------------------------------------------------------
# Penalty multipliers
# ---------------------------------------------------------------------------

def _compute_penalty(candidate: Dict, jd: JobProfile, cfg=None) -> Tuple[float, List[str]]:
    if cfg is None:
        cfg = _load_cfg()
    pen = cfg.penalties

    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    current_title = _normalise(candidate.get("profile", {}).get("current_title", ""))

    penalty = 0.0
    reasons = []

    # 1. Consulting-only career
    if career:
        total_months = sum(max(0, j.get("duration_months", 0)) for j in career)
        consulting_months = sum(
            max(0, j.get("duration_months", 0))
            for j in career
            if _contains_any(_normalise(j.get("company", "")), jd.disqualifying_firms)
        )
        if total_months > 0 and (consulting_months / total_months) > pen.consulting_only.career_fraction_threshold:
            penalty += pen.consulting_only.penalty
            reasons.append("consulting-only career")

    # 2. Wrong role domain
    unrelated_hits = _contains_any(current_title, UNRELATED_TITLE_TOKENS)
    if unrelated_hits:
        all_titles = " ".join(_normalise(j.get("title", "")) for j in career)
        has_any_ml = bool(
            _contains_any(all_titles, jd.tier1_title_tokens) or
            _contains_any(all_titles, jd.tier2_title_tokens)
        )
        if not has_any_ml:
            penalty += pen.wrong_domain.full_penalty
            reasons.append(f"wrong role domain ({unrelated_hits[0]})")
        else:
            penalty += pen.wrong_domain.partial_penalty
            reasons.append("currently in non-technical role (has some ML history)")

    # 3. CV / speech / robotics without NLP/IR
    all_skill_names = " ".join(
        _normalise(s.get("name", "") if isinstance(s, dict) else str(s)) for s in skills
    )
    cv_hits = _contains_any(all_skill_names, jd.disqualifying_skill_domains)
    nlp_hits = _contains_any(all_skill_names, jd.required_skills)
    if cv_hits and not nlp_hits:
        penalty += pen.cv_robotics_without_nlp.full_penalty
        reasons.append("CV/speech/robotics skills without NLP/IR overlap")
    elif cv_hits and len(cv_hits) > len(nlp_hits):
        penalty += pen.cv_robotics_without_nlp.partial_penalty
        reasons.append("heavy CV/speech focus; limited IR overlap")

    # 4. Job hopping
    short_stints = sum(
        1 for j in career
        if 0 < j.get("duration_months", 0) <= pen.job_hopping.short_stint_months
    )
    if short_stints >= pen.job_hopping.min_short_stints:
        penalty += pen.job_hopping.penalty
        reasons.append(f"frequent job-hopping ({short_stints} stints ≤{pen.job_hopping.short_stint_months} mo)")

    # 5. Behaviorally unavailable
    sig = candidate.get("redrob_signals", {})
    last_active = _parse_date(sig.get("last_active_date"))
    rrr = float(sig.get("recruiter_response_rate", 1.0))
    if last_active:
        days_inactive = (REFERENCE_DATE - last_active).days
        if (days_inactive > pen.behaviorally_unavailable.inactive_days_threshold and
                rrr < pen.behaviorally_unavailable.response_rate_threshold):
            penalty += pen.behaviorally_unavailable.penalty
            reasons.append("inactive >6 months with very low response rate")

    return _clamp(penalty), reasons


# ---------------------------------------------------------------------------
# Internal TF-IDF (backwards compat — used when no similarities provided)
# ---------------------------------------------------------------------------

_tfidf_vectorizer = None
_jd_vector = None


def _get_tfidf_similarity(candidate_text: str) -> float:
    global _tfidf_vectorizer, _jd_vector
    if _tfidf_vectorizer is None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from backend.jd_parser import JD_TEXT_FOR_TFIDF
        _tfidf_vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), min_df=1, max_features=5000, sublinear_tf=True,
        )
        _tfidf_vectorizer.fit([JD_TEXT_FOR_TFIDF])
        _jd_vector = _tfidf_vectorizer.transform([JD_TEXT_FOR_TFIDF])

    if not candidate_text.strip():
        return 0.0
    from sklearn.metrics.pairwise import cosine_similarity
    cand_vec = _tfidf_vectorizer.transform([candidate_text])
    return float(_clamp(cosine_similarity(_jd_vector, cand_vec)[0][0]))


def _build_candidate_text(candidate: Dict) -> str:
    profile = candidate.get("profile", {})
    parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
        profile.get("current_industry", ""),
        " ".join(
            s.get("name", "") if isinstance(s, dict) else str(s)
            for s in candidate.get("skills", [])
        ),
        " ".join(
            f"{j.get('title', '')} {j.get('description', '')} {j.get('industry', '')}"
            for j in candidate.get("career_history", [])
        ),
    ]
    return " ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Core scoring: rule-based only (no semantic blend)
# ---------------------------------------------------------------------------

def _score_candidate_rule_based(
    candidate: Dict,
    jd: JobProfile,
    cfg=None,
) -> Tuple[float, Dict]:
    if cfg is None:
        cfg = _load_cfg()

    components = {}
    components["title_role"] = _score_title_role(candidate, jd, cfg)
    components["skill_match"] = _score_skill_match(candidate, jd, cfg)
    components["production_evidence"] = _score_production_evidence(candidate, jd, cfg)
    components["experience_fit"] = _score_experience_fit(candidate, jd, cfg)
    components["domain_fit"] = _score_domain_fit(candidate, jd, cfg)
    components["location"] = _score_location(candidate, jd, cfg)

    beh, beh_sub = _score_behavioral(candidate, jd, cfg)
    components["behavioral"] = beh
    components["behavioral_sub"] = beh_sub

    penalty, penalty_reasons = _compute_penalty(candidate, jd, cfg)
    components["penalty"] = penalty
    components["penalty_reasons"] = penalty_reasons

    cw = cfg.scoring.component_weights
    raw = (
        cw.title_role * components["title_role"] +
        cw.skill_match * components["skill_match"] +
        cw.production_evidence * components["production_evidence"] +
        cw.behavioral * components["behavioral"] +
        cw.experience_fit * components["experience_fit"] +
        cw.domain_fit * components["domain_fit"] +
        cw.location * components["location"]
    )
    components["raw_score"] = raw
    return raw, components


# ---------------------------------------------------------------------------
# Public: score a single candidate (backwards-compat unit-test interface)
# ---------------------------------------------------------------------------

def score_candidate(
    candidate: Dict,
    jd: JobProfile = JD_PROFILE,
    config=None,
) -> Tuple[float, Dict]:
    """
    Score a single candidate. Returns (final_score, components_dict).

    Maintains the original TF-IDF blend for backwards compatibility.
    The main pipeline uses score_candidates_bulk with pre-computed similarities.
    """
    if config is None:
        config = _load_cfg()

    raw, components = _score_candidate_rule_based(candidate, jd, config)

    tfidf_text = _build_candidate_text(candidate)
    tfidf_sim = _get_tfidf_similarity(tfidf_text)
    components["tfidf_similarity"] = tfidf_sim

    tfidf_blend = config.semantic.tfidf.rule_blend
    tfidf_sem = config.semantic.tfidf.semantic_blend
    blended = _clamp(tfidf_blend * raw + tfidf_sem * tfidf_sim)

    penalty = components["penalty"]
    final = _clamp(blended * (1.0 - penalty))
    components["final_score"] = final

    return final, components


# ---------------------------------------------------------------------------
# Public: bulk scoring with optional pre-computed similarities
# ---------------------------------------------------------------------------

def score_candidates_bulk(
    candidates: List[Dict],
    jd: JobProfile = JD_PROFILE,
    similarities: Optional[Dict[str, float]] = None,
    config=None,
) -> List[Dict]:
    """
    Score candidates efficiently.

    Args:
        candidates: List of raw candidate dicts.
        jd: Job profile.
        similarities: Pre-computed semantic similarity scores from retrieval module.
                      Keys are candidate_id strings. If None, falls back to internal TF-IDF.
        config: ScoringConfig instance. If None, loads default.

    Returns:
        List of result dicts with keys: candidate_id, final_score, components.
    """
    if config is None:
        config = _load_cfg()

    use_precomputed = similarities is not None

    if use_precomputed:
        rule_blend = config.semantic.embedding.rule_blend
        sem_blend = config.semantic.embedding.semantic_blend
    else:
        # Internal TF-IDF: fit once across all candidates
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity as sk_cosine
        from backend.jd_parser import JD_TEXT_FOR_TFIDF

        global _tfidf_vectorizer, _jd_vector

        texts = [_build_candidate_text(c) for c in candidates]
        all_texts = [JD_TEXT_FOR_TFIDF] + texts

        _tfidf_vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), min_df=2, max_features=8000, sublinear_tf=True,
        )
        _tfidf_vectorizer.fit(all_texts)
        all_vecs = _tfidf_vectorizer.transform(all_texts)
        _jd_vector = all_vecs[0]
        cand_vecs = all_vecs[1:]
        sims_array = sk_cosine(_jd_vector, cand_vecs)[0]

        rule_blend = config.semantic.tfidf.rule_blend
        sem_blend = config.semantic.tfidf.semantic_blend

    results = []
    for i, candidate in enumerate(candidates):
        raw, components = _score_candidate_rule_based(candidate, jd, config)

        if use_precomputed:
            cid = candidate.get("candidate_id", "")
            sem_sim = float(similarities.get(cid, 0.0))
            components["semantic_similarity"] = sem_sim
        else:
            sem_sim = float(_clamp(sims_array[i]))
            components["tfidf_similarity"] = sem_sim

        blended = _clamp(rule_blend * raw + sem_blend * sem_sim)
        penalty = components["penalty"]
        final = _clamp(blended * (1.0 - penalty))
        components["final_score"] = final

        results.append({
            "candidate": candidate,
            "candidate_id": candidate.get("candidate_id", ""),
            "final_score": final,
            "components": components,
        })

    return results
