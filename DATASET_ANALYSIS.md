# DATASET ANALYSIS — SignalRank AI
**Generated:** 2026-06-26  
**Challenge:** Redrob Intelligent Candidate Discovery & Ranking Challenge

---

## 1. File Inventory

| File | Location | Size | Status | Role |
|------|----------|------|--------|------|
| `candidate_schema.json` | `data/raw/` | ~8 KB | Present | Defines expected structure of every candidate record |
| `job_description.md` | `data/raw/` | ~5 KB | Present | Target JD (Senior AI Engineer, Founding Team) |
| `output_template.csv` | `data/raw/` | ~8 KB | Present | Baseline sample output — 100 ranked rows |
| `submission_metadata_template.yaml` | `data/raw/` | ~3 KB | Present | Submission manifest template |
| `submission_spec.md` | `docs/` | ~6 KB | Present | Authoritative format rules and scoring spec |
| `redrob_signals_doc.md` | `docs/` | ~3 KB | Present | Reference for 23 behavioral signals |
| `validate_submission.py` | `scripts/` | ~5 KB | Present | Organizer-provided CSV format validator |
| **`candidates.jsonl`** | `data/raw/` | 5.1 MB | **Synthetic (2,000 records)** | Organizer dataset NOT yet received — current file is generated test data |

> **Critical note:** The `candidates.jsonl` file currently in the repository is synthetically generated for pipeline testing. The actual organizer dataset has not been provided. All statistics below describe the synthetic dataset.

---

## 2. Schema Inventory

### 2a. Top-Level Candidate Record Structure

```
{
  candidate_id   : "CAND_XXXXXXX"   REQUIRED — 7-digit zero-padded ID
  profile        : { ... }           REQUIRED — biographical signals
  career_history : [ ... ]           REQUIRED — 1–10 job entries
  education      : [ ... ]           REQUIRED — 0–5 entries (array, may be empty)
  skills         : [ ... ]           REQUIRED — 0+ skill objects
  redrob_signals : { ... }           REQUIRED — 23 platform behavioral signals
  certifications : [ ... ]           OPTIONAL — 7.7% coverage in synthetic data
  languages      : [ ... ]           OPTIONAL — 0% coverage in synthetic data
}
```

Field coverage across 2,000 synthetic candidates:

| Field | Records present | Coverage |
|-------|----------------|----------|
| `candidate_id` | 2000 | 100% |
| `profile` | 2000 | 100% |
| `career_history` | 2000 | 100% |
| `education` | 2000 | 100% |
| `skills` | 2000 | 100% |
| `redrob_signals` | 2000 | 100% |
| `certifications` | 154 | 7.7% |
| `languages` | 0 | 0% |

### 2b. Profile Sub-Schema

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `anonymized_name` | string | required | No PII; always present |
| `headline` | string | required | 1-line professional tagline |
| `summary` | string | required | Multi-sentence bio |
| `location` | string | required | City / region |
| `country` | string | required | All synthetic records: `"India"` |
| `years_of_experience` | float | 0–50 | Range in synthetic data: 2.0–12.0, mean 6.2 |
| `current_title` | string | required | Most discriminative field for role alignment |
| `current_company` | string | required | — |
| `current_company_size` | enum | required | 8 buckets: 1-10 through 10001+ |
| `current_industry` | string | required | — |

### 2c. Career History Sub-Schema (per entry)

| Field | Type | Notes |
|-------|------|-------|
| `company` | string | required |
| `title` | string | required |
| `start_date` | date string | YYYY-MM-DD format |
| `end_date` | date string or null | null = current role |
| `duration_months` | integer ≥ 0 | pre-computed; must match start/end delta |
| `is_current` | boolean | exactly one entry should be true per candidate |
| `industry` | string | — |
| `company_size` | enum | same 8-bucket enum as profile |
| `description` | string | most useful text for production-evidence scoring |

