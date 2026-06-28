# SignalRank AI — System Architecture

## Overview

SignalRank AI is a two-stage candidate ranking pipeline designed to run entirely offline on CPU in under 5 minutes. It combines semantic retrieval (FAISS vector search + TF-IDF) with evidence-grounded rule-based scoring.

---

## Pipeline diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  INPUT                                                          │
│  candidates.jsonl + job_description.md                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  MODULE 1: candidate_parser.py                                  │
│  • Stream JSONL → CandidateProfile dataclass                    │
│  • Pre-compute: days_since_active, career fractions,            │
│    consulting_fraction, ml_fraction, profile_text               │
│  • Store raw dict for scorer backwards-compat                   │
└────────────────────────┬────────────────────────────────────────┘
                         │  CandidateProfile[]  (all N)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  MODULE 2: honeypot.py                                          │
│  • 7 impossibility checks over ALL candidates (O(N), fast)      │
│    1. Career timeline overlaps (>90d → flag, >365d → knockout)  │
│    2. Graduation year after first career start                  │
│    3. Stated YOE vs actual career span (>3y discrepancy)        │
│    4. All-expert skills + suspicious endorsements               │
│    5. All behavioral signals simultaneously at maximum          │
│    6. Duration months > 1.5× career span                       │
│    7. Impossible education dates                                │
│  • Sets cp.is_honeypot + cp.honeypot_reasons                    │
└────────────────────────┬────────────────────────────────────────┘
                         │  annotated CandidateProfile[]
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  MODULE 3: retrieval.py — SemanticRetriever                     │
│                                                                 │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐  │
│  │ FAISS Embedding Path    │  │ TF-IDF Path                  │  │
│  │ all-MiniLM-L6-v2        │  │ scikit-learn TfidfVectorizer  │  │
│  │ (22MB, CPU-native)      │  │ ngram(1,2), 8K features       │  │
│  │                         │  │                              │  │
│  │ encode() → float32 mat  │  │ fit_transform() → sparse mat │  │
│  │ IndexFlatIP (exact IP)  │  │ cosine_similarity(jd, cands) │  │
│  │ search(jd_emb, top-3000)│  │ top-3000 by TF-IDF score     │  │
│  └──────────┬──────────────┘  └───────────┬──────────────────┘  │
│             │   ranked_ids                │   ranked_ids         │
│             └─────────────┬──────────────┘                       │
│                           ▼                                      │
│            ┌─────────────────────────┐                           │
│            │ RRF Fusion (k=60)       │                           │
│            │ score = Σ 1/(k + rank_i)│                           │
│            │ top-1500 by RRF score   │                           │
│            └─────────────┬───────────┘                           │
│                          │ + title safety net                    │
│                          │   (tier-1 titles always included)     │
└─────────────────────────┬─────────────────────────────────────┘
                          │  RetrievalResult {profiles, similarities}
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  MODULE 4: scorer.py — score_candidates_bulk()                  │
│                                                                 │
│  7 Components (weights from config/scoring.yaml):               │
│  ┌─────────────────────────────────────────────┐                │
│  │ title_role (0.25)  — career history % in ML │                │
│  │ skill_match (0.20) — depth × breadth × trust│                │
│  │ production (0.15)  — deploy evidence in text│                │
│  │ behavioral (0.15)  — recency/response/notice│                │
│  │ experience (0.10)  — ideal range 5-9 years  │                │
│  │ domain (0.10)      — product vs consulting  │                │
│  │ location (0.05)    — Pune/Noida/Bangalore   │                │
│  └─────────────────────────────────────────────┘                │
│                                                                 │
│  Blending:                                                      │
│  rule_score = weighted sum of 7 components                      │
│  final = (0.75 × rule + 0.25 × embedding_sim) × (1 − penalty)  │
│                                                                 │
│  Penalty multipliers:                                           │
│  • consulting-only (−30%), wrong-domain (−45%)                  │
│  • CV/robotics without NLP (−30%), job-hopping (−10%)           │
│  • behaviorally-unavailable (−20%), honeypot (−95%)             │
└────────────────────────┬────────────────────────────────────────┘
                         │  scored results + similarities
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  MODULE 5: explainer.py                                         │
│  • Generate recruiter-facing 1-2 sentence reasoning per         │
│    top-100 candidate                                            │
│  • Evidence-anchored: names matched skills, production signals, │
│    behavioral status, location                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  MODULE 6: exporter.py                                          │
│  • submission.csv: candidate_id, rank, score, reasoning         │
│    (exactly 100 rows, ranks 1-100, score non-increasing, UTF-8) │
│  • debug.json: full breakdowns for UI and evaluation            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Embedding cache design

