#!/usr/bin/env python3
"""
SignalRank AI — Evaluation Framework

Produces a structured evaluation report covering:
  - Format sanity checks (spec compliance)
  - Score distribution analysis
  - Top-N candidate profiling (top-10, top-25, top-100)
  - Archetype discrimination test
  - Baseline comparison (keyword-count model vs hybrid model)
  - Honeypot safety audit
  - Ranking stability check

Usage:
  python evaluation/eval.py --results outputs/debug.json --candidates data/raw/candidates.jsonl
  python evaluation/eval.py --results outputs/debug.json --candidates data/raw/candidates.jsonl --json outputs/eval_report.json
"""

import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Metric primitives
# ---------------------------------------------------------------------------

def dcg_at_k(relevances: List[float], k: int) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances[:k]))


def ndcg_at_k(relevances: List[float], k: int) -> float:
    ideal = sorted(relevances, reverse=True)
    idcg = dcg_at_k(ideal, k)
    return dcg_at_k(relevances, k) / idcg if idcg > 0 else 0.0


def average_precision(relevances: List[float], threshold: float = 0.5) -> float:
    hits, ap = 0, 0.0
    for i, rel in enumerate(relevances, 1):
        if rel >= threshold:
            hits += 1
            ap += hits / i
    return ap / hits if hits > 0 else 0.0


def precision_at_k(relevances: List[float], k: int, threshold: float = 0.5) -> float:
    return sum(1 for r in relevances[:k] if r >= threshold) / k


def compute_labeled_metrics(
    ranked_ids: List[str],
    ground_truth: Dict[str, float],
) -> Dict[str, float]:
    relevances = [ground_truth.get(cid, 0.0) for cid in ranked_ids]
    return {
        "ndcg@10": ndcg_at_k(relevances, 10),
        "ndcg@50": ndcg_at_k(relevances, 50),
        "map": average_precision(relevances),
        "p@10": precision_at_k(relevances, 10),
        "composite": (
            0.50 * ndcg_at_k(relevances, 10) +
            0.30 * ndcg_at_k(relevances, 50) +
            0.15 * average_precision(relevances) +
            0.05 * precision_at_k(relevances, 10)
        ),
    }


# ---------------------------------------------------------------------------
# Sanity checks
# ---------------------------------------------------------------------------

_ML_KEYWORDS = frozenset({
    "ml", "ai", "machine learning", "data scientist", "nlp",
    "search", "research", "applied", "ranking", "retrieval",
    "recommendation", "inference", "scientist",
})


def sanity_checks(results: List[Dict]) -> Dict:
    scores = [r["final_score"] for r in results]
    ranks = [r["rank"] for r in results]
    cids = [r["candidate_id"] for r in results]

    checks = {}
    checks["scores_non_increasing"] = all(
        scores[i] >= scores[i + 1] - 1e-9 for i in range(len(scores) - 1)
    )
    checks["ranks_unique_1_to_100"] = sorted(ranks) == list(range(1, 101))
    checks["candidate_ids_unique"] = len(cids) == len(set(cids))
    checks["scores_in_range"] = all(0.0 <= s <= 1.0 + 1e-9 for s in scores)

    top10_titles = [
        r["profile_snapshot"]["current_title"].lower()
        for r in results[:10]
    ]
    ml_count = sum(
        1 for t in top10_titles
        if any(kw in t for kw in _ML_KEYWORDS)
    )
    checks["top10_ml_candidates"] = ml_count
    checks["top10_ml_fraction"] = ml_count / 10

    hp_in_top100 = sum(1 for r in results if r.get("is_honeypot", False))
    checks["honeypots_in_top100"] = hp_in_top100
    checks["no_honeypots_in_top100"] = hp_in_top100 == 0

    reasoning_filled = sum(1 for r in results if r.get("reasoning", "").strip())
    checks["reasoning_coverage"] = reasoning_filled / len(results)

    return checks


# ---------------------------------------------------------------------------
# Score distribution
# ---------------------------------------------------------------------------

