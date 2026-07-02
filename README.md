# SignalRank AI

Intelligent candidate ranking for any role, at scale.

SignalRank AI is a hybrid pipeline that reads a job description, understands what the role actually needs, evaluates candidates holistically across seven evidence-grounded dimensions, and produces a recruiter-trustworthy ranked shortlist with transparent reasoning for every candidate.

Built for the **Redrob Intelligent Candidate Discovery & Ranking Challenge 2026**.

---

## What it does

Most ATS systems rank by keyword count. SignalRank ranks by fit.

**Two-stage pipeline:**

1. **Semantic retrieval** — `sentence-transformers/all-MiniLM-L6-v2` encodes every candidate profile into a 384-dimension dense vector. FAISS retrieves the top-3000 by embedding similarity. TF-IDF retrieves another top-3000 by lexical match. Both lists are fused via Reciprocal Rank Fusion (k=60) into a ~1500-candidate pool, ensuring high recall even when a strong candidate uses different terminology than the JD.

2. **Rule-based hybrid reranking** — The pool is scored across seven evidence-grounded components. Penalty multipliers collapse scores for disqualified archetypes. Final score blends rule-based and semantic signals.

**Result:** A ranked shortlist of 100 candidates with per-candidate score breakdowns, recruiter-readable reasoning, and key differentiators — ready to export.

---

## Scoring formula

```
final_score = (0.75 × rule_score + 0.25 × semantic_similarity) × (1 − penalty)

rule_score =
  0.25 × title_role_score        # decisive filter — collapses keyword stuffers
  0.20 × skill_match_score       # depth × breadth × assessment validation
  0.15 × production_evidence     # deployed systems, scale mentions, latency/QPS
  0.15 × behavioral_score        # recency, response rate, notice period, GitHub activity
  0.10 × experience_fit          # ideal range with ramp curve (configurable)
  0.10 × domain_fit              # product company > neutral > consulting-only
  0.05 × location_score          # configurable tier-1 and tier-2 cities
```

All weights and thresholds live in `config/scoring.yaml` — tune without touching code.

**Penalty multipliers**

| Condition | Penalty |
|---|---|
| Consulting-only career (TCS / Infosys / Wipro / Accenture / etc.) | −30% |
| Wrong role domain (HR / Sales / Marketing / Content) | −45% |
| CV or speech engineering without NLP/IR overlap | −30% |
| Job-hopping (≥4 stints ≤18 months) | −10% |
| Behaviorally unavailable (>180d inactive + <10% response rate) | −20% |
| Honeypot detected | −95% |

---

## Features

**Dynamic job description parsing**
Paste or upload any JD. The parser auto-extracts role title, required skills, seniority, experience range, and locations using vocabulary matching and regex — no LLM required. Switch between the demo JD and any custom JD without restarting the app.

**Three candidate input modes**
- Upload a `.jsonl` candidate dataset (organizer format)
- Upload a ZIP of PDF, DOCX, or TXT resumes — each file is parsed, structured, and scored
- Paste a public Google Drive folder link — resumes are downloaded automatically and ranked

**Recruiter dashboard**
- Ranked candidate cards with score bars and confidence ratings
- Advanced filters: minimum score, YOE range, max notice period, behavioral score threshold, sort by any component
- Full Profile modal: complete score breakdown, behavioral signal breakdown, matched and missing skills, career evidence
- Key Differentiator panel: shows which components this candidate outperforms the cohort average and by how much
- Shortlist and Recruiter Notes: bookmark candidates and add notes, export shortlist as CSV
- Insights tab: cohort-level score distributions, component averages, top-skills breakdown
- Evaluation tab: format compliance checks, baseline comparison, honeypot audit

**Honeypot detection (7 checks)**
Career timeline overlaps, graduation/career-start contradictions, stated-YOE vs actual span, all-expert-with-maxed-endorsements, all-behavioral-signals-at-maximum, duration inflation, impossible education dates.

**Embedding cache**
Candidate embeddings are saved to disk after first run. Subsequent runs skip re-encoding. A size-protection guard prevents a smaller upload from overwriting a larger cached dataset.

---

## Quick start

```bash
# 1. Create a virtual environment and install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Place the organizer dataset
cp /path/to/candidates.jsonl data/raw/candidates.jsonl

# 3. Run the ranking pipeline
python rank.py \
  --candidates ./data/raw/candidates.jsonl \
  --out ./outputs/submission.csv \
  --json ./outputs/debug.json

# 4. Validate the output
python scripts/validate_submission.py outputs/submission.csv

# 5. Open the recruiter dashboard
streamlit run app/streamlit_app.py
```

