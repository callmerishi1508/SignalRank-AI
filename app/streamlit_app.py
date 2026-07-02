"""
SignalRank AI — Recruiter Dashboard
Professional candidate ranking interface for the Redrob AI Challenge.

Run: streamlit run app/streamlit_app.py
"""

import csv as _csv
import html as _html
import io
import json
import os
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SignalRank AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ══════════════════════════════════════════════════════════════════════════════
   SIGNALRANK AI — PREMIUM DESIGN SYSTEM v3.0
   Optimized for hackathon judges: clean, trustworthy, scannable
══════════════════════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Global font ─────────────────────────────────────────────────────────── */
html, body, [class*="st-"], .stMarkdown, p, div, span, label {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
[data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; }

/* ── Design tokens ───────────────────────────────────────────────────────── */
:root {
    /* Neutral */
    --n900: #0F172A;  --n800: #1E293B;  --n700: #334155;
    --n600: #475569;  --n500: #64748B;  --n400: #94A3B8;
    --n300: #CBD5E1;  --n200: #E2E8F0;  --n100: #F1F5F9;  --n50:  #F8FAFC;
    /* Blue */
    --b700: #1D4ED8;  --b600: #2563EB;  --b500: #3B82F6;
    --b200: #BFDBFE;  --b100: #DBEAFE;  --b50:  #EFF6FF;
    /* Green */
    --g700: #15803D;  --g600: #16A34A;
    --g100: #DCFCE7;  --g50:  #F0FDF4;
    /* Amber */
    --a700: #B45309;  --a600: #D97706;
    --a100: #FEF3C7;  --a50:  #FFFBEB;
    /* Red */
    --r700: #B91C1C;  --r600: #DC2626;
    --r100: #FEE2E2;  --r50:  #FEF2F2;
    /* Purple */
    --p700: #6D28D9;  --p100: #EDE9FE;
    /* Typography scale */
    --t-xs:   0.7rem;    /* 11.2px — metadata, helper */
    --t-sm:   0.8rem;    /* 12.8px — labels, captions */
    --t-base: 0.875rem;  /* 14px   — body text */
    --t-md:   0.9375rem; /* 15px   — slightly larger body */
    --t-lg:   1.0625rem; /* 17px   — card titles */
    --t-xl:   1.25rem;   /* 20px   — section headings */
    --t-2xl:  1.625rem;  /* 26px   — large numbers */
    --t-hero: 2.1rem;    /* 33.6px — hero title */
    /* Radii */
    --r-xs: 4px;  --r-sm: 6px;  --r-md: 10px;
    --r-lg: 14px; --r-xl: 18px; --r-pill: 9999px;
    /* Shadows */
    --s-sm: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
    --s-md: 0 4px 12px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04);
    --s-lg: 0 8px 24px rgba(0,0,0,.10), 0 4px 8px rgba(0,0,0,.04);
}

/* ── Layout ──────────────────────────────────────────────────────────────── */
.block-container { padding-top: .85rem !important; }
footer, #MainMenu, .stDeployButton { visibility: hidden; display: none; }

/* ── Scrollbar ───────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--n300); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--n400); }

/* ── Focus ring ──────────────────────────────────────────────────────────── */
*:focus-visible {
    outline: 2px solid var(--b500) !important;
    outline-offset: 2px;
    border-radius: var(--r-xs);
}

