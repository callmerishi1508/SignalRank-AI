# SignalRank AI — Pitch Deck Outline

7 slides, target 5–7 minutes spoken. Each slide has one main message.

---

## Slide 1: Problem

**Headline**: Keyword-ranked shortlists miss the best candidates — and promote the worst

**Body**:
- Recruiter receives 2,000 profiles for one role
- Traditional ATS: keyword frequency → ML engineer who stuffed "PyTorch, BERT, Transformers" beats an NLP specialist with 8 years of production ranking systems
- Result: wrong shortlist, wrong hires, wasted time

**Visual**: Two side-by-side candidate cards — keyword-stuffer vs genuine NLP engineer — with keyword-count ranking reversal highlighted

---

## Slide 2: Our Approach

**Headline**: Two-stage pipeline: semantic retrieval → evidence-grounded reranking

**Body**:
```
candidates.jsonl
      │
      ▼
  [Stage 1 — Retrieval]
  FAISS dense search (top 3000)
  TF-IDF lexical search (top 3000)
  Reciprocal Rank Fusion → pool of ~1500
      │
      ▼
  [Stage 2 — Reranking]
  7-component rule scoring × embedding blend
  Honeypot detection (7 checks)
  Penalty application
      │
      ▼
  Top-100 shortlist with evidence
```

**Key insight**: Stage 1 finds the candidates semantic matching alone would miss. Stage 2 explains *why* each candidate ranks where they do.

---

## Slide 3: Scoring Signal

**Headline**: Every rank is backed by traceable evidence

**Body**:

| Component | Weight | What it measures |
|-----------|--------|-----------------|
| Title / Role | 25% | Career fraction in ML/AI titles |
| Skill Match | 20% | Proficiency-weighted + endorsement-boosted |
| Production Evidence | 15% | Deployment + scale keywords in career text |
| Behavioral Availability | 15% | Recency, response rate, notice period |
| Experience Fit | 10% | Ideal 5-9y curve, penalizes extremes |
| Domain Fit | 10% | Product company vs consulting firm career |
| Location | 5% | Tier-based city alignment |

Penalty multipliers: consulting-only −30%, wrong domain −45%, job-hopping −10%, honeypot −95%

**Visual**: Score breakdown bar chart for the #1 ranked candidate

---

## Slide 4: Honeypot Defense

**Headline**: We catch 7 types of fake profiles before they reach the shortlist

**Body**:

Checks we run on every candidate:
1. Overlapping job timelines (same company, dates conflict)
2. Graduation date after career start
3. Stated YOE vs actual span mismatch >3 years
4. All skills rated "Expert" with maximum endorsements
5. All behavioral signals at maximum simultaneously
6. Job durations inflate stated career span >50%
7. Education spanning >12 years

Result on real-spec dataset: ~80 honeypots expected. All get a ×0.05 score multiplier — effectively eliminated.

**Visual**: Before/after — 3 honeypot profiles, their fake signals, their collapsed scores

---

## Slide 5: Demo

**Headline**: Built for recruiters, not data scientists

**Body**:

Walk through the 4 dashboard tabs:
1. **Ranked Shortlist** — filter by score, title, penalty status
2. **Candidate Detail** — full 7-component breakdown with color-coded bars
3. **Evaluation** — format compliance, baseline comparison, error detection
4. **Score Distribution** — visualize the full field

All weights and parameters are tunable in one YAML file — no code changes needed.

**Visual**: Screenshots of Ranked Shortlist and Candidate Detail tabs

---

## Slide 6: Results

**Headline**: Strong differentiation from keyword baseline — correct archetype separation

**Body**:

On synthetic validation dataset (2,000 candidates):

| Metric | Result |
|--------|--------|
| Top-10 ML/AI fraction | 10/10 (100%) |
| Honeypots in top-100 | 0 |
| Baseline overlap @10 | 1/10 (strong differentiation) |
| Runtime (cold) | ~19 seconds |
| Runtime (cache hit) | ~6 seconds |
| Network calls during ranking | 0 |

Archetype checks all pass: ideal ML engineer scores 2× keyword stuffer, consulting-only engineers penalized >30%.

---

## Slide 7: Architecture and Constraints

**Headline**: CPU-native, offline, reproducible — works on any laptop

**Body**:

| Constraint | Our implementation |
|------------|-------------------|
| CPU only | No CUDA, no MPS — pure numpy + faiss-cpu |
| No network during ranking | All models pre-cached; zero HTTP calls |
| Deterministic | Fixed seed; same input → same output |
| Configurable | All weights, thresholds in config/scoring.yaml |

Model: sentence-transformers/all-MiniLM-L6-v2 (22 MB, offline after first download)

**Closing line**: One config file. One command. A recruiter-trustworthy shortlist in under 20 seconds.

---

## Appendix slides (as needed)

- A1: RRF mechanics (formula + worked example)
- A2: Full penalty table with rationale
- A3: Evaluation metric formula (NDCG@10 + NDCG@50 + MAP + P@10)
- A4: Scoring YAML structure (config tuning guide)
- A5: Test coverage summary (56 tests, what each covers)
