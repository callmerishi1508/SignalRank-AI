# IMPLEMENTATION PLAN — SignalRank AI
**Generated:** 2026-06-26 | **Revised:** 2026-06-26  
**Status:** FINAL (approved with refinements) — implementation approved to begin

---

## Current Implementation Status

The original pipeline (Phase 1–4 in the previous plan) is **complete and passing all tests**. The approved refinements require targeted changes to:

1. Create `config/scoring.yaml` and a config loader — *already created as design artifact*
2. Create `backend/candidate_parser.py` (new Candidate Understanding module)
3. Create `backend/retrieval.py` (new adaptive Semantic Retrieval module)
4. Refactor `backend/scorer.py` to read all constants from config
5. Refactor `backend/honeypot.py` to read thresholds from config
6. Refactor `backend/jd_parser.py` to read experience ranges and weights from config
7. Fix Streamlit upload bug
8. Add `sentence-transformers` to `requirements.txt`
9. Add tests for new modules

All existing functionality (explainability, export, validation, evaluation) is preserved unchanged.

---

## Module Dependency Graph (Updated)

```
config/scoring.yaml
       │
       ├──────────────────────────────────────┐
       │                                      │
       ▼                                      ▼
backend/jd_parser.py            backend/candidate_parser.py
(JobProfile — reads exp range,  (CandidateProfile — normalized
 weights from config)            candidate, derived signals)
       │                                      │
       └───────────────────┬──────────────────┘
                           │
                           ▼
                  backend/retrieval.py
                  (reads threshold + model from config)
                  → float[] similarity scores
                           │
                           ▼
                  backend/scorer.py
                  (reads ALL weights, thresholds,
                   penalties from config)
                           │
                           ▼
                  backend/explainer.py    backend/exporter.py
                  (unchanged interface)   (unchanged interface)
                           │
                           ▼
                       rank.py
                  (assembles all modules)
                           │
                  ┌────────┴────────┐
                  ▼                 ▼
         app/streamlit_app.py   evaluation/eval.py
         (fixed upload bug)     (unchanged)

tests/
  test_scorer.py         (updated: inject config in tests)
  test_pipeline.py       (updated: uses new module structure)
  test_retrieval.py      (new: embedding vs TF-IDF fallback)
  test_candidate_parser.py (new: normalization unit tests)
  test_config.py         (new: config loading and validation)
```

**Build order constraint**: `config loader` → `jd_parser.py` + `candidate_parser.py` → `retrieval.py` → `scorer.py` → `explainer.py` + `exporter.py` → `rank.py` → `streamlit_app.py` + `eval.py`

---

## Phase 0 — Design Artifacts (COMPLETE ✓)

- `DATASET_ANALYSIS.md` — complete
- `ARCHITECTURE_DECISION.md` — updated with refinements
- `IMPLEMENTATION_PLAN.md` — this document
- `config/scoring.yaml` — created with all parameters

---

## Phase 1 — Config Infrastructure

### What to build

**`backend/config_loader.py`** (new)

A `ScoringConfig` dataclass that:
- Loads `config/scoring.yaml` at startup
- Validates all required keys are present
- Provides typed accessors (no raw dict access in other modules)
- Has a `from_defaults()` classmethod for testing without file I/O

```python
# Interface
@dataclass
class ScoringConfig:
    component_weights: Dict[str, float]
    behavioral_sub_weights: Dict[str, float]
    semantic: SemanticConfig
    skill: SkillConfig
    penalties: PenaltyConfig
    honeypot: HoneypotConfig
    # ... all sections

def load_config(path: str = "config/scoring.yaml") -> ScoringConfig:
    ...
```

Config is loaded once in `rank.py` and passed down to every module that needs it. No module reads the YAML file directly.

### Validation checkpoint

```bash
python -c "from backend.config_loader import load_config; c = load_config(); print('Config loaded:', c.component_weights)"
```
Expected: prints the weights dict, no errors.

### Tests to write

- `tests/test_config.py`:
  - Config loads without error
  - Component weights sum to 1.0
  - Behavioral sub-weights sum to 1.0
  - All required keys present
  - Invalid YAML raises clear error
  - `from_defaults()` matches scoring.yaml values

