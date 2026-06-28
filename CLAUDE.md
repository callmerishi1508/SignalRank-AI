# CLAUDE.md

This repository is being built for a hackathon challenge focused on **AI-powered candidate ranking**. The goal is to read a job description, understand what the role actually needs, evaluate candidates using the full profile signal, and produce a recruiter-trustworthy ranked shortlist.

Claude Code should treat this file as the operating contract for the entire project.

---

## 1) Mission

Build a complete, working, cleanly structured candidate-ranking system from scratch.

The system must:

* understand job descriptions semantically, not just by keyword matching
* analyze candidate profiles holistically
* rank candidates by true fit
* explain why each candidate was ranked where they were
* export results in the organizer-required format
* be easy to run, test, and demo

This is a hackathon project. Prioritize **clarity, correctness, speed, and demo value** over unnecessary complexity.

---

## 2) Non-negotiable product principles

1. **One fixed architecture.**
   Do not keep redesigning the system. Build the agreed architecture and improve within it.

2. **No overengineering.**
   Avoid unnecessary agents, microservices, message queues, or multi-model orchestration unless absolutely required.

3. **Evidence first.**
   Every score or ranking should be explainable with traceable evidence from the data.

4. **Dataset-driven development.**
   First inspect the organizer datasets, infer the schema, and adapt the pipeline to the actual files.

5. **Production-grade basics.**
   Clean code, clear structure, reproducible runs, defensive error handling, and readable outputs matter more than fancy abstractions.

6. **Judge experience matters.**
   The UI and deck should make the system easy to understand in under 2 minutes.

---

## 3) Target solution architecture

Use a lean hybrid pipeline:

* **Job understanding layer**

  * extract structured requirements from the JD
  * identify must-have skills, nice-to-have skills, seniority, domain, responsibilities, and constraints

* **Candidate normalization layer**

  * parse profiles into a consistent internal schema
  * clean and standardize experience, skills, education, projects, and activity signals

* **Retrieval layer**

  * create semantic embeddings for JDs and candidate profiles
  * retrieve candidate subsets using semantic similarity and structured filters

* **Ranking layer**

  * combine semantic match, structured feature match, and hard rules
  * produce a final ranking score

* **Explainability layer**

  * attach reasons, matched evidence, and risk flags to each candidate

* **Export layer**

  * generate the final ranked output file in the required format

This architecture is fixed unless a dataset constraint makes a small adapter change necessary.

---

## 4) What to build

### Core user flow

1. Load dataset files.
2. Load a job description.
3. Parse and understand the JD.
4. Parse candidate profiles.
5. Rank candidates.
6. Show shortlist with evidence.
7. Export ranked output.

### Product deliverables

* working codebase in GitHub
* runnable local app or demo interface
* evaluation pipeline
* ranked output file
* PDF deck explaining approach
* clean README with setup and usage

---

## 5) Required implementation order

Follow this order unless the user explicitly changes direction:

1. Inspect datasets and required output schema
2. Build data ingestion and schema inference
3. Build normalization/cleaning pipeline
4. Build JD understanding module
5. Build candidate understanding module
6. Build retrieval and ranking logic
7. Build explainability and evidence extraction
8. Build export generator
9. Build evaluation scripts/notebooks
10. Build UI/demo layer
11. Build documentation
12. Run smoke tests and end-to-end validation

Do not start polishing UI before the ranking pipeline is working.

---

## 6) Codebase structure

Use a simple, readable layout. Example:

```text
repo/
  app/                # UI or frontend
  backend/            # API / ranking pipeline
  data/               # sample inputs, schema notes, test fixtures
  evaluation/         # metrics, benchmarks, validation scripts
  scripts/            # utilities and one-off runners
  outputs/            # generated rankings and reports
  docs/               # architecture, notes, deck source, screenshots
  tests/              # unit and integration tests
  README.md
  CLAUDE.md
```

If the chosen stack differs, preserve the same separation of concerns:

* ingestion
* normalization
* ranking
* evaluation
* export
* UI

---

## 7) Data handling rules

The organizer dataset is the source of truth.

When working with data:

* inspect column names and types first
* note missing values and duplicate rows
* identify text fields that need normalization
* identify labels if present
* identify the relationship between jobs and candidates
* build adapters for the actual schema, not an assumed schema

Do not hardcode assumptions about file names or column names until they are verified.

### Data validation must include

* file readability
* schema detection
* null checks
* duplicate checks
* text cleaning sanity checks
* output schema validation
* row-count checks after transformations

---

