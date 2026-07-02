# SignalRank AI — Presentation Deck
## Complete Slide Script with Design Specifications

---

> **Deck purpose:** Hackathon demo + SaaS pitch  
> **Audience:** Judges, recruiters, technical evaluators  
> **Length:** 10 slides · 8–10 minutes  
> **Brand palette:** Navy `#0F172A` · Blue `#2563EB` · Emerald `#10B981` · Slate `#F8FAFC`  
> **Font:** Inter (headings 700–800, body 400–500)  
> **Aspect ratio:** 16:9 widescreen

---

## SLIDE 1 — Title

### Layout
Full-bleed dark background (`#0F172A`). Left-aligned content block occupying 55% of the slide width. Right side: abstract geometric mesh or gradient orb in electric blue (`#2563EB → #7C3AED`) at 30% opacity — decorative, non-distracting.

### Content

**Top-left corner — small label chip**
```
⚡  Redrob AI Challenge 2026
```
Style: Pill badge · Background `#1E3A5F` · Text `#60A5FA` · Font size 11px · Border-radius 20px

**Main headline (H1)**
```
SignalRank AI
```
Style: Font-size 72px · Weight 800 · Color white · Letter-spacing −0.04em · Line-height 1.0

**Accent line below headline**
```
Rank talent by fit, not keywords.
```
Style: Font-size 22px · Weight 400 · Color `#94A3B8` · Margin-top 12px

**Divider**
Thin horizontal line · Width 80px · Color `#2563EB` · Height 3px · Margin 28px 0

**Sub-description (body)**
```
An AI-powered candidate ranking system that reads any job description,
understands what the role actually needs, and produces a recruiter-trustworthy
shortlist — with evidence for every ranking decision.
```
Style: Font-size 16px · Color `#CBD5E1` · Line-height 1.7 · Max-width 520px

**Bottom-left — presenter details**
```
Heena  ·  jvm12@iitbbs.ac.in
github.com/callmerishi1508/SignalRank-AI
```
Style: Font-size 12px · Color `#64748B`

### Speaker Notes
> Open with energy. Pause after saying "SignalRank AI." Let the tagline land — "Rank talent by fit, not keywords" is the core value proposition. Then briefly explain: "In the next 8 minutes I'll show you how we built a pipeline that thinks like a great recruiter — not like a search engine."

---

## SLIDE 2 — The Problem

### Layout
Two-column layout. Left column (60%): content. Right column (40%): a simple visual metaphor — an inverted funnel with the word "KEYWORDS" at the top in red and "Best Candidate" at the bottom crossed out. Keep it minimal vector art, not a photograph.

### Headline
```
Hiring is broken at the retrieval layer.
```
Style: Font-size 36px · Weight 700 · Color `#0F172A` · Letter-spacing −0.02em

### Content — Left Column

**Stat block (3 numbers, large)**

```
75%        of rejected candidates     are qualified — just poorly ranked
6 hours    average recruiter time     spent screening per role
0           signal from keywords      on culture, trajectory, or production fit
```

Style: Stat number in `#2563EB` at 42px weight 800. Label text in `#334155` at 14px.

**Problem bullets**

```
  ✗  ATS systems match job title strings, not actual career trajectories
  ✗  Keyword stuffers rank above real engineers
  ✗  HR Managers with "Python" in skills appear above ML Engineers
  ✗  No explanation — recruiter cannot trust or audit the ranking
  ✗  Every new JD requires manual reconfiguration
```
Style: Red `✗` in `#EF4444`. Text `#334155`. Font-size 15px. Line-height 2.0.

### Speaker Notes
> "The core problem isn't that we don't have enough candidates. We have too many and no reliable way to rank them. Traditional ATS systems treat a job description like a keyword query — whoever has the most matching strings wins. That produces HR Managers ranked above ML Engineers, consulting-only profiles ranked above product engineers, and shortlists that a recruiter cannot audit or explain to a hiring manager."