def score_distribution(results: List[Dict]) -> Dict:
    scores = sorted([r["final_score"] for r in results], reverse=True)
    n = len(scores)

    def pct(p):
        idx = max(0, min(n - 1, int(p * n / 100)))
        return round(scores[idx], 4)

    bands = {"gt_0.80": 0, "0.60_0.80": 0, "0.40_0.60": 0, "lt_0.40": 0}
    for s in scores:
        if s > 0.80:
            bands["gt_0.80"] += 1
        elif s > 0.60:
            bands["0.60_0.80"] += 1
        elif s > 0.40:
            bands["0.40_0.60"] += 1
        else:
            bands["lt_0.40"] += 1

    return {
        "n": n,
        "min": round(min(scores), 4),
        "max": round(max(scores), 4),
        "mean": round(sum(scores) / n, 4),
        "p10": pct(10), "p25": pct(25), "p50": pct(50),
        "p75": pct(75), "p90": pct(90), "p99": pct(99),
        "score_bands": bands,
        "score_gap_rank1_to_10": round(scores[0] - scores[9], 4),
        "score_gap_rank10_to_100": round(scores[9] - scores[99], 4),
    }


# ---------------------------------------------------------------------------
# Top-N profiling
# ---------------------------------------------------------------------------

def profile_top_n(results: List[Dict], n: int) -> Dict:
    top = results[:n]
    titles = [r["profile_snapshot"]["current_title"] for r in top]
    title_counts = Counter(titles).most_common(10)
    scores = [r["final_score"] for r in top]
    yoes = [r["profile_snapshot"]["years_of_experience"] for r in top]

    # Score component averages
    component_keys = [
        "title_role", "skill_match", "production_evidence",
        "behavioral", "experience_fit", "domain_fit", "location",
    ]
    comp_avgs = {}
    for k in component_keys:
        vals = [r.get("scores", {}).get(k, 0.0) for r in top]
        comp_avgs[k] = round(sum(vals) / len(vals), 4)

    # Penalty analysis
    penalized = [r for r in top if r.get("scores", {}).get("penalty", 0) > 0.05]

    # Behavioral signals
    open_to_work = sum(
        1 for r in top
        if r.get("profile_snapshot", {}).get("current_title")  # non-empty
    )

    return {
        "n": n,
        "score_range": [round(min(scores), 4), round(max(scores), 4)],
        "score_mean": round(sum(scores) / len(scores), 4),
        "mean_yoe": round(sum(yoes) / len(yoes), 1),
        "title_distribution": dict(title_counts),
        "component_averages": comp_avgs,
        "penalized_count": len(penalized),
        "penalty_reasons": Counter(
            reason
            for r in penalized
            for reason in r.get("penalty_reasons", [])
        ).most_common(5),
    }


# ---------------------------------------------------------------------------
# Systematic error detection
# ---------------------------------------------------------------------------

_WRONG_DOMAIN = frozenset({
    "hr", "human resources", "recruiter", "content writer", "graphic designer",
    "marketing", "sales", "accountant", "operations", "legal",
    "customer support", "customer success", "supply chain",
})


def detect_systematic_errors(results: List[Dict], candidates: Optional[List[Dict]] = None) -> Dict:
    errors = []

    for r in results:
        title = r["profile_snapshot"]["current_title"].lower()
        score = r["final_score"]
        rank = r["rank"]
        cid = r["candidate_id"]

        if r.get("is_honeypot"):
            errors.append({
                "type": "honeypot_in_top100",
                "rank": rank,
                "candidate_id": cid,
                "title": title,
                "score": score,
            })

        if any(kw in title for kw in _WRONG_DOMAIN) and score > 0.50:
            errors.append({
                "type": "wrong_domain_high_score",
                "rank": rank,
                "candidate_id": cid,
                "title": title,
                "score": score,
            })

    # Check for score compression (top-10 within 0.01 of each other)
    top10_scores = [r["final_score"] for r in results[:10]]
    score_range = max(top10_scores) - min(top10_scores)

    # Check for title monotony (if all top-10 have same title)
    top10_titles = [r["profile_snapshot"]["current_title"] for r in results[:10]]
    title_diversity = len(set(top10_titles))

    return {
        "critical_errors": errors,
        "error_count": len(errors),
        "top10_score_range": round(score_range, 4),
        "top10_title_diversity": title_diversity,
        "score_compression_warning": score_range < 0.010,
        "title_monotony_warning": title_diversity <= 2,
    }