---

## Phase 2 — Candidate Understanding Module

### What to build

**`backend/candidate_parser.py`** (new)

A `CandidateProfile` dataclass and `parse_candidate(raw_dict, config)` function.

This module does all normalization once, before any scoring logic touches the data.

```python
@dataclass
class CandidateProfile:
    candidate_id: str
    current_title: str                  # normalized
    headline: str
    summary: str
    location: str
    country: str
    years_of_experience: float
    career: List[CareerEntry]           # typed, dates parsed
    skills: List[SkillEntry]            # typed, proficiency normalized
    education: List[EducationEntry]     # typed
    signals: RedroBSignals             # typed behavioral signals
    certifications: List[str]

    # Derived signals (computed once here, not recomputed in scorer)
    days_since_active: int
    consulting_career_fraction: float
    ml_career_fraction: float
    total_career_months: int
    is_consulting_only: bool            # fraction > config threshold
    has_cv_domain_skills: bool
    has_nlp_skills: bool
    profile_text: str                   # flat text for semantic retrieval
```

The scorer and retrieval module receive `CandidateProfile` objects, not raw dicts. This:
- Eliminates repeated `.get("career_history", [])` calls with silent defaults
- Makes malformed-record handling explicit and centralized
- Makes `profile_text` construction (for retrieval) a one-time operation

### Validation checkpoint

```bash
python -c "
import json
from backend.config_loader import load_config
from backend.candidate_parser import parse_candidate
config = load_config()
with open('data/raw/candidates.jsonl') as f:
    raw = json.loads(f.readline())
c = parse_candidate(raw, config)
print(c.candidate_id, c.current_title, c.consulting_career_fraction)
"
```

### Tests to write

- `tests/test_candidate_parser.py`:
  - Required fields missing → raises ValueError with candidate_id in message
  - All dates parse correctly (including null end_date)
  - `consulting_career_fraction` correct for known consulting career
  - `days_since_active` correct for known date
  - `profile_text` non-empty for any valid candidate

---

## Phase 3 — Semantic Retrieval Module

### What to build

**`backend/retrieval.py`** (new)

A `SemanticRetriever` class implementing the two-stage retrieve → rerank interface.

**Interface:**

```python
@dataclass
class RetrievalResult:
    pool: List[CandidateProfile]     # candidates in reranking pool (top_k + safety net)
    similarities: Dict[str, float]   # candidate_id → cosine similarity score
    backend_used: str                # "embedding_faiss" or "tfidf"
    rule_blend: float                # blend weight for rule-based score
    semantic_blend: float            # blend weight for semantic similarity

class SemanticRetriever:
    def __init__(self, config: ScoringConfig): ...

    def retrieve(
        self,
        all_profiles: List[CandidateProfile],
        jd: JobProfile,
        jd_text: str,
        no_cache: bool = False,
    ) -> RetrievalResult:
        """
        Primary path: encode candidates, build FAISS index, query with JD,
        apply title safety net. Returns pool + per-candidate similarities.

        Fallback path: TF-IDF cosine over all candidates (no top-K).
        Fallback activates when config.semantic.backend == "tfidf"
        or when faiss-cpu / sentence-transformers are not installed.
        Logs which path was taken.
        """
```

The scorer receives a `RetrievalResult` and iterates only over `result.pool` — it has no knowledge of how candidates were selected or similarities computed.

**Primary path — FAISS embedding:**