Career entry counts in synthetic data: min=1, max=3, mean=1.2  
No career entries have an empty `description`.

### 2d. Education Sub-Schema

| Field | Type | Notes |
|-------|------|-------|
| `institution` | string | required |
| `degree` | string | required |
| `field_of_study` | string | required |
| `start_year` | integer | 1970–2030 |
| `end_year` | integer | 1970–2035 |
| `grade` | string or null | Optional; GPA or percentage |
| `tier` | enum | tier_1 / tier_2 / tier_3 / tier_4 / unknown |

Education tier distribution (synthetic): tier_1=275, tier_2=1215, tier_3=510, tier_4=0, unknown=0  
One education record per candidate in the synthetic dataset (schema allows 0–5).

### 2e. Skills Sub-Schema

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | free text skill name |
| `proficiency` | enum | beginner / intermediate / advanced / expert |
| `endorsements` | integer ≥ 0 | self-reported endorsement count |
| `duration_months` | integer ≥ 0 | months of active use |

Skills per candidate: min=1, max=10, mean=6.8  
Proficiency distribution: expert 29%, advanced 31%, intermediate 27%, beginner 13%

### 2f. Redrob Signals (23 behavioral fields)

| Signal | Range | Ranking Relevance | Notes |
|--------|-------|-------------------|-------|
| `profile_completeness_score` | 0–100 | Low | Suspicious if exactly 100 (honeypot flag) |
| `signup_date` | date | None | — |
| `last_active_date` | date | **HIGH** | Proxy for availability; >6 months = effectively inactive |
| `open_to_work_flag` | bool | **HIGH** | Explicit availability signal |
| `profile_views_received_30d` | int ≥ 0 | Low | Recruiter-side demand signal; noisy |
| `applications_submitted_30d` | int ≥ 0 | Low | Job-seeking activity; too high may indicate desperation |
| `recruiter_response_rate` | 0.0–1.0 | **HIGH** | < 0.10 = effectively un-contactable |
| `avg_response_time_hours` | float ≥ 0 | Medium | Lower = more responsive |
| `skill_assessment_scores` | dict[str→0-100] | **HIGH** | Verified skill proof; strongest trust signal |
| `connection_count` | int ≥ 0 | Low | — |
| `endorsements_received` | int ≥ 0 | Medium | Volume endorsement count |
| `notice_period_days` | 0–180 | **HIGH** | > 90 = significant hiring friction |
| `expected_salary_range_inr_lpa` | {min, max} | Medium | Scope for budget fit |
| `preferred_work_mode` | enum | Medium | JD specifies hybrid |
| `willing_to_relocate` | bool | Medium | JD allows major Indian metros |
| `github_activity_score` | -1 to 100 | HIGH | -1 = no GitHub linked; 0+ = activity score |
| `search_appearance_30d` | int ≥ 0 | Low | — |
| `saved_by_recruiters_30d` | int ≥ 0 | Low | — |
| `interview_completion_rate` | 0.0–1.0 | HIGH | Low = unreliable for scheduling |
| `offer_acceptance_rate` | -1 to 1.0 | Medium | -1 = no prior offers |
| `verified_email` | bool | Low | — |
| `verified_phone` | bool | Low | — |
| `linkedin_connected` | bool | Low | — |

Behavioral signal distribution (synthetic):
- `open_to_work_flag = True`: 78.7%
- `github_activity_score = -1`: 25.5%
- Notice period: 0-15 days = 0.8%, 16-30 = 22.4%, 31-60 = 32.4%, 61-90 = 44.5%, 91+ = 0%
- Work mode: remote 33.9%, hybrid 33.4%, flexible 32.7%

---

## 3. Relationships Between Datasets

There is a single dataset (`candidates.jsonl`) representing candidates to be ranked against one fixed job description (`job_description.md`).

