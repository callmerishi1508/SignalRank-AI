# ARCHITECTURE DECISION — SignalRank AI
**Generated:** 2026-06-26 | **Revised:** 2026-06-26  
**Status:** FINAL (approved with refinements) — do not alter without explicit user approval

---

## 1. Final Architecture (Fixed)

The system runs as a **two-stage pipeline**: semantic retrieval produces a candidate pool, then rule-based reranking produces the final ranking. Honeypot detection runs across all candidates before retrieval.

```
config/scoring.yaml
       │ (all weights, thresholds, penalties, FAISS config)
       ▼
candidates.jsonl
       │
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                           rank.py (CLI)                               │
│  1. Load config  2. Parse all candidates  3. Detect honeypots (all)  │
│  4. Encode + FAISS retrieve  5. Rerank pool  6. Explain  7. Export   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────┐
         │                         │                     │
         ▼                         ▼                     ▼
backend/jd_parser.py   backend/candidate_parser.py  backend/honeypot.py
(Job Understanding)    (Candidate Understanding)    (all N candidates,
                                                    thresholds from config)
         │                         │
         └───────────┬─────────────┘
                     │
                     ▼
          backend/retrieval.py           outputs/embedding_cache/
          ┌──────────────────────────────────────────────────┐
          │  PRIMARY: Embedding + FAISS                       │
          │                                                   │
          │  1. Encode all N candidates (batch, CPU)          │
          │     → load from cache if available                │
          │  2. Encode JD text                                │
          │  3. Build FAISS index (IndexFlatIP or IndexIVFFlat│
          │  4. Search: JD → top_k=1500 candidates + sims     │
          │  5. Title safety net: add any tier-1-title        │
          │     candidates not already in top_k pool          │
          │  → candidate pool (≤1500 + safety net)            │
          │                                                   │
          │  FALLBACK: TF-IDF (no top_k — all candidates)     │
          │  Activated by config or missing dependencies       │
          └──────────────────────────┬───────────────────────┘
                                     │ (pool, sim_scores)
                                     ▼
                          backend/scorer.py
                          (Hybrid Reranking — pool only)
                          ┌───────────────────────────────┐
                          │  Per candidate in pool:        │
                          │    7-component rule-based      │
                          │    final = 0.75×rule           │
                          │          + 0.25×faiss_sim      │
                          │    (or 0.85/0.15 for TF-IDF)  │
                          │    apply penalty multipliers   │
                          │    (honeypot flag → ×0.05)    │
                          └──────────────┬────────────────┘
                                         │ sort DESC → top 100
                                         ▼
                              backend/explainer.py
                              (Explainability)
                                         │
                                         ▼
                              backend/exporter.py
                              (submission.csv + debug.json)
                                         │
                               ┌─────────┴──────────┐
                               ▼                    ▼
                      app/streamlit_app.py    evaluation/eval.py
                      (UI Dashboard)          (NDCG/MAP/P@K)
```

---

## 2. Seven Module Boundaries

The system is structured as seven distinct, independently testable modules with clean interfaces between them.