## 8) Ranking logic rules

The ranking system should combine:

* semantic similarity between JD and candidate profile
* structured skill overlap
* required experience match
* domain alignment
* education or certification signals if relevant
* behavioral/activity signals if present in the dataset
* penalty for missing must-have constraints

Recommended approach:

* use hard filters only for truly mandatory constraints
* use soft scoring for everything else
* keep the scoring formula understandable
* store score breakdowns for debugging and explanation

### Important

Do not use keyword matching alone as the main ranking method.

---

## 9) Explainability rules

For each shortlisted candidate, provide:

* rank
* total score
* major matched skills
* matched experience themes
* strongest supporting evidence
* missing or weak areas
* confidence / caution note if useful

The explanation should be concise, recruiter-friendly, and grounded in actual extracted signals.

Avoid vague phrasing like:

* "strong fit" without evidence
* "best candidate" without reason
* "high potential" without support

---

## 10) UI/UX rules

The UI should feel like a professional recruiter dashboard.

### Design priorities

* clean
* minimal
* trustable
* easy to scan
* fast to demo

### Suggested screens

* upload / input screen
* ranking dashboard
* candidate detail panel
* export / download area
* evaluation summary

### UI rules

* one main call to action
* no clutter
* use tables/cards intelligently
* show why a candidate was ranked where they were
* make filters obvious but not excessive

---

## 11) Documentation requirements

Keep documentation short, accurate, and useful.

### Required docs

* `README.md` with setup, run, and usage instructions
* architecture overview
* data schema notes
* evaluation method
* export format notes
* any assumptions made about the dataset

### README must include

* what the system does
* how to install dependencies
* how to run the app
* how to run evaluation
* how to generate output files
* example inputs and outputs

---

## 12) Testing requirements

Test the project as a real product.

### Minimum tests

* data loader test
* schema validation test
* JD parser test
* candidate parsing test
* ranking output format test
* end-to-end smoke test

### If labels exist

Add evaluation tests for:

* precision@k
* recall@k
* nDCG@k
* MRR

### If labels do not exist

Add sanity checks for:

* ranking stability
* explanation quality
* output completeness
* baseline comparison against a simple keyword model

---

## 13) Output file rules

The final ranked output must:

* follow the organizer's provided format exactly
* include required IDs and ranking fields
* be deterministic and reproducible
* be validated before submission

If the format is unclear, inspect the organizer template before coding the exporter.

---

## 14) Model and dependency policy

Use the simplest tools that solve the problem well.

Preferred stack characteristics:

* lightweight
* reproducible locally
* easy to package
* easy to debug

Avoid:

* unnecessary model cascades
* hidden dependencies
* heavyweight orchestration frameworks
* unstable experimental features

If a model/API is used, document:

* purpose
* input
* output
* fallback behavior

---

## 15) Development style rules

* Write readable code first.
* Prefer small, focused modules.
* Use descriptive names.
* Add comments only where they help clarity.
* Keep functions short.
* Centralize constants and configuration.
* Handle errors with useful messages.
* Avoid silent failures.
* Log important pipeline stages.

### Good code habits

* validate inputs early
* isolate transformation logic
* make ranking reproducible
* keep export formatting separate from ranking logic
* use type hints where helpful

---

## 16) What not to do

Do not:

* rewrite the project architecture repeatedly
* add features that do not improve ranking quality or judge clarity
* build unnecessary backend complexity
* ignore the dataset schema
* assume labels or columns that were not verified
* ship unexplained scores
* leave broken scripts or placeholder files
* overfocus on UI while the pipeline is incomplete

---

## 17) Progress discipline

Work in a build-test-fix loop.

For every major change:

1. implement the change
2. run the relevant test or smoke check
3. confirm the result
4. only then continue

Do not accumulate large unverified changes.

---

## 18) If uncertain

When something is ambiguous:

* inspect the dataset
* inspect the output template
* check existing repo files
* prefer the organizer's format over assumptions
* ask the user before making architectural changes

Do not silently invent requirements.

---

## 19) Acceptance criteria

The project is complete only when all of the following are true:

* the pipeline runs end to end
* candidate rankings are generated successfully
* output file matches required format
* explanations are included and readable
* README is complete
* deck PDF is prepared
* basic tests pass
* demo is understandable without extra explanation

---

## 20) Final delivery standard

By the end, the repo should feel like a polished hackathon submission:

* clean structure
* real ranking logic
* convincing evidence
* professional UI
* reproducible results
* submission-ready output

This project is meant to look like something a recruiter could actually use.