- **1 JD → N candidates**: Each candidate is scored against the single target JD.
- **No cross-candidate relationships**: Candidate records are independent (no references between records).
- **No label file**: Ground-truth relevance scores are not provided — the organizer holds them for scoring.
- **Submission maps to candidates**: Output CSV `candidate_id` values must exactly match IDs in `candidates.jsonl`.

---

## 4. Missing Values Analysis

### Required Fields
No missing values in any required field across the 2,000 synthetic candidate records. The organizer dataset is expected to be similarly complete (it is synthetically generated by the organizer per the challenge spec).

### Optional Fields with Significant Absence
| Field | Missing | Notes |
|-------|---------|-------|
| `certifications` | 92.3% | Optional; provide signal bonus when present |
| `languages` | 100% | Optional; not scored in current pipeline |
| `education[].grade` | ~60% | Optional per schema; not used in scoring |
| `redrob_signals.github_activity_score = -1` | 25.5% | Treated as "no GitHub" — mild negative |
| `redrob_signals.offer_acceptance_rate = -1` | Present | Treated as neutral |
| `career_history[].end_date = null` | Present (current roles) | Correctly handled as REFERENCE_DATE |

---

## 5. Duplicate Analysis

- **candidate_id duplicates**: 0 found across all 2,000 records.
- **Profile-level semantic duplicates**: Not checked (out of scope; organizer dataset is synthetic so duplicates are unlikely).

---

## 6. Label Availability

**No ground-truth labels are provided.**

The organizer evaluates submitted rankings against a hidden relevance-tier mapping using:

| Metric | Weight |
|--------|--------|
| NDCG@10 | 50% |
| NDCG@50 | 30% |
| MAP | 15% |
| P@10 | 5% |

**Composite score** = 0.50 × NDCG@10 + 0.30 × NDCG@50 + 0.15 × MAP + 0.05 × P@10

Since no labels exist locally, evaluation relies on:
1. Sanity checks (scores monotonic, ranks unique, no honeypots in top 100)
2. Archetype discrimination tests (ideal ML engineer >> keyword stuffer)
3. Baseline comparison (our model vs naive keyword-count model)
4. Post-submission leaderboard feedback

---

## 7. Submission Format Analysis

### Required output: `<team_id>.csv`

```
candidate_id,rank,score,reasoning
CAND_XXXXXXX,1,0.9920,"1-2 sentence justification"
...
CAND_XXXXXXX,100,0.2000,"..."
```

Hard rules (auto-rejection if violated):
- Exactly 100 data rows (+ 1 header)
- Ranks 1–100 used exactly once
- Each `candidate_id` appears exactly once
- All `candidate_id` values must exist in `candidates.jsonl`
- `score` must be non-increasing as rank increases
- Tie-break on equal scores: `candidate_id` ascending (lexicographic)
- UTF-8 encoding
- Reasoning field is optional but strongly recommended (used in Stage 4 manual review)

Compute constraints:
- ≤5 minutes wall-clock
- ≤16 GB RAM
- CPU only — no GPU
- No network access during ranking (no API calls to OpenAI, Anthropic, etc.)
- ≤5 GB disk intermediate state

### Honeypot rule
Dataset contains ~80 "honeypot" candidates with impossible profiles forced to relevance tier 0. If >10% of your top 100 are honeypots → **disqualification**.

---

## 8. Current Score Distribution

Based on scoring all 2,000 synthetic candidates:

| Percentile | Score |
|------------|-------|
| p1 (top 1%) | 0.8996 |
| p5 (top 5%) | 0.8882 |
| p10 | 0.8018 |
| p25 | 0.6112 |
| p50 (median) | 0.5824 |
| p75 | 0.2194 |
| p90 | 0.2012 |
| p99 | 0.1948 |

Score bands:
- > 0.80: 211 candidates (10.6%) — strong ML/AI profiles
- 0.50–0.80: 873 candidates (43.7%) — partial fit or behavioral penalties
- < 0.50: 916 candidates (45.8%) — wrong domain, consulting-only, or honeypot

