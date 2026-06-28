# SignalRank AI — Evaluation Report

**Date**: 2026-06-26  
**Dataset**: Synthetic dataset (2,000 candidates)  
**Model**: sentence-transformers/all-MiniLM-L6-v2 + FAISS + TF-IDF + RRF

---

## 1. Submission Format Compliance

| Check | Result |
|-------|--------|
| Scores monotonically non-increasing | ✓ PASS |
| Ranks 1–100 each appear exactly once | ✓ PASS |
| Candidate IDs all unique | ✓ PASS |
| All scores in [0, 1] | ✓ PASS |
| No honeypots in top-100 | ✓ PASS (0 honeypots) |
| Top-10 ML/AI candidates | ✓ PASS (10/10 = 100%) |
| Reasoning coverage | 100% |

All format checks pass. Organizer validator confirms: **"Submission is valid."**

---

## 2. Score Distribution (Top-100)

| Statistic | Value |
|-----------|-------|
| Range | 0.9031 – 0.9226 |
| Mean | 0.9097 |
| P10 / P50 / P90 | 0.9157 / 0.9092 / 0.9044 |
| Top-10 score spread | 0.0063 |
| Top-10 → Top-100 gap | 0.0133 |

**Note on score compression**: The top-100 candidates all score in a 0.020-point band (0.9031–0.9226). This is expected with the synthetic dataset, where all "true positive" archetypes are generated from similar templates with identical key signals. On the real organizer dataset, we expect wider score spread because candidate quality will be more heterogeneous.

---

## 3. Top-N Candidate Profiles

### Top-10

| Metric | Value |
|--------|-------|
| Score range | 0.9163 – 0.9226 |
| Mean YOE | 7.4 years |
| Penalized candidates | 0/10 |
| Title diversity | 6 unique titles |

Title breakdown:
- 4× NLP Engineer
- 2× Applied ML Engineer
- 1× Senior AI Engineer
- 1× Research Engineer - ML
- 1× Senior ML Engineer
- 1× Search Engineer

Component averages (top-10):
- title_role: 0.991 | skill_match: 1.000 | production_evidence: 1.000
- behavioral: 0.918 | experience_fit: 1.000 | domain_fit: 0.900 | location: 1.000

### Top-100

All 100 candidates are ML/AI engineers. No HR Managers, Sales, or Content Writers appear. No honeypots detected. Behavioral score (0.882 avg) is the primary within-band discriminator.

---

## 4. Systematic Error Detection

| Check | Result |
|-------|--------|
| Honeypots in top-100 | 0 (✓) |
| Wrong-domain high scorers | 0 (✓) |
| Score compression warning | ⚠ Yes (top-10 range = 0.006, synthetic-data artifact) |
| Title monotony | ✓ OK (6 unique titles in top-10) |

No critical errors detected. Score compression is a known synthetic-data artifact and will not affect ranking on the real dataset.

---

## 5. Baseline Comparison

We compare against a keyword-count baseline that scores candidates by:
```
baseline = 0.60 × (ML_keyword_matches / 18) + 0.25 × (yoe / 10) + 0.15 × recruiter_response_rate
```

| Metric | Result | Interpretation |
|--------|--------|----------------|
| Overlap @10 | 1/10 | Our model picks 9/10 different candidates — strong differentiation |
| Overlap @25 | 4/25 | 21/25 different candidates in top-25 |
| Overlap @50 | 15/50 | 35/50 different in top-50 |

**Our top-10 titles**: NLP Engineer ×4, Applied ML Engineer ×2, Senior AI Engineer ×1, Research Engineer - ML ×1, Senior ML Engineer ×1, Search Engineer ×1

**Keyword baseline top-10 titles**: Ranking Engineer ×1, Senior AI Engineer ×2, Applied ML Engineer ×1, Applied Scientist ×1, Research Engineer - ML ×2, NLP Engineer ×1, ML Engineer ×2

The keyword baseline selects well on title keywords but is less effective at discriminating by behavioral availability, production evidence, and consulting-firm career history. Our model incorporates all three via the scoring components and RRF semantic retrieval.

---

## 6. Honeypot Safety

22 candidates in the synthetic dataset were flagged as honeypots (1.1% of total). None appear in the top-100 ranked output. The honeypot multiplier (×0.05 = 95% score reduction) collapses their final scores well below any legitimate candidate.

Honeypot detection trigger rates (across flagged candidates):
- Timeline overlap (>90 days): primary trigger
- All-maxed behavioral signals: secondary trigger
- Duration inflation: secondary trigger

---

## 7. Archetype Discrimination Test

The test suite verifies the following inequalities hold:

| Comparison | Margin | Status |
|-----------|--------|--------|
| Ideal ML engineer ≥ 0.70 | — | ✓ |
| Keyword stuffer (HR) ≤ 0.40 | — | ✓ |
| Ideal > keyword stuffer | >0.30 gap | ✓ |
| Active candidate > inactive (same profile) | >0.10 gap | ✓ |
| Consulting-only penalized vs product-company | >0.20 gap | ✓ |
| CV specialist (no NLP) penalized | <0.50 score | ✓ |

---

## 8. Performance Measurements

| Stage | Time (2,000 candidates) |
|-------|------------------------|
| Candidate parsing | 0.05s |
| Honeypot detection | 0.01s |
| Embedding encoding (cold) | 18.0s |
| FAISS index build | <0.01s |
| TF-IDF fit | 0.08s |
| RRF fusion + retrieve | 0.08s |
| Pool scoring (1,681 candidates) | 0.10s |
| Reasoning generation | 0.01s |
| Export | 0.01s |
| **Total (cold cache)** | **~19.2s** |
| **Total (cache hit)** | **~5.7s** |

---

## 9. Limitations and Risks

### Score compression on synthetic data
All top-100 candidates score between 0.903–0.923, a 0.020-point band. Fine-grained ranking within this band is dominated by small differences in behavioral signals and location. On the real dataset with heterogeneous candidate quality, the score spread should be substantially wider.

### Synthetic data does not reflect real label distribution
The synthetic generator creates clean archetypes. The real dataset may include edge cases: ML engineers at consulting firms, research-only profiles with no production deployment, senior candidates with atypical titles. The evaluation will be updated once real data is received.

### Model vocabulary coverage
`all-MiniLM-L6-v2` was trained on a broad text corpus and handles ML vocabulary well, but may underperform for very new or domain-specific terminology. The TF-IDF path (via RRF) provides complementary lexical matching for exact term matches.

### No ground-truth labels available
The organizer holds the relevance labels. All metrics above are sanity checks and proxy measures. The composite score (NDCG@10×0.5 + NDCG@50×0.3 + MAP×0.15 + P@10×0.05) will be computed by the organizer post-submission.

---

## 10. Recommendations

1. **Do not over-tune to synthetic data.** Score compression and title distribution in the synthetic dataset may not reflect real-data patterns.

2. **When real data arrives**: run `evaluation/eval.py --candidates <real_data>` to check archetype discrimination, then compare top-10 titles. If keyword stuffers appear, increase `title_role` weight in `config/scoring.yaml`.

3. **Monitor behavioral score distribution.** If top-10 candidates have identical behavioral scores (e.g., all scored 1.0), the behavioral signal isn't discriminating. Consider widening the `behavioral_recency.thresholds_days` curve.

4. **Honeypot rate in real data**: The spec says ~80 honeypots in the real dataset. Verify that <10 appear in top-100 before submission.
