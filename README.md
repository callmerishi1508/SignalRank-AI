# SignalRank AI

**Rank talent by fit, not keywords.**

Redrob Intelligent Candidate Discovery & Ranking Challenge — hackathon submission.

---

## What it does

SignalRank AI ranks candidates from a large pool against a job description using a two-stage hybrid pipeline:

**Stage 1 — Semantic retrieval**: sentence-transformers + FAISS vector index + TF-IDF, fused via Reciprocal Rank Fusion (RRF), retrieves a high-recall candidate pool in seconds.

**Stage 2 — Rule-based hybrid reranking**: 7 evidence-grounded scoring components (title alignment, skill depth, production evidence, behavioral availability, experience fit, domain fit, location) blend with pre-computed semantic similarity. Penalty multipliers collapse scores for disqualified archetypes.

The system correctly ranks actual ML/AI engineers above keyword-stuffed HR Managers and Content Writers — the explicit trap in the challenge dataset.

---

## Quick start

```bash
# 1. Create virtualenv and install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Run the ranking pipeline
python rank.py --candidates ./data/raw/candidates.jsonl --out ./outputs/submission.csv --json ./outputs/debug.json

# 3. Validate the submission CSV
python scripts/validate_submission.py outputs/submission.csv

# 4. View results in the dashboard
streamlit run app/streamlit_app.py
```

> **Performance** (synthetic 2,000 candidates, Apple M-series CPU):  
> First run (cold cache): ~19s | Cache hit: ~6s  
> Extrapolates to ≤5 min for 100K candidates.

---

## Repository structure

```
signalrank-ai/
├── rank.py                     # Main pipeline entry point
├── requirements.txt
├── config/
│   └── scoring.yaml            # ALL scoring parameters (weights, thresholds, tuning)
├── backend/
│   ├── constants.py            # Shared constants (REFERENCE_DATE) — single source of truth
│   ├── config_loader.py        # Config singleton — all modules import from here
│   ├── candidate_parser.py     # CandidateProfile dataclass + JSONL loader
│   ├── jd_parser.py            # Structured job profile + JD embedding text
│   ├── retrieval.py            # SemanticRetriever: FAISS + TF-IDF + RRF + cache
│   ├── scorer.py               # 7-component hybrid scoring engine
│   ├── honeypot.py             # Honeypot detection (7 impossibility checks)
│   ├── explainer.py            # Recruiter-facing reasoning generation
│   └── exporter.py             # CSV + JSON output (spec-compliant)
├── app/
│   └── streamlit_app.py        # Recruiter dashboard UI
├── evaluation/
│   └── eval.py                 # Full evaluation framework (sanity + distribution + baseline)
├── scripts/
│   ├── validate_submission.py  # Organizer-provided CSV format validator
│   └── generate_test_data.py   # Synthetic candidate generator for testing
├── tests/
│   ├── test_config.py          # Config loader tests
│   ├── test_candidate_parser.py
│   ├── test_retrieval.py       # FAISS + RRF + cache tests
│   ├── test_scorer.py          # 7-component scoring unit tests
│   └── test_pipeline.py        # End-to-end integration tests
├── data/raw/
│   ├── candidate_schema.json   # Organizer candidate record schema
│   ├── job_description.md      # Target JD (Senior AI Engineer)
│   └── candidates.jsonl        # Place organizer dataset here
├── docs/
│   ├── architecture.md         # System design and component guide
│   ├── deployment.md           # Setup, tuning, environment notes
│   ├── evaluation_report.md    # Evaluation methodology and results
│   └── user_guide.md           # Recruiter dashboard user guide
└── outputs/
    ├── submission.csv           # Submit this file
    ├── debug.json               # Full JSON with score breakdowns
    └── eval_report.json         # Structured evaluation report
```

---

## Pipeline in detail

```
candidates.jsonl
      ↓
[candidate_parser.py]  →  CandidateProfile[]  (normalized, with derived fields)
      ↓
[honeypot.py]          →  flags impossible profiles (7 checks, all thresholds in config)
      ↓
[retrieval.py]         →  SemanticRetriever
                           ├─ FAISS (sentence-transformers/all-MiniLM-L6-v2)  top-3000
                           ├─ TF-IDF (scikit-learn)                           top-3000
                           └─ RRF fusion (k=60) + title safety net  →  ~1500-candidate pool
      ↓
[scorer.py]            →  score_candidates_bulk(pool, similarities)
                           7 components × configured weights + penalty multipliers
                           final = (0.75 × rule + 0.25 × embedding_sim) × (1 − penalty)
      ↓
[explainer.py]         →  recruiter-readable reasoning for each candidate
      ↓
[exporter.py]          →  submission.csv (spec-compliant: 100 rows, rank 1-100)
```

