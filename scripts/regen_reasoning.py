"""
Regenerate reasoning and update debug.json + submission.csv from existing ranked results.

This avoids re-encoding 100K candidates when only the reasoning logic changed.
Reads raw candidate data to feed the updated explainer, then patches debug.json + CSV.

Usage:
    python scripts/regen_reasoning.py [--candidates PATH] [--debug PATH] [--out PATH]
"""
import argparse, csv, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.candidate_parser import load_candidates
from backend.explainer import generate_reasoning
from backend.exporter import _enrich_candidate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", default="data/raw/candidates.jsonl")
    parser.add_argument("--debug",      default="outputs/debug.json")
    parser.add_argument("--out",        default="outputs/submission.csv")
    args = parser.parse_args()

    print(f"Loading debug.json from {args.debug}...")
    with open(args.debug) as f:
        ranked = json.load(f)

    needed_ids = {r["candidate_id"] for r in ranked}
    print(f"  {len(needed_ids)} candidate IDs to look up")

    print(f"Loading candidates from {args.candidates}...")
    all_profiles = load_candidates(args.candidates)
    id_to_raw = {p.candidate_id: p.raw for p in all_profiles if p.candidate_id in needed_ids}
    print(f"  Found {len(id_to_raw)} matching profiles")

    print("Regenerating reasoning...")
    for result in ranked:
        cid = result["candidate_id"]
        raw = id_to_raw.get(cid)
        if raw is None:
            continue

        components = result.get("scores", {})
        components["final_score"] = result["final_score"]
        components["penalty_reasons"] = result.get("penalty_reasons", [])
        components["behavioral_sub"] = result.get("behavioral_breakdown", {})

        is_hp = result.get("is_honeypot", False)
        hp_flags = []
        if is_hp:
            hp_flags = ["flagged profile"]

        new_reasoning = generate_reasoning(
            candidate=raw,
            components=components,
            rank=result["rank"],
            is_honeypot=is_hp,
            honeypot_flags=hp_flags,
        )
        result["reasoning"] = new_reasoning

        enriched = _enrich_candidate(raw, components)
        result["matched_skills"]   = enriched["matched_skills"]
        result["missing_skills"]   = enriched["missing_skills"]
        result["career_snippets"]  = enriched["career_snippets"]
        result["skills_snapshot"]  = enriched["skills_snapshot"]

    print(f"Writing updated debug.json to {args.debug}...")
    with open(args.debug, "w", encoding="utf-8") as f:
        json.dump(ranked, f, indent=2, ensure_ascii=False)

    print(f"Writing updated submission.csv to {args.out}...")
    prev_score = ranked[0]["final_score"] if ranked else 1.0
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        for row in ranked[:100]:
            score = min(round(row["final_score"], 6), prev_score)
            prev_score = score
            reasoning = row["reasoning"].replace("\n", " ").replace("\r", " ").strip()
            writer.writerow([row["candidate_id"], row["rank"], score, reasoning])

    print("Done.")


if __name__ == "__main__":
    main()