The dashboard auto-loads `outputs/debug.json` on startup. You can also load any result file via the sidebar.

---

## Performance

Benchmarked on 100,000-candidate organizer dataset, Apple M-series CPU (8 cores, 16 GB RAM):

| Run type | Time |
|---|---|
| First run (encoding 100K profiles + ranking) | ~848 seconds |
| Cached run (load cache + rank) | ~60 seconds |
| Ranking step only (FAISS search + scoring + export) | < 60 seconds |
| Reasoning-only regeneration (`scripts/regen_reasoning.py`) | ~4 seconds |

Per the submission spec §3, pre-computation may exceed the 5-minute window. Only the ranking step must complete within it — which it does on cached runs. Use `--no-cache` to force re-encoding while still saving the result for the next run.

---

## Using a custom job description

**From the dashboard:**
1. Open the sidebar → **Job Description** → **Paste / Upload JD** tab
2. Paste any job description or upload a `.txt` / `.md` file
3. Click **Parse & Use This JD**
4. The dashboard shows the extracted role, seniority, experience range, skills, and locations
5. Upload candidates and rank — the pipeline scores against the new JD

**From the CLI:**
```python
from backend.jd_parser import parse_jd_text, set_active_jd

with open("my_jd.txt") as f:
    parsed = parse_jd_text(f.read())

set_active_jd(parsed)
# Now run rank.py — it will use the custom JD
```

The parser extracts skills from a vocabulary of 80+ tech terms, infers title tokens from the role type, and generates role-appropriate disqualifying domains automatically.

---

## Resume upload (PDF / DOCX / TXT)

SignalRank can rank candidates directly from raw resumes — no structured JSONL required.

**ZIP upload (dashboard):**
1. Prepare a `.zip` containing resume files (PDF, DOCX, or TXT — one file per candidate)
2. Open the sidebar → **Candidates** → **ZIP of Resumes** tab
3. Upload the ZIP and click **Parse & Rank Resumes**

**Google Drive (dashboard):**
1. Share a Drive folder as **Anyone with the link → Viewer**
2. Open the sidebar → **Candidates** → **Google Drive** tab
3. Paste the folder link and click **Download & Rank**

The resume parser extracts name, current title, career history, skills, years of experience, and education using regex and vocabulary matching. Behavioral signals are set to neutral defaults (resumes do not contain availability data).

---

## Repository structure

```
signalrank-ai/
├── rank.py                       # Main CLI entry point
├── requirements.txt
├── config/
│   └── scoring.yaml              # All scoring parameters — weights, thresholds, penalties
├── backend/
│   ├── constants.py              # REFERENCE_DATE — single source of truth for date math
│   ├── config_loader.py          # Config singleton — imported by all modules
│   ├── candidate_parser.py       # CandidateProfile dataclass + JSONL loader
│   ├── jd_parser.py              # JobProfile, parse_jd_text(), dynamic JD registry
│   ├── retrieval.py              # SemanticRetriever: FAISS + TF-IDF + RRF + cache
│   ├── scorer.py                 # 7-component hybrid scoring engine
│   ├── honeypot.py               # Honeypot detection (7 checks, thresholds in config)
│   ├── explainer.py              # Recruiter-facing reasoning generation (5 narrative styles)
│   ├── exporter.py               # CSV + JSON output (spec-compliant)
│   ├── resume_parser.py          # PDF/DOCX/TXT resume → structured candidate dict
│   └── drive_downloader.py       # Google Drive folder → local resume files
├── app/
│   └── streamlit_app.py          # Recruiter dashboard UI
├── .streamlit/
│   └── config.toml               # Forces light mode, sets brand colors
├── evaluation/
│   └── eval.py                   # Evaluation framework: sanity, distribution, baseline
├── scripts/
│   ├── validate_submission.py    # Organizer-provided CSV validator
│   ├── regen_reasoning.py        # Regenerate reasoning in ~4s without re-encoding
│   └── generate_test_data.py     # Synthetic candidate generator for testing
├── tests/
│   ├── test_config.py
│   ├── test_candidate_parser.py
│   ├── test_retrieval.py
│   ├── test_scorer.py
│   └── test_pipeline.py
├── data/
│   └── raw/
│       ├── candidate_schema.json # Organizer candidate record schema
│       └── job_description.md    # Target JD (Senior AI Engineer, Redrob)
│       # candidates.jsonl → place here locally (not committed, 465 MB)
├── docs/
│   ├── architecture.md
│   ├── deployment.md
│   ├── evaluation_report.md
│   └── user_guide.md
└── outputs/
    ├── submission.csv            # Submit this
    ├── debug.json                # Full JSON with score breakdowns (loaded by dashboard)
    └── eval_report.json          # Structured evaluation report
```

