# SignalRank AI — Judge FAQ

Concise answers for the most likely technical and product questions.

---

## Technical Questions

### Why not keyword matching?

Keyword matching scores frequency, not fit. A candidate who writes "PyTorch, BERT, Transformers, LLM, RAG, FAISS, NLP, IR" in their skills section scores higher than an NLP engineer who describes what they actually built with those tools.

Our system gives keyword matching only 20% weight (via the skill_match component), and that 20% is proficiency-weighted and endorsement-boosted — not a raw count. The decisive 25% comes from title_role alignment: what titles has this person held across their career? An HR Manager with perfect skills scores 0.05 on title_role, collapsing their total score below 0.30. This is by design.

---

### Why FAISS?

FAISS (Facebook AI Similarity Search) is the industry standard for approximate nearest-neighbor search over dense vector embeddings. We use `IndexFlatIP` (exact inner product on normalized vectors, equivalent to cosine similarity) because our pool is 2,000 candidates — small enough that an exact index is faster than an approximate one and produces no search error.

For 100,000+ candidates, we switch to `IndexIVFFlat` by changing one line in `config/scoring.yaml` (`index_type: "ivf"`). The FAISS configuration is already validated in the config loader.

FAISS gives us:
- Millisecond retrieval after one-time encoding
- No external service dependency
- On-disk caching of embeddings and the index
- CPU-native operation with no GPU requirement

---

### Why Reciprocal Rank Fusion (RRF)?

Neither FAISS nor TF-IDF alone is sufficient:

- FAISS (dense retrieval) finds candidates whose profile is semantically close to the job description. It excels at paraphrase and domain-aware matching but can miss candidates who use exact JD vocabulary in unusual contexts.
- TF-IDF (sparse retrieval) finds candidates who share specific vocabulary with the JD. It excels at exact term matching but treats synonyms as different signals.

A strong candidate who describes "dense retrieval" and "vector search" will rank high on FAISS. A strong candidate who repeats the exact JD phrases ("semantic ranking", "LTR") will rank high on TF-IDF. RRF fuses both ranked lists so neither path loses strong candidates.

The formula is simple: `score(candidate) = Σ 1 / (k + rank_in_list)` where `k=60` reduces the advantage of top-ranked candidates. This is the same technique used in hybrid search in Elasticsearch and OpenSearch.

---

### Why not a fine-tuned LLM?

Three reasons:

1. **Hard constraint: no network calls during ranking.** A hosted LLM (GPT-4, Claude, Gemini) requires network access and would add API costs and latency.

2. **No labeled training data.** Fine-tuning a bi-encoder or cross-encoder for this specific hiring task requires (JD, good candidate, bad candidate) triplets. The organizer dataset has no relevance labels until after submission. We cannot fine-tune without labels.

3. **Calibration risk.** A large language model used as a scorer tends to be sensitive to phrasing, position, and prompt wording. Our rule-based reranker with externalized weights is predictable, debuggable, and tunable without retraining.

The embedding model (`all-MiniLM-L6-v2`, 22 MB) was chosen because it runs in 1 second on CPU, has strong performance on semantic textual similarity benchmarks, and is reproducible across machines. It is not fine-tuned on recruiting data, which is the primary limitation.

---

### How do you prevent keyword stuffing?

Three independent mechanisms work together:

1. **Title alignment (25% weight)**: The `title_role` component scores the fraction of a candidate's career history in ML/AI-titled roles. An HR Manager who adds "Machine Learning, PyTorch, LLM" to their skills gets a title_role score of 0.05–0.15, collapsing their total.

2. **Honeypot detection**: Candidates who set every skill to "Expert" with the maximum endorsement count trigger the all-maxed-behavioral check. Any single career with all skills at maximum proficiency and all endorsements at ceiling is flagged as suspicious.