```python
def _retrieve_embedding_faiss(
    self, profiles, jd, jd_text, no_cache
) -> RetrievalResult:
    # 1. Load or build embedding cache
    cache_dir = Path(self.config.semantic.embedding.cache.path)
    if not no_cache and self._cache_valid(cache_dir):
        embeddings = np.load(cache_dir / "embeddings.npy")
        ids = np.load(cache_dir / "ids.npy", allow_pickle=True)
    else:
        model = SentenceTransformer(self.config.semantic.embedding.model_name)
        texts = [p.profile_text for p in profiles]
        embeddings = model.encode(
            texts,
            batch_size=self.config.semantic.embedding.batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
        )                                     # shape (N, 384)
        ids = np.array([p.candidate_id for p in profiles])
        cache_dir.mkdir(parents=True, exist_ok=True)
        np.save(cache_dir / "embeddings.npy", embeddings)
        np.save(cache_dir / "ids.npy", ids)
        (cache_dir / "mtime").write_text(str(os.path.getmtime(CANDIDATES_FILE)))

    # 2. Build FAISS index
    faiss_cfg = self.config.semantic.embedding.faiss
    if faiss_cfg.index_type == "flat":
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)
    else:  # "ivf"
        quantizer = faiss.IndexFlatIP(embeddings.shape[1])
        index = faiss.IndexIVFFlat(
            quantizer, embeddings.shape[1],
            faiss_cfg.nlist, faiss.METRIC_INNER_PRODUCT
        )
        index.train(embeddings)
        index.add(embeddings)
        index.nprobe = faiss_cfg.nprobe

    # 3. Encode JD and search
    model = SentenceTransformer(self.config.semantic.embedding.model_name)
    jd_vec = model.encode([jd_text], normalize_embeddings=True)
    top_k = faiss_cfg.top_k
    sims, indices = index.search(jd_vec, min(top_k, len(profiles)))
    # sims shape: (1, top_k),  indices shape: (1, top_k)

    pool_ids = {ids[i]: float(sims[0][j]) for j, i in enumerate(indices[0]) if i >= 0}

    # 4. Title safety net
    if faiss_cfg.title_safety_net:
        profiles_by_id = {p.candidate_id: p for p in profiles}
        for p in profiles:
            if _has_tier1_title(p, jd) and p.candidate_id not in pool_ids:
                pool_ids[p.candidate_id] = 0.0  # no semantic credit; eligible for rule reranking

    pool = [profiles_by_id[cid] for cid in pool_ids]
    cfg = self.config.semantic.embedding
    return RetrievalResult(
        pool=pool,
        similarities=pool_ids,
        backend_used="embedding_faiss",
        rule_blend=cfg.rule_blend,
        semantic_blend=cfg.semantic_blend,
    )
```

**Fallback path — TF-IDF:**

```python
def _retrieve_tfidf(self, profiles, jd_text) -> RetrievalResult:
    # Scores ALL candidates — no top-K selection
    cfg = self.config.semantic.tfidf
    vectorizer = TfidfVectorizer(
        ngram_range=tuple(cfg.ngram_range),
        max_features=cfg.max_features,
        min_df=cfg.min_df,
        sublinear_tf=cfg.sublinear_tf,
    )
    texts = [p.profile_text for p in profiles]
    all_texts = [jd_text] + texts
    vectorizer.fit(all_texts)
    vecs = vectorizer.transform(all_texts)
    sims = cosine_similarity(vecs[0], vecs[1:])[0]

    return RetrievalResult(
        pool=profiles,
        similarities={p.candidate_id: float(s) for p, s in zip(profiles, sims)},
        backend_used="tfidf",
        rule_blend=cfg.rule_blend,
        semantic_blend=cfg.semantic_blend,
    )
```

**Fallback activation logic:**

```python
def retrieve(self, all_profiles, jd, jd_text, no_cache=False) -> RetrievalResult:
    if self.config.semantic.backend == "tfidf":
        return self._retrieve_tfidf(all_profiles, jd_text)
    try:
        import faiss
        from sentence_transformers import SentenceTransformer
        return self._retrieve_embedding_faiss(all_profiles, jd, jd_text, no_cache)
    except ImportError as e:
        logger.warning(f"Falling back to TF-IDF: {e}")
        return self._retrieve_tfidf(all_profiles, jd_text)
```

**Cache invalidation:**

```python
def _cache_valid(self, cache_dir: Path) -> bool:
    mtime_file = cache_dir / "mtime"
    embeddings_file = cache_dir / "embeddings.npy"
    if not (mtime_file.exists() and embeddings_file.exists()):
        return False
    stored_mtime = float(mtime_file.read_text())
    current_mtime = os.path.getmtime(CANDIDATES_FILE)
    return abs(stored_mtime - current_mtime) < 1.0  # 1-second tolerance
```

### Validation checkpoint