```
outputs/embedding_cache/
├── embeddings.npy      # (N, 384) float32 — all-MiniLM-L6-v2 vectors
├── candidate_ids.npy   # (N,) object array — candidate_id strings
├── index.faiss         # IndexFlatIP — persisted for fast reload
└── metadata.json       # {source_path, source_mtime, n_candidates, model}
```

**Cache invalidation**: metadata.json stores the `mtime` of `candidates.jsonl`. If the file is newer than the cache, the entire cache is invalidated and rebuilt. Use `--no-cache` to force rebuild.

**Second-run speedup**: ~19s (cold) → ~6s (cache hit). The model still loads for JD query encoding, but candidate batch encoding is skipped.

---

## Config architecture

```
config/scoring.yaml
├── semantic
│   ├── backend: "embedding"
│   ├── embedding
│   │   ├── model_name: "sentence-transformers/all-MiniLM-L6-v2"
│   │   ├── faiss: {index_type, top_k, title_safety_net, persist_index}
│   │   ├── cache: {enabled, path}
│   │   └── rule_blend: 0.75 / semantic_blend: 0.25
│   ├── rrf: {enabled, k, top_embedding_k, top_tfidf_k}
│   └── tfidf: {ngram_range, max_features, rule_blend, semantic_blend}
├── scoring
│   ├── component_weights: {title_role, skill_match, …}  ← must sum to 1.0
│   ├── behavioral_sub_weights: {recency, open_to_work, …}  ← must sum to 1.0
│   ├── skill: {proficiency_weights, assessment_score_threshold, …}
│   ├── production_evidence: {keywords_for_full_score, …}
│   ├── experience: {score_at_zero_yoe, ramp_base, …}
│   ├── behavioral_recency: {thresholds_days, scores}
│   ├── behavioral_notice_period: {thresholds_days, scores}
│   ├── location: {score_tier1_location, …}
│   └── domain: {score_product_company, …}
├── penalties: {honeypot_multiplier, consulting_only, wrong_domain, …}
└── honeypot: {timeline_overlap_tolerance_days, …}
```

`config_loader.py` validates that `component_weights` sum to 1.0 and provides dot-access (`cfg.scoring.component_weights.title_role`). Every numeric constant in `backend/` reads from this file.

---

## Key design decisions

### Why FAISS + TF-IDF → RRF (not just one)?

Embedding models encode *semantic* meaning — "senior machine learning practitioner" maps near "ML engineer" even without exact vocabulary overlap. TF-IDF is complementary: it excels at rare technical tokens (specific library names, metric names) that embeddings may dilute.

RRF fusion combines their ranked lists without requiring score normalization. A candidate strong in both appears near the top of the merged list; a candidate strong in only one still benefits from that rank.

### Why IndexFlatIP (exact) over IVFFlat (approximate)?

With ≤100K candidates, IndexFlatIP adds <5ms per query. The accuracy guarantee is worth it for a single-query ranking task. IVFFlat is available as a config option for larger datasets.

### Why title alignment is 25% of score

The organizer's "trap" is keyword stuffers — HR Managers listing every ML term in their skills. A profile-text embedding alone may rank them moderately high because the *vocabulary* matches even if the role doesn't. The title component scores career history as a weighted duration-fraction: 5 years as ML Engineer + 2 years as HR Manager → 71% tier-1 fraction → high score. Pure HR with no ML history → 0.05 score, collapsing total below 0.25.

### Why behavioral is a primary component, not a tiebreaker

The JD explicitly states inactive candidates should be downweighted. A candidate with a 2% recruiter response rate and last login 8 months ago is effectively unavailable. Scoring this at 0.02 recency × 0.30 weight significantly separates them from active candidates with otherwise identical profiles.

---

## Performance model

| Dataset size | Cold run | Cached run | Notes |
|-------------|----------|------------|-------|
| 2,000 | ~19s | ~6s | Synthetic dataset used in testing |
| 10,000 | ~55s | ~10s | Estimated |
| 50,000 | ~230s | ~20s | Estimated — within 5-min constraint |
| 100,000 | ~450s | ~35s | Near limit — use IVFFlat if needed |

The bottleneck is sentence-transformer encoding (~100 candidates/second on CPU). FAISS search and rule-based scoring are negligible.

---

## Module boundaries

| Module | Inputs | Outputs | Pure? |
|--------|--------|---------|-------|
| `config_loader.py` | YAML file | `ScoringConfig` | Yes (cached) |
| `candidate_parser.py` | JSONL dict | `CandidateProfile` | Yes |
| `jd_parser.py` | hardcoded JD | `JobProfile` | Yes (singleton) |
| `honeypot.py` | dict, config | `(bool, List[str])` | Yes |
| `retrieval.py` | profiles, config | `RetrievalResult` | Stateful (cache) |
| `scorer.py` | dict, jd, config | `(float, dict)` | Yes |
| `explainer.py` | dict, components | `str` | Yes |
| `exporter.py` | results list | CSV/JSON files | Side-effect |
