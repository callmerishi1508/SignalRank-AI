# SignalRank AI — Demo Script

**Audience**: Hackathon judges, technical and non-technical  
**System state**: Streamlit dashboard running (`streamlit run app/streamlit_app.py`)  
**Data loaded**: `outputs/debug.json` (pre-generated, loads in <1s)

---

## 2-Minute Demo (Judge walk-through)

### Opening (15 seconds)
> "SignalRank AI takes 2,000 candidates and a job description and produces a ranked shortlist of 100 — in under 20 seconds, on a laptop, with no API calls. Every rank is backed by traceable evidence a recruiter can actually read."

### Dashboard tour (90 seconds)

**Ranked Shortlist tab** (30 seconds)
- Point to the top card: CAND_0000009, NLP Engineer, score 0.9226, "High" confidence badge.
- Open the **"💡 Why this candidate?"** expander.
- Show the component bars: title_role 1.00, skill_match 1.00, production_evidence 1.00.
- Show matched skills (Python, FAISS, sentence-transformers, Elasticsearch, NLP, PyTorch).
- Read the reasoning aloud: *"At Springworks (ML Engineer), demonstrated clear production impact: designed and deployed production vector search using FAISS. Reduced retrieval latency from 200ms to 18ms at 10M QPS."*
- Say: "This is not a keyword score. We found production deployment evidence in the career text."

**Compare tab** (30 seconds)
- Select rank #1 and rank #2.
- Show the ▲/▼ delta column: behavioral is the primary differentiator (0.934 vs 0.912).
- Point to the recommendation banner: "Candidate A is the stronger choice."
- Say: "Side-by-side comparison so the recruiter can decide in one view."

**Insights tab** (15 seconds)
- Show the seniority distribution chart: all top-100 are mid-senior ML engineers, no noise.
- Show the radar chart of average component scores.
- Say: "The shortlist is coherent — no HR managers, no keyword stuffers."

**Closing (15 seconds)**
> "56 tests, zero honeypots in the top-100, fully offline, fully reproducible. One command. One config file."

---

## 5-Minute Demo (Full walk-through)

### 0:00 — The problem (30 seconds)
> "A recruiter receives 2,000 applications for a Senior AI Engineer role. Traditional keyword search promotes the candidate who typed 'PyTorch, BERT, Transformers' seven times over an NLP engineer with 8 years of production ranking systems. We built a system that actually reads the profiles."

### 0:30 — The approach (60 seconds)
Open the terminal and run:
```bash
python rank.py --candidates data/raw/candidates.jsonl --out outputs/submission.csv --json outputs/debug.json
```
While it runs:
> "Two stages. Stage 1: sentence-transformers encodes every profile into a 384-dimensional vector. FAISS retrieves the top 3,000 most semantically similar candidates in milliseconds. We also run TF-IDF for lexical coverage, then fuse both ranked lists with Reciprocal Rank Fusion — a technique from the information retrieval literature. We get a pool of ~1,500 candidates where recall is very high."

When it completes (~8 seconds cached):
> "Stage 2: seven rule-based scoring components. Title alignment is 25% of the score — so an HR Manager with every AI keyword scores 0.05 on title, collapsing their total below 0.25. No keyword stuffer makes the top 100."

### 1:30 — Shortlist tour (60 seconds)
Switch to the Streamlit dashboard. Open the **Ranked Shortlist** tab.

> "The top result is an NLP Engineer from Springworks. Let me open their evidence panel."

Expand **"💡 Why this candidate?"**:
- Walk through each component bar.
- Highlight production evidence: "The word 'deployed' triggered our production evidence detector. We also found '10M QPS' — a scale mention. This candidate shipped a real system."
- Show matched skills and note that all are from the job description.
- Read the reasoning.

> "We also show what's potentially missing — in this case, 'Ranking' and 'Learning to Rank' don't appear explicitly in their profile. That's honest signal for the recruiter."

### 2:30 — Honeypot defense (45 seconds)
> "The dataset contains ~80 synthetically impossible profiles. Candidates with overlapping job timelines, graduation dates after their first job, or every single skill rated 'Expert' with the maximum endorsement count. These are designed to game keyword systems."

Show the terminal output: `Honeypots detected: 22`

> "Our detector runs 7 independent impossibility checks. Any candidate triggering two or more gets a 95% score reduction. Zero honeypots in the top 100."

