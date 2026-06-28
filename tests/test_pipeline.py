"""
End-to-end pipeline integration tests.

Tests that a full run from candidates.jsonl → submission.csv produces
a valid, spec-compliant output.
"""

import csv
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_synthetic_candidates(n: int = 200) -> list:
    """Generate a small synthetic dataset inline for testing."""
    from scripts.generate_test_data import generate_candidates
    return generate_candidates(n)


def test_full_pipeline_produces_valid_csv():
    """Full pipeline: generate → score → export → validate CSV format."""
    from rank import run_pipeline
    from scripts.validate_submission import validate_submission

    candidates = load_synthetic_candidates(300)

    with tempfile.TemporaryDirectory() as tmpdir:
        candidates_path = os.path.join(tmpdir, "candidates.jsonl")
        csv_path = os.path.join(tmpdir, "submission.csv")
        json_path = os.path.join(tmpdir, "debug.json")

        # Write candidates
        with open(candidates_path, "w") as f:
            for c in candidates:
                f.write(json.dumps(c) + "\n")

        # Run pipeline
        run_pipeline(candidates_path, csv_path, json_path)

        # Validate CSV format
        assert Path(csv_path).exists(), "submission.csv not created"
        errors = validate_submission(csv_path)
        assert not errors, f"CSV validation failed: {errors}"

        # Validate JSON output
        assert Path(json_path).exists(), "debug.json not created"
        with open(json_path) as f:
            results = json.load(f)
        assert len(results) == 100, f"Expected 100 results, got {len(results)}"

    print("PASS: full pipeline produces valid submission CSV")


def test_csv_has_exactly_100_rows():
    from rank import run_pipeline

    candidates = load_synthetic_candidates(300)

    with tempfile.TemporaryDirectory() as tmpdir:
        cpath = os.path.join(tmpdir, "candidates.jsonl")
        opath = os.path.join(tmpdir, "output.csv")

        with open(cpath, "w") as f:
            for c in candidates:
                f.write(json.dumps(c) + "\n")

        run_pipeline(cpath, opath)

        with open(opath, newline="") as f:
            rows = list(csv.reader(f))

        assert rows[0] == ["candidate_id", "rank", "score", "reasoning"], \
            f"Wrong header: {rows[0]}"
        assert len(rows) == 101, f"Expected 101 rows (1 header + 100 data), got {len(rows)}"

    print("PASS: CSV has exactly 100 data rows")


def test_scores_monotonically_non_increasing():
    from rank import run_pipeline

    candidates = load_synthetic_candidates(300)

    with tempfile.TemporaryDirectory() as tmpdir:
        cpath = os.path.join(tmpdir, "candidates.jsonl")
        opath = os.path.join(tmpdir, "output.csv")

        with open(cpath, "w") as f:
            for c in candidates:
                f.write(json.dumps(c) + "\n")

        run_pipeline(cpath, opath)

        scores = []
        with open(opath, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scores.append(float(row["score"]))

        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i+1], \
                f"Score not monotonically non-increasing at ranks {i+1},{i+2}: {scores[i]:.6f} < {scores[i+1]:.6f}"

    print("PASS: scores are monotonically non-increasing")


def test_ideal_candidates_rank_in_top10():
    """
    Verifies that true ML/AI engineers rank above keyword stuffers.
    Seeds the candidate pool with known true positives and checks their rank.
    """
    from rank import run_pipeline
    from scripts.generate_test_data import (
        make_true_positive, make_keyword_stuffer, generate_candidates
    )

    # Create a pool: 100 fillers + 5 known true positives
    fillers = generate_candidates(250)
    true_positives = [make_true_positive(f"CAND_TP_{i:07d}") for i in range(5)]
    all_candidates = fillers + true_positives

    with tempfile.TemporaryDirectory() as tmpdir:
        cpath = os.path.join(tmpdir, "candidates.jsonl")
        opath = os.path.join(tmpdir, "output.csv")
        jpath = os.path.join(tmpdir, "debug.json")

        with open(cpath, "w") as f:
            for c in all_candidates:
                f.write(json.dumps(c) + "\n")

        run_pipeline(cpath, opath, jpath)

        with open(jpath) as f:
            results = json.load(f)

        top10_ids = {r["candidate_id"] for r in results[:10]}
        tp_ids = {c["candidate_id"] for c in true_positives}
        tp_in_top10 = len(top10_ids & tp_ids)

        # At least 2 of 5 true positives should be in top 10
        assert tp_in_top10 >= 2, \
            f"Expected at least 2 true positives in top 10, got {tp_in_top10}"

    print(f"PASS: {tp_in_top10}/5 true positives ranked in top 10")


def test_honeypots_not_in_top10():
    """Verifies that detected honeypots are excluded from the top 10."""
    from rank import run_pipeline
    from scripts.generate_test_data import make_honeypot, generate_candidates

    fillers = generate_candidates(250)
    honeypots = [make_honeypot(f"CAND_HP_{i:07d}") for i in range(10)]
    all_candidates = fillers + honeypots

    with tempfile.TemporaryDirectory() as tmpdir:
        cpath = os.path.join(tmpdir, "candidates.jsonl")
        opath = os.path.join(tmpdir, "output.csv")
        jpath = os.path.join(tmpdir, "debug.json")

        with open(cpath, "w") as f:
            for c in all_candidates:
                f.write(json.dumps(c) + "\n")

        run_pipeline(cpath, opath, jpath)

        with open(jpath) as f:
            results = json.load(f)

        top10_ids = {r["candidate_id"] for r in results[:10]}
        hp_ids = {c["candidate_id"] for c in honeypots}
        hp_in_top10 = len(top10_ids & hp_ids)

        assert hp_in_top10 == 0, \
            f"Expected 0 honeypots in top 10, got {hp_in_top10}"

    print(f"PASS: 0 honeypots in top 10")


def run_all_tests():
    tests = [
        test_csv_has_exactly_100_rows,
        test_scores_monotonically_non_increasing,
        test_full_pipeline_produces_valid_csv,
        test_ideal_candidates_rank_in_top10,
        test_honeypots_not_in_top10,
    ]

    passed = 0
    failed = 0
    for test in tests:
        print(f"Running {test.__name__}...")
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {e}")
            failed += 1
        except Exception as e:
            import traceback
            print(f"ERROR: {type(e).__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