# ---------------------------------------------------------------------------
# Baseline comparison
# ---------------------------------------------------------------------------

_BASELINE_SKILLS = frozenset({
    "machine learning", "ml", "nlp", "natural language processing",
    "python", "deep learning", "faiss", "embeddings", "vector search",
    "elasticsearch", "recommendation", "ranking", "retrieval",
    "transformer", "bert", "pytorch", "tensorflow",
})


def baseline_score(candidate: Dict) -> float:
    skills = {s.get("name", "").lower() for s in candidate.get("skills", [])}
    keyword_match = len(skills & _BASELINE_SKILLS) / max(1, len(_BASELINE_SKILLS))
    yoe = float(candidate.get("profile", {}).get("years_of_experience", 0) or 0)
    rrr = float(candidate.get("redrob_signals", {}).get("recruiter_response_rate", 0.5) or 0.5)
    return 0.60 * keyword_match + 0.25 * min(yoe / 10, 1.0) + 0.15 * rrr


def baseline_comparison(candidates: List[Dict], our_results: List[Dict]) -> Dict:
    baseline_scores = sorted(
        [(c["candidate_id"], baseline_score(c), c) for c in candidates],
        key=lambda x: -x[1],
    )
    id_to_cand = {c["candidate_id"]: c for c in candidates}

    our_top10 = {r["candidate_id"] for r in our_results[:10]}
    our_top25 = {r["candidate_id"] for r in our_results[:25]}
    our_top50 = {r["candidate_id"] for r in our_results[:50]}
    our_top100 = {r["candidate_id"] for r in our_results[:100]}

    bl_top10 = {cid for cid, _, _ in baseline_scores[:10]}
    bl_top25 = {cid for cid, _, _ in baseline_scores[:25]}
    bl_top50 = {cid for cid, _, _ in baseline_scores[:50]}

    bl_top10_titles = [
        id_to_cand.get(cid, {}).get("profile", {}).get("current_title", "?")
        for cid, _, _ in baseline_scores[:10]
    ]
    our_top10_titles = [
        r["profile_snapshot"]["current_title"] for r in our_results[:10]
    ]

    # Calculate how many baseline top-10 we moved out of top-100
    bl_top10_in_our_top100 = len(bl_top10 & our_top100)

    return {
        "overlap@10": len(our_top10 & bl_top10),
        "overlap@25": len(our_top25 & bl_top25),
        "overlap@50": len(our_top50 & bl_top50),
        "baseline_top10_titles": bl_top10_titles,
        "our_top10_titles": our_top10_titles,
        "bl_top10_in_our_top100": bl_top10_in_our_top100,
        "summary": (
            f"Our model picks {10 - len(our_top10 & bl_top10)}/10 different candidates "
            f"in top-10 vs keyword baseline. "
            f"{bl_top10_in_our_top100}/10 baseline top-10 appear anywhere in our top-100."
        ),
    }


# ---------------------------------------------------------------------------
# Ranking stability check
# ---------------------------------------------------------------------------

def ranking_stability(results_path_a: str, results_path_b: Optional[str] = None) -> Dict:
    """
    Check stability: same results file run twice should produce identical rankings.
    If two result paths given, compare them.
    """
    with open(results_path_a) as f:
        results_a = json.load(f)
    if results_path_b:
        with open(results_path_b) as f:
            results_b = json.load(f)
    else:
        results_b = results_a  # trivially stable

    ids_a = [r["candidate_id"] for r in results_a[:100]]
    ids_b = [r["candidate_id"] for r in results_b[:100]]

    matches_at = {}
    for k in [10, 25, 50, 100]:
        matches_at[f"same_at_{k}"] = len(set(ids_a[:k]) & set(ids_b[:k]))

    return {
        "top1_stable": ids_a[0] == ids_b[0] if ids_a and ids_b else False,
        "top3_same_set": set(ids_a[:3]) == set(ids_b[:3]),
        "overlap_at_k": matches_at,
        "fully_stable": ids_a == ids_b,
    }