| # | Module | File(s) | Input | Output | What it does |
|---|--------|---------|-------|--------|--------------|
| 1 | **Job Understanding** | `backend/jd_parser.py` | `job_description.md` | `JobProfile` dataclass | Parses JD into structured required skills, title tokens, location tiers, disqualifiers. Reads experience ranges from config. |
| 2 | **Candidate Understanding** | `backend/candidate_parser.py` | Raw candidate dict (from JSONL) | `CandidateProfile` dataclass | Normalizes raw JSONL into a typed, cleaned internal representation. Computes derived signals (days_since_active, consulting_fraction, career span, profile_text for retrieval). |
| 3 | **Semantic Retrieval** | `backend/retrieval.py` | All `CandidateProfile` objects + `JobProfile` + config | `(candidate_pool, sim_scores[])` | **Primary**: encodes candidate texts with `all-MiniLM-L6-v2`, builds FAISS index, queries with JD embedding → returns top-K pool + similarity scores per candidate in pool. **Fallback**: TF-IDF cosine over all candidates (no top-K). Cache embedding matrix to disk across runs. |
| 4 | **Hybrid Reranking** | `backend/scorer.py` | `CandidateProfile[]` (pool only) + `JobProfile` + sim_scores + config | `(final_score, component_scores_dict)` per candidate | Computes 7 rule-based components for pool candidates only. Blends with FAISS similarity (0.75/0.25 or 0.85/0.15). Applies penalty multipliers including honeypot ×0.05. All constants from config. |
| 5 | **Explainability** | `backend/explainer.py` | Candidate, component scores, rank, honeypot flags | Reasoning string | Generates 1–2 sentence recruiter-facing justification citing specific signals. Unchanged. |
| 6 | **Export** | `backend/exporter.py` | Ranked result list | `submission.csv`, `debug.json` | Writes spec-compliant CSV; writes full score breakdown JSON for UI. Unchanged. |
| 7 | **Evaluation** | `evaluation/eval.py` | `debug.json`, (optional) ground truth | Metrics dict + printed report | Computes NDCG@K, MAP, P@K when labels exist; runs sanity checks when they don't. Unchanged. |

`honeypot.py` runs over **all N candidates** before retrieval. Honeypot flags are stored in `CandidateProfile.is_honeypot`. The reranking stage applies the ×0.05 penalty for flagged candidates — they cannot appear in the top 100.

---

## 3. Technology Stack

### 3a. Core ML / Ranking

| Component | Technology | Version | Justification |
|-----------|-----------|---------|---------------|
| Sentence embeddings | `sentence-transformers` | 2.x | `all-MiniLM-L6-v2` is 22MB, CPU-native; encodes meaning rather than tokens; bridges vocabulary gap the JD explicitly warns about |
| Vector index | `faiss-cpu` | 1.7+ | CPU-only FAISS build; `IndexFlatIP` for exact inner product (= cosine on normalized embeddings); `IndexIVFFlat` for approximate search at very large scale |
| Embedding persistence | `numpy` | 1.24+ | `np.save` / `np.load` for embedding matrix cache; eliminates re-encoding on repeated runs |
| Semantic fallback | `sklearn.TfidfVectorizer` | 1.3+ | Lexical fallback when `faiss-cpu` or `sentence-transformers` unavailable; scores all candidates (no top-K) |
| Configuration | `PyYAML` | 6.x | Loads `config/scoring.yaml` at startup; all numeric constants from this file |
| Date parsing | `python-dateutil` | 2.8+ | Robust ISO date parsing for career/education timelines |

**Why precomputed embeddings + FAISS (not brute-force cosine at query time):**  
Three reasons:

1. **Speed across runs.** Encoding 100K candidates once (~90s on CPU) is acceptable. Encoding them again on every subsequent run wastes time. FAISS holds the pre-built index in memory; querying it with the JD embedding takes milliseconds regardless of dataset size.

2. **Scalability beyond brute-force.** Brute-force cosine similarity (numpy matrix multiply) is already fast for 100K × 384 dimensions (~200ms). But FAISS `IndexIVFFlat` in approximate mode is significantly faster for larger datasets (millions), and the same `retrieval.py` interface handles both sizes without code changes.

3. **Clean two-stage interface.** FAISS returns a pool of top-K candidates with similarity scores attached. The reranking module receives this pool and never needs to know how the similarities were computed. This is a cleaner separation than embedding-and-score-all-at-once.

**Why TF-IDF is preserved as a fallback (not removed):**  
The compute constraints prohibit GPU and network access; `faiss-cpu` and `sentence-transformers` are additional install-time dependencies that may not be present in the organizer's sandbox. TF-IDF has zero extra dependencies beyond scikit-learn (already required). Fallback activates automatically if imports fail; behavior is identical from rank.py's perspective.

**Why blend ratios differ by backend:**

| Backend | Rule weight | Semantic weight | Reason |
|---------|-------------|-----------------|--------|
| FAISS embedding | 0.75 | 0.25 | Embeddings encode meaning → trustworthy semantic signal; keyword stuffers score lower in embedding space than in TF-IDF |
| TF-IDF | 0.85 | 0.15 | TF-IDF rewards token overlap → keyword stuffers can inflate this signal; lower weight reduces the risk |