---

## SLIDE 3 — Our Solution

### Layout
Dark slide (`#0F172A`). Central bold statement at top. Below it: a three-step visual pipeline in horizontal flow — each step is a card with icon, title, and one-line description. Bottom strip: two outcome numbers in large type.

### Headline
```
One pipeline. Any job. Any candidate set.
```
Style: Font-size 40px · Weight 800 · Color white · Centered · Letter-spacing −0.03em

**Sub-headline**
```
SignalRank AI combines semantic understanding with evidence-grounded rules
to rank candidates the way a great technical recruiter would.
```
Style: Font-size 16px · Color `#94A3B8` · Centered · Max-width 640px · Margin auto

### Three-Step Flow Cards

Each card: Background `#1E293B` · Border-radius 12px · Padding 24px · Border-left 4px solid accent color

**Card 1 — Understand**
- Accent: `#2563EB`
- Icon: 🔍
- Title: **"Understand the Role"**
- Body: "Paste or upload any JD. We extract required skills, seniority, experience range, and locations automatically — no LLM, no manual tagging."

**Card 2 — Retrieve**
- Accent: `#7C3AED`
- Icon: ⚡
- Title: **"Retrieve the Right Pool"**
- Body: "FAISS semantic search + TF-IDF lexical search, fused via Reciprocal Rank Fusion. High recall — no strong candidate is missed."

**Card 3 — Rank with Evidence**
- Accent: `#10B981`
- Icon: 📊
- Title: **"Rank with Evidence"**
- Body: "7 evidence-grounded components. Every score is explainable. Every ranking has a recruiter-readable reason."

### Outcome Numbers (Bottom Strip)
Background: `#0F172A` strip with border-top `#1E293B`

```
100K candidates → ranked in 60s        0 honeypots in top-100        56/56 tests pass
```
Style: Numbers in `#10B981` at 28px weight 800. Labels in `#94A3B8` at 13px.

### Speaker Notes
> "Our solution has three layers. First, we understand the job description — any JD, not just the one we were given. Second, we retrieve a high-recall candidate pool using a two-stage system so no strong candidate is filtered out before scoring. Third, we rank with seven evidence components that mirror how a senior technical recruiter evaluates a profile."

---

## SLIDE 4 — How It Works (Architecture)

### Layout
Light background (`#F8FAFC`). Full-width pipeline diagram as the centrepiece. Two rows: top row is the visual pipeline; bottom row is a small legend table.

### Headline
```
Two-stage hybrid pipeline
```
Style: Font-size 32px · Weight 700 · Color `#0F172A`

### Pipeline Diagram (described for designer)

Draw a horizontal left-to-right flow with connecting arrows. Each box is a rounded rectangle.

```
[candidates.jsonl]
        │
        ▼
┌──────────────────┐
│  Candidate        │  ← Normalises 100K profiles into CandidateProfile
│  Parser           │     dataclass · pre-computes career fractions,
│                  │     skill lookups, profile text for embedding
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Honeypot        │  ← 7 independent checks: timeline overlaps,
│  Detector        │     YOE contradictions, all-maxed signals
└────────┬─────────┘
         │
    ┌────┴─────────────────────────┐
    ▼                              ▼
┌─────────────┐          ┌─────────────────┐
│  FAISS      │          │  TF-IDF          │
│  Dense      │          │  Lexical         │
│  Retrieval  │          │  Retrieval       │
│  top-3000   │          │  top-3000        │
└─────┬───────┘          └────────┬─────────┘
      │                           │
      └───────────┬───────────────┘
                  ▼
         ┌────────────────┐
         │  RRF Fusion    │  ← Reciprocal Rank Fusion k=60
         │  ~1500 pool    │     Combines both ranked lists
         └───────┬────────┘
                 ▼
         ┌────────────────┐
         │  7-Component   │  ← title_role 25% · skill_match 20%
         │  Hybrid Scorer │     production 15% · behavioral 15%
         │                │     experience 10% · domain 10% · location 5%
         └───────┬────────┘
                 ▼
         ┌────────────────┐
         │  Explainer     │  ← Recruiter-readable reasoning per candidate
         └───────┬────────┘
                 ▼
         ┌────────────────┐
         │  submission.csv│  ← 100 rows · ranks 1-100 · non-increasing scores
         └────────────────┘
```