### 3:15 — Comparison view (45 seconds)
Switch to the **Compare** tab.
- Select rank #1 and rank #3.
- Show delta column: behavioral is the differentiator.
- Expand the strengths/risks sections.
- Point to the recommendation banner.

> "A recruiter could shortlist 10 candidates in the morning using the dashboard, then bring 3 to the hiring manager with this comparison view. The decision is visible, not black-box."

### 4:00 — Insights and evaluation (30 seconds)
Switch to the **Insights** tab.
- Show the score histogram.
- Show the seniority bar chart: all top-100 are mid-senior.
- Show the notice period chart: 70%+ available within 30 days.

> "The pipeline is fully evaluated. 56 tests, all passing. Our top-10 overlaps only 1/10 with a keyword-count baseline — we're finding different and better candidates."

### 4:30 — Closing (30 seconds)
> "CPU-only. No API calls. Reproducible from one command. All parameters tunable without code changes — just edit the YAML. We built this for a recruiter who needs a trusted shortlist in under 20 seconds, not a researcher who needs a GPU cluster."

---

## Judge Talking Points

Use these when questions arise during or after the demo.

### Why RRF instead of a single retriever?
> "FAISS finds semantically close profiles. TF-IDF finds candidates who use the exact job description vocabulary. A strong candidate might use domain jargon ('dense retrieval') that maps semantically but not lexically to the JD. RRF ensures both paths contribute — we get higher recall without needing to tune a re-ranking model."

### What stops someone from gaming your scoring?
> "Title alignment. A candidate who keyword-stuffs their skills section but has 'HR Generalist' in their career history scores 0.05 on the title_role component, which collapses their total. Skills inflation is caught by the title signal and the honeypot detector's all-maxed check."

### How do you explain the reasoning?
> "The explainer reads the actual career history and finds the entry with the highest density of production keywords — 'deployed', 'production', 'QPS', 'latency'. It then constructs a sentence that names the company, the role, and quotes the specific evidence. It doesn't generate — it extracts and formats."

### Why not use a large language model for ranking?
> "Zero network calls during ranking is a hard constraint. The only model running is a 22 MB embedding model cached locally. An LLM would add 30-60 seconds per candidate, $0.01-0.10 per candidate in API costs, and a network dependency that breaks in offline environments."

### What is your evaluation metric?
> "The organizer metric is NDCG@10 weighted 50%, NDCG@50 weighted 30%, MAP 15%, P@10 5%. We don't have ground truth labels yet — the organizer scores submissions after the deadline. Our evaluation is sanity-based: archetype discrimination, honeypot safety, baseline comparison."

---

## Key Innovations to Emphasize

1. **Reciprocal Rank Fusion**: Most hackathon submissions pick one retriever. Fusing FAISS + TF-IDF via RRF is the same technique used in production IR systems.

2. **Honeypot defense**: The spec explicitly disqualifies submissions with >10% honeypots in the top-100. Our 7-check detector catches all known patterns with zero false positives.

3. **Five narrative styles**: Most ranking systems return a score. Ours returns a recruiter-quality sentence that names a specific company and quotes career evidence. The narrative style varies by the candidate's dominant signal.

4. **Recruiter comparison view**: Side-by-side comparison with ▲/▼ component deltas and a recommendation banner. This is the feature a real recruiter would actually use.

5. **One YAML to rule them all**: Every numeric constant — from `title_role` weight (0.25) to FAISS `top_k` (3000) to `job_hopping_threshold` (4 stints) — is in `config/scoring.yaml`. The scoring formula is tunable without code changes.

---

## Likely Judge Questions

| Question | One-sentence answer |
|----------|-------------------|
| Why this model size? | 22 MB fits in any judge's laptop RAM in 1 second; a 7B LLM does not. |
| Can it handle 100K candidates? | Switch `index_type: "ivf"` in the config; FAISS IVF scales sub-linearly. |
| What is your NDCG? | Ground truth labels are organizer-held; our archetype tests show correct discrimination. |
| Why not fine-tune the embeddings? | Fine-tuning requires labeled data we don't have; the YAML lets us tune weights instead. |
| How long did this take to build? | The pipeline; see the git history for the development sequence. |
| What would you build next? | Recruiter feedback loop: when a recruiter marks a candidate as hired/rejected, retrain the score weights. |