### 3b. Configuration

All scoring constants live in `config/scoring.yaml`. The scoring engine reads this file at startup via a `ScoringConfig` dataclass. No numeric constant — weights, thresholds, penalties, behavioral curves — is hardcoded in `backend/` modules.

This means:
- Weights can be adjusted between submissions by editing the YAML, no code changes
- Different JDs can have their own config profiles in future
- Unit tests can inject override configs to test edge cases

### 3c. UI and Output

| Component | Technology | Justification |
|-----------|-----------|---------------|
| Dashboard | Streamlit | Single-file, Python-native, accepted as sandbox_link |
| Charts | Plotly | Interactive; standard with Streamlit |
| Output format | CSV (stdlib `csv`) | Spec mandates CSV |
| Debug output | JSON (stdlib `json`) | Full score breakdown; loaded by Streamlit UI |
| Input reading | JSONL streaming | Memory-efficient for large datasets |

---

## 4. Data Pipeline

The pipeline is explicitly two-stage: retrieval produces a candidate pool; reranking scores the pool.

```
Load config/scoring.yaml
    ↓
Load JSONL (streaming, line by line)
    ↓
[Module 2: Candidate Understanding — all N candidates]
  Parse raw dict → CandidateProfile:
    - Validate required fields + candidate_id format
    - Parse all dates, normalize text to lowercase
    - Compute days_since_active
    - Compute consulting_career_fraction, ml_career_fraction
    - Build profile_text (flat string for encoding)
    - Derive flags: is_consulting_only, has_cv_domain_skills, has_nlp_skills
    ↓
[Honeypot Detection — all N candidates]
  7 checks using thresholds from config
  Store: CandidateProfile.is_honeypot = bool
         CandidateProfile.honeypot_flags = List[str]
    ↓
[Module 3: Semantic Retrieval]
  PRIMARY (backend: "embedding"):
    Load embedding cache from outputs/embedding_cache/ if valid
      (invalidated when candidates.jsonl is modified)
    else: encode all N candidate profile_texts with all-MiniLM-L6-v2
      batch_size=64, normalize_embeddings=True
      save to cache
    Encode JD text
    Build FAISS index (IndexFlatIP or IndexIVFFlat per config)
    Search: top_k=1500 candidates by inner product similarity
    Apply title safety net:
      add any CandidateProfile with tier-1 title token not already in pool
    → candidate_pool (≤1500 + safety net additions)
    → sim_scores: float[] indexed by pool position

  FALLBACK (backend: "tfidf" or import failure):
    Fit TF-IDF on all N candidate texts + JD text
    Compute cosine_similarity for ALL N candidates
    → candidate_pool = all N candidates
    → sim_scores: float[N]
    ↓
[Module 4: Hybrid Reranking — pool candidates only]
  Per candidate in pool:
    compute 7 rule-based components (reads all weights from config)
    blend: rule_blend × rule_score + semantic_blend × sim_score
    apply penalty multipliers (from config):
      if is_honeypot: final_score × 0.05
      else: apply consulting/domain/cv/hopping/unavailable penalties
    ↓
Sort pool: final_score DESC, candidate_id ASC for ties
    ↓
Select top 100 from pool
    ↓
[Module 5: Explainability]
  Generate 1-2 sentence reasoning for each top-100 candidate
    ↓
[Module 6: Export]
  Write submission.csv (100 rows, spec-compliant)
  Write debug.json (full score breakdown for top 100 + pool stats)
    ↓
Validate CSV: row count, rank uniqueness, score monotonicity
```

---

## 5. ML Pipeline Detail

### 5a. Rule-Based Scoring (75% or 85% weight depending on backend)

All component weights, sub-weights, breakpoints, and bonus caps are read from `config/scoring.yaml`. The logic below describes the computation; the numeric constants come from config.

**Component 1: Title/Role Alignment**  
Duration-weighted across career history. tier1_title_tokens from `jd_parser.py` matched against each job's title. Score = weighted sum of (tier1_fraction × 1.0 + tier2_fraction × 0.55 + unrelated_fraction × 0.05) + recency boost if current title is ML/AI. Config keys: `title.*`