/* ════════════════════════════════════════════════════════════════════════════
   HERO BANNER
════════════════════════════════════════════════════════════════════════════ */
.sr-hero {
    background: linear-gradient(135deg, #0A1628 0%, #0F2554 40%, #1447C7 85%, #2563EB 100%);
    padding: 2rem 2.5rem 1.9rem;
    border-radius: var(--r-xl);
    margin-bottom: 1.4rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 6px 40px rgba(21,78,216,.28), 0 2px 8px rgba(0,0,0,.14);
}
.sr-hero::after {
    content: '';
    position: absolute;
    top: -50%; right: -8%;
    width: 420px; height: 420px;
    background: radial-gradient(circle, rgba(96,165,250,.15) 0%, transparent 65%);
    pointer-events: none;
}
.sr-hero-eyebrow {
    display: flex; align-items: center; gap: .6rem; margin-bottom: .55rem;
}
.sr-hero-badge {
    display: inline-flex; align-items: center; gap: .3rem;
    background: rgba(96,165,250,.22);
    color: #93C5FD;
    border: 1px solid rgba(147,197,253,.35);
    padding: .22rem .75rem;
    border-radius: var(--r-pill);
    font-size: .65rem;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
}
.sr-hero-title {
    color: #fff;
    font-size: var(--t-hero);
    font-weight: 800;
    margin: 0 0 .5rem;
    letter-spacing: -0.8px;
    line-height: 1.15;
}
.sr-hero-title span { color: #93C5FD; }
.sr-hero-divider {
    width: 40px; height: 2px;
    background: linear-gradient(90deg, #3B82F6, transparent);
    border-radius: 2px;
    margin-bottom: .55rem;
}
.sr-hero-sub {
    color: rgba(255,255,255,.60);
    font-size: .875rem;
    line-height: 1.65;
    margin: 0;
    max-width: 700px;
}
.sr-hero-sub b { color: rgba(255,255,255,.88); font-weight: 600; }

/* ════════════════════════════════════════════════════════════════════════════
   KPI METRIC CARDS
════════════════════════════════════════════════════════════════════════════ */
.kpi-card {
    background: #fff;
    border: 1px solid var(--n200);
    border-radius: var(--r-lg);
    padding: 1.3rem 1rem 1.1rem;
    text-align: center;
    position: relative;
    overflow: hidden;
    box-shadow: var(--s-sm);
    transition: box-shadow .18s, transform .18s;
}
.kpi-card:hover { box-shadow: var(--s-md); transform: translateY(-2px); }
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: var(--r-lg) var(--r-lg) 0 0;
}
.kpi-blue::before   { background: linear-gradient(90deg, #2563EB 0%, #60A5FA 100%); }
.kpi-green::before  { background: linear-gradient(90deg, #16A34A 0%, #4ADE80 100%); }
.kpi-amber::before  { background: linear-gradient(90deg, #D97706 0%, #FCD34D 100%); }
.kpi-red::before    { background: linear-gradient(90deg, #DC2626 0%, #FCA5A5 100%); }
.kpi-purple::before { background: linear-gradient(90deg, #6D28D9 0%, #A78BFA 100%); }
.kpi-neutral::before { background: var(--n200); }

.kpi-value {
    font-size: clamp(1.5rem, 2.8vw, 2.2rem);
    font-weight: 800;
    color: var(--n900);
    line-height: 1;
    margin-bottom: .4rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    letter-spacing: -.03em;
    font-variant-numeric: tabular-nums;
}
.kpi-label {
    font-size: .68rem;
    font-weight: 700;
    color: var(--n500);
    text-transform: uppercase;
    letter-spacing: .08em;
    margin-bottom: .2rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.kpi-sub {
    font-size: .67rem;
    color: var(--n400);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.4;
}

/* ════════════════════════════════════════════════════════════════════════════
   CANDIDATE CARDS
════════════════════════════════════════════════════════════════════════════ */
.cand-card {
    background: #fff;
    border: 1px solid var(--n200);
    border-radius: var(--r-lg);
    padding: 1.25rem 1.5rem;
    margin-bottom: .65rem;
    transition: box-shadow .15s, border-color .12s, transform .1s;
}
.cand-card:hover {
    box-shadow: var(--s-md);
    border-color: var(--b200);
    transform: translateY(-1px);
}
.cand-card-gold   { border-left: 4px solid #F59E0B !important; }
.cand-card-silver { border-left: 4px solid #94A3B8 !important; }
.cand-card-bronze { border-left: 4px solid #CD7F32 !important; }

/* ── Rank badge ──────────────────────────────────────────────────────────── */
.rank-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 2.5rem; height: 2.5rem; border-radius: 50%;
    font-weight: 800; font-size: .8rem; flex-shrink: 0;
    letter-spacing: -.03em;
}
.rb-gold   { background: linear-gradient(145deg,#FEF9C3,#FDE047); color: #78350F;
    box-shadow: 0 2px 10px rgba(245,158,11,.35); }
.rb-silver { background: linear-gradient(145deg,#F1F5F9,#CBD5E1); color: #334155;
    box-shadow: 0 1px 4px rgba(0,0,0,.1); }
.rb-bronze { background: linear-gradient(145deg,#FFF7ED,#FED7AA); color: #92400E;
    box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.rb-plain  { background: var(--n100); color: var(--n400); }

/* ── Score pills ─────────────────────────────────────────────────────────── */
.score-pill {
    background: var(--b50); color: var(--b700); border: 1.5px solid var(--b200);
    padding: .22rem .85rem; border-radius: var(--r-pill);
    font-size: .875rem; font-weight: 800; font-variant-numeric: tabular-nums;
    letter-spacing: -.01em;
}
.score-pill-warn { background: var(--a50); color: #92400E; border-color: #FDE68A; }
.score-pill-low  { background: var(--r50); color: var(--r700); border-color: var(--r100); }

/* ── Score bars ──────────────────────────────────────────────────────────── */
.bar-bg   { background: var(--n100); border-radius: 4px; height: 6px; margin-top: 4px; }
.bar-fill { height: 6px; border-radius: 4px; transition: width .4s cubic-bezier(.4,0,.2,1); }
.bar-bg-sm { background: var(--n100); border-radius: 3px; height: 4px; }

/* ── Tags ────────────────────────────────────────────────────────────────── */
.tag {
    display: inline-block; padding: .17rem .6rem; border-radius: var(--r-sm);
    font-size: .72rem; font-weight: 600; margin: .05rem .04rem; line-height: 1.45;
    white-space: nowrap;
}
.tag-hp     { background: var(--r50); color: var(--r700); border: 1px solid var(--r100); }
.tag-pen    { background: var(--a50); color: var(--a700); border: 1px solid var(--a100); }
.tag-active { background: var(--g50); color: var(--g700); border: 1px solid var(--g100); }
.tag-conf   { background: var(--b50); color: var(--b700); border: 1px solid var(--b100); }
.tag-loc    { background: var(--n50); color: var(--n600); border: 1px solid var(--n200); }
.tag-skill  { background: var(--p100); color: var(--p700); border: 1px solid #DDD6FE; }
.tag-miss   { background: var(--r50); color: #991B1B; border: 1px solid var(--r100); }

/* ════════════════════════════════════════════════════════════════════════════
   SECTION LABELS
════════════════════════════════════════════════════════════════════════════ */
.section-label {
    font-size: .7rem; font-weight: 700; color: var(--n400);
    letter-spacing: .1em; text-transform: uppercase;
    margin: .85rem 0 .45rem;
    padding-bottom: .3rem;
    border-bottom: 1px solid var(--n100);
    display: block;
}

/* ════════════════════════════════════════════════════════════════════════════
   EVIDENCE CARDS
════════════════════════════════════════════════════════════════════════════ */
.evidence-card {
    background: var(--n50);
    border: 1px solid var(--n200);
    border-left: 3px solid var(--b500);
    border-radius: var(--r-md);
    padding: .85rem 1rem;
    margin-bottom: .55rem;
    font-size: var(--t-base);
    line-height: 1.6;
}
.evidence-title {
    font-size: .72rem; font-weight: 700; color: var(--n500);
    letter-spacing: .07em; text-transform: uppercase; margin-bottom: .3rem;
}
.evidence-snippet { color: var(--n700); font-style: italic; font-size: var(--t-base); }
.evidence-meta    { color: var(--n500); font-size: .78rem; }

/* ════════════════════════════════════════════════════════════════════════════
   ALERT BANNERS  (left-border accent — premium SaaS pattern)
════════════════════════════════════════════════════════════════════════════ */
.alert-ok {
    background: var(--g50); border: 1px solid var(--g100);
    border-left: 4px solid var(--g600);
    border-radius: var(--r-md);
    padding: .75rem 1.1rem; font-size: var(--t-base); color: #14532D;
    margin-bottom: .75rem; line-height: 1.55;
}
.alert-warn {
    background: var(--a50); border: 1px solid var(--a100);
    border-left: 4px solid var(--a600);
    border-radius: var(--r-md);
    padding: .75rem 1.1rem; font-size: var(--t-base); color: #78350F;
    margin-bottom: .75rem; line-height: 1.55;
}
.alert-info {
    background: var(--b50); border: 1px solid var(--b100);
    border-left: 4px solid var(--b600);
    border-radius: var(--r-md);
    padding: .75rem 1.1rem; font-size: var(--t-base); color: #1E3A5F;
    margin-bottom: .75rem; line-height: 1.55;
}

/* ════════════════════════════════════════════════════════════════════════════
   COMPONENT SCORE ROW
════════════════════════════════════════════════════════════════════════════ */
.comp-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: .35rem 0; border-bottom: 1px solid var(--n50);
    font-size: var(--t-base);
}
.comp-name  { color: var(--n700); font-weight: 500; }
.comp-wt    { color: var(--n400); font-size: .75rem; margin-left: .25rem; }
.comp-score { font-weight: 700; font-variant-numeric: tabular-nums; }

/* ════════════════════════════════════════════════════════════════════════════
   CONFIDENCE
════════════════════════════════════════════════════════════════════════════ */
.conf-high   { color: var(--g700); font-weight: 700; }
.conf-medium { color: var(--a700); font-weight: 700; }
.conf-low    { color: var(--r600); font-weight: 700; }

/* ════════════════════════════════════════════════════════════════════════════
   COMPARE VIEW
════════════════════════════════════════════════════════════════════════════ */
.compare-winner {
    background: var(--g50); border: 1px solid var(--g100);
    border-left: 4px solid var(--g600);
    border-radius: var(--r-md);
    padding: .8rem 1.1rem; font-size: .925rem; color: #14532D; font-weight: 600;
    margin-bottom: .85rem; line-height: 1.5;
}
.compare-risk {
    background: var(--a50); border: 1px solid var(--a100);
    border-left: 4px solid var(--a600);
    border-radius: var(--r-md);
    padding: .75rem 1.1rem; font-size: var(--t-base); color: #78350F;
}

/* ════════════════════════════════════════════════════════════════════════════
   SIDEBAR
════════════════════════════════════════════════════════════════════════════ */
.sidebar-section {
    font-size: .65rem; font-weight: 700; color: var(--n400);
    letter-spacing: .12em; text-transform: uppercase;
    margin: 1rem 0 .45rem;
    padding-bottom: .25rem;
    border-bottom: 1px solid var(--n100);
    display: block;
}
.sidebar-info {
    background: var(--n50); border: 1px solid var(--n200);
    border-radius: var(--r-md);
    padding: .75rem .9rem;
    font-size: .78rem; color: var(--n600); line-height: 1.7;
}
.sidebar-info b { color: var(--n800); font-weight: 600; }
.sidebar-info .si-row { display: flex; gap: .4rem; align-items: flex-start; margin-bottom: .1rem; }
.sidebar-info .si-dot { color: var(--b500); font-size: .6rem; flex-shrink: 0; margin-top: .35rem; }

/* ════════════════════════════════════════════════════════════════════════════
   TABS
════════════════════════════════════════════════════════════════════════════ */
button[data-testid="stTab"] p {
    font-size: .875rem !important;
    font-weight: 500 !important;
    color: var(--n500) !important;
    transition: color .12s;
    letter-spacing: -.01em !important;
}
button[data-testid="stTab"]:hover p    { color: var(--n800) !important; }
button[data-testid="stTab"][aria-selected="true"] p {
    color: var(--b700) !important;
    font-weight: 700 !important;
}

/* ════════════════════════════════════════════════════════════════════════════
   SHORTLIST / RECRUITER ACTIONS
════════════════════════════════════════════════════════════════════════════ */
.sl-badge {
    display: inline-flex; align-items: center; gap: .25rem;
    background: var(--b50); border: 1px solid var(--b200);
    color: var(--b700); border-radius: var(--r-pill);
    font-size: .72rem; font-weight: 600;
    padding: .15rem .55rem;
}
button[data-testid="baseButton-secondary"] {
    font-size: .78rem !important;
}

/* ════════════════════════════════════════════════════════════════════════════
   RESPONSIVE
════════════════════════════════════════════════════════════════════════════ */
@media (max-width: 600px) {
    .sr-hero            { padding: 1.3rem 1.4rem 1.2rem; }
    .sr-hero-title      { font-size: 1.45rem; letter-spacing: -.5px; }
    .sr-hero-sub        { font-size: .82rem; }
    .cand-card          { padding: 1rem 1.1rem; }
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
import uuid as _uuid

for _k, _v in [
    ("results", None),
    ("pipeline_stats", None),
    ("selected_idx", 0),
    ("shortlist", set()),         # set of candidate_ids saved by recruiter
    ("recruiter_notes", {}),      # candidate_id → note string
    ("parsed_jd", None),          # ParsedJD extracted dict from jd_parser.parse_jd_text()
    ("parsed_jd_profile", None),  # actual JobProfile object (thread-safe, per-session)
    ("jd_mode", "demo"),          # "demo" | "custom"
    ("session_id", str(_uuid.uuid4())[:8]),  # unique per browser session
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# Base output directory — configurable via SIGNALRANK_OUTPUTS env var for production
_OUTPUTS_BASE = Path(os.environ.get("SIGNALRANK_OUTPUTS", "outputs"))
_OUTPUTS_BASE.mkdir(parents=True, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

_e = _html.escape  # Escape user-supplied strings before embedding in unsafe_allow_html blocks


def _score_color(score: float) -> str:
    if score >= 0.80: return "#10B981"
    if score >= 0.55: return "#F59E0B"
    return "#EF4444"


def _rank_class(rank: int) -> str:
    return {1: "rb-gold", 2: "rb-silver", 3: "rb-bronze"}.get(rank, "rb-plain")


def _bar(score: float, color: str = "#3B82F6", height: int = 5) -> str:
    pct = min(100, int(score * 100))
    return (f'<div class="bar-bg" style="height:{height}px">'
            f'<div class="bar-fill" style="width:{pct}%;background:{color};height:{height}px"></div>'
            f'</div>')


def _conf_class(conf: str) -> str:
    return {"High": "conf-high", "Medium": "conf-medium", "Low": "conf-low"}.get(conf, "conf-medium")


def _pill_class(score: float) -> str:
    if score >= 0.80: return "score-pill"
    if score >= 0.55: return "score-pill-warn"
    return "score-pill-low"


def load_results_from_json(path: str) -> bool:
    p = Path(path)
    if not p.exists():
        return False
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list) or not data:
            return False
        st.session_state.results = data
        return True
    except (json.JSONDecodeError, OSError):
        return False


def _session_output_paths():
    """Return session-scoped output paths so concurrent users don't overwrite each other."""
    sid = st.session_state.get("session_id", "default")
    session_dir = _OUTPUTS_BASE / sid
    session_dir.mkdir(parents=True, exist_ok=True)
    return str(session_dir / "results.csv"), str(session_dir / "results.json")


def _active_jd_profile():
    """Return the per-session JobProfile (thread-safe — never reads the shared global)."""
    from backend.jd_parser import JD_PROFILE
    return st.session_state.get("parsed_jd_profile") or JD_PROFILE


def _run_pipeline_core(tmp_path: str, no_cache: bool = False) -> bool:
    """Shared pipeline runner — session-scoped outputs, explicit JD, proper progress UI."""
    from rank import run_pipeline

    out_csv, out_json = _session_output_paths()

    stages = [
        ("Parsing candidates", 12),
        ("Detecting honeypots", 22),
        ("Building semantic index (FAISS + TF-IDF)", 65),
        ("Scoring candidate pool", 78),
        ("Generating explanations", 90),
        ("Writing outputs", 100),
    ]

    progress_bar = st.progress(0)
    status_text = st.empty()
    t0 = time.time()

    try:
        for stage_name, pct in stages[:2]:
            status_text.markdown(
                f'<div class="alert-info">⏳ <b>{stage_name}…</b></div>',
                unsafe_allow_html=True,
            )
            progress_bar.progress(pct)
            time.sleep(0.03)

        run_pipeline(tmp_path, out_csv, out_json,
                     no_cache=no_cache, jd_override=_active_jd_profile())

        for stage_name, pct in stages[2:]:
            status_text.markdown(
                f'<div class="alert-info">⏳ <b>{stage_name}…</b></div>',
                unsafe_allow_html=True,
            )
            progress_bar.progress(pct)
            time.sleep(0.03)

        progress_bar.progress(100)
        elapsed = time.time() - t0
        status_text.markdown(
            f'<div class="alert-ok">⚡ <b>Pipeline complete in {elapsed:.1f}s</b> — '
            f'candidates ranked and ready for review.</div>',
            unsafe_allow_html=True,
        )
        st.session_state.pipeline_stats = {"elapsed": elapsed, "csv": out_csv, "json": out_json}
        return load_results_from_json(out_json)

    except Exception as exc:
        status_text.empty()
        progress_bar.empty()
        print(f"[SignalRank] pipeline error: {exc}", file=sys.stderr)
        st.error(f"Pipeline error: {exc}")
        return False


def run_pipeline_on_upload(uploaded_file) -> bool:
    from rank import run_pipeline

    raw_bytes = uploaded_file.read()
    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        st.error("File must be UTF-8 encoded.")
        return False

    first_lines = [ln.strip() for ln in content.splitlines() if ln.strip()][:3]
    if not first_lines:
        st.error("The uploaded file is empty.")
        return False

    for ln in first_lines:
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            st.error("Invalid JSON on one of the first lines. Check the file format.")
            return False
        if not isinstance(obj, dict):
            st.error(f"Expected JSONL (one JSON object per line). Got {type(obj).__name__}.")
            return False

    all_lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    valid_count = sum(
        1 for ln in all_lines
        if _safe_json_has_cid(ln)
    )
    if valid_count == 0:
        st.error("No valid candidate records found. Each line must have a 'candidate_id' field.")
        return False

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        return _run_pipeline_core(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _safe_json_has_cid(ln: str) -> bool:
    try:
        obj = json.loads(ln)
        return isinstance(obj, dict) and bool(obj.get("candidate_id"))
    except (json.JSONDecodeError, ValueError):
        return False


def _run_pipeline_on_candidate_dicts(candidates: List[Dict]) -> bool:
    """Write a list of candidate dicts to a temp JSONL file and run the pipeline."""
    if not candidates:
        st.error("No candidates to rank.")
        return False

    with tempfile.NamedTemporaryFile(
        suffix=".jsonl", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        for c in candidates:
            tmp.write(json.dumps(c, ensure_ascii=False) + "\n")
        tmp_path = tmp.name

    try:
        return _run_pipeline_core(tmp_path, no_cache=True)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _run_pipeline_on_zip(zip_bytes: bytes, zip_name: str) -> bool:
    """Extract PDF/DOCX/TXT files from a ZIP, parse resumes, run pipeline."""
    import zipfile
    from backend.resume_parser import parse_resume_files

    with tempfile.TemporaryDirectory(prefix="signalrank_zip_") as tmpdir:
        zip_path = Path(tmpdir) / zip_name
        zip_path.write_bytes(zip_bytes)

        with zipfile.ZipFile(zip_path) as zf:
            supported = {".pdf", ".docx", ".doc", ".txt"}
            members = [
                m for m in zf.namelist()
                if Path(m).suffix.lower() in supported
                and not m.startswith("__MACOSX")
            ]
            if not members:
                st.error("No PDF, DOCX, or TXT files found inside the ZIP.")
                return False

            extracted = []
            for m in members:
                zf.extract(m, tmpdir)
                extracted.append(Path(tmpdir) / m)

        st.info(f"Extracted {len(extracted)} resume file(s) from ZIP. Parsing…")

        with st.spinner("Parsing resumes…"):
            candidates = parse_resume_files(extracted)

    errors = [c for c in candidates if "error" in c]
    ok = [c for c in candidates if "error" not in c]
    if errors:
        st.warning(f"{len(errors)} resume(s) could not be parsed: "
                   + ", ".join(e["filename"] for e in errors))

    if not ok:
        st.error("No resumes were successfully parsed.")
        return False

    return _run_pipeline_on_candidate_dicts(ok)


def _run_pipeline_on_drive_link(link: str) -> bool:
    """Download resumes from a public Google Drive folder and rank them."""
    from backend.drive_downloader import download_drive_folder
    from backend.resume_parser import parse_resume_files

    status = st.empty()
    try:
        with st.spinner("Connecting to Google Drive…"):
            files = download_drive_folder(
                link,
                progress_cb=lambda msg: status.info(msg),
            )
    except (ValueError, RuntimeError) as exc:
        st.error(str(exc))
        return False

    status.info(f"Downloaded {len(files)} file(s). Parsing resumes…")

    with st.spinner("Parsing resumes…"):
        from backend.resume_parser import parse_resume_files
        candidates = parse_resume_files(files)

    errors = [c for c in candidates if "error" in c]
    ok = [c for c in candidates if "error" not in c]
    if errors:
        st.warning(f"{len(errors)} resume(s) could not be parsed: "
                   + ", ".join(e["filename"] for e in errors))

    if not ok:
        st.error("No resumes were successfully parsed.")
        return False

    status.success(f"Parsed {len(ok)} resume(s). Running pipeline…")
    return _run_pipeline_on_candidate_dicts(ok)


def _render_component_breakdown(scores: Dict, show_sem: bool = True):
    """Render 7-component score bars with weights."""
    sem_val = scores.get("tfidf_similarity", scores.get("semantic_similarity", 0))
    rows = [
        ("Title / Role Fit",    scores.get("title_role", 0),          0.25),
        ("Skill Match",         scores.get("skill_match", 0),          0.20),
        ("Production Evidence", scores.get("production_evidence", 0),  0.15),
        ("Behavioral",          scores.get("behavioral", 0),           0.15),
        ("Experience Fit",      scores.get("experience_fit", 0),       0.10),
        ("Domain / Company",    scores.get("domain_fit", 0),           0.10),
        ("Location",            scores.get("location", 0),             0.05),
    ]
    if show_sem:
        rows.append(("Semantic Similarity", sem_val, None))

    for name, val, wt in rows:
        color = _score_color(val)
        wt_label = f"w={wt:.0%}" if wt is not None else "blend"
        st.markdown(f"""
        <div class="comp-row">
          <span class="comp-name">{name}<span class="comp-wt">({wt_label})</span></span>
          <span class="comp-score" style="color:{color}">{val:.3f}</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(_bar(val, color), unsafe_allow_html=True)


def _render_behavioral_breakdown(beh_sub: Dict):
    label_map = {
        "recency": "Last Active",
        "open_to_work": "Open to Work",
        "response_rate": "Response Rate",
        "notice_period": "Notice Period",
        "interview_completion": "Interview Completion",
        "github_activity": "GitHub Activity",
    }
    for k, v in beh_sub.items():
        color = _score_color(v)
        label = label_map.get(k, k.replace("_", " ").title())
        st.markdown(f"""
        <div class="comp-row">
          <span class="comp-name">{label}</span>
          <span class="comp-score" style="color:{color}">{v:.2f}</span>
        </div>
        {_bar(v, color, 4)}
        """, unsafe_allow_html=True)


def _render_skills_tags(skills: List[Dict], matched: List[str], missing: List[str]):
    """Render matched (green) and missing (red) skill tags."""
    matched_set = {s.lower() for s in matched}
    h = '<div style="margin:.4rem 0">'
    for s in skills[:8]:
        name = s.get("name", "")
        prof = s.get("proficiency", "")
        is_match = name.lower() in matched_set
        cls = "tag-skill" if is_match else "tag-loc"
        h += f'<span class="tag {cls}" title="{_e(prof)}">{_e(name)}</span> '
    h += "</div>"

    if missing:
        h += '<div class="section-label" style="margin-top:.5rem">Missing JD Skills</div>'
        h += '<div style="margin:.25rem 0">'
        for s in missing:
            h += f'<span class="tag tag-miss">− {_e(s)}</span> '
        h += "</div>"

    st.markdown(h, unsafe_allow_html=True)


def _render_career_snippets(snippets: List[Dict]):
    for sn in snippets:
        co = _e(sn.get("company", ""))
        title = _e(sn.get("title", ""))
        text = _e(sn.get("snippet", ""))
        has_prod = sn.get("has_production_evidence", False)
        prod_badge = '<span class="tag tag-active" style="font-size:.65rem">⚡ prod</span>' if has_prod else ""
        st.markdown(f"""
        <div class="evidence-card">
          <div class="evidence-title">{title} — {co} {prod_badge}</div>
          <div class="evidence-snippet">"{text}"</div>
        </div>
        """, unsafe_allow_html=True)


# ── Full Profile Dialog ───────────────────────────────────────────────────────
@st.dialog("Candidate Profile", width="large")
def _show_full_profile_dialog(result: Dict):
    snap    = result.get("profile_snapshot", {})
    scores  = result.get("scores", {})
    sig     = result.get("redrob_signals_snapshot", {})
    beh_sub = result.get("behavioral_breakdown", {})
    edu     = result.get("education_snapshot", {})
    matched = result.get("matched_skills", [])
    missing = result.get("missing_skills", [])
    skills  = result.get("skills_snapshot", [])
    snippets = result.get("career_snippets", [])
    conf    = result.get("confidence", "Medium")

    rank  = result["rank"]
    cid   = result["candidate_id"]
    score = result["final_score"]
    color = _score_color(score)
    conf_cls = _conf_class(conf)

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.6rem">
      <div class="rank-badge {_rank_class(rank)}">#{rank}</div>
      <div>
        <div style="font-size:1.1rem;font-weight:700">{_e(snap.get('current_title',''))}</div>
        <div style="font-size:.85rem;color:#64748B">
          {_e(snap.get('current_company',''))} &nbsp;·&nbsp;
          {snap.get('years_of_experience',0)}y exp &nbsp;·&nbsp;
          <span style="font-family:monospace;font-size:.75rem;color:#94A3B8">{_e(cid)}</span>
        </div>
      </div>
      <div style="margin-left:auto;text-align:right">
        <span class="{_pill_class(score)}">{score:.3f}</span>
        <div style="margin-top:.25rem"><span class="{conf_cls}">{conf}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    reasoning = result.get("reasoning", "")
    if reasoning:
        st.markdown(f'<div style="font-size:.9rem;line-height:1.65;color:#334155;'
                    f'background:#F8FAFC;border-radius:8px;padding:.75rem 1rem;'
                    f'border-left:3px solid #3B82F6;margin-bottom:.75rem">{_e(reasoning)}</div>',
                    unsafe_allow_html=True)

    left, right = st.columns(2)

    with left:
        st.markdown('<div class="section-label">Score Breakdown</div>', unsafe_allow_html=True)
        for lbl, key, wt in [
            ("Title / Role Fit", "title_role", "25%"),
            ("Skill Match",      "skill_match", "20%"),
            ("Production",       "production_evidence", "15%"),
            ("Behavioral",       "behavioral", "15%"),
            ("Experience Fit",   "experience_fit", "10%"),
            ("Domain / Company", "domain_fit", "10%"),
            ("Location",         "location", "5%"),
        ]:
            v = scores.get(key, 0)
            c = _score_color(v)
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;font-size:.8rem;padding:.15rem 0">
              <span>{lbl} <span style="color:#9CA3AF;font-size:.7rem">({wt})</span></span>
              <span style="font-weight:700;color:{c}">{v:.3f}</span>
            </div>{_bar(v, c, 4)}""", unsafe_allow_html=True)
        pen = scores.get("penalty", 0)
        pen_reasons = result.get("penalty_reasons", [])
        pen_color = "#DC2626" if pen > 0.05 else "#16A34A"
        st.markdown(f"""
        <div style="margin-top:.5rem;padding:.5rem .75rem;background:#F8FAFC;
             border-radius:6px;font-size:.8rem;border:1px solid #E2E8F0">
          Penalty: <b style="color:{pen_color}">{pen:.0%}</b> → Final: <b>{score:.3f}</b>
          {'<br><span style="color:#92400E;font-size:.75rem">' + '; '.join(pen_reasons) + '</span>' if pen_reasons else ''}
        </div>""", unsafe_allow_html=True)

    with right:
        if beh_sub:
            st.markdown('<div class="section-label">Behavioral Signals</div>', unsafe_allow_html=True)
            beh_labels = {
                "recency": "Last Active", "open_to_work": "Open to Work",
                "response_rate": "Response Rate", "response_speed": "Response Speed",
                "notice_period": "Notice Period", "interview_completion": "Interview Completion",
                "github_activity": "GitHub Activity", "recruiter_demand": "Recruiter Demand",
                "active_seeking": "Active Seeking",
            }
            for k, v in beh_sub.items():
                c = _score_color(v)
                lbl = beh_labels.get(k, k.replace("_", " ").title())
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;font-size:.8rem;padding:.15rem 0">
                  <span>{lbl}</span><span style="font-weight:700;color:{c}">{v:.2f}</span>
                </div>{_bar(v, c, 4)}""", unsafe_allow_html=True)

        raw_signals = []
        rrr = sig.get("recruiter_response_rate")
        if rrr is not None: raw_signals.append(f"Response rate: {rrr:.0%}")
        notice = sig.get("notice_period_days")
        if notice is not None: raw_signals.append(f"Notice: {int(notice)}d")
        saved = sig.get("saved_by_recruiters_30d")
        if saved is not None: raw_signals.append(f"Saved by {int(saved)} recruiters/mo")
        github = sig.get("github_activity_score")
        if github is not None: raw_signals.append(f"GitHub: {int(github)}/100")
        otw = sig.get("open_to_work_flag")
        if otw: raw_signals.append("Open to work ✓")
        sal = sig.get("expected_salary_range_inr_lpa")
        if sal: raw_signals.append(f"Expected: {sal} LPA")

        if raw_signals:
            st.markdown('<div class="section-label" style="margin-top:.5rem">Redrob Signals</div>',
                        unsafe_allow_html=True)
            sig_html = '<div style="margin:.3rem 0">'
            for s in raw_signals:
                sig_html += f'<span class="tag tag-loc" style="margin-bottom:.25rem">{_e(s)}</span> '
            sig_html += "</div>"
            st.markdown(sig_html, unsafe_allow_html=True)

        if edu.get("degree"):
            st.markdown('<div class="section-label" style="margin-top:.5rem">Education</div>',
                        unsafe_allow_html=True)
            tier_badge = (f' <span class="tag tag-active" style="font-size:.65rem">{_e(edu["tier"])}</span>'
                          if edu.get("tier") in ("tier1", "tier2") else "")
            st.markdown(f'<div style="font-size:.82rem">{_e(edu.get("degree",""))} '
                        f'in {_e(edu.get("field",""))}<br>'
                        f'<span style="color:#64748B">{_e(edu.get("institution",""))}</span>'
                        f'{tier_badge}</div>', unsafe_allow_html=True)

    if skills or matched or missing:
        st.markdown('<div class="section-label" style="margin-top:.6rem">Skills</div>', unsafe_allow_html=True)
        _render_skills_tags(skills, matched, missing)

    if snippets:
        st.markdown('<div class="section-label" style="margin-top:.6rem">Career Evidence</div>',
                    unsafe_allow_html=True)
        _render_career_snippets(snippets)

    headline = result.get("headline", "")
    if headline:
        st.markdown(f'<div style="margin-top:.6rem;font-size:.82rem;color:#64748B;'
                    f'font-style:italic">{_e(headline)}</div>', unsafe_allow_html=True)

    sl_col, _ = st.columns([1, 3])
    with sl_col:
        _in_sl = cid in st.session_state.shortlist
        _lbl = "📌 Remove from Shortlist" if _in_sl else "📌 Save to Shortlist"
        if st.button(_lbl, key=f"dialog_sl_{cid}"):
            if _in_sl:
                st.session_state.shortlist.discard(cid)
            else:
                st.session_state.shortlist.add(cid)
            st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="sr-hero">
  <div class="sr-hero-eyebrow">
    <span class="sr-hero-badge">⚡ Redrob AI Challenge 2026</span>
  </div>
  <div class="sr-hero-title">SignalRank <span>AI</span></div>
  <div class="sr-hero-divider"></div>
  <p class="sr-hero-sub">
    <b>Rank talent by fit, not keywords.</b> &nbsp;Two-stage hybrid pipeline:
    semantic retrieval (FAISS + TF-IDF) → evidence scoring (7 components) → honeypot detection.
  </p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:

    # ── 1. Job Description ────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">Job Description</div>', unsafe_allow_html=True)

    _jd_tab_demo, _jd_tab_custom = st.tabs(["Demo JD", "Paste / Upload JD"])

    with _jd_tab_demo:
        st.markdown("""
        <div class="sidebar-info">
          <b>Senior AI Engineer</b>
          <div class="si-row"><span class="si-dot">▸</span><span>Redrob AI · Series A</span></div>
          <div class="si-row"><span class="si-dot">▸</span><span>Pune / Noida · Hybrid</span></div>
          <div class="si-row"><span class="si-dot">▸</span><span>5–9 yrs ML/AI experience</span></div>
          <div class="si-row"><span class="si-dot">▸</span><span>Embeddings · FAISS · NLP · RAG</span></div>
          <div class="si-row"><span class="si-dot">▸</span><span>Production search/ranking required</span></div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Use Demo JD", key="jd_use_demo", use_container_width=True):
            st.session_state.parsed_jd = None
            st.session_state.parsed_jd_profile = None
            st.session_state.jd_mode = "demo"
            st.success("Using demo JD (Redrob Senior AI Engineer)")

    with _jd_tab_custom:
        _jd_file = st.file_uploader(
            "Upload JD (.txt or .md)",
            type=["txt", "md"],
            key="jd_file_upload",
            label_visibility="collapsed",
        )
        _jd_file_text = ""
        if _jd_file is not None:
            try:
                _jd_file_text = _jd_file.read().decode("utf-8")
            except Exception:
                st.error("Could not read file. Upload a plain text (.txt) or markdown (.md) JD.")

        _jd_textarea = st.text_area(
            "Or paste your JD here",
            value=_jd_file_text if _jd_file_text else st.session_state.get("_jd_saved_text", ""),
            height=190,
            placeholder="Paste any job description — Google, Amazon, any company.\n"
                         "Skills, experience, locations are auto-extracted.",
            label_visibility="collapsed",
            key="jd_text_area",
        )
        # Persist typed text across reruns
        st.session_state["_jd_saved_text"] = _jd_textarea

        if st.button("Parse & Use This JD", key="jd_parse_btn",
                     use_container_width=True, type="primary"):
            _jd_to_parse = _jd_textarea.strip()
            if not _jd_to_parse:
                st.warning("Paste or upload a job description first.")
            else:
                from backend.jd_parser import parse_jd_text
                with st.spinner("Parsing…"):
                    try:
                        _parsed = parse_jd_text(_jd_to_parse)
                        # Store profile in session state — never in shared global
                        st.session_state.parsed_jd = _parsed.extracted
                        st.session_state.parsed_jd_profile = _parsed.profile
                        st.session_state.jd_mode = "custom"
                        st.success(f"Active JD: **{_parsed.profile.title}**")
                    except Exception as _exc:
                        st.error(f"Parse error: {_exc}")

        if st.session_state.jd_mode == "custom" and st.session_state.parsed_jd:
            _ex = st.session_state.parsed_jd
            _skills_prev = ", ".join(_ex.get("required_skills", [])[:5])
            _locs_prev = ", ".join(_ex.get("locations", [])[:3]) or "not specified"
            st.markdown(f"""
            <div class="sidebar-info" style="margin-top:.4rem">
              <b style="color:#1D4ED8">{_e(str(_ex.get('title','Role')))}</b>
              <div class="si-row"><span class="si-dot">▸</span>
                <span>{_e(str(_ex.get('seniority','').title()))} · {_e(str(_ex.get('experience','?')))}</span></div>
              <div class="si-row"><span class="si-dot">▸</span>
                <span>{_e(_locs_prev)}</span></div>
              <div class="si-row"><span class="si-dot">▸</span>
                <span style="font-size:.77rem">{_e(_skills_prev)}{" …" if len(_ex.get("required_skills", [])) > 5 else ""}</span></div>
            </div>
            """, unsafe_allow_html=True)

    # ── 2. Candidates Input ───────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">Candidates</div>', unsafe_allow_html=True)

    _c_tab_jsonl, _c_tab_zip, _c_tab_drive = st.tabs(["JSONL", "ZIP of Resumes", "Google Drive"])

    with _c_tab_jsonl:
        st.caption("Upload a .jsonl file where each line is a candidate JSON record.")
        _uploaded_jsonl = st.file_uploader(
            "Upload candidates.jsonl",
            type=["jsonl", "json"],
            key="cand_jsonl_upload",
            label_visibility="collapsed",
        )
        if _uploaded_jsonl:
            if st.button("⚡ Rank Candidates", key="rank_jsonl",
                         type="primary", use_container_width=True):
                with st.spinner(""):
                    run_pipeline_on_upload(_uploaded_jsonl)
        else:
            st.button("⚡ Rank Candidates", key="rank_jsonl_dis",
                      type="primary", use_container_width=True, disabled=True)

    with _c_tab_zip:
        st.caption("Upload a ZIP file of PDF, DOCX, or TXT resumes. Each file = one candidate.")
        _uploaded_zip = st.file_uploader(
            "Upload resumes ZIP",
            type=["zip"],
            key="cand_zip_upload",
            label_visibility="collapsed",
        )
        if _uploaded_zip:
            if st.button("⚡ Parse & Rank Resumes", key="rank_zip",
                         type="primary", use_container_width=True):
                _run_pipeline_on_zip(_uploaded_zip.read(), _uploaded_zip.name)
        else:
            st.button("⚡ Parse & Rank Resumes", key="rank_zip_dis",
                      type="primary", use_container_width=True, disabled=True)

    with _c_tab_drive:
        st.caption(
            "Paste a public Google Drive folder link containing PDF/DOCX/TXT resumes.\n"
            "The folder must be shared as **Anyone with the link → Viewer**."
        )
        _drive_link = st.text_input(
            "Google Drive folder link",
            placeholder="https://drive.google.com/drive/folders/…",
            label_visibility="collapsed",
            key="drive_link_input",
        )
        if st.button("⚡ Download & Rank", key="rank_drive",
                     type="primary", use_container_width=True):
            if not _drive_link.strip():
                st.warning("Paste a Google Drive folder link first.")
            else:
                _run_pipeline_on_drive_link(_drive_link.strip())

    # ── 3. Load Existing Results ───────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">Load Existing Results</div>', unsafe_allow_html=True)
    results_path = st.text_input("Results JSON", value="outputs/debug.json",
                                 label_visibility="collapsed")
    if st.button("↑ Load from file", use_container_width=True):
        if load_results_from_json(results_path):
            st.success("Loaded")
        else:
            st.error("File not found or invalid.")

    # ── 4. Export ──────────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section">Export</div>', unsafe_allow_html=True)
    _s_csv, _s_json = _session_output_paths()
    for label, path, mime, fname in [
        ("📥 Ranked CSV", _s_csv, "text/csv", "ranked_candidates.csv"),
        ("📄 Full JSON", _s_json, "application/json", "ranked_candidates.json"),
        ("📊 Eval Report", str(_OUTPUTS_BASE / "eval_report.json"), "application/json", "eval_report.json"),
    ]:
        p = Path(path)
        if p.exists():
            with open(p, encoding="utf-8") as f:
                st.download_button(label, data=f.read(), file_name=fname, mime=mime,
                                   use_container_width=True)

    st.markdown('<div class="sidebar-section">System Info</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="sidebar-info">
      <b>Pipeline</b>
      <div class="si-row"><span class="si-dot">▸</span><span>FAISS dense + TF-IDF → RRF fusion</span></div>
      <div class="si-row"><span class="si-dot">▸</span><span>7-component evidence scorer</span></div>
      <div class="si-row"><span class="si-dot">▸</span><span>15 of 23 Redrob signals used</span></div>
      <div class="si-row"><span class="si-dot">▸</span><span>Honeypot detection (7 checks)</span></div>
    </div>
    """, unsafe_allow_html=True)


# ── Auto-load — try session path first, then shared demo results ──────────────
if st.session_state.results is None:
    _sess_csv, _sess_json = _session_output_paths()
    if not load_results_from_json(_sess_json):
        # Fall back to shared demo results (pre-computed for the demo preset)
        _demo_json = str(_OUTPUTS_BASE / "debug.json")
        load_results_from_json(_demo_json)

if st.session_state.results is None:
    st.markdown("""
    <div style="text-align:center;padding:5rem 2rem;color:#64748B">
      <div style="font-size:3.2rem;margin-bottom:1.2rem;opacity:.75">⚡</div>
      <div style="font-size:1.2rem;font-weight:800;color:#0F172A;letter-spacing:-.02em;margin-bottom:.6rem">
        Ready to rank candidates
      </div>
      <div style="font-size:.9rem;line-height:1.8;max-width:420px;margin:0 auto;color:#475569">
        Upload <code style="background:#F1F5F9;padding:.1rem .45rem;border-radius:4px;font-size:.82em;color:#1D4ED8">candidates.jsonl</code>
        in the sidebar and click <strong style="color:#0F172A">Rank Candidates</strong>,<br>
        or load an existing <code style="background:#F1F5F9;padding:.1rem .45rem;border-radius:4px;font-size:.82em;color:#1D4ED8">outputs/debug.json</code>.
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

results: List[Dict] = st.session_state.results
top100: List[Dict] = results[:100]


# ── KPI metrics ───────────────────────────────────────────────────────────────
_ML_KW = {"ml", "ai", "machine learning", "scientist", "nlp", "search",
           "applied", "ranking", "retrieval", "recommendation"}

top10_ml = sum(
    1 for r in top100[:10]
    if any(kw in r["profile_snapshot"]["current_title"].lower() for kw in _ML_KW)
)
avg_top10 = sum(r["final_score"] for r in top100[:10]) / 10
hp_count  = sum(1 for r in top100 if r.get("is_honeypot", False))
penalized = sum(1 for r in top100 if r.get("scores", {}).get("penalty", 0) > 0.05)
high_conf = sum(1 for r in top100 if r.get("confidence", "") == "High")

c1, c2, c3, c4, c5 = st.columns(5)

_hp_cls  = "kpi-green" if hp_count == 0 else ("kpi-amber" if hp_count <= 10 else "kpi-red")
_pen_cls = "kpi-green" if penalized == 0 else "kpi-amber"
_ml_cls  = "kpi-green" if top10_ml >= 8 else "kpi-amber"
_hp_val  = f"✓ {hp_count}" if hp_count == 0 else f"⚠ {hp_count}"

kpi_data = [
    (c1, f"{top10_ml}/10",      "ML/AI in Top-10",  "Target ≥ 8/10",           _ml_cls),
    (c2, f"{avg_top10:.3f}",    "Avg Top-10 Score", "Out of 1.000",            "kpi-blue"),
    (c3, str(high_conf),        "High Confidence",  f"of {len(top100)} ranked","kpi-purple"),
    (c4, _hp_val,               "Honeypots",        ">10 = disqualified",      _hp_cls),
    (c5, str(penalized),        "Penalized",        "Consulting / wrong domain", _pen_cls),
]
for col, val, label, sub, color_cls in kpi_data:
    col.markdown(f"""
    <div class="kpi-card {color_cls}">
      <div class="kpi-value">{val}</div>
      <div class="kpi-label">{label}</div>
      <div class="kpi-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

if st.session_state.pipeline_stats:
    stats = st.session_state.pipeline_stats
    st.markdown(f"""
    <div class="alert-ok" style="margin-top:.8rem">
    ⚡ <b>Pipeline complete in {stats['elapsed']:.1f}s</b> &nbsp;·&nbsp;
    Backend: FAISS + TF-IDF (RRF) &nbsp;·&nbsp; Output: <code>{stats['csv']}</code>
    </div>
    """, unsafe_allow_html=True)

if hp_count > 10:
    st.markdown(f"""
    <div class="alert-warn">
    ⚠ <b>Honeypot risk:</b> {hp_count} honeypots detected in top-100. This exceeds the organizer
    limit of 10 and triggers automatic disqualification. Review honeypot thresholds.
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)

# ── Main tabs ─────────────────────────────────────────────────────────────────
tab_shortlist, tab_detail, tab_compare, tab_insights, tab_eval, tab_saved = st.tabs([
    "📋 Ranked Shortlist",
    "🔍 Candidate Detail",
    "⚖️ Compare",
    "📊 Insights",
    "🧪 Evaluation",
    f"📌 Saved ({len(st.session_state.shortlist)})",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Ranked Shortlist
# ─────────────────────────────────────────────────────────────────────────────
with tab_shortlist:
    hcol, fcol = st.columns([3, 1])
    with hcol:
        st.markdown("""
        <div style="margin:.3rem 0 .2rem">
          <span style="font-size:1rem;font-weight:700;letter-spacing:-.01em">
            Top Candidates
          </span>
          <span style="font-size:.82rem;opacity:.65;margin-left:.6rem">
            Senior AI Engineer — Redrob AI Founding Team
          </span>
          <span style="font-size:.73rem;opacity:.45;margin-left:.5rem;
                font-style:italic">Hybrid score: 75% rule-based · 25% semantic</span>
        </div>
        """, unsafe_allow_html=True)
    with fcol:
        show_n = st.selectbox("Show top", [10, 25, 50, 100], label_visibility="visible")

    with st.expander("🔧 Filters & Sort", expanded=False):
        f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.2, 1.4])
        with f1:
            min_score = st.slider("Min score", 0.0, 1.0, 0.0, 0.01)
            filter_title = st.text_input("Title contains", "", placeholder="e.g. NLP, Senior")
        with f2:
            yoe_range = st.slider("Years of experience", 0, 20, (0, 20))
            filter_conf = st.selectbox("Confidence", ["All", "High", "Medium", "Low"])
        with f3:
            max_notice = st.slider("Max notice period (days)", 0, 180, 180)
            min_behavioral = st.slider("Min behavioral score", 0.0, 1.0, 0.0, 0.05)
        with f4:
            sort_by = st.selectbox("Sort by", [
                "Final Score", "Title Fit", "Skill Match",
                "Production Evidence", "Behavioral", "Experience Fit",
                "Domain Fit", "Rank (default)",
            ])
            hide_penalized = st.checkbox("Hide penalized")
            hide_hp = st.checkbox("Hide honeypots", value=True)

    _sort_key_map = {
        "Final Score":          lambda r: -r["final_score"],
        "Title Fit":            lambda r: -r.get("scores", {}).get("title_role", 0),
        "Skill Match":          lambda r: -r.get("scores", {}).get("skill_match", 0),
        "Production Evidence":  lambda r: -r.get("scores", {}).get("production_evidence", 0),
        "Behavioral":           lambda r: -r.get("scores", {}).get("behavioral", 0),
        "Experience Fit":       lambda r: -r.get("scores", {}).get("experience_fit", 0),
        "Domain Fit":           lambda r: -r.get("scores", {}).get("domain_fit", 0),
        "Rank (default)":       lambda r: r["rank"],
    }

    def _get_notice(r):
        sig = r.get("redrob_signals_snapshot", {})
        nd = sig.get("notice_period_days")
        return nd if nd is not None else 9999

    filtered = [
        r for r in top100
        if r["final_score"] >= min_score
        and yoe_range[0] <= r["profile_snapshot"].get("years_of_experience", 0) <= yoe_range[1]
        and (not filter_title or filter_title.lower() in r["profile_snapshot"]["current_title"].lower())
        and (filter_conf == "All" or r.get("confidence", "Medium") == filter_conf)
        and _get_notice(r) <= max_notice
        and r.get("scores", {}).get("behavioral", 0) >= min_behavioral
        and (not hide_penalized or r.get("scores", {}).get("penalty", 0) <= 0.05)
        and (not hide_hp or not r.get("is_honeypot", False))
    ]

    if sort_by != "Rank (default)":
        filtered = sorted(filtered, key=_sort_key_map[sort_by])

    filtered = filtered[:show_n]

    if not filtered:
        st.markdown("""
        <div style="text-align:center;padding:2rem;color:#64748B">
          <div style="font-size:2rem;margin-bottom:.5rem">🔍</div>
          <b>No candidates match the current filters.</b><br>
          <span style="font-size:.85rem">Try relaxing the score threshold or removing title filters.</span>
        </div>
        """, unsafe_allow_html=True)

    # Compute top-100 average scores for Key Differentiator comparison
    _COMP_KEYS = ["title_role", "skill_match", "production_evidence", "behavioral", "experience_fit", "domain_fit"]
    _avg_scores: Dict[str, float] = {}
    if top100:
        for k in _COMP_KEYS:
            _avg_scores[k] = sum(r.get("scores", {}).get(k, 0) for r in top100) / len(top100)

    def _differentiator_html(result: Dict) -> str:
        scores = result.get("scores", {})
        sig = result.get("redrob_signals_snapshot", {})
        comp_labels = {
            "title_role":           "Title/Role Fit",
            "skill_match":          "Skill Depth",
            "production_evidence":  "Production Evidence",
            "behavioral":           "Behavioral Signals",
            "experience_fit":       "Experience Fit",
            "domain_fit":           "Domain Fit",
        }
        diffs = sorted(
            [(k, scores.get(k, 0) - _avg_scores.get(k, 0), scores.get(k, 0), lbl)
             for k, lbl in comp_labels.items()],
            key=lambda x: -x[1]
        )
        html = '<div style="margin-top:.6rem">'
        html += '<div class="section-label" style="margin-bottom:.35rem">⚡ Why This Rank</div>'
        for k, diff, val, lbl in diffs[:2]:
            diff_color = "#10B981" if diff >= 0 else "#EF4444"
            diff_sign = "+" if diff >= 0 else ""
            html += f"""
            <div style="display:flex;align-items:center;gap:.5rem;margin:.2rem 0;font-size:.82rem">
              <span style="color:#374151;min-width:8.5rem">{lbl}</span>
              <span style="font-weight:700;color:{_score_color(val)}">{val:.3f}</span>
              <span style="color:{diff_color};font-size:.7rem">({diff_sign}{diff:.3f} vs avg)</span>
            </div>"""
        # Key behavioral signals
        behavioral_notes = []
        rrr = sig.get("recruiter_response_rate")
        if isinstance(rrr, (int, float)) and rrr >= 0.80:
            behavioral_notes.append(f"{rrr:.0%} recruiter response rate")
        saved = sig.get("saved_by_recruiters_30d")
        if isinstance(saved, (int, float)) and saved >= 8:
            behavioral_notes.append(f"saved by {int(saved)} recruiters/month")
        notice = sig.get("notice_period_days")
        if isinstance(notice, (int, float)) and notice <= 15:
            behavioral_notes.append(f"{int(notice)}-day notice period")
        elif isinstance(notice, (int, float)) and notice <= 30:
            behavioral_notes.append(f"{int(notice)}-day notice period")
        github = sig.get("github_activity_score")
        if isinstance(github, (int, float)) and github >= 75:
            behavioral_notes.append(f"GitHub activity {int(github)}/100")
        if behavioral_notes:
            notes_str = " · ".join(behavioral_notes[:3])
            html += f'<div style="margin-top:.3rem;font-size:.78rem;color:#475569">{_e(notes_str)}</div>'
        html += '</div>'
        return html

    for result in filtered:
        rank  = result["rank"]
        cid   = result["candidate_id"]
        score = result["final_score"]
        snap  = result["profile_snapshot"]
        title = snap["current_title"]
        yoe   = snap["years_of_experience"]
        loc   = snap.get("location", "")
        co    = snap.get("current_company", "")
        reasoning = result.get("reasoning", "")
        penalty   = result.get("scores", {}).get("penalty", 0)
        is_hp     = result.get("is_honeypot", False)
        conf      = result.get("confidence", "Medium")

        tags = ""
        if cid in st.session_state.shortlist:
            tags += '<span class="sl-badge">📌 Shortlisted</span> '
        if is_hp:
            tags += '<span class="tag tag-hp">🚫 honeypot</span>'
        else:
            if penalty > 0.20:
                tags += '<span class="tag tag-pen">⚠ penalized</span>'
            tags += f'<span class="tag tag-conf">{conf} confidence</span>'
        beh = result.get("scores", {}).get("behavioral", 0)
        if beh > 0.85:
            tags += '<span class="tag tag-active">● active</span>'
        if loc:
            tags += f'<span class="tag tag-loc">📍 {_e(loc)}</span>'

        score_class = _pill_class(score)
        color = _score_color(score)
        rank_accent = {1: "cand-card-gold", 2: "cand-card-silver", 3: "cand-card-bronze"}.get(rank, "")

        # Main card HTML — all user-supplied strings escaped via _e()
        st.markdown(f"""
        <div class="cand-card {rank_accent}">
          <div style="display:flex;align-items:flex-start;gap:.9rem">
            <div class="rank-badge {_rank_class(rank)}">#{rank}</div>
            <div style="flex:1;min-width:0">
              <div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;margin-bottom:.25rem">
                <span style="font-weight:700;color:#0F172A;font-size:1.0rem;letter-spacing:-.01em">{_e(title)}</span>
                {tags}
              </div>
              <div style="font-size:.8rem;color:#64748B;margin:.05rem 0 .4rem">
                {_e(co)} &nbsp;·&nbsp; {yoe}y exp &nbsp;·&nbsp;
                <span style="font-family:monospace;font-size:.75rem;color:#94A3B8">{_e(cid)}</span>
              </div>
              <div style="font-size:.875rem;color:#334155;line-height:1.6">{_e(reasoning)}</div>
            </div>
            <div style="flex-shrink:0;text-align:right;min-width:72px;padding-left:.5rem">
              <span class="{score_class}">{score:.3f}</span>
              {_bar(score, color)}
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Expandable "Why this candidate?" panel
        with st.expander("💡 Why this candidate?", expanded=False):
            # Shortlist action row
            _in_sl = cid in st.session_state.shortlist
            _sl_col1, _sl_col2, _sl_col3 = st.columns([1.2, 1, 4])
            with _sl_col1:
                _btn_label = "📌 Remove" if _in_sl else "📌 Save to Shortlist"
                if st.button(_btn_label, key=f"sl_{cid}"):
                    if _in_sl:
                        st.session_state.shortlist.discard(cid)
                    else:
                        st.session_state.shortlist.add(cid)
                    st.rerun()
            with _sl_col2:
                if st.button("🔍 Full Profile", key=f"fp_{cid}"):
                    st.session_state.selected_idx = rank - 1
                    _show_full_profile_dialog(result)
            with _sl_col3:
                if _in_sl:
                    st.markdown('<span style="color:#10B981;font-size:.82rem">✓ In shortlist</span>', unsafe_allow_html=True)

            st.markdown("<hr style='margin:.4rem 0;border-color:#E2E8F0'>", unsafe_allow_html=True)
            e1, e2 = st.columns([1, 1])

            with e1:
                st.markdown('<div class="section-label">Score Breakdown</div>', unsafe_allow_html=True)
                scores_d = result.get("scores", {})
                for comp_name, comp_key, comp_wt in [
                    ("Title / Role Fit",    "title_role",          "25%"),
                    ("Skill Match",         "skill_match",          "20%"),
                    ("Production Evidence", "production_evidence",  "15%"),
                    ("Behavioral",          "behavioral",           "15%"),
                    ("Experience Fit",      "experience_fit",       "10%"),
                    ("Domain / Company",    "domain_fit",           "10%"),
                    ("Location",            "location",             "5%"),
                ]:
                    v = scores_d.get(comp_key, 0)
                    c = _score_color(v)
                    st.markdown(f"""
                    <div style="display:flex;justify-content:space-between;align-items:center;
                         padding:.2rem 0;font-size:.8rem">
                      <span style="color:#374151">{comp_name}
                        <span style="color:#9CA3AF;font-size:.7rem">({comp_wt})</span>
                      </span>
                      <span style="font-weight:700;color:{c}">{v:.3f}</span>
                    </div>
                    {_bar(v, c, 4)}
                    """, unsafe_allow_html=True)

                pen = scores_d.get("penalty", 0)
                pen_reasons = result.get("penalty_reasons", [])
                penalty_color = "#DC2626" if pen > 0.05 else "#16A34A"
                st.markdown(f"""
                <div style="margin-top:.65rem;padding:.6rem .85rem;background:#F8FAFC;
                     border-radius:8px;font-size:.82rem;border:1px solid #E2E8F0">
                  Penalty: <b style="color:{penalty_color}">{pen:.0%}</b>
                  &nbsp;→&nbsp; Final: <b>{score:.3f}</b>
                  {'<br><span style="color:#92400E;font-size:.75rem">' + '; '.join(pen_reasons) + '</span>' if pen_reasons else ''}
                </div>
                """, unsafe_allow_html=True)

                sem = scores_d.get("tfidf_similarity", scores_d.get("semantic_similarity", 0))
                conf_cls = _conf_class(conf)
                st.markdown(f"""
                <div style="margin-top:.5rem;font-size:.82rem;color:#475569">
                  Semantic: <b style="color:#0F172A">{sem:.3f}</b> &nbsp;·&nbsp;
                  Confidence: <span class="{conf_cls}">{conf}</span>
                </div>
                """, unsafe_allow_html=True)

            with e2:
                # Matched skills
                matched = result.get("matched_skills", [])
                missing = result.get("missing_skills", [])
                skills_snap = result.get("skills_snapshot", [])

                if matched or skills_snap:
                    st.markdown('<div class="section-label">Matched Skills</div>', unsafe_allow_html=True)
                    matched_set = {s.lower() for s in matched}
                    skill_html = '<div style="margin:.3rem 0">'
                    displayed = matched[:6] + [s["name"] for s in skills_snap if s.get("name", "").lower() not in matched_set][:2]
                    for name in displayed[:8]:
                        cls = "tag-skill" if name.lower() in matched_set else "tag-loc"
                        skill_html += f'<span class="tag {cls}">{_e(name)}</span> '
                    skill_html += "</div>"
                    st.markdown(skill_html, unsafe_allow_html=True)

                if missing:
                    st.markdown('<div class="section-label">Missing JD Skills</div>', unsafe_allow_html=True)
                    miss_html = '<div style="margin:.3rem 0">'
                    for m in missing:
                        miss_html += f'<span class="tag tag-miss">− {m}</span> '
                    miss_html += "</div>"
                    st.markdown(miss_html, unsafe_allow_html=True)

                # Career evidence snippets
                snippets = result.get("career_snippets", [])
                if snippets:
                    st.markdown('<div class="section-label">Career Evidence</div>', unsafe_allow_html=True)
                    for sn in snippets[:2]:
                        co_s = _e(sn.get("company", ""))
                        t_s  = _e(sn.get("title", ""))
                        txt  = _e(sn.get("snippet", ""))
                        has_p = sn.get("has_production_evidence", False)
                        prod_b = '<span class="tag tag-active" style="font-size:.62rem">⚡ prod</span>' if has_p else ""
                        st.markdown(f"""
                        <div class="evidence-card">
                          <div class="evidence-title">{t_s} — {co_s} {prod_b}</div>
                          <div class="evidence-snippet">"{txt}"</div>
                        </div>
                        """, unsafe_allow_html=True)
                elif not matched and not skills_snap:
                    st.markdown("""
                    <div style="color:#94A3B8;font-size:.82rem;padding:.5rem 0">
                      No enriched data. Re-run the pipeline to see evidence details.
                    </div>
                    """, unsafe_allow_html=True)

            # Key Differentiator — full width below the 2-column evidence panel
            if _avg_scores:
                st.markdown(_differentiator_html(result), unsafe_allow_html=True)

            # Recruiter Notes
            st.markdown('<div class="section-label" style="margin-top:.6rem">Recruiter Notes</div>', unsafe_allow_html=True)
            note_key = f"note_{cid}"
            current_note = st.session_state.recruiter_notes.get(cid, "")
            new_note = st.text_area(
                label="note", label_visibility="collapsed",
                value=current_note,
                key=note_key,
                placeholder="Add notes about this candidate (interview status, concerns, etc.)",
                height=70,
            )
            if new_note != current_note:
                st.session_state.recruiter_notes[cid] = new_note

        st.markdown("<div style='margin-bottom:.1rem'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — Candidate Detail (full explainability panel)
# ─────────────────────────────────────────────────────────────────────────────
with tab_detail:
    options = [
        f"#{r['rank']}  {r['candidate_id']}  —  {r['profile_snapshot']['current_title']}"
        for r in top100
    ]
    sel_label = st.selectbox("Select candidate", options, index=st.session_state.selected_idx,
                             key="detail_select")
    sel_idx = options.index(sel_label)
    st.session_state.selected_idx = sel_idx
    r = top100[sel_idx]

    snap   = r["profile_snapshot"]
    scores = r.get("scores", {})
    is_hp  = r.get("is_honeypot", False)
    conf   = r.get("confidence", "Medium")

    # ── Top summary strip ──────────────────────────────────────────────────
    conf_cls = _conf_class(conf)
    sem_val = scores.get("tfidf_similarity", scores.get("semantic_similarity", 0))
    rule_score = r.get("rule_based_score", r["final_score"])

    st.markdown(f"""
    <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-left:4px solid #2563EB;
         border-radius:14px;padding:1.1rem 1.4rem;margin-bottom:1rem;
         display:flex;align-items:center;gap:1.2rem;flex-wrap:wrap;
         box-shadow:0 1px 4px rgba(0,0,0,.05)">
      <div class="rank-badge {_rank_class(r['rank'])}" style="width:2.75rem;height:2.75rem;font-size:.88rem">
        #{r['rank']}
      </div>
      <div style="flex:1;min-width:200px">
        <div style="font-weight:800;font-size:1.1rem;color:#0F172A;letter-spacing:-.02em;margin-bottom:.18rem">
          {_e(snap['current_title'])}
        </div>
        <div style="font-size:.82rem;color:#64748B">
          {_e(snap.get('current_company','—'))} &nbsp;·&nbsp; {snap['years_of_experience']}y exp
          &nbsp;·&nbsp; {_e(snap['location'])}
          &nbsp;·&nbsp; <span style="font-family:monospace;font-size:.75rem;color:#94A3B8">{_e(r['candidate_id'])}</span>
        </div>
        {f'<div style="font-size:.82rem;color:#475569;margin-top:.25rem;font-style:italic">{_e(r.get("headline",""))}</div>' if r.get("headline") else ""}
      </div>
      <div style="text-align:right;padding-left:.5rem">
        <div style="font-size:2rem;font-weight:800;color:#1D4ED8;letter-spacing:-.03em;line-height:1">{r['final_score']:.3f}</div>
        <div style="font-size:.72rem;color:#64748B;margin:.2rem 0 .3rem;text-transform:uppercase;letter-spacing:.06em">Final Score</div>
        <div style="font-size:.82rem">Confidence: <span class="{conf_cls}">{conf}</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if is_hp:
        st.error("⛔ Classified as honeypot — near-zero score applied. Do not shortlist.")

    pen_reasons = r.get("penalty_reasons", [])
    if pen_reasons:
        st.warning("**Penalty applied:** " + " · ".join(pen_reasons))

    # ── Main 3-column layout ───────────────────────────────────────────────
    col_left, col_mid, col_right = st.columns([1.1, 1, 1])

    # Left: score breakdown
    with col_left:
        st.markdown("##### Score Breakdown")
        _render_component_breakdown(scores)

        pen = scores.get("penalty", 0)
        pen_color = "#DC2626" if pen > 0.05 else "#16A34A"
        st.markdown(f"""
        <div style="margin-top:.8rem;padding:.65rem .9rem;background:#F8FAFC;
             border-radius:10px;font-size:.82rem;border:1px solid #E2E8F0">
          Penalty: <b style="color:{pen_color}">{pen:.0%}</b>
          &nbsp;·&nbsp; Rule: <b>{rule_score:.3f}</b>
          &nbsp;·&nbsp; Semantic: <b>{sem_val:.3f}</b>
          <br><span style="color:#94A3B8;font-size:.72rem">
            Final = (0.75 × rule + 0.25 × semantic) × (1 − penalty)
          </span>
        </div>
        """, unsafe_allow_html=True)

        beh_sub = r.get("behavioral_breakdown", {})
        if beh_sub:
            st.markdown("##### Behavioral Signals", help="Sub-scores contributing to the Behavioral component")
            _render_behavioral_breakdown(beh_sub)

    # Middle: skills + education
    with col_mid:
        st.markdown("##### Skills")
        skills_snap = r.get("skills_snapshot", [])
        matched_skills = r.get("matched_skills", [])
        missing_skills = r.get("missing_skills", [])
        matched_set = {s.lower() for s in matched_skills}

        if skills_snap:
            order_map = {"expert": 4, "advanced": 3, "intermediate": 2, "beginner": 1}
            for s in skills_snap:
                name = s.get("name", "")
                prof = s.get("proficiency", "")
                end = s.get("endorsements", 0)
                is_match = name.lower() in matched_set
                color = "#4F46E5" if is_match else "#374151"
                match_icon = "✓ " if is_match else ""
                prof_val = order_map.get(prof, 1) / 4
                prof_color = _score_color(prof_val + 0.2)
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                     padding:.25rem 0;border-bottom:1px solid #F8FAFC;font-size:.8rem">
                  <span style="color:{color};font-weight:{'600' if is_match else '400'}">{match_icon}{_e(name)}</span>
                  <span style="color:#64748B;font-size:.72rem">{_e(prof)} · {end} end.</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:#94A3B8;font-size:.83rem">No skill data available.</div>',
                        unsafe_allow_html=True)

        if missing_skills:
            st.markdown('<div class="section-label" style="margin-top:.7rem">Missing JD Skills</div>',
                        unsafe_allow_html=True)
            miss_html = '<div style="margin:.25rem 0">'
            for m in missing_skills:
                miss_html += f'<span class="tag tag-miss">− {m}</span> '
            miss_html += "</div>"
            st.markdown(miss_html, unsafe_allow_html=True)

        edu = r.get("education_snapshot", {})
        if edu and edu.get("degree"):
            st.markdown("##### Education")
            tier = edu.get("tier", "")
            tier_label = f" · {tier.replace('_', ' ').title()}" if tier else ""
            st.markdown(f"""
            <div class="evidence-card">
              <div style="font-weight:600;color:#0F172A;font-size:.85rem">{_e(edu.get('degree',''))} in {_e(edu.get('field',''))}</div>
              <div style="color:#64748B;font-size:.78rem">{_e(edu.get('institution',''))}{_e(tier_label)}</div>
            </div>
            """, unsafe_allow_html=True)

    # Right: recruiter summary + career evidence
    with col_right:
        st.markdown("##### Recruiter Summary")
        reasoning = r.get("reasoning", "No reasoning available.")
        st.markdown(f"""
        <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
             padding:.8rem 1rem;font-size:.85rem;color:#1E3A5F;line-height:1.6">
          {_e(reasoning)}
        </div>
        """, unsafe_allow_html=True)

        snippets = r.get("career_snippets", [])
        if snippets:
            st.markdown("##### Career Evidence")
            _render_career_snippets(snippets)

        signals = r.get("redrob_signals_snapshot", {})
        if signals:
            st.markdown("##### Recruiter Signals")
            sig_items = [
                ("Last Active", signals.get("last_active_date", "—")),
                ("Open to Work", "Yes ✓" if signals.get("open_to_work_flag") else "No"),
                ("Response Rate", f"{signals.get('recruiter_response_rate', 0):.0%}" if signals.get("recruiter_response_rate") is not None else "—"),
                ("Notice Period", f"{signals.get('notice_period_days', '—')} days"),
                ("GitHub Activity", f"{signals.get('github_activity_score', '—')}/100"),
                ("Interview Completion", f"{signals.get('interview_completion_rate', 0):.0%}" if signals.get("interview_completion_rate") is not None else "—"),
            ]
            sal = signals.get("expected_salary_range_inr_lpa")
            if sal:
                sig_items.append(("Expected CTC", f"₹{sal.get('min','?')}–{sal.get('max','?')} LPA"))
            rows_html = "".join(
                f'<div style="display:flex;justify-content:space-between;padding:.2rem 0;'
                f'border-bottom:1px solid #F8FAFC;font-size:.79rem">'
                f'<span style="color:#64748B">{k}</span>'
                f'<span style="color:#0F172A;font-weight:500">{v}</span></div>'
                for k, v in sig_items
            )
            st.markdown(f"""
            <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;
                 padding:.7rem 1rem;">{rows_html}</div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — Candidate Comparison
# ─────────────────────────────────────────────────────────────────────────────
with tab_compare:
    st.markdown("Select two candidates to compare side-by-side — experience, skills, signals, and scores.")

    options_cmp = [
        f"#{r['rank']}  {r['candidate_id']}  —  {r['profile_snapshot']['current_title']}"
        for r in top100
    ]

    cmp_col1, cmp_col2 = st.columns(2)
    with cmp_col1:
        sel_a = st.selectbox("Candidate A", options_cmp, index=0, key="cmp_a")
    with cmp_col2:
        sel_b = st.selectbox("Candidate B", options_cmp, index=min(1, len(options_cmp)-1), key="cmp_b")

    idx_a = options_cmp.index(sel_a)
    idx_b = options_cmp.index(sel_b)
    ra, rb = top100[idx_a], top100[idx_b]

    if idx_a == idx_b:
        st.markdown("""
        <div class="alert-info">
          Select two different candidates to compare.
        </div>
        """, unsafe_allow_html=True)
    else:
        sa, sb = ra["final_score"], rb["final_score"]
        winner_rank = ra["rank"] if sa >= sb else rb["rank"]
        winner_id   = ra["candidate_id"] if sa >= sb else rb["candidate_id"]
        delta = abs(sa - sb)

        st.markdown(f"""
        <div class="compare-winner">
          🏆 &nbsp;<b>#{winner_rank} {_e(winner_id)}</b> is the stronger candidate
          &nbsp;·&nbsp; Scores: <b>{max(sa, sb):.3f}</b> vs {min(sa, sb):.3f}
          &nbsp;(Δ {delta:.4f})
        </div>
        """, unsafe_allow_html=True)

        def _render_candidate_compare(r: Dict, label: str):
            snap = r["profile_snapshot"]
            scores_c = r.get("scores", {})
            conf_c = r.get("confidence", "Medium")
            conf_cls_c = _conf_class(conf_c)
            is_winner = r["final_score"] == max(sa, sb)
            border_color = "#3B82F6" if is_winner else "#E2E8F0"
            bg_color = "#EFF6FF" if is_winner else "#FFFFFF"

            st.markdown(f"""
            <div style="border:2px solid {border_color};border-radius:14px;
                 padding:1.1rem 1.3rem;background:{bg_color};margin-bottom:.75rem;
                 box-shadow:{'0 4px 16px rgba(37,99,235,.1)' if is_winner else 'none'}">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem">
                <span style="font-size:.68rem;font-weight:700;color:#64748B;text-transform:uppercase;
                      letter-spacing:.1em">{_e(label)}</span>
                {'<span class="tag tag-active" style="font-size:.7rem">✦ Higher Ranked</span>' if is_winner else ''}
              </div>
              <div style="font-weight:800;font-size:1.05rem;color:#0F172A;letter-spacing:-.02em;margin-bottom:.2rem">
                {_e(snap['current_title'])}
              </div>
              <div style="font-size:.8rem;color:#64748B;margin-bottom:.15rem">
                {_e(snap.get('current_company','—'))} &nbsp;·&nbsp; {snap['years_of_experience']}y exp
              </div>
              <div style="font-size:.8rem;color:#64748B;margin-bottom:.4rem">
                📍 {_e(snap['location'])}
              </div>
              <div style="display:flex;align-items:baseline;gap:.45rem;margin:.1rem 0 .3rem">
                <span style="font-size:1.75rem;font-weight:800;color:#1D4ED8;letter-spacing:-.03em;line-height:1">
                  {r['final_score']:.3f}
                </span>
                <span style="font-size:.75rem;font-weight:400;color:#64748B">final score</span>
              </div>
              <div style="font-size:.8rem">Confidence: <span class="{conf_cls_c}">{conf_c}</span></div>
            </div>
            """, unsafe_allow_html=True)

            # Score breakdown comparison
            st.markdown('<div class="section-label">Component Scores</div>', unsafe_allow_html=True)
            comp_rows = [
                ("Title / Role",       "title_role",          0.25),
                ("Skill Match",        "skill_match",          0.20),
                ("Production Evid.",   "production_evidence",  0.15),
                ("Behavioral",         "behavioral",           0.15),
                ("Experience Fit",     "experience_fit",       0.10),
                ("Domain / Company",   "domain_fit",           0.10),
                ("Location",           "location",             0.05),
            ]
            other_scores = top100[idx_b].get("scores", {}) if r is ra else top100[idx_a].get("scores", {})
            for name, key, wt in comp_rows:
                my_val = scores_c.get(key, 0)
                their_val = other_scores.get(key, 0)
                my_color = _score_color(my_val)
                arrow = "▲" if my_val > their_val else ("▼" if my_val < their_val else "=")
                arrow_color = "#10B981" if arrow == "▲" else ("#EF4444" if arrow == "▼" else "#94A3B8")
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                     padding:.22rem 0;border-bottom:1px solid #F8FAFC;font-size:.79rem">
                  <span style="color:#374151">{name}</span>
                  <span>
                    <span style="color:{arrow_color};font-size:.65rem;margin-right:.2rem">{arrow}</span>
                    <span style="font-weight:700;color:{my_color}">{my_val:.3f}</span>
                  </span>
                </div>
                {_bar(my_val, my_color, 3)}
                """, unsafe_allow_html=True)

            # Strengths
            strength_comps = sorted(comp_rows, key=lambda x: -scores_c.get(x[1], 0))[:3]
            strength_strs = [f"{n} ({scores_c.get(k,0):.2f})" for n, k, _ in strength_comps
                             if scores_c.get(k, 0) >= 0.70]
            if strength_strs:
                st.markdown('<div class="section-label" style="margin-top:.5rem">Strengths</div>',
                            unsafe_allow_html=True)
                st.markdown(
                    '<div style="font-size:.8rem;color:#15803D">' +
                    " · ".join(strength_strs) + "</div>",
                    unsafe_allow_html=True
                )

            # Risks
            risk_comps = [row for row in comp_rows if scores_c.get(row[1], 0) < 0.55]
            pen = scores_c.get("penalty", 0)
            pen_reasons = r.get("penalty_reasons", [])
            risks = [f"{n} ({scores_c.get(k,0):.2f})" for n, k, _ in risk_comps]
            if pen > 0.05:
                risks.insert(0, f"Penalty {pen:.0%}: {'; '.join(pen_reasons[:1])}")
            if risks:
                st.markdown('<div class="section-label" style="margin-top:.4rem">Risks</div>',
                            unsafe_allow_html=True)
                st.markdown(
                    '<div style="font-size:.8rem;color:#C2410C">' +
                    " · ".join(risks[:3]) + "</div>",
                    unsafe_allow_html=True
                )

            # Skills
            matched_c = r.get("matched_skills", [])
            missing_c = r.get("missing_skills", [])
            if matched_c or missing_c:
                st.markdown('<div class="section-label" style="margin-top:.5rem">Skills</div>',
                            unsafe_allow_html=True)
                skill_html = '<div style="margin:.2rem 0">'
                for s in matched_c[:5]:
                    skill_html += f'<span class="tag tag-skill">{_e(s)}</span> '
                for s in missing_c[:3]:
                    skill_html += f'<span class="tag tag-miss">− {_e(s)}</span> '
                skill_html += "</div>"
                st.markdown(skill_html, unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            _render_candidate_compare(ra, "Candidate A")
        with col_b:
            _render_candidate_compare(rb, "Candidate B")

        # Side-by-side reasoning
        st.markdown('<div class="section-label" style="margin-top:1.25rem">Recruiter Summary Comparison</div>',
                    unsafe_allow_html=True)
        rz_a, rz_b = st.columns(2)
        with rz_a:
            st.markdown(f"""
            <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
                 padding:.8rem 1rem;font-size:.83rem;color:#1E3A5F;line-height:1.6">
              <b>{_e(ra['profile_snapshot']['current_title'])} (#{ra['rank']})</b><br><br>
              {_e(ra.get('reasoning','—'))}
            </div>
            """, unsafe_allow_html=True)
        with rz_b:
            st.markdown(f"""
            <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
                 padding:.8rem 1rem;font-size:.83rem;color:#1E3A5F;line-height:1.6">
              <b>{_e(rb['profile_snapshot']['current_title'])} (#{rb['rank']})</b><br><br>
              {_e(rb.get('reasoning','—'))}
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — Ranking Insights Dashboard
# ─────────────────────────────────────────────────────────────────────────────
with tab_insights:
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        _PLOT_FONT  = dict(family="Inter, sans-serif", size=12, color="#334155")
        _PLOT_PAPER = "#FFFFFF"
        _PLOT_BG    = "#F8FAFC"
        _PLOT_MAR   = dict(l=20, r=20, t=44, b=20)
        _BLUE_SEQ   = "Blues"
        _PRIMARY    = "#2563EB"
        _TITLE_FONT = dict(family="Inter, sans-serif", size=14, color="#0F172A")

        scores_all  = [r["final_score"] for r in top100]
        titles_all  = [r["profile_snapshot"]["current_title"] for r in top100]
        yoes_all    = [float(r["profile_snapshot"]["years_of_experience"]) for r in top100]
        locs_all    = [r["profile_snapshot"].get("location", "Unknown") for r in top100]
        confs_all   = [r.get("confidence", "Medium") for r in top100]

        # Seniority bands from YOE
        def _seniority(yoe: float) -> str:
            if yoe < 3:  return "Junior (<3y)"
            if yoe < 6:  return "Mid (3-6y)"
            if yoe < 10: return "Senior (6-10y)"
            return "Principal (10y+)"

        seniority_all = [_seniority(y) for y in yoes_all]

        # Notice period distribution
        notices = []
        for r in top100:
            sig = r.get("redrob_signals_snapshot", {})
            n = sig.get("notice_period_days")
            if n is not None:
                if n <= 15:   notices.append("Immediate (≤15d)")
                elif n <= 30: notices.append("Short (16-30d)")
                elif n <= 60: notices.append("Medium (31-60d)")
                else:         notices.append("Long (>60d)")

        # Skills frequency across top-100
        skill_counter: Counter = Counter()
        for r in top100:
            for s in r.get("matched_skills", []):
                skill_counter[s] += 1
        top_skills_freq = skill_counter.most_common(15)

        # ── Row 1: Score distribution + Seniority ─────────────────────────────
        row1_l, row1_r = st.columns(2)

        with row1_l:
            fig_hist = px.histogram(
                x=scores_all, nbins=20,
                title="Score Distribution — Top 100",
                labels={"x": "Final Score", "y": "Candidates"},
                color_discrete_sequence=[_PRIMARY],
            )
            fig_hist.update_layout(
                paper_bgcolor=_PLOT_PAPER, plot_bgcolor=_PLOT_BG,
                font=_PLOT_FONT, margin=_PLOT_MAR, showlegend=False,
                title_font=_TITLE_FONT,
            )
            mean_s = sum(scores_all) / len(scores_all)
            fig_hist.add_vline(x=mean_s, line_dash="dot", line_color="#94A3B8",
                               annotation_text=f"mean {mean_s:.3f}", annotation_position="top right")
            st.plotly_chart(fig_hist, use_container_width=True)

        with row1_r:
            sen_counts = Counter(seniority_all)
            sen_order = ["Junior (<3y)", "Mid (3-6y)", "Senior (6-10y)", "Principal (10y+)"]
            sen_vals  = [sen_counts.get(s, 0) for s in sen_order]
            fig_sen = px.bar(
                x=sen_order, y=sen_vals,
                title="Seniority Distribution",
                labels={"x": "Band", "y": "Count"},
                color=sen_vals, color_continuous_scale="Blues",
            )
            fig_sen.update_layout(
                paper_bgcolor=_PLOT_PAPER, plot_bgcolor=_PLOT_BG,
                font=_PLOT_FONT, margin=_PLOT_MAR,
                coloraxis_showscale=False, title_font_size=14,
            )
            st.plotly_chart(fig_sen, use_container_width=True)

        # ── Row 2: Skills frequency + Location distribution ────────────────────
        row2_l, row2_r = st.columns(2)

        with row2_l:
            if top_skills_freq:
                sk_names = [n for n, _ in reversed(top_skills_freq)]
                sk_counts = [c for _, c in reversed(top_skills_freq)]
                fig_skills = px.bar(
                    x=sk_counts, y=sk_names, orientation="h",
                    title="Top Skills in Shortlist (matched to JD)",
                    labels={"x": "Candidates with skill", "y": "Skill"},
                    color=sk_counts, color_continuous_scale="Blues",
                )
                fig_skills.update_layout(
                    paper_bgcolor=_PLOT_PAPER, plot_bgcolor=_PLOT_BG,
                    font=_PLOT_FONT, margin=dict(l=120, r=20, t=40, b=20),
                    coloraxis_showscale=False, title_font_size=14, height=400,
                )
                st.plotly_chart(fig_skills, use_container_width=True)
            else:
                st.info("Skill frequency data not available. Re-run pipeline to populate.")

        with row2_r:
            loc_counts = Counter(locs_all).most_common(10)
            if loc_counts:
                lc_names  = [l for l, _ in reversed(loc_counts)]
                lc_vals   = [c for _, c in reversed(loc_counts)]
                fig_loc = px.bar(
                    x=lc_vals, y=lc_names, orientation="h",
                    title="Location Distribution — Top 100",
                    labels={"x": "Count", "y": "Location"},
                    color=lc_vals, color_continuous_scale="Blues",
                )
                fig_loc.update_layout(
                    paper_bgcolor=_PLOT_PAPER, plot_bgcolor=_PLOT_BG,
                    font=_PLOT_FONT, margin=dict(l=100, r=20, t=40, b=20),
                    coloraxis_showscale=False, title_font_size=14,
                )
                st.plotly_chart(fig_loc, use_container_width=True)

        # ── Row 3: Availability + Ranking factors radar ────────────────────────
        row3_l, row3_r = st.columns(2)

        with row3_l:
            if notices:
                notice_counts = Counter(notices)
                notice_order = ["Immediate (≤15d)", "Short (16-30d)", "Medium (31-60d)", "Long (>60d)"]
                nv = [notice_counts.get(n, 0) for n in notice_order]
                colors_notice = ["#10B981", "#3B82F6", "#F59E0B", "#EF4444"]
                fig_notice = go.Figure(go.Bar(
                    x=notice_order, y=nv,
                    marker_color=colors_notice,
                ))
                fig_notice.update_layout(
                    title="Availability Distribution (Notice Period)",
                    paper_bgcolor=_PLOT_PAPER, plot_bgcolor=_PLOT_BG,
                    font=_PLOT_FONT, margin=_PLOT_MAR, title_font_size=14,
                    showlegend=False,
                )
                st.plotly_chart(fig_notice, use_container_width=True)
            else:
                st.info("Availability data not available. Re-run pipeline to populate.")

        with row3_r:
            # Average component scores — radar
            comp_keys  = ["title_role", "skill_match", "production_evidence",
                          "behavioral", "experience_fit", "domain_fit", "location"]
            comp_labels = ["Title/Role", "Skills", "Production", "Behavioral",
                           "Experience", "Domain", "Location"]
            avg_vals = [
                sum(r.get("scores", {}).get(k, 0) for r in top100) / max(len(top100), 1)
                for k in comp_keys
            ]
            fig_radar = go.Figure(go.Scatterpolar(
                r=avg_vals + [avg_vals[0]],
                theta=comp_labels + [comp_labels[0]],
                fill="toself",
                fillcolor="rgba(59,130,246,0.12)",
                line=dict(color=_PRIMARY, width=2),
                name="Top-100 avg",
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1],
                                           tickfont=dict(size=9), gridcolor="#E2E8F0")),
                title=dict(text="Avg Ranking Factors — Top 100", font_size=14),
                paper_bgcolor=_PLOT_PAPER,
                font=_PLOT_FONT,
                margin=dict(l=40, r=40, t=50, b=20),
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        # ── Confidence breakdown table ─────────────────────────────────────────
        st.markdown('<div class="section-label" style="margin-top:1rem">Confidence Distribution</div>',
                    unsafe_allow_html=True)
        conf_counts = Counter(confs_all)
        cc1, cc2, cc3 = st.columns(3)
        _conf_kpi = {"High": "kpi-green", "Medium": "kpi-amber", "Low": "kpi-red"}
        for col, level in [(cc1, "High"), (cc2, "Medium"), (cc3, "Low")]:
            count = conf_counts.get(level, 0)
            pct = count / len(top100) * 100
            col.markdown(f"""
            <div class="kpi-card {_conf_kpi[level]}">
              <div class="kpi-value">{count}</div>
              <div class="kpi-label">{level} Confidence</div>
              <div class="kpi-sub">{pct:.0f}% of top-100</div>
            </div>
            """, unsafe_allow_html=True)

    except ImportError:
        st.warning("Install plotly for charts: `pip install plotly`")

        st.markdown("##### Score Distribution (text fallback)")
        scores_all = [r["final_score"] for r in top100]
        bins = [0] * 10
        for s in scores_all:
            b = min(9, int(s * 10))
            bins[b] += 1
        for i, count in enumerate(bins):
            lo, hi = i / 10, (i + 1) / 10
            st.text(f"{lo:.1f}–{hi:.1f}: {'█' * count} ({count})")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — Evaluation
# ─────────────────────────────────────────────────────────────────────────────
with tab_eval:
    eval_path = Path("outputs/eval_report.json")
    if not eval_path.exists():
        st.markdown("""
        <div class="alert-info">
          No evaluation report found. Generate it with:<br><br>
          <code>python evaluation/eval.py --results outputs/debug.json
          --candidates data/raw/candidates.jsonl --json outputs/eval_report.json</code>
        </div>
        """, unsafe_allow_html=True)
    else:
        with open(eval_path) as f:
            ev = json.load(f)

        sc    = ev.get("sanity_checks", {})
        dist  = ev.get("score_distribution", {})
        bl    = ev.get("baseline_comparison", {})
        t10   = ev.get("top10_profile", {})
        err   = ev.get("error_detection", {})

        # Format checks
        st.markdown('<div class="section-label">Format &amp; Sanity Checks</div>', unsafe_allow_html=True)
        check_items = [
            ("Scores monotonically non-increasing", sc.get("scores_non_increasing", False)),
            ("Ranks 1–100 each appear exactly once", sc.get("ranks_unique_1_to_100", False)),
            ("Candidate IDs all unique", sc.get("candidate_ids_unique", False)),
            ("All scores in [0, 1]", sc.get("scores_in_range", False)),
            ("No honeypots in top-100", sc.get("no_honeypots_in_top100", False)),
            (f"Top-10 ML/AI: {sc.get('top10_ml_candidates','?')}/10", sc.get("top10_ml_fraction", 0) >= 0.7),
        ]
        all_pass = all(ok for _, ok in check_items)
        check_html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem .75rem;margin:.5rem 0 1rem">'
        for label, ok in check_items:
            icon_color = "#16A34A" if ok else "#DC2626"
            icon_char  = "✓" if ok else "✗"
            check_html += f'''<div style="display:flex;align-items:center;gap:.4rem;
                font-size:.875rem;color:#334155">
              <span style="color:{icon_color};font-weight:700;font-size:1rem">{icon_char}</span>
              {label}
            </div>'''
        check_html += '</div>'
        st.markdown(check_html, unsafe_allow_html=True)

        if all_pass:
            st.markdown('<div class="alert-ok">All format checks passed. Submission is valid.</div>',
                        unsafe_allow_html=True)

        st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown('<div class="section-label">Top-10 Component Averages</div>', unsafe_allow_html=True)
            comp_avgs = t10.get("component_averages", {})
            for comp, val in comp_avgs.items():
                label = comp.replace("_", " ").title()
                color = _score_color(val)
                pct = int(val * 100)
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;font-size:.875rem;
                     padding:.28rem 0;color:#334155">
                  <span>{label}</span>
                  <b style="color:{color};font-variant-numeric:tabular-nums">{val:.3f}</b>
                </div>
                <div class="bar-bg"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div>
                """, unsafe_allow_html=True)

        with col_r:
            st.markdown('<div class="section-label">Baseline Comparison</div>', unsafe_allow_html=True)
            if bl:
                st.metric("Overlap @10 vs keyword model", f"{bl.get('overlap@10','?')}/10",
                          help="Low overlap = our model picks different (and better) candidates than keyword count")
                st.metric("Overlap @25", f"{bl.get('overlap@25','?')}/25")
                st.metric("Overlap @50", f"{bl.get('overlap@50','?')}/50")
                if bl.get("summary"):
                    st.markdown(f'<div style="font-size:.875rem;color:#334155;margin-top:.5rem">{bl["summary"]}</div>',
                                unsafe_allow_html=True)
            else:
                st.info("Rerun eval.py with `--candidates` to see baseline comparison.")

        st.markdown('<div class="section-label" style="margin-top:1rem">Error Detection</div>',
                    unsafe_allow_html=True)
        errors = err.get("critical_errors", [])
        if errors:
            st.error(f"⚠ {len(errors)} critical error(s) found")
            for e in errors:
                st.markdown(f"- **{e['type']}** rank={e['rank']} `{e['candidate_id']}` score={e['score']:.3f}")
        else:
            st.success("✓ No critical errors detected")

        if err.get("score_compression_warning"):
            st.warning(f"⚠ Top-10 score spread is {err.get('top10_score_range',0):.4f} — compressed (likely synthetic-data artifact)")
        if err.get("title_monotony_warning"):
            st.warning(f"⚠ Top-10 title diversity low ({err.get('top10_title_diversity',0)} unique titles)")
        if not err.get("score_compression_warning") and not err.get("title_monotony_warning"):
            st.success("✓ No ranking anomalies detected")


# ─────────────────────────────────────────────────────────────────────────────
# TAB 6 — Saved Shortlist
# ─────────────────────────────────────────────────────────────────────────────
with tab_saved:
    saved_ids = st.session_state.shortlist
    saved_cands = [r for r in top100 if r["candidate_id"] in saved_ids]

    if not saved_cands:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#64748B">
          <div style="font-size:2.5rem;margin-bottom:.75rem">📌</div>
          <b>Your shortlist is empty.</b><br>
          <span style="font-size:.875rem">Open "💡 Why this candidate?" on any card and click "Save to Shortlist".</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        sh_col1, sh_col2 = st.columns([3, 1])
        with sh_col1:
            st.markdown(f"""
            <div style="font-size:1rem;font-weight:700;color:#0F172A;margin:.3rem 0 .2rem">
              Shortlisted Candidates
              <span style="font-size:.82rem;font-weight:400;color:#64748B;margin-left:.6rem">
                {len(saved_cands)} saved · ready to export or share
              </span>
            </div>
            """, unsafe_allow_html=True)
        with sh_col2:
            def _export_shortlist():
                buf = io.StringIO()
                writer = _csv.writer(buf)
                writer.writerow(["rank", "candidate_id", "score", "title", "company", "yoe", "confidence", "reasoning", "notes"])
                for r in saved_cands:
                    snap = r["profile_snapshot"]
                    writer.writerow([
                        r["rank"], r["candidate_id"], round(r["final_score"], 4),
                        snap.get("current_title",""), snap.get("current_company",""),
                        snap.get("years_of_experience",0), r.get("confidence",""),
                        r.get("reasoning",""), st.session_state.recruiter_notes.get(r["candidate_id"],""),
                    ])
                return buf.getvalue()
            st.download_button(
                "⬇️ Export Shortlist CSV",
                data=_export_shortlist(),
                file_name="shortlist.csv",
                mime="text/csv",
            )

        for result in saved_cands:
            rank  = result["rank"]
            cid   = result["candidate_id"]
            score = result["final_score"]
            snap  = result["profile_snapshot"]
            title = snap["current_title"]
            yoe   = snap["years_of_experience"]
            co    = snap.get("current_company", "")
            loc   = snap.get("location", "")
            conf  = result.get("confidence", "Medium")
            reasoning = result.get("reasoning", "")
            note = st.session_state.recruiter_notes.get(cid, "")
            color = _score_color(score)
            score_class = _pill_class(score)
            rank_accent = {1: "cand-card-gold", 2: "cand-card-silver", 3: "cand-card-bronze"}.get(rank, "")
            loc_tag = f'<span class="tag tag-loc">📍 {_e(loc)}</span>' if loc else ""
            conf_cls = _conf_class(conf)
            note_html = (f'<div style="margin-top:.35rem;font-size:.78rem;color:#6B7280;'
                         f'font-style:italic">{_e(note)}</div>') if note else ""

            st.markdown(f"""
            <div class="cand-card {rank_accent}">
              <div style="display:flex;align-items:flex-start;gap:.9rem">
                <div class="rank-badge {_rank_class(rank)}">#{rank}</div>
                <div style="flex:1;min-width:0">
                  <div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;margin-bottom:.25rem">
                    <span style="font-weight:700;color:#0F172A;font-size:1.0rem">{_e(title)}</span>
                    <span class="tag tag-conf">{conf} confidence</span>
                    {loc_tag}
                  </div>
                  <div style="font-size:.8rem;color:#64748B;margin:.05rem 0 .4rem">
                    {_e(co)} &nbsp;·&nbsp; {yoe}y exp &nbsp;·&nbsp;
                    <span style="font-family:monospace;font-size:.75rem;color:#94A3B8">{_e(cid)}</span>
                  </div>
                  <div style="font-size:.875rem;color:#334155;line-height:1.6">{_e(reasoning)}</div>
                  {note_html}
                </div>
                <div style="flex-shrink:0;text-align:right;min-width:72px;padding-left:.5rem">
                  <span class="{score_class}">{score:.3f}</span>
                  {_bar(score, color)}
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            rem_col, _ = st.columns([1, 5])
            with rem_col:
                if st.button("Remove", key=f"rm_{cid}"):
                    st.session_state.shortlist.discard(cid)
                    st.rerun()