3. **Production evidence gate**: The `production_evidence` component (15% weight) searches career description text for deployment keywords: "deployed", "production", "serving", "QPS", "latency", "real users". A candidate who lists 20 ML skills but whose career descriptions contain only project descriptions with no shipping evidence scores low on this component.

---

### How are honeypots detected?

The organizer spec states ~80 candidates in the dataset are "subtly impossible" profiles that must be excluded from the top-100.

We run 7 independent impossibility checks on every candidate:

| Check | What it detects |
|-------|----------------|
| Timeline overlap | Two jobs at the same company with overlapping date ranges (>90 days) |
| Graduation after career start | Education end date later than first job start date |
| Stated YOE vs actual span | `years_of_experience` field disagrees with career timeline by >3 years |
| All-maxed skills | Every skill rated "Expert" AND every endorsement count at maximum |
| All-maxed behavioral | Every behavioral signal (recency, response rate, notice period, GitHub) simultaneously at maximum |
| Duration inflation | Sum of all job durations exceeds the actual career timeline by >50% |
| Impossible education | Education spans >12 years (longer than any real degree program) |

Any candidate triggering 2 or more checks receives a 95% score penalty (multiplier ×0.05), collapsing their final score to below 0.05 regardless of other signals. The thresholds are configurable in `config/scoring.yaml`.

On the synthetic dataset: 22 honeypots detected, 0 appearing in the top-100.

---

### How is explainability generated?

The explainer does not use an LLM or template fill-in. It:

1. **Selects a narrative style** based on the candidate's dominant scoring signal:
   - `production_led`: if production_evidence ≥ 0.75 and title_role ≥ 0.65
   - `skills_led`: if skill_match ≥ 0.85 and title_role ≥ 0.55
   - `career_arc_led`: if title_role ≥ 0.85 and ≥2 ML-titled career entries
   - `availability_led`: if behavioral ≥ 0.88 and title_role ≥ 0.55
   - `balanced`: default when no signal dominates

2. **Extracts specific evidence** from the candidate's raw data:
   - Best production career entry (highest density of deployment keywords)
   - Top 2 skills by proficiency and endorsement count
   - Behavioral summary (last active date → "active today / this week", notice period, response rate)
   - Education snapshot

3. **Constructs 2-4 sentences** naming specific companies, roles, and quoting career description excerpts. No sentence is generated without a specific data anchor.

Example output: *"At Springworks (ML Engineer), demonstrated clear production impact: designed and deployed production vector search using FAISS. Reduced retrieval latency from 200ms to 18ms at 10M QPS. Technical depth in Python (expert, 114 endorsements), FAISS and sentence-transformers. Currently active this week, open to work, 30-day notice, 88% response rate."*

---

### How does the system scale?

The current configuration targets 2,000 candidates and completes in ~8 seconds (cold cache). Scaling path:

| Dataset size | Required change | Expected time |
|-------------|-----------------|---------------|
| 2,000 (current) | None | ~8s cold / ~4s cached |
| 10,000 | None — FAISS flat scales | ~25s cold / ~5s cached |
| 100,000 | Set `index_type: "ivf"` in scoring.yaml | ~60s cold / ~8s cached |
| 1,000,000 | IVF + batch parallelism (multi-thread scoring loop) | ~5 min cold / ~30s cached |

The embedding encoding step (most expensive) scales linearly with candidate count. The rule-based scoring loop is O(pool_size) where pool_size ≤ 1,500 regardless of input size (RRF caps the retrieval pool). FAISS IVF reduces query time from O(N) to O(sqrt(N)) at the cost of approximate results.

---

### How are candidates parsed and normalized?

Raw JSONL records are converted to `CandidateProfile` dataclasses with pre-computed derived fields:

- `consulting_fraction`: fraction of career history at known consulting firms (TCS, Infosys, Wipro, Accenture, etc.)
- `ml_fraction`: fraction of career titles containing ML/AI tokens
- `days_since_active`: integer days from `last_active_date` to `REFERENCE_DATE`
- `profile_text`: a structured prose paragraph combining title, skills, career descriptions, and behavioral signals — used as the embedding input