**Component 2: Skill Match**  
Required skill coverage (breadth × quality) + nice-to-have bonus + duration depth bonus. Proficiency weights and assessment threshold from config. Config keys: `scoring.skill.*`

**Component 3: Production Evidence**  
Distinct production keyword hits + scale mention regex bonus. Config keys: `scoring.production_evidence.*`

**Component 4: Behavioral Availability**  
Weighted sub-score across 6 signals. Recency, notice period, and GitHub use step-function curves defined in config. Config keys: `scoring.behavioral_*`

**Component 5: Experience Fit**  
Piecewise linear curve against JD's ideal experience range. Ramp parameters from config. Config keys: `scoring.experience.*`

**Component 6: Domain/Company Fit**  
Product company fraction vs consulting fraction in career history. Domain scores from config. Config keys: `scoring.domain.*`

**Component 7: Location**  
Tier-based location score using JD's tier1/tier2 location sets. Config keys: `scoring.location.*`

### 5b. Semantic Retrieval — FAISS Embedding Backend (primary)

**Step 1: Encode candidates (with cache)**
```python
# profile_text per candidate — built once in candidate_parser.py:
# "{current_title} {headline} {summary} {career_descriptions} {skill_names}"

model = SentenceTransformer("all-MiniLM-L6-v2")

if cache_valid(cache_path, candidates_file):
    embeddings = np.load(cache_path / "embeddings.npy")   # shape (N, 384)
    candidate_ids = np.load(cache_path / "ids.npy")
else:
    embeddings = model.encode(
        [c.profile_text for c in candidates],
        batch_size=64,
        normalize_embeddings=True,
        show_progress_bar=True,
    )                                                       # shape (N, 384)
    np.save(cache_path / "embeddings.npy", embeddings)
    np.save(cache_path / "ids.npy", candidate_ids)
```

**Step 2: Build FAISS index**
```python
# IndexFlatIP: exact inner product. For normalized vectors, IP = cosine similarity.
# No training step needed. O(N) memory. Recommended default.

index = faiss.IndexFlatIP(384)
index.add(embeddings)

# IndexIVFFlat (config: index_type: "ivf"):
# quantizer = faiss.IndexFlatIP(384)
# index = faiss.IndexIVFFlat(quantizer, 384, nlist, faiss.METRIC_INNER_PRODUCT)
# index.train(embeddings)
# index.add(embeddings)
# index.nprobe = nprobe
```

**Step 3: Query with JD embedding + title safety net**
```python
jd_embedding = model.encode([JD_TEXT_FOR_EMBEDDING], normalize_embeddings=True)
sims, indices = index.search(jd_embedding, top_k)   # top_k = 1500 by default

pool_ids = set(candidate_ids[indices[0]])

# Title safety net: ensure no tier-1 ML engineer is left out of reranking
# because they described their work in different vocabulary than the JD.
if config.semantic.embedding.faiss.title_safety_net:
    for c in all_candidates:
        if has_tier1_title(c) and c.candidate_id not in pool_ids:
            pool_ids.add(c.candidate_id)
            # append similarity score = 0.0 (no semantic credit, but eligible for rule-based reranking)

pool = [candidates_by_id[cid] for cid in pool_ids]
pool_sims = {cid: sim for cid, sim in zip(candidate_ids[indices[0]], sims[0])}
pool_sims.update({cid: 0.0 for cid in pool_ids if cid not in pool_sims})
```

**Step 4: Rerank pool — unchanged scorer interface**
```python
for candidate in pool:
    rule_score, components = score_rule_based(candidate, jd, config)
    sem_sim = pool_sims[candidate.candidate_id]
    blended = 0.75 * rule_score + 0.25 * sem_sim
    penalty = compute_penalty(candidate, config)
    final = blended * (1 - penalty)
```

**TF-IDF fallback** (activated by `backend: "tfidf"` in config or import failure):
```python
vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=8000, ...)
vectorizer.fit([JD_TEXT] + [c.profile_text for c in all_candidates])
sims = cosine_similarity(jd_vec, cand_vecs)[0]   # all N candidates
# pool = all_candidates, blended = 0.85 × rule + 0.15 × tfidf_sim
```