```bash
python -c "
from backend.config_loader import load_config
from backend.candidate_parser import parse_candidate
from backend.retrieval import SemanticRetriever
from backend.jd_parser import JD_PROFILE, JD_TEXT_FOR_EMBEDDING
import json

config = load_config()
profiles = []
with open('data/raw/candidates.jsonl') as f:
    for i, line in enumerate(f):
        if i >= 200: break
        profiles.append(parse_candidate(json.loads(line), config))

retriever = SemanticRetriever(config)
result = retriever.retrieve(profiles, JD_PROFILE, JD_TEXT_FOR_EMBEDDING)
print('Backend:', result.backend_used)
print('Pool size:', len(result.pool))
print('Sim range:', min(result.similarities.values()), max(result.similarities.values()))
print('Rule/semantic blend:', result.rule_blend, result.semantic_blend)
"
```
Expected: backend_used=embedding_faiss (or tfidf fallback), pool size ≤ 200, all similarities in [0, 1].

### Tests to write

`tests/test_retrieval.py`:
- **FAISS backend produces valid pool:** pool size ≤ top_k + safety_net candidates; all in [0, 1]
- **Title safety net works:** a tier-1-title candidate excluded from FAISS top-K is present in pool with similarity=0.0
- **TF-IDF backend includes all candidates:** pool size = N regardless of dataset size
- **Fallback activates on config override:** `backend: "tfidf"` in config → TF-IDF regardless of imports
- **Fallback activates on ImportError:** mocked ImportError for faiss → TF-IDF used; no exception raised
- **Blend ratios correct per backend:** FAISS → 0.75/0.25; TF-IDF → 0.85/0.15
- **Cache is written on first call:** embedding_cache/ directory and files exist after retrieval
- **Cache is loaded on second call:** retrieval completes without model encoding (verify via mocked encode)
- **Cache invalidated when mtime changes:** stale cache → fresh encode
- **ML candidate similarity > HR candidate similarity:** for same FAISS backend
- **Pool is deterministic:** same input → identical pool and similarities across runs

---

## Phase 4 — Scorer Refactoring

### What to change

`backend/scorer.py` currently hardcodes all numeric constants. The refactored version:

1. Accepts `config: ScoringConfig` as a parameter to `score_candidates_bulk()` and `score_candidate()`
2. Reads all thresholds, weights, breakpoints from `config.*`
3. Accepts pre-computed `similarity_score: float` per candidate (produced by retrieval module) instead of calling TF-IDF internally
4. Uses `CandidateProfile` objects instead of raw dicts

**Interface change:**

```python
# Old
def score_candidates_bulk(candidates: List[Dict], jd: JobProfile) -> List[Dict]:
    # fits TF-IDF internally, hardcodes blend ratios

# New
def score_candidates_bulk(
    profiles: List[CandidateProfile],
    jd: JobProfile,
    similarities: np.ndarray,
    rule_blend: float,
    semantic_blend: float,
    config: ScoringConfig,
) -> List[Dict]:
    # no TF-IDF, no hardcoded constants
```

**What does NOT change:**
- The 7-component structure
- The penalty logic
- The honeypot integration
- Output dict structure (so `explainer.py`, `exporter.py`, `streamlit_app.py` need no changes)

### Validation checkpoint

```bash
python tests/test_scorer.py
```
All 9 existing unit tests must still pass after refactoring.

Additionally:
- Verify same score output for a fixed candidate with fixed config (determinism)
- Verify score changes when a weight is changed in config (sensitivity)

### Tests to update

- `tests/test_scorer.py`: inject `ScoringConfig` from `from_defaults()` in all tests
- No new tests required here; existing 9 tests cover the logic

---

## Phase 5 — Honeypot Refactoring

### What to change

`backend/honeypot.py` currently hardcodes detection thresholds. Refactor to accept `config: ScoringConfig.honeypot` and read all thresholds from it.

**What does NOT change:**
- The 7-check structure
- Return type `(bool, List[str])`
- Integration with `rank.py`

### Validation checkpoint

```bash
python tests/test_scorer.py  # includes test_honeypot_detection_overlapping_jobs
```
All existing honeypot tests must still pass.

---

## Phase 6 — Streamlit Upload Fix

### What to fix