**Design note for the actual slide:** Convert the ASCII art above into clean boxes with flat icons. Use color-coding: blue for retrieval stage, purple for fusion, green for scoring, teal for output.

### Scoring Formula (bottom-right inset box)

```
final = (0.75 × rule_score + 0.25 × semantic_sim) × (1 − penalty)
```
Style: Monospace font · Background `#1E293B` · Color `#10B981` · Padding 12px · Border-radius 8px · Font-size 13px

### Speaker Notes
> "The pipeline has five stages. Parsing normalises every profile into a consistent schema. Honeypot detection removes fabricated candidates before they can pollute the pool. Then we run two independent retrieval methods — dense semantic search and lexical TF-IDF — and fuse them so a candidate strong in either method gets into the scoring pool. Finally, the hybrid scorer applies seven weighted components and generates a recruiter-readable explanation for each result."

---

## SLIDE 5 — The Scoring Engine (Deep Dive)

### Layout
Dark slide (`#0F172A`). Left half: vertical bar chart of the 7 components and their weights. Right half: two subsections — penalties table and a sample score breakdown card.

### Headline
```
Evidence-grounded scoring — not a black box.
```
Style: Font-size 32px · Weight 700 · Color white

### Left — Component Weight Chart

Horizontal bar chart. Each bar is a different shade from blue to green. Labels on the left, percentage on the right.

```
Title / Role Fit         ████████████████████████░  25%
Skill Match              ████████████████████░░░░░  20%
Production Evidence      ████████████████░░░░░░░░░  15%
Behavioral Availability  ████████████████░░░░░░░░░  15%
Experience Fit           ████████████░░░░░░░░░░░░░  10%
Domain / Company Fit     ████████████░░░░░░░░░░░░░  10%
Location                 ██████░░░░░░░░░░░░░░░░░░░   5%
```

Style: Bar color gradient left-to-right `#2563EB → #10B981`. Background track `#1E293B`. Percentage label in white weight 600.

**Small note below chart:**
```
All weights configurable in config/scoring.yaml — no code changes needed.
```
Style: Italic · Color `#64748B` · Font-size 12px

### Right Top — Penalty Multipliers Table

Style: Table with alternating row background `#1E293B` / `#0F172A`. Header row `#1D4ED8`.

| Condition | Penalty |
|---|---|
| Wrong role domain (HR/Sales/Marketing) | −45% |
| Consulting-only career (TCS/Infosys etc.) | −30% |
| CV/Speech without NLP overlap | −30% |
| Behaviorally unavailable | −20% |
| Job-hopping (≥4 stints ≤18 months) | −10% |
| Honeypot detected | −95% |

### Right Bottom — Sample Score Card

```
┌─────────────────────────────────────┐
│  Rank #1  ·  Score: 0.892           │
│  Senior ML Engineer @ Flipkart      │
│                                     │
│  Title Fit        ████████████ 0.91 │
│  Skill Match      ███████████░ 0.87 │
│  Production       ████████████ 0.93 │
│  Behavioral       █████████░░░ 0.74 │
│  Experience       ███████████░ 0.88 │
│  Domain           ████████████ 0.90 │
│  Location         █████████░░░ 0.80 │
└─────────────────────────────────────┘
```
Style: Card background `#1E293B` · Border-radius 10px · Border `1px solid #334155`

### Speaker Notes
> "The title alignment score is the most decisive signal — it's 25% of the total. An HR Manager with ten ML keywords in their skills section will score close to zero on this component, collapsing their total score below 0.25. This is intentional. It's the primary defense against keyword stuffing, which is the dominant failure mode in ATS systems. Every penalty has a documented reason — no magic numbers."