**Cache invalidation rule:** Compare `os.path.getmtime(candidates.jsonl)` against a timestamp stored in the cache directory. If candidates.jsonl is newer than the cache, re-encode. This is fast (one stat call) and robust.

**Performance estimates:**

| Stage | 10K candidates | 100K candidates |
|-------|---------------|-----------------|
| Encoding (first run) | ~9s | ~90s |
| Encoding (cache hit) | ~0s | ~0s |
| FAISS IndexFlatIP build | <1s | ~4s |
| FAISS search (top_k=1500) | <1ms | <10ms |
| Rule-based rerank (pool=1500) | ~0.7s | ~0.7s |
| **Total (first run)** | **~11s** | **~95s** |
| **Total (cache hit)** | **~2s** | **~5s** |

All estimates are for CPU only, single-threaded, `all-MiniLM-L6-v2` at batch_size=64.

### 5c. Penalty System

All multipliers from `config/scoring.yaml` under `penalties.*`. Applied as:
```
final_score = clamp(blended_score × (1 - penalty))
```
Penalties are additive (stacked before final multiply):
- `penalty = min(1.0, consulting + wrong_domain + cv_robotics + hopping + unavailable)`
- Honeypot overrides: `final_score × honeypot_multiplier` regardless of other penalties

---

## 6. Ranking Strategy

NDCG@10 carries 50% of the composite score. The top-10 positions are the highest-value region. Design implications:

1. The title alignment component (25%) must be strong enough to prevent any keyword-stuffer from reaching the top 10, even with high semantic similarity.
2. Honeypot detection must guarantee zero false negatives in the top 100.
3. Within the top-100 shortlist, meaningful score spread is needed. Embedding-based semantic similarity (at 25%) provides more discriminative power within the ML-engineer band than TF-IDF (at 15%), because true-positive candidates will embed closer to the JD than near-positives based on career description content rather than just vocabulary.

---

## 7. Explainability

Each top-100 candidate receives a 1–2 sentence recruiter-facing reasoning string that:
- Cites the actual job title and company name
- Names the top 3 matched required skills
- States availability signals (active date, notice period)
- Calls out any penalty applied (consulting background, inactive status)
- Does not use vague phrasing ("strong fit," "high potential") without evidence

No honeypot candidate appears in the top 100; no reasoning is generated for penalized profiles.

---

## 8. Evaluation Methodology

### Without ground truth (current)
1. Format validation: 100 rows, ranks 1–100, monotonic scores, valid IDs
2. Archetype discrimination: ideal ML engineer ≥ 0.70, keyword stuffer ≤ 0.40
3. Honeypot rate in top 100 = 0%
4. Score range: all ∈ [0, 1]
5. Determinism: same input → identical output
6. Baseline comparison: our system vs naive keyword-count model

### With ground truth (post-submission)
```
composite = 0.50×NDCG@10 + 0.30×NDCG@50 + 0.15×MAP + 0.05×P@10
```

---

## 9. Folder Structure

```
signalrank-ai/
  rank.py                         # CLI entry point
  requirements.txt
  submission_metadata.yaml
  config/
    scoring.yaml                  # ALL scoring weights, thresholds, penalties

  backend/
    jd_parser.py                  # [1] Job Understanding: structured JD profile
    candidate_parser.py           # [2] Candidate Understanding: normalizes raw dicts
    retrieval.py                  # [3] Semantic Retrieval: embedding / TF-IDF adaptive
    scorer.py                     # [4] Hybrid Ranking: 7 components + blend + penalties
    honeypot.py                   # Honeypot detection (pre-scoring)
    explainer.py                  # [5] Explainability: reasoning strings
    exporter.py                   # [6] Export: submission.csv + debug.json

  app/
    streamlit_app.py              # Recruiter dashboard UI

  data/
    raw/
      candidate_schema.json
      job_description.md
      output_template.csv
      candidates.jsonl            # Place organizer dataset here
    processed/                    # Reserved for cleaned intermediate data

  docs/
    submission_spec.md
    redrob_signals_doc.md

  evaluation/
    eval.py                       # [7] Evaluation: NDCG/MAP/sanity/baseline

  scripts/
    validate_submission.py
    generate_test_data.py

  outputs/
    submission.csv
    debug.json
    embedding_cache/          # auto-created; .npy embedding matrix + candidate_ids + timestamp

  tests/
    test_scorer.py                # Unit tests (updated to test config loading)
    test_pipeline.py              # Integration tests (unchanged behavior)
    test_retrieval.py             # New: tests embedding vs TF-IDF fallback

  DATASET_ANALYSIS.md
  ARCHITECTURE_DECISION.md
  IMPLEMENTATION_PLAN.md
  README.md
  CLAUDE.md
```

