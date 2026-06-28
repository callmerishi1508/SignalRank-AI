Submission Specification - Redrob Hackathon v4

**Read this carefully before submitting.** Submissions that don't match this spec will be auto-rejected by the validator without scoring.

# 1. What you're submitting

A CSV file ranking the top **100 candidates** from candidates.jsonl for the released job description.

**Rank 1 is the best fit; rank 100 is the 100th best fit.**

You do _not_ rank candidates 101 onward - only the top 100.

# 2. File format

## Filename

Your team's registered participant ID, with .csv extension. For example: team_xxx.csv.

## Encoding

UTF-8.

## Required columns (in this order)

candidate_id,rank,score,reasoning

| **Column**   | **Type**    | **Required?**                           | **Description**                                                                                                                          |
| ------------ | ----------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| candidate_id | string      | Yes                                     | The CAND_XXXXXXX ID from candidates.jsonl                                                                                                |
| rank         | int (1-100) | Yes                                     | The rank position. Must use each integer 1 through 100 exactly once.                                                                     |
| score        | float       | Yes                                     | Your model's score for this candidate. Should be **monotonically non-increasing** as rank increases.                                     |
| reasoning    | string      | Optional but **strongly recommended**   | A 1-2 sentence justification explaining why this candidate is at this rank. Used at Stage 4 (manual review) to evaluate top submissions. |

## Example

candidate_id,rank,score,reasoning
CAND_0042871,1,0.987,"Senior AI Engineer with 7 years building RAG systems at product companies; strong recent engagement and Bangalore-based."
CAND_0019884,2,0.973,"6 years applied ML; previously shipped vector search at scale; matches the 'product over research' profile in the JD."
CAND_0091235,3,0.962,"Strong NLP + retrieval background; some concern on notice period (120 days) but otherwise strong fit."
...
CAND_0007729,100,0.412,"Adjacent skills only - likely below cutoff but included as final filler given experience and engagement signals."

# 3. Rules

## Format

- **Exactly 100 rows of data** (plus 1 header row).
- Each rank (1 through 100) appears **exactly once**.
- Each candidate_id appears **exactly once**.
- Every candidate_id must exist in the released candidates.jsonl.
- score is non-increasing with rank - i.e., score at rank 1 >= score at rank 2 >= ... >= score at rank 100. Ties are allowed.
- If two candidates have the same score, you must still assign unique ranks. Break score ties deterministically using a secondary signal from your model, or by candidate_id ascending.

## Compute constraints

Your code that produces the submission must satisfy the following constraints:

| **Constraint** | **Limit**                                                                                                                  |
| -------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Total runtime  | <= 5 minutes wall-clock                                                                                                    |
| Memory         | <= 16 GB RAM                                                                                                               |
| Compute        | CPU only - **no GPU** during ranking                                                                                       |
| Network        | Off - your ranking code must not make external API calls (no OpenAI, Anthropic, Cohere, Gemini, or any hosted LLM service) |
| Disk           | <= 5 GB intermediate state                                                                                                 |

## Three-submission cap

You may make at most **3 submissions** total during the competition window. Your final entry is your **last valid submission**.

# 4. How submissions are scored

## Metrics

| **Metric**               | **Weight** | **What it measures**                             |
| ------------------------ | ---------- | ------------------------------------------------ |
| NDCG@10                  | 0.50       | Quality of your top-10 picks                     |
| NDCG@50                  | 0.30       | Quality of your top-50 picks                     |
| MAP (Mean Avg Precision) | 0.15       | Precision across all relevance levels            |
| P@10                     | 0.05       | Fraction of top-10 that are "relevant" (tier 3+) |

## Final composite

**Final composite** = 0.50 x NDCG@10 + 0.30 x NDCG@50 + 0.15 x MAP + 0.05 x P@10

# 5. Evaluation pipeline (stages)

| **Stage**                                  | **What happens**                                                                                                                                             | **What gets you eliminated**                                                                             |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------- |
| **1. Format validation**                   | Auto-validator runs on every submission                                                                                                                      | Any spec violation in section 3                                                                          |
| **2. Scoring**                             | Composite computed once on the full hidden ground truth, after submissions close                                                                             | Final score below cutoff for advancement to Stage 3                                                      |
| **3. Code reproduction + honeypot check**  | Top-N submissions: full code repo requested. Ranking step reproduced in sandboxed environment (5min, 16GB, no GPU, no network). Honeypot rate computed.      | Cannot reproduce within compute limits; honeypot rate >10% in top 100; missing or fabricated code repo   |
| **4. Manual review**                       | Reasoning quality (6 checks above). Methodology coherence. Git history authenticity. Code quality.                                                           | Failed reasoning checks; flat git history with no iteration; codebase consists entirely of LLM API calls |
| **5. Defend-your-work interview**          | Top X finalists: 30-minute video call with Redrob engineering. Walk through architecture, defend design choices.                                             | Cannot explain architecture; contradicts submitted code; clearly didn't build it                         |

# 7. Honeypot warning

The dataset contains a small number (~80) of **honeypot candidates** with subtly impossible profiles. These are forced to relevance tier 0 in the ground truth. Submissions with honeypot rate > 10% in top 100 are disqualified.