`app/streamlit_app.py` has a JSON parse error on file upload. The uploaded file bytes are being iterated as a BytesIO object (which splits on raw bytes, not JSON lines).

**Fix:**

```python
# In run_pipeline_on_upload():

# BROKEN (iterates BytesIO line by line — splits on raw bytes)
with open(tmp_path, 'wb') as f:
    for chunk in uploaded_file:
        f.write(chunk)

# FIXED
content = uploaded_file.read()
if isinstance(content, bytes):
    content = content.decode('utf-8')

# Validate at least one line is JSON before writing
try:
    first_line = content.strip().split('\n')[0]
    json.loads(first_line)
except (json.JSONDecodeError, IndexError) as e:
    st.error(f"File does not appear to be valid JSONL: {e}")
    return

with open(tmp_path, 'w', encoding='utf-8') as f:
    f.write(content)
```

Also add a user-facing error message when any pipeline step fails (replace raw exception with `st.error()`).

### Validation checkpoint

1. Start `streamlit run app/streamlit_app.py`
2. Upload `data/raw/candidates.jsonl` via the UI
3. Click "Run Pipeline"
4. Confirm: Ranked Shortlist tab populates with 100 candidates, no error in browser

---

## Phase 7 — Requirements and Dependencies

### Update `requirements.txt`

Add:
```
sentence-transformers>=2.3.0
faiss-cpu>=1.7.4
PyYAML>=6.0
```

`sentence-transformers` requires `torch` (CPU-only). Torch CPU wheel is ~150MB.  
`faiss-cpu` is ~50MB. Total new disk cost is ~200MB, well within the ≤5GB constraint.

### Test the install

```bash
pip install -r requirements.txt
python -c "from sentence_transformers import SentenceTransformer; print('sentence-transformers OK')"
python -c "import faiss; print('faiss OK, version', faiss.__version__)"
python -c "import yaml; print('PyYAML OK')"
```

---

## Phase 8 — Integration Testing (Update Existing Tests)

### Update `tests/test_pipeline.py`

The 5 existing integration tests test the full pipeline end-to-end. After refactoring, they should:
- Still use `python rank.py` as the entry point (black-box, not internal APIs)
- Confirm that output format, row count, monotonicity are unchanged
- Confirm that true positives remain in top 10
- Confirm that honeypots are not in top 10

No changes to test assertions — only to any internal scaffolding that creates test candidates.

### New `tests/test_retrieval.py`

See Phase 3 above for test list.

### New `tests/test_candidate_parser.py`

See Phase 2 above for test list.

### New `tests/test_config.py`

See Phase 1 above for test list.

---

## Ordered Implementation Sequence

Work in this exact order. Each step must pass its validation checkpoint before proceeding.

| Step | Task | File(s) | Checkpoint |
|------|------|---------|------------|
| 1 | Update requirements | `requirements.txt` | `pip install -r requirements.txt` including faiss-cpu succeeds |
| 2 | Build config loader | `backend/config_loader.py` | Config loads, weights sum to 1.0, FAISS config accessible |
| 3 | Build candidate parser | `backend/candidate_parser.py` | Parse one candidate; `profile_text` non-empty |
| 4 | Build retrieval module — FAISS primary | `backend/retrieval.py` | FAISS path: pool ≤ top_k+safety_net, sims in [0,1], cache written |
| 5 | Build retrieval module — TF-IDF fallback | `backend/retrieval.py` | TF-IDF path: pool = all N, sims in [0,1]; fallback activates on ImportError |
| 6 | Refactor scorer | `backend/scorer.py` | Accepts `RetrievalResult`; 9 unit tests still pass |
| 7 | Refactor honeypot | `backend/honeypot.py` | Reads thresholds from config; existing honeypot test passes |
| 8 | Refactor jd_parser | `backend/jd_parser.py` | Weights and experience ranges read from config |
| 9 | Update rank.py | `rank.py` | Full two-stage pipeline runs; logs backend used |
| 10 | Fix Streamlit upload | `app/streamlit_app.py` | File upload populates UI without error |
| 11 | Write new tests | `tests/test_*.py` | All new + existing tests pass |
| 12 | Full end-to-end validation | all | All checkpoints below pass |
| 13 | Deploy to Streamlit Cloud | — | sandbox_link obtained |
| 14 | Tune if needed | `config/scoring.yaml` | Post-real-dataset scoring analysis |
| 15 | Build pitch deck | `docs/` | Stage 5 defend-your-work preparation |