---

## 10. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| `faiss-cpu` or `sentence-transformers` absent in organizer sandbox | Medium | High | Auto-fallback to TF-IDF on ImportError; logged clearly; no crash |
| FAISS top_k=1500 misses a strong ML engineer (recall gap) | Low | High | Title safety net adds every tier-1-title candidate regardless of FAISS rank; top_k configurable |
| Embedding cache stale after candidates.jsonl update | Low | Medium | Cache invalidated by mtime comparison; `--no-cache` flag forces re-encode |
| First-run encoding (100K candidates) too slow | Very Low | High | ~90s estimated, within 5-min constraint; cached for all subsequent runs |
| Score compression in top-100 | Medium | Medium | 25% embedding weight provides more semantic spread than TF-IDF; configurable |
| Honeypot rate >10% in top 100 | Very Low | Catastrophic | 7-check detection across all N candidates; ×0.05 penalty |
| Keyword stuffers in top 10 | Low | High | Title alignment at 25%; embedding distances HR from ML profiles |
| Config file missing or malformed | Low | Catastrophic | Load-time validation; clear error message with missing key name |
| Wrong CSV filename at submission | Medium | Catastrophic | Add rename step to submission checklist |
| Streamlit upload bug causes demo failure | High | Medium | Fix in Phase 6; fallback: auto-load debug.json on app startup |

---

## 11. Justification Summary

| Decision | Rationale |
|----------|-----------|
| FAISS index (IndexFlatIP) for embedding retrieval | Exact inner product on normalized vectors = cosine similarity; no approximation error; O(N) memory; handles 100K vectors in <10ms |
| Precomputed + cached embeddings | Encoding 100K candidates takes ~90s on first run; cache eliminates this for all subsequent runs |
| Two-stage pipeline (FAISS retrieve → rule-based rerank) | Reranking runs on pool of 1500, not all N candidates; scales cleanly; retrieval and ranking are independently testable |
| Title safety net in retrieval | Prevents recall failures for ML engineers who describe their work without standard ML vocabulary |
| IndexIVFFlat as config option | Approximate search for very large datasets (millions); same interface; configurable nlist/nprobe |
| TF-IDF as import-failure fallback | Zero extra dependencies beyond scikit-learn; auto-activated when faiss-cpu or sentence-transformers missing |
| Higher semantic weight for embeddings (25%) vs TF-IDF (15%) | Embeddings are not lexical → keyword stuffers cannot inflate the signal; TF-IDF is lexical → lower weight to reduce that risk |
| All weights in `config/scoring.yaml` | Between-submission tuning without code changes; prevents accidental hardcoding drift |
| `candidate_parser.py` builds `profile_text` once | Text construction for retrieval is not repeated in scoring; single responsibility |
| Honeypot detection on all N before retrieval | Ensures honeypot flag is available during reranking; FAISS top-K may include honeypots (they often have AI vocabulary) |
| Title alignment at 25% | Decisive signal against the organizer's keyword-stuffer trap; HR/non-ML titles score <0.10 on this component |
| Production evidence at 15% | JD explicitly disqualifies researchers who haven't shipped |
| Behavioral availability at 15% | JD explicitly instructs use of Redrob signals for hiring urgency |
| Honeypot penalty ×0.05 (not 0.0) | Non-zero prevents tie-breaking edge cases when sorting |