# ---------------------------------------------------------------------------
# Full report
# ---------------------------------------------------------------------------

def run_full_evaluation(
    results_path: str,
    candidates_path: Optional[str] = None,
    ground_truth_path: Optional[str] = None,
    output_json: Optional[str] = None,
) -> Dict:
    with open(results_path) as f:
        results = json.load(f)

    candidates = None
    if candidates_path and Path(candidates_path).exists():
        with open(candidates_path) as f:
            candidates = [json.loads(line) for line in f if line.strip()]

    report = {
        "meta": {
            "results_file": results_path,
            "n_ranked": len(results),
        },
        "sanity_checks": sanity_checks(results),
        "score_distribution": score_distribution(results),
        "top10_profile": profile_top_n(results, 10),
        "top25_profile": profile_top_n(results, 25),
        "top100_profile": profile_top_n(results, 100),
        "error_detection": detect_systematic_errors(results, candidates),
        "ranking_stability": ranking_stability(results_path),
    }

    if candidates:
        report["baseline_comparison"] = baseline_comparison(candidates, results)

    if ground_truth_path and Path(ground_truth_path).exists():
        with open(ground_truth_path) as f:
            gt = json.load(f)
        ranked_ids = [r["candidate_id"] for r in results]
        report["labeled_metrics"] = compute_labeled_metrics(ranked_ids, gt)

    if output_json:
        Path(output_json).parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, "w") as f:
            json.dump(report, f, indent=2)

    return report


# ---------------------------------------------------------------------------
# Human-readable printer
# ---------------------------------------------------------------------------

def _section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def _pass_fail(value: bool) -> str:
    return "✓ PASS" if value else "✗ FAIL"