---

## Running tests

```bash
# Full suite
python -m pytest tests/ -v

# Individual suites
python -m pytest tests/test_config.py -v           # Config loader (10 tests)
python -m pytest tests/test_candidate_parser.py -v  # Candidate normalization (15 tests)
python -m pytest tests/test_retrieval.py -v         # FAISS + RRF + cache (17 tests)
python -m pytest tests/test_scorer.py -v            # Scoring engine (9 tests)
python -m pytest tests/test_pipeline.py -v          # End-to-end (5 tests)
```

Current status: **56/56 tests pass.**

---

## Evaluation

```bash
python evaluation/eval.py \
  --results outputs/debug.json \
  --candidates data/raw/candidates.jsonl \
  --json outputs/eval_report.json
```

Produces:
- Format and spec compliance checks
- Score distribution with percentiles and bands
- Top-10, top-25, top-100 candidate profile breakdowns
- Systematic error detection (honeypots, wrong-domain high scores)
- Baseline comparison against a simple keyword-count model
- Ranking stability verification

---

## Configuration

All scoring parameters are in `config/scoring.yaml`. No code changes needed to tune the pipeline.

```yaml
scoring:
  component_weights:
    title_role: 0.25         # increase if keyword stuffers rank too high
    skill_match: 0.20
    production_evidence: 0.15
    behavioral: 0.15
    experience_fit: 0.10
    domain_fit: 0.10
    location: 0.05

semantic:
  embedding:
    rule_blend: 0.75         # 75% rule-based, 25% semantic
    semantic_blend: 0.25
    top_k: 3000              # candidates retrieved per method before fusion

retrieval:
  rrf_k: 60                  # RRF fusion constant
```

---

## Design decisions

**Title alignment is the decisive signal (25% weight).** An HR Manager with ten ML keywords in their skills section scores ~0.05 on `title_role`, collapsing their total score below 0.25. This is intentional — it is the primary defense against keyword stuffing, which is the dominant failure mode in ATS systems.

**Two-stage retrieval decouples recall from latency.** FAISS retrieves top-3000 in milliseconds after one-time encoding. Rule-based scoring then operates on this pool, not all N candidates. Re-encoding is only needed when the candidate set changes.

**RRF fusion improves recall without tuning.** Candidates strong in semantic similarity but weak in lexical match (or vice versa) are captured by combining both ranked lists. RRF is parameter-light and does not require score normalization.

**Behavioral signals are availability-weighted, not tiebreakers.** A candidate who has not responded to recruiters in six months is effectively unavailable, regardless of skill depth. The behavioral component penalizes this directly.

**Explainability is grounded in extracted evidence.** Reasoning paragraphs lead with the candidate's current role and company (unique per candidate), then cite production evidence, then highlight skill gaps or strengths. Vague phrases like "strong fit" without evidence are not generated.

**All thresholds are externalized.** Every numeric constant — from FAISS `top_k` to penalty fractions to notice period cutoffs — lives in `config/scoring.yaml`. The system is fully tunable without code changes.

---


## Dependencies

| Package | Purpose |
|---|---|
| `sentence-transformers` | Candidate and JD embedding (all-MiniLM-L6-v2, 22 MB, runs offline) |
| `faiss-cpu` | Approximate nearest neighbor search over 100K candidate vectors |
| `scikit-learn` | TF-IDF vectorizer for lexical retrieval |
| `streamlit` | Recruiter dashboard UI |
| `pdfplumber` | PDF text extraction for resume upload |
| `python-docx` | DOCX text extraction for resume upload |
| `gdown` | Google Drive folder download (public links, no OAuth required) |
| `PyYAML` | Config loading |
| `pandas`, `plotly` | Evaluation charts and data handling |

Zero network calls are made during the ranking pipeline. The only model used is `all-MiniLM-L6-v2`, loaded from the local HuggingFace cache.