---

## SLIDE 6 — What Makes It Different

### Layout
Light background. Three-column card grid. Each card highlights one differentiator with a short headline, one-paragraph explanation, and a concrete example or number. Above the grid: a one-line challenge statement.

### Headline
```
Three things most systems can't do.
```
Style: Font-size 34px · Weight 700 · Color `#0F172A`

### Three Differentiator Cards

**Card 1 — Any JD, Any Role**
- Icon: 📋
- Background: White · Border-top 4px solid `#2563EB`
- Title: **"Works for any job description"**
- Body: "Paste a Google AI Scientist JD, an Amazon SDE JD, or a finance analyst JD — the parser extracts role title, required skills, seniority, and locations automatically. No manual configuration. Switch roles between sessions without restarting."
- Example chip: `"AI Scientist @ Google → parsed in <1s"`

**Card 2 — Resumes, Not Just Structured Data**
- Icon: 📄
- Background: White · Border-top 4px solid `#7C3AED`
- Title: **"Accepts raw resumes from anywhere"**
- Body: "Upload a ZIP of PDFs, a Google Drive folder link, or a JSONL dataset. The resume parser extracts career history, skills, and experience from unstructured text. No special format required from the HR team."
- Example chip: `"PDF → ranked candidate in 3s"`

**Card 3 — Every Ranking is Explainable**
- Icon: 💡
- Background: White · Border-top 4px solid `#10B981`
- Title: **"Recruiter-readable reasoning, not a score"**
- Body: "Each candidate gets a paragraph explaining why they ranked where they did — citing their current role, production evidence, skill gaps, and behavioral signals. A recruiter can defend every shortlist decision to a hiring manager."
- Example chip: `"'Senior ML Engineer at Flipkart (7y ML/AI). Built FAISS-based search serving 100M users…'"`

### Bottom Banner (dark strip)
```
The only system that combines: dynamic JD parsing + resume upload + 7-component evidence scoring + human-readable reasoning
```
Style: Background `#0F172A` · Text white · Font-size 14px · Centered · Padding 16px

### Speaker Notes
> "Three things that differentiate SignalRank from a keyword ATS. First, it's fully dynamic — you don't get a system built for one job description. Any HR team at any company can use it. Second, it accepts raw resumes — the HR team doesn't need to pre-process anything. Upload a folder from Google Drive and the system handles extraction. Third, every ranking is auditable. The recruiter doesn't just get a number, they get a paragraph they can actually read and stand behind."

---

## SLIDE 7 — Live Demo

### Layout
Dark slide. Full width. This is the demo slide — minimal text, mostly used as a visual placeholder during a live demo. If slides are shared as a PDF, include three static dashboard screenshots.

### Headline
```
Live Demo
```
Style: Font-size 48px · Weight 800 · Color white · Centered

**Sub-label**
```
signalrank-ai.streamlit.app
```
Style: Font-size 18px · Color `#60A5FA` · Centered · Underlined

### Three Demo Screenshot Placeholders

If presenting live, replace with actual browser window. If PDF:

**Screenshot 1 — Candidate Shortlist View**
- Caption: "Ranked candidate cards with score pills, confidence badges, and one-click full profile"
- Border: `2px solid #334155` · Border-radius 12px

**Screenshot 2 — Full Profile Modal**
- Caption: "Complete score breakdown, behavioral signals, matched/missing skills, and career evidence"
- Border: `2px solid #334155` · Border-radius 12px

**Screenshot 3 — Key Differentiator Panel**
- Caption: "Per-candidate 'Why this rank' — components vs. cohort average with +/− delta"
- Border: `2px solid #334155` · Border-radius 12px

### Demo Flow Script (for presenter)