Score by archetype (mean):
| Title | Mean Score | Min | Max |
|-------|-----------|-----|-----|
| Research Engineer - ML | 0.8757 | 0.8650 | 0.8898 |
| Applied ML Engineer | 0.8750 | 0.8649 | 0.8878 |
| Senior AI Engineer | 0.8729 | 0.8675 | 0.8802 |
| Senior ML Engineer | 0.8705 | 0.8644 | 0.8783 |
| HR Manager | ~0.200 | — | — |
| Content Writer | ~0.195 | — | — |
| Keyword stuffer (any wrong title) | ~0.200 | — | — |

**Known gap:** Top-100 scores are compressed into a 0.025-point range (0.8643–0.8898). Within-shortlist discrimination is weak — all top-100 candidates look similar to the ranker. This is partly a synthetic-data artifact (all true-positives generated from similar templates), but calibration may need improvement for the real dataset.

---

## 9. Identified Challenges and Edge Cases

### 9a. Keyword-Stuffing Trap
The JD explicitly warns that the dataset contains candidates who list many AI keywords (Python, ML, NLP, FAISS) in their skills but work as HR Managers, Content Writers, or Accountants. Naive keyword-matching rankers will rank these candidates near the top. **Current system correctly penalizes them (−45% penalty for wrong role domain).**

### 9b. Honeypot Candidates (~80 in real dataset)
Profiles with subtly impossible timelines or all-maximum signals. Submissions with >10% honeypots in top 100 are disqualified. **Current detection handles: overlapping jobs, graduation-after-career-start, experience-year contradictions, all-maxed behavioral signals.**

### 9c. Inactive Strong Candidates
A technically perfect ML engineer who hasn't logged in for 6+ months with <10% recruiter response rate is behaviorally unavailable. The JD explicitly says to downweight these. **Current system applies behavioral scoring with recency-based decay.**

### 9d. Consulting-Only Career Trap
Candidates with ML skills but entire careers at TCS/Infosys/Wipro/Accenture are explicitly disqualified by the JD. **Current system applies −30% penalty for >85% consulting career.**

### 9e. CV/Robotics Without NLP
Computer vision specialists or robotics engineers without NLP/IR experience should be penalized. **Current system checks for CV/speech/robotics skills without corresponding NLP skills.**

### 9f. Score Compression in Top-100
When the real dataset arrives, many candidates may cluster near similar scores, making small differences in the scoring formula highly impactful for NDCG@10. The scoring formula needs to be more discriminative within the shortlist, not just between archetypes.

### 9g. Streamlit File Upload Bug
The Streamlit UI's "Run Pipeline" upload handler has a file-parsing error when users upload the JSONL file through the browser (observed in logs: JSON parse errors on every line). The uploaded file bytes are not being decoded correctly before writing to the temp file. **Needs fix.**

### 9h. Organizer Dataset Format Uncertainty
The actual `candidates.jsonl` from the organizer may have slight format differences from our synthetic data — different null handling, encoding edge cases, or additional fields. The pipeline should be robust to unknown extra fields and gracefully handle malformed records.

---

## 10. Required Preprocessing Strategy

1. **Load**: Stream JSONL line-by-line (memory-efficient for 100K+ records)
2. **Validate**: Required fields present, `candidate_id` format matches `CAND_XXXXXXX`
3. **Normalize**: Lowercase skill names, title strings for matching; parse all dates
4. **Compute derived fields**:
   - `days_since_active` from `last_active_date`
   - Career duration fractions (ML/AI %, consulting %)
   - Consulting-only flag
   - CV/speech/robotics domain flag
5. **Honeypot check**: Timeline overlaps, impossible dates, all-maximum signals
6. **Score**: 7-component rule-based + TF-IDF semantic blend
7. **Sort**: By score descending, candidate_id ascending for ties
8. **Select top 100** and generate reasoning
9. **Export**: Validate CSV before writing