---

## Scoring formula

```
final_score = (0.75 × rule_score + 0.25 × semantic_similarity) × (1 − penalty)

rule_score =
  0.25 × title_role_score        # decisive — prevents keyword stuffers ranking high
  0.20 × skill_match_score       # depth × breadth × assessment validation
  0.15 × production_evidence     # deployed systems, scale mentions
  0.15 × behavioral_score        # recency, response rate, notice period, GitHub
  0.10 × experience_fit          # ideal range: 5–9 years
  0.10 × domain_fit              # product company > large neutral > consulting
  0.05 × location_score          # Pune/Noida tier-1, Bangalore/Hyd tier-2
```

All weights and thresholds are in `config/scoring.yaml` — tune without touching code.

### Penalty multipliers

| Condition | Penalty |
|-----------|---------|
| Consulting-only career (>85% TCS/Infosys/Wipro/Accenture/etc.) | −30% |
| Wrong role domain (HR/Sales/Marketing/Content) | −45% |
| CV/speech/robotics without NLP/IR overlap | −30% |
| Job-hopping (≥4 stints ≤18 months) | −10% |
| Behaviorally unavailable (>180d inactive + <10% response rate) | −20% |
| Honeypot detected | −95% |

---

## Running tests

```bash
# All tests
python -m pytest tests/ -v

# Individual suites
python -m pytest tests/test_config.py -v          # Config loader (10 tests)
python -m pytest tests/test_candidate_parser.py -v # Candidate normalization (15 tests)
python -m pytest tests/test_retrieval.py -v        # Retrieval + RRF + cache (17 tests)
python -m pytest tests/test_scorer.py -v           # Scoring engine (9 tests)
python -m pytest tests/test_pipeline.py -v         # End-to-end (5 tests)
```

Current status: **56/56 tests pass**.

---

## Evaluation

```bash
python evaluation/eval.py \
  --results outputs/debug.json \
  --candidates data/raw/candidates.jsonl \
  --json outputs/eval_report.json
```

Produces:
- Format/spec sanity checks
- Score distribution with percentiles and bands
- Top-10, top-25, top-100 profiles (title breakdown, component averages)
- Systematic error detection (honeypots, wrong-domain high scores)
- Baseline comparison (our model vs keyword-count model)
- Ranking stability verification

---

## Generating synthetic test data

```bash
python scripts/generate_test_data.py --n 5000 --out data/raw/candidates.jsonl
```

Generates a realistic mix of archetypes: true ML engineers, keyword stuffers, consulting-only, inactive candidates, CV specialists, and honeypots.

---

## Configuration tuning

All scoring parameters live in `config/scoring.yaml`. To tune between submissions:

```yaml
scoring:
  component_weights:
    title_role: 0.25        # increase if keyword stuffers still rank high
    behavioral: 0.15        # increase to prefer available candidates
    skill_match: 0.20       # increase for skill depth importance

semantic:
  embedding:
    rule_blend: 0.75        # 75% rule-based, 25% semantic
    semantic_blend: 0.25
```

No code changes needed — just edit the YAML and re-run.

---

## Design decisions

1. **Title alignment is the decisive signal** (25% weight). An HR Manager with 9 AI keywords in skills scores ~0.05 on title_role, collapsing their total score below 0.25.

2. **Two-stage retrieval prevents re-encoding latency**. FAISS retrieves top-3000 in milliseconds after one-time encoding. Rule-based scoring then operates on this pool, not all N candidates.

3. **RRF fusion improves recall**. Combining FAISS rankings + TF-IDF rankings via Reciprocal Rank Fusion ensures candidates strong in either semantic or lexical similarity are in the pool.

4. **Embedding cache eliminates repeat costs**. Candidate embeddings are persisted to disk (`.npy` + `.faiss`). Subsequent runs skip the ~15s encoding step.

5. **Behavioral signals are availability-weighted, not tiebreakers**. A candidate who hasn't responded to recruiters in 6 months is effectively unavailable — scored accordingly regardless of skill depth.

6. **Honeypot detection is mandatory**. The spec disqualifies submissions with >10% honeypots in top-100. Seven independent detection checks (timeline overlaps, YOE contradictions, all-maxed signals) handle the known patterns.

7. **All thresholds are externalized**. `config/scoring.yaml` contains every numeric constant — from FAISS `top_k` to penalty fractions. The scoring formula is tunable without code changes.

---

## Submission assets

- `outputs/submission.csv` — the ranked output file (submit this)
- `outputs/debug.json` — full debug output with score breakdowns
- `outputs/eval_report.json` — structured evaluation report
- `submission_metadata.yaml` — organizer submission manifest