```
1.  Open sidebar → "Paste / Upload JD" tab
2.  Paste Google AI Scientist JD
3.  Click "Parse & Use This JD" → show extracted profile (skills, seniority, locations)
4.  Switch to "ZIP of Resumes" tab → upload sample resumes ZIP
5.  Click "Parse & Rank Resumes" → show progress bar → show ranked results
6.  Click on Rank #1 → open Full Profile modal → walk through score breakdown
7.  Open "Key Differentiator" section → show why this candidate leads
8.  Click "Save to Shortlist" → navigate to Saved tab → export CSV
```

### Speaker Notes
> "I'll walk through the full flow in under two minutes. Watch what happens when I paste a completely different JD — notice the system re-extracts the role profile instantly and uses it for scoring. This isn't a hardcoded demo — it's a real pipeline running against a real candidate set."

---

## SLIDE 8 — Results

### Layout
Light background. Top half: three large metric cards side-by-side. Bottom half: two-column comparison — "keyword model baseline" vs "SignalRank AI."

### Headline
```
Results on the organizer's 100K candidate dataset.
```
Style: Font-size 30px · Weight 700 · Color `#0F172A`

### Three Metric Cards (Top)

**Card 1**
- Big number: `60s`
- Label: "Full ranking pipeline (cached run)"
- Sub: "First run: ~848s for 100K embedding pre-computation, saved to disk"
- Color: `#2563EB`

**Card 2**
- Big number: `0`
- Label: "Honeypots in top-100"
- Sub: "7-check detection system. >10% honeypots = disqualification."
- Color: `#10B981`

**Card 3**
- Big number: `56/56`
- Label: "Tests pass"
- Sub: "Unit + integration + end-to-end. Config, parser, retrieval, scorer, pipeline."
- Color: `#7C3AED`

### Comparison Table (Bottom)

| | Keyword Baseline | SignalRank AI |
|---|---|---|
| **Method** | Skill keyword count | Hybrid semantic + rule-based |
| **HR Manager ranked in top-10?** | Yes (keyword stuffing) | No (title_role score < 0.05) |
| **Consulting-only ranked high?** | Yes | No (domain penalty −30%) |
| **Explainability** | None | Full paragraph per candidate |
| **Custom JD support** | Manual reconfigure | Paste & parse in <1s |
| **Resume input** | JSONL only | JSONL + ZIP + Google Drive |

Style: Table header background `#1E3A5F` text white. Alternating rows `#F8FAFC` / white. SignalRank AI column has left border `3px solid #10B981`.

### Speaker Notes
> "The 60-second ranking time is after a one-time embedding pre-computation. The important number is zero honeypots — the organizer explicitly disqualifies any submission with more than 10% honeypots in the top 100. Ours has zero. The comparison table shows the most important practical difference: a keyword baseline will promote HR Managers who stuffed ML terms into their profile. SignalRank collapses that score immediately through title alignment."

---

## SLIDE 9 — SaaS Potential & Roadmap

### Layout
Two-column layout. Left: current state and immediate extensions. Right: roadmap timeline with three phases.

### Headline
```
Beyond the hackathon — a real recruiting tool.
```
Style: Font-size 32px · Weight 700 · Color `#0F172A`

### Left Column — What It Already Does as a SaaS

```
✓  Any company, any JD — fully dynamic
✓  Three candidate input modes (JSONL / ZIP / Google Drive)
✓  Session-isolated outputs — safe for concurrent users
✓  Recruiter dashboard with filters, shortlist, notes
✓  Export ranked CSV per session
✓  Production-ready Docker container
✓  Environment-configurable data paths
```
Style: Green `✓` in `#10B981`. Text `#334155`. Line-height 2.0.

**Deployment chip strip:**
```
[Streamlit Cloud]  [Railway]  [Render]  [Google Cloud Run]  [Docker]
```
Style: Small pill chips · Background `#EFF6FF` · Text `#1D4ED8` · Border `1px solid #BFDBFE`

### Right Column — Roadmap