def print_report(report: Dict) -> None:
    print("\n" + "=" * 60)
    print("  SIGNALRANK AI — EVALUATION REPORT")
    print("=" * 60)
    print(f"  Results file : {report['meta']['results_file']}")
    print(f"  Candidates   : {report['meta']['n_ranked']} ranked")

    # ── Sanity checks ──
    _section("1. FORMAT & SANITY CHECKS")
    sc = report["sanity_checks"]
    print(f"  {_pass_fail(sc['scores_non_increasing'])}  Scores monotonically non-increasing")
    print(f"  {_pass_fail(sc['ranks_unique_1_to_100'])}  Ranks 1–100 each appear exactly once")
    print(f"  {_pass_fail(sc['candidate_ids_unique'])}  Candidate IDs all unique")
    print(f"  {_pass_fail(sc['scores_in_range'])}  All scores in [0, 1]")
    print(f"  {_pass_fail(sc['no_honeypots_in_top100'])}  No honeypots in top-100 ({sc['honeypots_in_top100']} found)")
    print(f"  {_pass_fail(sc['top10_ml_candidates'] >= 7)}  Top-10 ML/AI candidates: {sc['top10_ml_candidates']}/10 ({sc['top10_ml_fraction']:.0%})")
    print(f"  INFO  Reasoning coverage: {sc['reasoning_coverage']:.0%}")

    # ── Score distribution ──
    _section("2. SCORE DISTRIBUTION (top-100)")
    sd = report["score_distribution"]
    print(f"  Range  : [{sd['min']} – {sd['max']}]   Mean: {sd['mean']}")
    print(f"  P10/P25/P50 : {sd['p10']} / {sd['p25']} / {sd['p50']}")
    print(f"  P75/P90/P99 : {sd['p75']} / {sd['p90']} / {sd['p99']}")
    print(f"  Top-10 spread  : {sd['score_gap_rank1_to_10']:.4f}")
    print(f"  Top-10→100 gap : {sd['score_gap_rank10_to_100']:.4f}")
    bands = sd["score_bands"]
    total = sum(bands.values())
    for band, count in bands.items():
        bar = "█" * (count * 30 // max(total, 1))
        print(f"  {band:>12}: {bar:<30} {count:>4} ({count/total:.0%})")

    # ── Top-N profiles ──
    for label, key in [("TOP 10", "top10_profile"), ("TOP 25", "top25_profile"), ("TOP 100", "top100_profile")]:
        _section(f"3. {label} CANDIDATE PROFILE")
        p = report[key]
        print(f"  Score range : {p['score_range'][0]} – {p['score_range'][1]}  (mean {p['score_mean']})")
        print(f"  Mean YOE    : {p['mean_yoe']} years")
        print(f"  Penalized   : {p['penalized_count']}/{p['n']}")
        print(f"  Title breakdown:")
        for title, cnt in list(p["title_distribution"].items())[:6]:
            print(f"    {cnt:>3}× {title}")
        print(f"  Component averages:")
        for comp, val in p["component_averages"].items():
            bar = "█" * int(val * 20)
            print(f"    {comp:<24} {val:.3f}  {bar}")

    # ── Error detection ──
    _section("4. SYSTEMATIC ERROR DETECTION")
    ed = report["error_detection"]
    print(f"  Critical errors found : {ed['error_count']}")
    if ed["critical_errors"]:
        for err in ed["critical_errors"][:5]:
            print(f"    [{err['type']}] rank={err['rank']} {err['title']} score={err['score']:.3f}")
    else:
        print("  ✓ No critical errors detected")
    print(f"  Top-10 score spread       : {ed['top10_score_range']:.4f}  {'⚠ compressed' if ed['score_compression_warning'] else '✓ ok'}")
    print(f"  Top-10 title diversity    : {ed['top10_title_diversity']} unique  {'⚠ monotone' if ed['title_monotony_warning'] else '✓ ok'}")

    # ── Baseline comparison ──
    if "baseline_comparison" in report:
        _section("5. BASELINE COMPARISON (keyword model vs hybrid model)")
        bc = report["baseline_comparison"]
        print(f"  Overlap @10 : {bc['overlap@10']}/10")
        print(f"  Overlap @25 : {bc['overlap@25']}/25")
        print(f"  Overlap @50 : {bc['overlap@50']}/50")
        print(f"  {bc['summary']}")
        print()
        print(f"  Baseline top-10 titles:")
        for t in bc["baseline_top10_titles"]:
            print(f"    - {t}")
        print(f"  Our top-10 titles:")
        for t in bc["our_top10_titles"]:
            print(f"    - {t}")

    # ── Labeled metrics ──
    if "labeled_metrics" in report:
        _section("6. GROUND-TRUTH METRICS")
        lm = report["labeled_metrics"]
        print(f"  NDCG@10  : {lm['ndcg@10']:.4f}  (weight 50%)")
        print(f"  NDCG@50  : {lm['ndcg@50']:.4f}  (weight 30%)")
        print(f"  MAP      : {lm['map']:.4f}  (weight 15%)")
        print(f"  P@10     : {lm['p@10']:.4f}  (weight  5%)")
        print(f"  Composite: {lm['composite']:.4f}")

    # ── Stability ──
    _section("7. RANKING STABILITY")
    rs = report["ranking_stability"]
    print(f"  {_pass_fail(rs['fully_stable'])}  Output is deterministic (same input → same output)")
    print(f"  {_pass_fail(rs['top1_stable'])}  Top-1 candidate stable")
    print(f"  {_pass_fail(rs['top3_same_set'])}  Top-3 set stable")

    print("\n" + "=" * 60 + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="SignalRank AI — Evaluation Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--results", required=True, help="Path to ranking JSON (from rank.py --json)")
    parser.add_argument("--candidates", default=None, help="candidates.jsonl (for baseline comparison)")
    parser.add_argument("--ground-truth", default=None, help="Ground truth JSON {candidate_id: relevance}")
    parser.add_argument("--json", default=None, dest="output_json", help="Write structured report to JSON")
    args = parser.parse_args()

    report = run_full_evaluation(
        results_path=args.results,
        candidates_path=args.candidates,
        ground_truth_path=args.ground_truth,
        output_json=args.output_json,
    )
    print_report(report)

    if args.output_json:
        print(f"Structured report saved to: {args.output_json}")


if __name__ == "__main__":
    main()
