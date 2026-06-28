"""
Honeypot detection.

The dataset contains ~80 candidates with "subtly impossible profiles" that are
forced to relevance tier 0. Submissions with >10% honeypot rate in top 100
are disqualified. We detect and assign near-zero scores to these.

All detection thresholds are read from config/scoring.yaml.
Backwards-compatible public interface: detect_honeypot(candidate, config=None)
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.constants import REFERENCE_DATE


def _load_cfg():
    from backend.config_loader import load_config
    return load_config()


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except (ValueError, TypeError):
        return None


def _parse_year(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def detect_honeypot(
    candidate: Dict,
    config=None,
) -> Tuple[bool, List[str]]:
    """
    Return (is_honeypot, list_of_reasons).

    Args:
        candidate: Raw candidate dict.
        config: ScoringConfig. If None, loads default from scoring.yaml.
    """
    if config is None:
        config = _load_cfg()
    hp = config.honeypot

    flags = []

    # ------------------------------------------------------------------
    # Check 1: Career timeline overlaps
    # ------------------------------------------------------------------
    career = candidate.get("career_history", [])
    intervals = []
    for job in career:
        start = _parse_date(job.get("start_date"))
        end = _parse_date(job.get("end_date")) or REFERENCE_DATE
        if start and end and start <= end:
            intervals.append((start, end, job.get("company", "?")))

    intervals.sort(key=lambda x: x[0])
    single_flag_knockout = False

    for i in range(len(intervals) - 1):
        s1, e1, c1 = intervals[i]
        s2, e2, c2 = intervals[i + 1]
        overlap_start = max(s1, s2)
        overlap_end = min(e1, e2)
        if overlap_start < overlap_end:
            overlap_days = (overlap_end - overlap_start).days
            if overlap_days > hp.timeline_overlap_tolerance_days:
                flags.append(
                    f"overlapping jobs: '{c1}' and '{c2}' overlap by {overlap_days} days"
                )
                if overlap_days > hp.single_flag_knockout_overlap_days:
                    single_flag_knockout = True

    # ------------------------------------------------------------------
    # Check 2: Graduation year after first career start
    # ------------------------------------------------------------------
    education = candidate.get("education", [])
    if education and career:
        max_grad_year = max(
            (_parse_year(e.get("end_year")) or 0) for e in education
        )
        first_career_start = min(
            (_parse_date(j.get("start_date")) or REFERENCE_DATE) for j in career
        )
        if max_grad_year > 0 and first_career_start.year < max_grad_year - 1:
            flags.append(
                f"education ends {max_grad_year} but career started {first_career_start.year}"
            )

    # ------------------------------------------------------------------
    # Check 3: Stated YOE vs actual career span
    # ------------------------------------------------------------------
    yoe_stated = float(candidate.get("profile", {}).get("years_of_experience", -1))
    if yoe_stated >= 0 and career:
        earliest_start = min(
            (_parse_date(j.get("start_date")) or REFERENCE_DATE) for j in career
        )
        actual_years = (REFERENCE_DATE - earliest_start).days / 365.25
        if yoe_stated > actual_years + hp.yoe_discrepancy_threshold_years:
            flags.append(
                f"stated YOE ({yoe_stated:.1f}) exceeds actual span ({actual_years:.1f}y) "
                f"by >{hp.yoe_discrepancy_threshold_years:.0f} years"
            )

    # ------------------------------------------------------------------
    # Check 4: Impossible skill endorsements
    # ------------------------------------------------------------------
    skills = candidate.get("skills", [])
    if skills and len(skills) >= 5:
        endorsements = [int(s.get("endorsements", 0)) for s in skills]
        all_expert = sum(1 for s in skills if s.get("proficiency") == "expert")
        frac_expert = all_expert / len(skills)
        high_endorse = sum(1 for e in endorsements if e >= hp.endorsement_suspicious_threshold)
        if frac_expert > hp.expert_skill_fraction_threshold and high_endorse >= hp.high_endorsement_count_min:
            flags.append(
                f">90% skills at 'expert' with {high_endorse} having "
                f"{hp.endorsement_suspicious_threshold}+ endorsements"
            )

    # ------------------------------------------------------------------
    # Check 5: All behavioral signals at maximum simultaneously
    # ------------------------------------------------------------------
    sig = candidate.get("redrob_signals", {})
    if sig:
        perfect_signals = sum([
            sig.get("profile_completeness_score", 0) == 100,
            sig.get("recruiter_response_rate", 0) == 1.0,
            sig.get("interview_completion_rate", 0) == 1.0,
            sig.get("offer_acceptance_rate", -1) == 1.0,
            sig.get("github_activity_score", -1) == 100,
        ])
        if perfect_signals >= hp.perfect_behavioral_signals_threshold:
            flags.append(f"all behavioral signals at maximum ({perfect_signals}/5 perfect)")

    # ------------------------------------------------------------------
    # Check 6: Duration months inconsistent with career span
    # ------------------------------------------------------------------
    if career and intervals:
        total_duration_months = sum(max(0, j.get("duration_months", 0)) for j in career)
        span_start = intervals[0][0]
        span_months = (REFERENCE_DATE - span_start).days / 30.44
        if (total_duration_months > span_months * hp.duration_inflation_factor and
                span_months > hp.min_career_span_months_for_duration_check):
            flags.append(
                f"sum of durations ({total_duration_months} mo) greatly exceeds "
                f"career span ({span_months:.0f} mo)"
            )

    # ------------------------------------------------------------------
    # Check 7: Education dates impossible
    # ------------------------------------------------------------------
    for edu in education:
        start_y = _parse_year(edu.get("start_year"))
        end_y = _parse_year(edu.get("end_year"))
        if start_y and end_y:
            if end_y < start_y:
                flags.append(f"education end year {end_y} < start year {start_y}")
            if end_y - start_y > hp.education_max_duration_years:
                flags.append(f"degree duration {end_y - start_y} years (implausible)")

    is_honeypot = len(flags) >= hp.min_flags_for_honeypot or single_flag_knockout
    return is_honeypot, flags
