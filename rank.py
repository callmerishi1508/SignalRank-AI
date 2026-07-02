#!/usr/bin/env python3
"""
SignalRank AI — main ranking entry point.

Two-stage pipeline:
  1. Parse candidates → CandidateProfile objects
  2. Honeypot detection (all candidates, O(N))
  3. Semantic retrieval: FAISS + TF-IDF → RRF → candidate pool
  4. Rule-based hybrid reranking on pool with pre-computed similarities
  5. Explain top 100, export submission CSV

Usage:
    python rank.py --candidates ./data/raw/candidates.jsonl --out ./outputs/submission.csv
    python rank.py --candidates ./candidates.jsonl --out ./out.csv --json ./debug.json --no-cache

Constraints (submission_spec.md §3):
    - CPU only
    - No network calls during ranking
    - ≤5 minutes wall-clock
    - ≤16 GB RAM
    - Output: exactly 100 rows, ranks 1-100, score non-increasing
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

from backend.candidate_parser import load_candidates_list, CandidateProfile
from backend.config_loader import load_config
from backend.honeypot import detect_honeypot
from backend.jd_parser import get_active_jd_profile
from backend.retrieval import SemanticRetriever
from backend.scorer import score_candidates_bulk
from backend.explainer import generate_reasoning
from backend.exporter import export_csv, export_json

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def run_pipeline(
    candidates_path: str,
    output_csv: str,
    output_json: Optional[str] = None,
    no_cache: bool = False,
) -> None:
    """
    End-to-end ranking pipeline.

    Args:
        candidates_path: Path to candidates.jsonl.
        output_csv: Path to write submission CSV.
        output_json: Optional path to write full debug JSON.
        no_cache: If True, ignore existing embedding cache and rebuild.
    """
    t0 = time.time()
    cfg = load_config()
    honeypot_penalty = cfg.penalties.honeypot_multiplier

    # -----------------------------------------------------------------------
    # Stage 1: Load + parse candidates
    # -----------------------------------------------------------------------
    log.info(f"Loading candidates from {candidates_path}")
    profiles = load_candidates_list(candidates_path)
    log.info(f"Loaded {len(profiles):,} candidates in {time.time()-t0:.1f}s")

    if len(profiles) == 0:
        raise ValueError(
            "No valid candidates were parsed from the file. "
            "Ensure the file is a non-empty JSONL where each line is a candidate record."
        )

    if len(profiles) < 100:
        log.warning(f"Only {len(profiles)} candidates — need ≥100 for submission")

    # -----------------------------------------------------------------------
    # Stage 2: Honeypot detection (all candidates)
    # -----------------------------------------------------------------------
    log.info("Running honeypot detection...")
    t1 = time.time()
    for cp in profiles:
        is_hp, hp_flags = detect_honeypot(cp.raw, config=cfg)
        cp.is_honeypot = is_hp
        cp.honeypot_reasons = hp_flags
    hp_count = sum(1 for cp in profiles if cp.is_honeypot)
    log.info(f"Honeypot detection: {hp_count} flagged in {time.time()-t1:.1f}s")

    # -----------------------------------------------------------------------
    # Stage 3: Semantic retrieval → candidate pool
    # -----------------------------------------------------------------------
    log.info("Running semantic retrieval...")
    t2 = time.time()

    source_path = Path(candidates_path)
    jd = get_active_jd_profile()
    retriever = SemanticRetriever(config=cfg, jd=jd)
    result = retriever.fit_and_retrieve(profiles, source_path=source_path, force_reencode=no_cache)

    log.info(
        f"Retrieval done in {time.time()-t2:.1f}s | backend={result.backend_used} "
        f"| pool={len(result.profiles)} candidates"
    )

    # -----------------------------------------------------------------------
    # Stage 4: Rule-based hybrid reranking on pool
    # -----------------------------------------------------------------------
    log.info(f"Scoring pool of {len(result.profiles)} candidates...")
    t3 = time.time()

    pool_raw = [cp.raw for cp in result.profiles]
    ranked = score_candidates_bulk(
        pool_raw,
        jd=jd,
        similarities=result.similarities,
        config=cfg,
    )

    # Build a lookup from candidate_id → CandidateProfile for explanation
    id_to_profile = {cp.candidate_id: cp for cp in result.profiles}

    # Apply honeypot multiplier
    for row in ranked:
        cid = row["candidate_id"]
        cp = id_to_profile.get(cid)
        if cp and cp.is_honeypot:
            row["final_score"] = row["final_score"] * honeypot_penalty
            row["is_honeypot"] = True
            row["honeypot_flags"] = cp.honeypot_reasons
        else:
            row["is_honeypot"] = False
            row["honeypot_flags"] = []

    log.info(f"Scoring complete in {time.time()-t3:.1f}s")

    # Sort: score desc, candidate_id asc for ties
    ranked.sort(key=lambda r: (-r["final_score"], r["candidate_id"]))

    # -----------------------------------------------------------------------
    # Stage 5: Generate reasoning for top 100
    # -----------------------------------------------------------------------
    log.info("Generating reasoning for top 100...")
    for i, row in enumerate(ranked[:100]):
        cid = row["candidate_id"]
        cp = id_to_profile.get(cid)
        row["reasoning"] = generate_reasoning(
            candidate=row["candidate"],
            components=row["components"],
            rank=i + 1,
            is_honeypot=row["is_honeypot"],
            honeypot_flags=row["honeypot_flags"],
        )

    # -----------------------------------------------------------------------
    # Stage 6: Export
    # -----------------------------------------------------------------------
    log.info(f"Exporting CSV → {output_csv}")
    export_csv(ranked, output_csv)

    if output_json:
        log.info(f"Exporting JSON → {output_json}")
        export_json(ranked, output_json)

    elapsed = time.time() - t0
    log.info(f"Pipeline complete in {elapsed:.1f}s")

    # Summary
    top3 = ranked[:3]
    log.info("Top 3 candidates:")
    for i, r in enumerate(top3):
        log.info(
            f"  #{i+1} {r['candidate_id']} score={r['final_score']:.4f} "
            f"backend={result.backend_used}"
        )

    print(f"\nSubmission written to: {output_csv}")
    print(f"Total candidates scored: {len(profiles):,}")
    print(f"Pool size (retrieval): {len(result.profiles)}")
    print(f"Honeypots detected: {hp_count}")
    print(f"Backend used: {result.backend_used}")
    print(f"Pipeline time: {elapsed:.1f}s")


def main():
    parser = argparse.ArgumentParser(
        description="SignalRank AI — Candidate Ranking Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rank.py --candidates ./data/raw/candidates.jsonl --out ./outputs/submission.csv
  python rank.py --candidates ./candidates.jsonl --out ./out.csv --json ./debug.json
  python rank.py --candidates ./candidates.jsonl --out ./out.csv --no-cache
        """,
    )
    parser.add_argument(
        "--candidates",
        required=True,
        help="Path to candidates.jsonl",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output CSV path (e.g. ./outputs/team_signalrank.csv)",
    )
    parser.add_argument(
        "--json",
        default=None,
        help="Optional: full JSON debug output path",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=False,
        help="Ignore existing embedding cache; rebuild from scratch",
    )

    args = parser.parse_args()
    run_pipeline(args.candidates, args.out, args.json, no_cache=args.no_cache)


if __name__ == "__main__":
    main()