**Phase 1 — Now (complete)**
- Timeline chip: `v1.0 · July 2026`
- Items: Two-stage pipeline, 7-component scorer, explainability, resume parser, Drive integration, Streamlit dashboard

**Phase 2 — Next 30 days**
- Timeline chip: `v1.1 · August 2026`
- Items: Multi-role support (rank for multiple JDs simultaneously), batch resume processing (100+ PDFs), ATS integrations (Greenhouse, Lever API connectors), recruiter feedback loop (thumbs up/down → re-ranks)

**Phase 3 — 90 days**
- Timeline chip: `v2.0 · Q4 2026`
- Items: Multi-tenant auth (company workspaces), persistent candidate database, longitudinal tracking (candidate re-evaluated across multiple roles), bias audit report per ranking run

Style: Each phase is a card with left border in `#2563EB` / `#7C3AED` / `#10B981`. Phase title in matching color.

### Speaker Notes
> "What we built is already a usable SaaS product — not just a hackathon demo. Any HR team can go to the deployed URL, paste their JD, upload their candidate set, and get a ranked shortlist in seconds. The roadmap focuses on three things: multi-role support for in-house recruiting teams, ATS integrations so it fits into existing workflows, and a feedback loop so the system improves with recruiter input."

---

## SLIDE 10 — Close

### Layout
Full-bleed dark background (`#0F172A`). Centered layout. Large tagline. Three links. QR code (optional, bottom-right).

### Top Badge
```
⚡  Redrob AI Challenge 2026  ·  SignalRank AI
```
Style: Pill · Background `#1E3A5F` · Text `#60A5FA` · Font-size 12px · Centered

### Main Headline
```
Rank talent by fit.
Not by who optimised their resume for a search engine.
```
Style: Font-size 48px · Weight 800 · Color white · Centered · Letter-spacing −0.03em · Line-height 1.25

**Accent line**
```
SignalRank AI makes candidate ranking auditable, explainable, and fair.
```
Style: Font-size 18px · Color `#94A3B8` · Centered · Margin-top 16px

### Divider
Thin horizontal rule · Width 120px · Color `#2563EB` · Centered · Margin 40px auto

### Three Links (centered row)

```
🌐 Live App          📂 GitHub Repo          📧 Contact
share.streamlit.io   github.com/callmerishi   jvm12@iitbbs.ac.in
                     1508/SignalRank-AI
```
Style: Each link in a subtle dark card (`#1E293B` · border-radius 10px · padding 16px 24px). Icon + label in `#60A5FA`. URL in `#94A3B8`.

### Bottom-left — Tech Stack Chips
```
[Python 3.11]  [sentence-transformers]  [FAISS]  [Streamlit]  [scikit-learn]
```
Style: Small pill chips · Background `#1E293B` · Text `#94A3B8` · Border `1px solid #334155`

### Speaker Notes
> "SignalRank AI demonstrates that ranking candidates by actual fit — career trajectory, production evidence, behavioral availability — is not just possible but fast, explainable, and deployable. The pipeline runs in 60 seconds on 100K candidates, produces zero honeypots, and gives a recruiter a paragraph they can read and defend. Thank you."

---

## Appendix A — Additional Slides (if asked)

### A1 — Honeypot Detection

**Title:** `How we catch fabricated profiles`

**Content — 7 Detection Checks:**

| Check | What it detects |
|---|---|
| Career timeline overlap | Candidate claims two full-time roles at the same time |
| YOE vs. actual span | States "10 years experience" but career history spans only 4 years |
| Graduation contradiction | Graduated in 2015 but started career in 2010 |
| All-expert profile | Every skill marked "Expert" with 50 endorsements each |
| All-maxed behavioral signals | Every behavioral score at the maximum value simultaneously |
| Duration inflation | Single role claims 25 years of duration |
| Impossible education dates | PhD completed before bachelor's degree ended |

**Penalty:** −95% score multiplier (effectively ranks them last)

---

### A2 — Technical Stack