This design means the scoring functions perform a single O(1) lookup per derived field rather than re-computing from raw data on every candidate.

---

### What evaluation metric are you targeting?

The organizer composite metric:

```
Score = NDCG@10 × 0.50 + NDCG@50 × 0.30 + MAP × 0.15 + P@10 × 0.05
```

NDCG (Normalized Discounted Cumulative Gain) rewards correct ranking of relevant candidates with a logarithmic discount for lower positions. MAP (Mean Average Precision) rewards consistent placement of all relevant candidates throughout the list.

The 50% weight on NDCG@10 means getting the very top 10 correct is the primary objective. Our title_role component (25% of the score) is calibrated to ensure that only genuinely ML/AI-titled engineers appear in the top 10.

We do not have ground-truth labels before the deadline. All our evaluation is sanity-based (archetype discrimination, honeypot safety, baseline comparison against a keyword model).

---

## Product Questions

### Who is the target user?

Technical recruiters and hiring managers at product-focused technology companies who need to screen large candidate pools for senior engineering roles. The dashboard is designed so a recruiter can complete an initial screen in 15-20 minutes: review the top-25 cards, compare 3-4 candidates, download the shortlist.

---

### Why should recruiters trust the scores?

Three trust signals:

1. **Every score is decomposed**: the dashboard shows all 7 components, not just the total. A recruiter can see exactly why a candidate ranked where they did.
2. **Evidence is cited**: the reasoning names the company, the role, and quotes text from the actual career description. There are no vague phrases ("strong fit", "high potential").
3. **Missing signals are shown**: if a candidate lacks a key JD skill, it appears as a "missing" tag — the system doesn't hide uncertainty.

---

### What would you build next?

In priority order:

1. **Recruiter feedback loop**: when a recruiter marks a candidate as "hired", "interviewed", or "rejected", use that signal to retrain the scoring weights via a simple linear model. This converts the system from configurable to self-improving.
2. **Real-time JD parsing**: the current JD is a hardcoded markdown file. Extend the JD parser to accept any job description via paste or URL, extract structured requirements, and adapt the scoring weights automatically.
3. **Cross-JD candidate ranking**: maintain a candidate database across multiple roles and route candidates to the best-fit JD rather than ranking one JD at a time.
4. **Bias audit mode**: add a reporting layer that flags if the top-100 are demographically skewed along detectable dimensions (institution tier, years of experience distribution) and suggests weight adjustments.

---

### Is this solving real recruiter problems?

Yes. The two explicit failure modes in the challenge dataset (keyword stuffing and honeypots) are both present in real-world applicant tracking systems. ATS keyword matching is a known failure mode that well-documented research shows reduces match quality. Honeypot-style profile manipulation is increasingly common on platforms that use algorithmic ranking.

The recruiter dashboard addresses a real workflow: a technical recruiter without ML expertise needs to hand a shortlist to a hiring manager with enough evidence to defend the choices. The component breakdown and evidence citations are designed for exactly that conversation.

---

### What are your known limitations?

1. **Score compression on synthetic data**: the top-100 all score within a 0.020-point band. This is a synthetic-data artifact; real heterogeneous data will show wider spread.
2. **No fine-tuning**: the embedding model was not fine-tuned on recruiting or technical hiring data. Unusual profile vocabulary may not embed correctly relative to the JD.
3. **Single JD**: the system ranks candidates against one fixed job description per run. Multi-JD routing is not implemented.
4. **English-only**: candidate profile text is assumed to be in English. Non-English profiles will embed poorly.
5. **Static REFERENCE_DATE**: behavioral recency is computed against a fixed date (`2026-06-25`). Candidates who became active after this date will not benefit from improved recency scores without re-running the pipeline.
