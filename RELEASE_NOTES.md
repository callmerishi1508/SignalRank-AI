# SignalRank AI — Release Notes

**Version**: 1.0.0  
**Release date**: 2026-06-29  
**Git ref**: `f2c6daa` (main)  
**Commits**: 11  
**Status**: Submission-ready

---

## What this release is

SignalRank AI v1.0.0 is the complete hackathon submission for the Redrob Intelligent Candidate Discovery & Ranking Challenge. It ranks 2,000 candidates against a job description in under 20 seconds on a CPU-only laptop, with zero API calls, full explainability, and honeypot defense.

---

## Completed Features

### Core Pipeline

- **Candidate normalization layer** (`backend/candidate_parser.py`): parses raw JSONL into `CandidateProfile` dataclasses with pre-computed derived fields (consulting_fraction, ml_fraction, days_since_active, profile_text)
- **Job description parser** (`backend/jd_parser.py`): extracts structured requirements from the markdown JD — required skills, experience range, seniority, domain, location
- **Two-stage semantic retrieval** (`backend/retrieval.py`):
  - FAISS `IndexFlatIP` (sentence-transformers/all-MiniLM-L6-v2, 384-dim) retrieves top-3,000 by embedding similarity
  - TF-IDF (scikit-learn, ngram 1-2, 8,192 features) retrieves top-3,000 by lexical similarity
  - Reciprocal Rank Fusion (k=60) merges both ranked lists into a ~1,500-candidate pool
  - Title safety net force-includes any candidate with a tier-1 ML/AI title
  - Embedding cache (`.npy` + `.faiss`) eliminates re-encoding on subsequent runs
- **Seven-component hybrid scoring engine** (`backend/scorer.py`):
  - title_role (25%), skill_match (20%), production_evidence (15%), behavioral (15%), experience_fit (10%), domain_fit (10%), location (5%)
  - Final blend: 75% rule-based + 25% embedding similarity
  - Additive penalty multipliers: consulting-only (−30%), wrong-domain (−45%), CV-without-NLP (−30%), job-hopping (−10%), unavailable (−20%), honeypot (−95%)
  - All weights and thresholds in `config/scoring.yaml`
- **Honeypot detection** (`backend/honeypot.py`): 7 independent impossibility checks; triggers at 2+ flags or a single-flag knockout; ×0.05 multiplier; 22 detected on synthetic dataset, 0 in top-100
- **Explainability engine** (`backend/explainer.py`): 5 narrative styles (production_led, skills_led, career_arc_led, availability_led, balanced) producing 2-4 sentence recruiter-quality justifications citing specific companies, career evidence excerpts, and behavioral signals
- **Submission exporter** (`backend/exporter.py`): organizer-compliant CSV (100 rows, monotonically non-increasing scores) + enriched debug JSON for the dashboard UI; synonym-based skill matching prevents false-positive "missing" labels

### Infrastructure

- **Config loader** (`backend/config_loader.py`): validates `config/scoring.yaml` at startup; weight sums, required keys, and type checks enforced; cached singleton for pipeline performance
- **Centralized constants** (`backend/constants.py`): single `REFERENCE_DATE` shared across all 4 modules that compute recency
- **Pipeline orchestrator** (`rank.py`): single-command entry point; embedding cache by default, `--no-cache` flag for reproducibility checks; structured logging with per-stage timing

### Dashboard

- **Streamlit recruiter dashboard** (`app/streamlit_app.py`):
  - **Ranked Shortlist tab**: top-100 cards with inline "Why this candidate?" expandable panels showing component bars, matched/missing skills, career evidence
  - **Candidate Detail tab**: full 3-column layout with 7-component breakdown, behavioral sub-scores, career snippets, education, Redrob signals
  - **Compare tab**: side-by-side comparison of any two candidates with ▲/▼ delta indicators, strengths/risks sections, and recommendation banner
  - **Insights tab**: 6 Plotly charts — score histogram, seniority distribution, skills frequency, location spread, notice period bands, component radar
  - **Evaluation tab**: format compliance status, baseline comparison, score distribution summary

### Evaluation and Testing

- **Evaluation framework** (`evaluation/eval.py`): NDCG@10/50, MAP, P@10 (when labels available); archetype discrimination tests, honeypot safety check, baseline comparison, ranking stability verification, score distribution analysis
- **Test suite** (`tests/`): 56 unit and integration tests covering config, candidate parsing, retrieval (RRF, FAISS, TF-IDF, title safety net, cache), scoring (7 archetype inequalities), and end-to-end pipeline format compliance — all passing
- **Submission validator** (`scripts/validate_submission.py`): header check, 100-row count, unique ranks, non-increasing scores, candidate ID format

### Documentation