---

## Validation Checkpoints — Required Before Submission

| Checkpoint | Command | Required Result |
|------------|---------|-----------------|
| Dependencies install | `pip install -r requirements.txt` | No errors; faiss-cpu imports cleanly |
| Config loads | `python -c "from backend.config_loader import load_config; load_config()"` | No errors; FAISS config present |
| Config test | `python tests/test_config.py` | All pass |
| Candidate parser test | `python tests/test_candidate_parser.py` | All pass |
| Retrieval test (FAISS) | `python tests/test_retrieval.py` | FAISS tests pass; cache written to outputs/embedding_cache/ |
| Retrieval test (TF-IDF) | `python tests/test_retrieval.py` | TF-IDF fallback tests pass |
| Scorer unit tests | `python tests/test_scorer.py` | 9/9 pass |
| Integration tests | `python tests/test_pipeline.py` | 5/5 pass |
| FAISS pool check | Inspect rank.py output | Logs "backend: embedding_faiss, pool_size: X" |
| Title safety net check | Inject tier-1 candidate with zero semantic overlap | Candidate appears in pool despite low FAISS rank |
| Cache check | Run pipeline twice; compare timing | Second run skips encoding (significantly faster) |
| Pipeline runs | `python rank.py --candidates data/raw/candidates.jsonl --out outputs/submission.csv` | Exit 0 |
| Output is valid | `python scripts/validate_submission.py outputs/submission.csv` | "VALID" |
| Performance (first run) | Time on 2000-candidate dataset | < 60s total |
| Performance (cache hit) | Time on 2000-candidate dataset (second run) | < 5s total |
| Honeypot rate | Inspect debug.json top-100 | 0 honeypot-flagged candidates |
| Streamlit loads | `streamlit run app/streamlit_app.py` | No crash, loads debug.json |
| Streamlit upload | Upload candidates.jsonl via UI | Pipeline runs; table populates without error |

---

## Test Matrix

| Module | Test file | Tests | Run command |
|--------|-----------|-------|-------------|
| Config loader | `test_config.py` | ~6 | `python tests/test_config.py` |
| Candidate parser | `test_candidate_parser.py` | ~5 | `python tests/test_candidate_parser.py` |
| Retrieval — FAISS primary | `test_retrieval.py` | ~7 | `python tests/test_retrieval.py` |
| Retrieval — TF-IDF fallback | `test_retrieval.py` | ~4 | (included above) |
| Scorer + honeypot | `test_scorer.py` | 9 (existing) | `python tests/test_scorer.py` |
| Full pipeline | `test_pipeline.py` | 5 (existing) | `python tests/test_pipeline.py` |
| CSV format | `validate_submission.py` | Format check | `python scripts/validate_submission.py outputs/submission.csv` |

---

## Configuration Tuning Guidance (Between Submissions)

The 3-submission cap means each submission must be deliberate. Use this playbook:

**Submission 1:** Use current weights. Baseline the composite score.

**If NDCG@10 is low (< 0.70):**
- Increase `title_role` weight (try 0.30) and reduce `location` (to 0.00)
- Increase `production_evidence` weight (try 0.20) and reduce `domain_fit` (to 0.05)
- Check if any wrong-domain candidates appear in top 10 (if yes: increase wrong_domain penalty)

**If NDCG@50 is low but NDCG@10 is good:**
- The top-100 ordering is weak; within-shortlist discrimination is insufficient
- Try increasing semantic_blend (to 0.30 for embedding backend) to spread scores further
- Try sharpening the experience curve (reduce `underexperienced_ramp_base`)

**If MAP is low:**
- Precision across all relevance levels is weak; too many non-relevant candidates in the top 100
- Increase consulting_only penalty threshold (from 0.85 to 0.75)
- Add or strengthen the `behaviorally_unavailable` penalty

All changes require only editing `config/scoring.yaml` — no code changes — then re-running the pipeline and validator.
