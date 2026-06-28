# SignalRank AI — Deployment Guide

## Requirements

- Python 3.9+ (tested on 3.9.6)
- CPU only — no GPU required
- ~2 GB RAM during encoding (sentence-transformers model + candidate embeddings)
- ~500 MB disk for model cache + embedding cache

### Python dependencies

```
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
sentence-transformers>=2.3.0
faiss-cpu>=1.7.4
PyYAML>=6.0
tqdm>=4.65.0
streamlit>=1.28.0
plotly>=5.18.0
python-dateutil>=2.8.2
```

---

## Setup

```bash
# Clone the repository
git clone <repo-url> signalrank-ai
cd signalrank-ai

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### Model download

`sentence-transformers/all-MiniLM-L6-v2` (~22 MB) downloads automatically on first run via Hugging Face Hub. It is cached locally at `~/.cache/huggingface/hub/`.

For **air-gapped environments** (no network access during ranking):

```bash
# Pre-download the model before going offline
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

The model is then available in the local cache. The ranking pipeline makes zero network calls.

---

## Running the pipeline

### Basic run

```bash
python rank.py \
  --candidates ./data/raw/candidates.jsonl \
  --out ./outputs/submission.csv \
  --json ./outputs/debug.json
```

### Force cache rebuild

```bash
python rank.py \
  --candidates ./data/raw/candidates.jsonl \
  --out ./outputs/submission.csv \
  --no-cache
```

### Validate submission

```bash
python scripts/validate_submission.py outputs/submission.csv
# Expected output: "Submission is valid."
```

---

## Streamlit dashboard

```bash
streamlit run app/streamlit_app.py
```

Opens at `http://localhost:8501`. The dashboard auto-loads `outputs/debug.json` if it exists.

### Run with pre-generated results

1. Run `rank.py --json outputs/debug.json` first
2. Open the dashboard — results load automatically

### Upload and rank via UI

1. Open the dashboard
2. Upload `candidates.jsonl` in the sidebar
3. Click **Rank Candidates** — pipeline runs in-browser with progress indicators

---

## Tuning scoring parameters

All numeric constants live in `config/scoring.yaml`. No code changes needed.

### Common tuning scenarios

**Keyword stuffers still appearing in top-50:**
```yaml
scoring:
  component_weights:
    title_role: 0.30    # increase from 0.25
    skill_match: 0.15   # reduce to compensate
```

**Too many inactive candidates in top-25:**
```yaml
scoring:
  component_weights:
    behavioral: 0.20    # increase from 0.15
    domain_fit: 0.05    # reduce to compensate
```

**RRF retrieval pool too small (missing obvious candidates):**
```yaml
semantic:
  rrf:
    top_embedding_k: 5000   # increase from 3000
    top_tfidf_k: 5000
  embedding:
    faiss:
      top_k: 2000           # increase pool size after RRF
```

**Large dataset (>50K candidates) too slow:**
```yaml
semantic:
  embedding:
    faiss:
      index_type: "ivf"     # switch from flat to approximate
      nlist: 300            # ~sqrt(N) for 90K candidates
      nprobe: 20
```

After any change, re-run the pipeline and evaluation:

```bash
python rank.py --candidates ./data/raw/candidates.jsonl --out ./outputs/submission.csv --json ./outputs/debug.json
python evaluation/eval.py --results outputs/debug.json --candidates data/raw/candidates.jsonl
```

---

## Running tests

```bash
# Full test suite
python -m pytest tests/ -v

# Fast unit tests only (no model loading)
python -m pytest tests/test_config.py tests/test_candidate_parser.py tests/test_scorer.py -v

# Integration tests (loads sentence-transformers model, ~60s)
python -m pytest tests/test_pipeline.py tests/test_retrieval.py -v
```

---

## Generating synthetic test data

If the organizer dataset is not available:

```bash
python scripts/generate_test_data.py --n 2000 --out data/raw/candidates.jsonl
```

The generator creates a realistic archetype mix:
- True positive ML engineers (various titles, skill depths, locations)
- Keyword stuffers (HR/Sales/Design with ML skill keywords)
- Consulting-only engineers (TCS/Infosys/Wipro career paths)
- Inactive candidates (last active 6–18 months ago)
- CV/speech specialists (computer vision, robotics, no NLP)
- Honeypots (~5% — overlapping timelines, all-maxed signals)

---

## Submission checklist

Before submitting:

- [ ] `outputs/submission.csv` exists and validates (`python scripts/validate_submission.py`)
- [ ] Exactly 100 rows, ranks 1-100, scores non-increasing
- [ ] All candidate IDs present in `candidates.jsonl`
- [ ] `submission_metadata.yaml` updated with team name and submission details
- [ ] No network calls made during ranking (confirmed by `--no-cache` run on clean machine)
- [ ] Runtime ≤ 5 minutes on target hardware
- [ ] RAM usage ≤ 16 GB during ranking

---

## Environment notes

| Constraint | Our implementation | Status |
|------------|-------------------|--------|
| CPU only | No CUDA, no MPS during submission | ✓ |
| No network during ranking | Model pre-cached; zero HTTP calls | ✓ |
| ≤5 min wall-clock | ~19s cold / ~6s cached (2K candidates) | ✓ |
| ≤16 GB RAM | ~2 GB peak (model + 100K embeddings) | ✓ |
| ≤5 GB disk | Model (~22MB) + cache (~300MB for 100K) | ✓ |
| UTF-8 output | Explicit encoding in exporter.py | ✓ |
| Deterministic | Fixed seed; same input → same output | ✓ |