**Title:** `Stack and dependencies`

| Layer | Technology | Purpose |
|---|---|---|
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 | 384-dim dense vectors, 22MB, CPU-only |
| Vector search | faiss-cpu IndexFlatIP | Exact inner-product search, 100K vectors in RAM |
| Lexical search | scikit-learn TfidfVectorizer | Unigram + bigram, 8K features |
| Fusion | Reciprocal Rank Fusion k=60 | Combines FAISS + TF-IDF ranked lists |
| Scoring | Custom Python, config-driven | 7 components, all thresholds in YAML |
| UI | Streamlit 1.50 | @st.dialog, session state, tabs |
| PDF parsing | pdfplumber | Resume text extraction |
| DOCX parsing | python-docx | Resume text extraction |
| Drive download | gdown | Public Drive folders, no OAuth |
| Config | PyYAML | All numeric constants externalised |
| Tests | pytest | 56 tests, unit + integration + e2e |

**Zero network calls during ranking.** All models run locally.

---

### A3 — Why Not a Pure LLM Approach?

**Title:** `Why not just ask GPT to rank them?`

| Consideration | LLM-only approach | SignalRank hybrid |
|---|---|---|
| Cost | ~$0.10 per candidate × 100K = $10,000 per run | $0 — fully offline |
| Speed | ~2s per candidate × 100K = 55 hours | 60 seconds cached |
| Reproducibility | Non-deterministic — different result each run | Deterministic and auditable |
| Explainability | "Trust me" reasoning | Evidence-traced score per component |
| Network dependency | Requires internet + API key | Zero network during ranking |
| Data privacy | Candidate data leaves your infrastructure | All data stays local |
| Bias auditability | Cannot inspect the model's decision | Every component weight is visible |

**Verdict:** LLMs are valuable for JD parsing and reasoning generation. They are the wrong tool for the ranking loop itself.

---

## Design System Reference

### Colours

| Token | Hex | Usage |
|---|---|---|
| `--navy` | `#0F172A` | Dark slide backgrounds, primary text |
| `--blue` | `#2563EB` | Primary accent, CTAs, links |
| `--blue-light` | `#60A5FA` | Secondary accent, icon highlights |
| `--purple` | `#7C3AED` | Retrieval stage, phase 2 |
| `--emerald` | `#10B981` | Positive signals, success states |
| `--amber` | `#F59E0B` | Medium/warning score states |
| `--red` | `#EF4444` | Negative signals, penalty markers |
| `--slate-100` | `#F1F5F9` | Light slide backgrounds |
| `--slate-200` | `#E2E8F0` | Dividers, table borders |
| `--slate-400` | `#94A3B8` | Secondary body text |
| `--slate-600` | `#475569` | Primary body text on light |
| `--card-dark` | `#1E293B` | Card backgrounds on dark slides |

### Typography Scale

| Use | Size | Weight |
|---|---|---|
| Slide headline (H1) | 36–72px | 800 |
| Section headline (H2) | 28–36px | 700 |
| Card title | 18–22px | 600 |
| Body text | 14–16px | 400–500 |
| Caption / label | 11–13px | 400–500 |
| Code / formula | 13–14px | Monospace |

### Slide Structure Rules

- Maximum 5 bullet points per slide
- Every bullet is one concrete fact, number, or outcome — no vague claims
- Every dark slide uses `#0F172A` background — never pure black `#000000`
- Every number is large (`≥28px`) and coloured (blue or emerald)
- No stock photography — use flat vector icons or abstract geometric shapes only
- Transitions: Fade only (0.3s) — no slide-in, no bounce

### Tool Recommendations

| Tool | Reason |
|---|---|
| **Figma** | Best for precise layouts matching this spec; use Auto Layout |
| **Canva** | Faster if Figma skills are limited; use dark business template |
| **Google Slides** | Most portable; use "Streamline Dark" theme and customise |
| **Pitch.com** | Native dark mode, good animation control, team-friendly |