- `README.md`: setup, run, test, evaluate, tune — complete user-facing guide
- `docs/architecture.md`: component interaction, data flow, design rationale
- `docs/deployment.md`: environment requirements, cold-start walkthrough, configuration guide
- `docs/evaluation_report.md`: methodology, score distribution, baseline comparison, limitations
- `docs/user_guide.md`: 5-tab dashboard user guide
- `docs/pitch_deck_outline.md`: 7-slide structure with appendix slides
- `SUBMISSION_AUDIT.md`: full deliverable checklist with manual actions
- `DEMO_SCRIPT.md`: 2-minute and 5-minute demo flows with judge talking points
- `JUDGE_FAQ.md`: concise answers for 15 likely judge questions
- `REVIEW_REPORT.md`: 7-perspective independent review with go/no-go recommendation
- `FINAL_RELEASE_REPORT.md`: stabilization pass change log, remaining limitations, reproducibility status

---

## Known Limitations

### Score compression on synthetic data
Top-100 candidates score within a 0.020-point band (0.9031–0.9226). This is a synthetic-data artifact — the generated candidates share similar templates. Real organizer data with heterogeneous candidates will produce wider score spread and clearer rank separation.

### Embedding model not fine-tuned for recruiting
`all-MiniLM-L6-v2` was trained on a general corpus (MS-MARCO + NLI). It handles ML vocabulary well but may underperform on very new terminology or Indian-specific industry vocabulary. The TF-IDF path in RRF provides complementary lexical coverage.

### No ground-truth labels available pre-submission
The organizer composite metric (NDCG@10 × 0.5 + NDCG@50 × 0.3 + MAP × 0.15 + P@10 × 0.05) is computed by the organizer after the deadline. All evaluation is sanity-based and proxy-measured.

### Single job description per run
The system ranks one JD at a time. Multi-JD routing or a multi-role dashboard is not implemented.

### Streamlit navigation constraint
Clicking a candidate card in the Shortlist tab does not auto-navigate to the Detail tab; the user must switch tabs and use the dropdown. This is a Streamlit architecture constraint.

### Static REFERENCE_DATE
Behavioral recency is computed against `date(2026, 6, 25)`. Candidates who became active after this date will not benefit from improved recency scores without a config change.

### No production hardening
The Streamlit app has no file upload size limit (DoS risk if hosted publicly) and no authentication. It is designed for local/demo use.

---

## Future Improvements

In priority order, if resources and time permit after submission:

1. **Recruiter feedback loop**: capture hired/rejected signals and use them to retrain scoring weights via a simple linear model. Converts the system from configurable to self-improving.

2. **Dynamic JD parsing**: accept any job description by paste or URL, not just the hardcoded markdown file. Parse requirements dynamically and adapt scoring weights.

3. **Cross-role routing**: maintain a multi-JD database and route candidates to the best-matching role rather than ranking one JD at a time.

4. **Bi-encoder fine-tuning**: if labeled data becomes available (e.g., from recruiter feedback), fine-tune `all-MiniLM-L6-v2` on (JD, candidate_profile, relevance_label) triplets.

5. **IVF index activation**: set `index_type: "ivf"` in scoring.yaml for datasets >50,000 candidates. Config is already wired; only the YAML change is needed.

6. **Bias audit reporting**: add a layer that detects demographic skew in the top-100 (institution tier, YOE distribution) and flags for recruiter review.

7. **API server mode**: expose the ranking pipeline as a REST endpoint so it can be integrated into existing ATS platforms.

---

## Final Submission Checklist

Complete the following in order:

- [ ] Update `submission_metadata.yaml`:
  - [ ] Replace `+91-XXXXXXXXXX` with real phone number
  - [ ] Confirm `github_repo` URL is correct
  - [ ] Set `sandbox_link` to live URL or `"N/A"` if not deploying
- [ ] Push to GitHub: `git push -u origin main`
- [ ] Confirm repository is public and accessible
- [ ] Run from clean checkout to verify reproducibility:
  ```bash
  pip install -r requirements.txt
  python rank.py --candidates data/raw/candidates.jsonl --out outputs/submission.csv --json outputs/debug.json --no-cache
  python scripts/validate_submission.py outputs/submission.csv
  ```
  Expected: `Submission is valid.`
- [ ] Submit `outputs/submission.csv` and `submission_metadata.yaml` to organizer
- [ ] Submit GitHub repository link to organizer
- [ ] Submit sandbox/demo link to organizer (if applicable)

**Note**: The organizer allows 3 total submissions. Reserve at least one for after receiving feedback or reviewing the leaderboard.

---

## Repository Stats

| Metric | Value |
|--------|-------|
| Total commits | 11 |
| Python source files | 18 |
| Lines of Python | ~5,400 |
| Test count | 56 |
| Test pass rate | 100% |
| Documentation files | 14 |
| Dependencies | 10 (all pinned) |
| Model size | 22 MB (all-MiniLM-L6-v2) |
| Cold-start runtime | ~8–20s (2,000 candidates) |
| Cache-hit runtime | ~4–8s |
| Network calls during ranking | 0 |
| Honeypots in top-100 | 0 |
