"""
SignalRank AI — Recruiter Dashboard
Professional candidate ranking interface for the Redrob AI Challenge.

Run: streamlit run app/streamlit_app.py
"""

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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="st-"], .stMarkdown, p, div {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ─── Scrollbar ───────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #F8FAFC; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 4px; }

/* ─── Header ─────────────────────────────────────────── */
.sr-header {
    background: linear-gradient(135deg, #0F172A 0%, #1E3A5F 55%, #1D4ED8 100%);
    padding: 1.6rem 2rem; border-radius: 16px; margin-bottom: 1.5rem;
    box-shadow: 0 4px 20px rgba(29,78,216,.18);
}
.sr-header h1 {
    color: #fff; font-size: 1.85rem; font-weight: 700; margin: 0;
    letter-spacing: -0.6px; line-height: 1.2;
}
.sr-header p { color: #94A3B8; margin: .35rem 0 0; font-size: .9rem; line-height: 1.5; }
.badge {
    display: inline-block; background: rgba(59,130,246,.25); color: #93C5FD;
    border: 1px solid rgba(147,197,253,.3);
    padding: .12rem .6rem; border-radius: 999px; font-size: .7rem;
    font-weight: 600; margin-left: .5rem; vertical-align: middle;
    letter-spacing: .05em; text-transform: uppercase;
}

/* ─── Metric cards ───────────────────────────────────── */
.metric-card {
    background: #fff; border: 1px solid #E2E8F0; border-radius: 14px;
    padding: 1.15rem 1rem; text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,.04); transition: box-shadow .15s;
}
.metric-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); }
.metric-value { font-size: 1.9rem; font-weight: 700; color: #0F172A; line-height: 1.1; }
.metric-label { font-size: .72rem; color: #64748B; margin-top: .3rem; font-weight: 600;
    letter-spacing: .04em; text-transform: uppercase; }
.metric-sub   { font-size: .68rem; color: #94A3B8; margin-top: .15rem; }

/* ─── Candidate card ─────────────────────────────────── */
.cand-card {
    background: #fff; border: 1px solid #E2E8F0; border-radius: 14px;
    padding: 1.1rem 1.3rem; margin-bottom: .5rem;
    transition: box-shadow .15s, border-color .15s, transform .1s;
}
.cand-card:hover {
    box-shadow: 0 8px 24px rgba(0,0,0,.08);
    border-color: #BFDBFE; transform: translateY(-1px);
}

.rank-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 2.3rem; height: 2.3rem; border-radius: 50%;
    font-weight: 700; font-size: .78rem; flex-shrink: 0;
    letter-spacing: -.02em;
}
.rb-gold   { background: linear-gradient(135deg,#FEF9C3,#FDE68A); color: #78350F;
    box-shadow: 0 2px 6px rgba(251,191,36,.3); }
.rb-silver { background: linear-gradient(135deg,#F1F5F9,#E2E8F0); color: #475569; }
.rb-bronze { background: linear-gradient(135deg,#FFF7ED,#FED7AA); color: #9A3412; }
.rb-plain  { background: #F8FAFC; color: #94A3B8; }

.score-pill {
    background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE;
    padding: .18rem .7rem; border-radius: 999px;
    font-size: .8rem; font-weight: 700; font-variant-numeric: tabular-nums;
}
.score-pill-warn { background: #FFF7ED; color: #9A3412; border-color: #FED7AA; }
.score-pill-low  { background: #FEF2F2; color: #DC2626; border-color: #FECACA; }

.tag {
    display: inline-block; padding: .1rem .48rem; border-radius: 5px;
    font-size: .68rem; font-weight: 600; margin: .04rem .02rem;
}
.tag-hp     { background: #FEF2F2; color: #DC2626; }
.tag-pen    { background: #FFF7ED; color: #C2410C; }
.tag-active { background: #F0FDF4; color: #15803D; }
.tag-conf   { background: #EFF6FF; color: #1D4ED8; }
.tag-loc    { background: #F8FAFC; color: #475569; border: 1px solid #E2E8F0; }
.tag-skill  { background: #F5F3FF; color: #6D28D9; border: 1px solid #DDD6FE; }
.tag-miss   { background: #FEF2F2; color: #991B1B; }

/* ─── Score bar ──────────────────────────────────────── */
.bar-bg   { background: #EFF6FF; border-radius: 4px; height: 5px; margin-top: 3px; }
.bar-fill { height: 5px; border-radius: 4px; transition: width .3s; }
.bar-bg-sm { background: #F1F5F9; border-radius: 3px; height: 4px; }

/* ─── Section label ──────────────────────────────────── */
.section-label {
    font-size: .7rem; font-weight: 700; color: #94A3B8;
    letter-spacing: .09em; text-transform: uppercase; margin: .6rem 0 .3rem;
}

/* ─── Explainability panel ───────────────────────────── */
.evidence-card {
    background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px;
    padding: .75rem 1rem; margin-bottom: .5rem; font-size: .82rem;
    line-height: 1.55;
}
.evidence-title { font-size: .72rem; font-weight: 700; color: #64748B;
    letter-spacing: .07em; text-transform: uppercase; margin-bottom: .3rem; }
.evidence-snippet { color: #374151; font-style: italic; }
.evidence-meta { color: #64748B; font-size: .75rem; }

/* ─── Comparison view ────────────────────────────────── */
.compare-header {
    background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px;
    padding: .7rem 1rem; margin-bottom: .75rem; font-weight: 600;
    color: #0F172A; font-size: .9rem;
}
.compare-winner {
    background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 10px;
    padding: .5rem .9rem; font-size: .82rem; color: #15803D; font-weight: 600;
}
.compare-risk {
    background: #FFF7ED; border: 1px solid #FED7AA; border-radius: 10px;
    padding: .5rem .9rem; font-size: .82rem; color: #9A3412;
}

/* ─── Sidebar ────────────────────────────────────────── */
.sidebar-label {
    font-size: .68rem; font-weight: 700; color: #94A3B8;
    letter-spacing: .09em; text-transform: uppercase; margin: .9rem 0 .3rem;
}

/* ─── Alert banners ──────────────────────────────────── */
.alert-warn {
    background: #FFFBEB; border: 1px solid #FDE68A; border-radius: 10px;
    padding: .65rem 1rem; font-size: .83rem; color: #92400E; margin-bottom: .75rem;
}
.alert-ok {
    background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 10px;
    padding: .65rem 1rem; font-size: .83rem; color: #15803D; margin-bottom: .75rem;
}
.alert-info {
    background: #EFF6FF; border: 1px solid #BFDBFE; border-radius: 10px;
    padding: .65rem 1rem; font-size: .83rem; color: #1D4ED8; margin-bottom: .75rem;
}

/* ─── Component row ──────────────────────────────────── */
.comp-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: .32rem 0; border-bottom: 1px solid #F8FAFC; font-size: .83rem;
}
.comp-name  { color: #374151; font-weight: 500; }
.comp-wt    { color: #9CA3AF; font-size: .73rem; margin-left: .25rem; }
.comp-score { font-weight: 700; font-variant-numeric: tabular-nums; }

/* ─── Confidence badge ───────────────────────────────── */
.conf-high   { color: #15803D; font-weight: 700; }
.conf-medium { color: #B45309; font-weight: 700; }
.conf-low    { color: #DC2626; font-weight: 700; }

/* ─── Hide Streamlit chrome ──────────────────────────── */
footer, #MainMenu, .stDeployButton { visibility: hidden; display: none; }
.block-container { padding-top: 1.2rem; }
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
for _k, _v in [("results", None), ("pipeline_stats", None), ("selected_idx", 0)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def run_pipeline_on_upload(uploaded_file) -> bool:
    from rank import run_pipeline

    raw_bytes = uploaded_file.read()
    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        st.error("File must be UTF-8 encoded.")
        return False

    first_lines = [ln.strip() for ln in content.splitlines() if ln.strip()][:3]
    for ln in first_lines:
        try:
            json.loads(ln)
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSONL on line: {ln[:60]}… — {exc}")
            return False

    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    out_csv = "outputs/submission.csv"
    out_json = "outputs/debug.json"
    os.makedirs("outputs", exist_ok=True)

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
        for stage_name, target_pct in stages[:2]:
            status_text.markdown(
                f'<div class="alert-info">⏳ <b>{stage_name}…</b></div>',
                unsafe_allow_html=True
            )
            progress_bar.progress(target_pct)
            time.sleep(0.04)

        run_pipeline(tmp_path, out_csv, out_json)

        for stage_name, target_pct in stages[2:]:
            status_text.markdown(
                f'<div class="alert-info">⏳ <b>{stage_name}…</b></div>',
                unsafe_allow_html=True
            )
            progress_bar.progress(target_pct)
            time.sleep(0.04)

        progress_bar.progress(100)
        elapsed = time.time() - t0
        status_text.markdown(
            f'<div class="alert-ok">⚡ <b>Pipeline complete in {elapsed:.1f}s</b> — '
            f'100 candidates ranked and ready for review.</div>',
            unsafe_allow_html=True
        )
        st.session_state.pipeline_stats = {"elapsed": elapsed, "csv": out_csv, "json": out_json}
        return load_results_from_json(out_json)

    except Exception as exc:
        status_text.empty()
        progress_bar.empty()
        st.error(f"Pipeline failed: {exc}")
        return False
    finally:
        os.unlink(tmp_path)


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
    html = '<div style="margin:.4rem 0">'
    for s in skills[:8]:
        name = s.get("name", "")
        prof = s.get("proficiency", "")
        is_match = name.lower() in matched_set
        cls = "tag-skill" if is_match else "tag-loc"
        title = f"{prof}" if prof else ""
        html += f'<span class="tag {cls}" title="{title}">{name}</span> '
    html += "</div>"

    if missing:
        html += '<div class="section-label" style="margin-top:.5rem">Missing JD Skills</div>'
        html += '<div style="margin:.25rem 0">'
        for s in missing:
            html += f'<span class="tag tag-miss">− {s}</span> '
        html += "</div>"

    st.markdown(html, unsafe_allow_html=True)


def _render_career_snippets(snippets: List[Dict]):
    for sn in snippets:
        co = sn.get("company", "")
        title = sn.get("title", "")
        text = sn.get("snippet", "")
        has_prod = sn.get("has_production_evidence", False)
        prod_badge = '<span class="tag tag-active" style="font-size:.65rem">⚡ prod</span>' if has_prod else ""
        st.markdown(f"""
        <div class="evidence-card">
          <div class="evidence-title">{title} — {co} {prod_badge}</div>
          <div class="evidence-snippet">"{text}"</div>
        </div>
        """, unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="sr-header">
  <h1>⚡ SignalRank AI <span class="badge">Redrob 2026</span></h1>
  <p>Rank talent by fit, not keywords &nbsp;·&nbsp; Two-stage pipeline: semantic retrieval + hybrid evidence scoring + honeypot detection</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-label">Run Pipeline</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Upload candidates.jsonl",
        type=["jsonl", "json"],
        help="Organizer-provided JSONL candidate dataset",
        label_visibility="collapsed",
    )
    if uploaded:
        if st.button("⚡ Rank Candidates", type="primary", use_container_width=True):
            with st.spinner(""):
                run_pipeline_on_upload(uploaded)
    else:
        st.button("⚡ Rank Candidates", type="primary", use_container_width=True, disabled=True)

    st.markdown('<div class="sidebar-label">Load Existing Results</div>', unsafe_allow_html=True)
    results_path = st.text_input("Results JSON", value="outputs/debug.json", label_visibility="collapsed")
    if st.button("↑ Load from file", use_container_width=True):
        if load_results_from_json(results_path):
            st.success("Loaded")
        else:
            st.error("File not found or invalid.")

    st.markdown('<div class="sidebar-label">Export</div>', unsafe_allow_html=True)
    for label, path, mime in [
        ("📥 Submission CSV", "outputs/submission.csv", "text/csv"),
        ("📄 Full Debug JSON", "outputs/debug.json", "application/json"),
        ("📊 Eval Report", "outputs/eval_report.json", "application/json"),
    ]:
        p = Path(path)
        if p.exists():
            with open(p, encoding="utf-8") as f:
                st.download_button(label, data=f.read(), file_name=p.name, mime=mime,
                                   use_container_width=True)

    st.divider()
    st.markdown("""
    <div style="font-size:.76rem; color:#64748B; line-height:1.75">
    <b style="color:#0F172A">Architecture</b><br>
    FAISS dense + TF-IDF → RRF → pool<br>
    7-component rule scorer<br>
    Honeypot detection (7 checks)<br>
    all-MiniLM-L6-v2 embeddings<br><br>
    <b style="color:#0F172A">Constraints</b><br>
    CPU only · No network · &lt;20s cold
    </div>
    """, unsafe_allow_html=True)


# ── Auto-load ─────────────────────────────────────────────────────────────────
if st.session_state.results is None:
    load_results_from_json("outputs/debug.json")

if st.session_state.results is None:
    st.markdown("""
    <div style="text-align:center;padding:4rem 0;color:#64748B">
      <div style="font-size:3rem;margin-bottom:1rem">📂</div>
      <div style="font-size:1.15rem;font-weight:700;color:#0F172A;margin-bottom:.5rem">
        No results loaded
      </div>
      <div style="font-size:.9rem;line-height:1.7">
        Upload <code>candidates.jsonl</code> and click <b>Rank Candidates</b>,<br>
        or enter the path to an existing <code>outputs/debug.json</code> in the sidebar.
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
kpi_data = [
    (c1, f"{top10_ml}/10", "ML/AI in Top-10",   "Target ≥ 8/10"),
    (c2, f"{avg_top10:.3f}", "Avg Top-10 Score", "Out of 1.000"),
    (c3, str(high_conf), "High Confidence", f"of 100 ranked"),
    (c4, "✓ 0" if hp_count == 0 else f"⚠ {hp_count}", "Honeypots", ">10 = disqualified"),
    (c5, str(penalized), "Penalized", "Consulting / wrong domain"),
]
for col, val, label, sub in kpi_data:
    col.markdown(f"""
    <div class="metric-card">
      <div class="metric-value">{val}</div>
      <div class="metric-label">{label}</div>
      <div class="metric-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)

if st.session_state.pipeline_stats:
    stats = st.session_state.pipeline_stats
    st.markdown(f"""
    <div class="alert-ok" style="margin-top:.75rem">
    ⚡ Pipeline completed in <b>{stats['elapsed']:.1f}s</b> &nbsp;·&nbsp;
    Backend: FAISS + TF-IDF (RRF) &nbsp;·&nbsp;
    Output ready: <code>{stats['csv']}</code>
    </div>
    """, unsafe_allow_html=True)

if hp_count > 10:
    st.markdown(f"""
    <div class="alert-warn">
    ⚠ <b>Honeypot risk:</b> {hp_count} honeypots detected in top-100. This exceeds the organizer
    limit of 10 and triggers automatic disqualification. Review honeypot thresholds.
    </div>
    """, unsafe_allow_html=True)

st.divider()


# ── Main tabs ─────────────────────────────────────────────────────────────────
tab_shortlist, tab_detail, tab_compare, tab_insights, tab_eval = st.tabs([
    "📋 Ranked Shortlist",
    "🔍 Candidate Detail",
    "⚖️ Compare",
    "📊 Insights",
    "🧪 Evaluation",
])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — Ranked Shortlist
# ─────────────────────────────────────────────────────────────────────────────
with tab_shortlist:
    hcol, fcol = st.columns([3, 1])
    with hcol:
        st.markdown(
            "**Top ranked candidates** for · Senior AI Engineer — Redrob AI Founding Team",
            help="Ranked by hybrid score: 75% rule-based + 25% semantic similarity"
        )
    with fcol:
        show_n = st.selectbox("Show", [10, 25, 50, 100], label_visibility="collapsed")

    with st.expander("🔧 Filters", expanded=False):
        f1, f2, f3, f4, f5 = st.columns(5)
        with f1:
            min_score = st.slider("Min score", 0.0, 1.0, 0.0, 0.01)
        with f2:
            filter_title = st.text_input("Title contains", "", placeholder="e.g. NLP")
        with f3:
            filter_conf = st.selectbox("Confidence", ["All", "High", "Medium", "Low"])
        with f4:
            hide_penalized = st.checkbox("Hide penalized")
        with f5:
            hide_hp = st.checkbox("Hide honeypots", value=True)

    filtered = [
        r for r in top100
        if r["final_score"] >= min_score
        and (not filter_title or filter_title.lower() in r["profile_snapshot"]["current_title"].lower())
        and (filter_conf == "All" or r.get("confidence", "Medium") == filter_conf)
        and (not hide_penalized or r.get("scores", {}).get("penalty", 0) <= 0.05)
        and (not hide_hp or not r.get("is_honeypot", False))
    ][:show_n]

    if not filtered:
        st.markdown("""
        <div style="text-align:center;padding:2rem;color:#64748B">
          <div style="font-size:2rem;margin-bottom:.5rem">🔍</div>
          <b>No candidates match the current filters.</b><br>
          <span style="font-size:.85rem">Try relaxing the score threshold or removing title filters.</span>
        </div>
        """, unsafe_allow_html=True)

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
            tags += f'<span class="tag tag-loc">📍 {loc}</span>'

        score_class = _pill_class(score)
        color = _score_color(score)
        rule_score = result.get("rule_based_score", score)

        # Main card HTML
        st.markdown(f"""
        <div class="cand-card">
          <div style="display:flex;align-items:flex-start;gap:.85rem">
            <div class="rank-badge {_rank_class(rank)}">#{rank}</div>
            <div style="flex:1;min-width:0">
              <div style="display:flex;align-items:center;gap:.45rem;flex-wrap:wrap;margin-bottom:.2rem">
                <span style="font-weight:700;color:#0F172A;font-size:.97rem">{title}</span>
                {tags}
              </div>
              <div style="font-size:.76rem;color:#64748B;margin:.1rem 0">
                <b>{cid}</b> &nbsp;·&nbsp; {yoe}y exp &nbsp;·&nbsp; {co}
              </div>
              <div style="font-size:.82rem;color:#374151;margin-top:.4rem;line-height:1.55">{reasoning}</div>
            </div>
            <div style="flex-shrink:0;text-align:right;min-width:70px">
              <span class="{score_class}">{score:.4f}</span>
              {_bar(score, color)}
              <div style="font-size:.65rem;color:#94A3B8;margin-top:.2rem">rule {rule_score:.3f}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Expandable "Why this candidate?" panel
        with st.expander("💡 Why this candidate?", expanded=False):
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
                penalty_color = "#EF4444" if pen > 0.05 else "#10B981"
                st.markdown(f"""
                <div style="margin-top:.6rem;padding:.5rem .75rem;background:#F8FAFC;
                     border-radius:8px;font-size:.79rem;border:1px solid #E2E8F0">
                  Penalty: <b style="color:{penalty_color}">{pen:.0%}</b>
                  &nbsp;→&nbsp; Final score: <b>{score:.4f}</b>
                  {'<br><span style="color:#9A3412;font-size:.72rem">' + '; '.join(pen_reasons) + '</span>' if pen_reasons else ''}
                </div>
                """, unsafe_allow_html=True)

                sem = scores_d.get("tfidf_similarity", scores_d.get("semantic_similarity", 0))
                conf_cls = _conf_class(conf)
                st.markdown(f"""
                <div style="margin-top:.5rem;font-size:.79rem;color:#374151">
                  Semantic sim: <b>{sem:.3f}</b> &nbsp;·&nbsp;
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
                        skill_html += f'<span class="tag {cls}">{name}</span> '
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
                        co_s = sn.get("company", "")
                        t_s = sn.get("title", "")
                        txt = sn.get("snippet", "")
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
    <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;
         padding:.85rem 1.2rem;margin-bottom:1rem;display:flex;align-items:center;gap:1.2rem;flex-wrap:wrap">
      <div class="rank-badge {_rank_class(r['rank'])}" style="width:2.6rem;height:2.6rem;font-size:.85rem">
        #{r['rank']}
      </div>
      <div style="flex:1;min-width:200px">
        <div style="font-weight:700;font-size:1.05rem;color:#0F172A">{snap['current_title']}</div>
        <div style="font-size:.8rem;color:#64748B;margin-top:.1rem">
          {r['candidate_id']} &nbsp;·&nbsp; {snap.get('current_company','—')}
          &nbsp;·&nbsp; {snap['years_of_experience']}y exp &nbsp;·&nbsp; {snap['location']}
        </div>
        <div style="font-size:.78rem;color:#475569;margin-top:.2rem;font-style:italic">
          {r.get('headline', '')}
        </div>
      </div>
      <div style="text-align:right">
        <div style="font-size:1.7rem;font-weight:800;color:#1D4ED8">{r['final_score']:.4f}</div>
        <div style="font-size:.72rem;color:#64748B">final score</div>
        <div style="font-size:.78rem;margin-top:.2rem">
          Confidence: <span class="{conf_cls}">{conf}</span>
        </div>
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
        pen_color = "#EF4444" if pen > 0.05 else "#10B981"
        st.markdown(f"""
        <div style="margin-top:.8rem;padding:.6rem .85rem;background:#F8FAFC;
             border-radius:10px;font-size:.81rem;border:1px solid #E2E8F0">
          Penalty: <b style="color:{pen_color}">{pen:.0%}</b>
          &nbsp;·&nbsp; Rule score: <b>{rule_score:.4f}</b>
          &nbsp;·&nbsp; Semantic sim: <b>{sem_val:.4f}</b>
          <br><span style="color:#64748B;font-size:.73rem">
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
                  <span style="color:{color};font-weight:{'600' if is_match else '400'}">{match_icon}{name}</span>
                  <span style="color:#64748B;font-size:.72rem">{prof} · {end} end.</span>
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
              <div style="font-weight:600;color:#0F172A;font-size:.85rem">{edu.get('degree','')} in {edu.get('field','')}</div>
              <div style="color:#64748B;font-size:.78rem">{edu.get('institution','')}{tier_label}</div>
            </div>
            """, unsafe_allow_html=True)

    # Right: recruiter summary + career evidence
    with col_right:
        st.markdown("##### Recruiter Summary")
        reasoning = r.get("reasoning", "No reasoning available.")
        st.markdown(f"""
        <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
             padding:.8rem 1rem;font-size:.85rem;color:#1E3A5F;line-height:1.6">
          {reasoning}
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
          🏆 Recommendation: <b>#{winner_rank} {winner_id}</b> scores higher by {delta:.4f}
          &nbsp;·&nbsp; Score: {max(sa, sb):.4f} vs {min(sa, sb):.4f}
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
                 padding:1rem 1.2rem;background:{bg_color};margin-bottom:.75rem">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem">
                <span style="font-size:.72rem;font-weight:700;color:#64748B;text-transform:uppercase;
                      letter-spacing:.07em">{label}</span>
                {'<span class="tag tag-active">★ Higher Ranked</span>' if is_winner else ''}
              </div>
              <div style="font-weight:700;font-size:1rem;color:#0F172A">{snap['current_title']}</div>
              <div style="font-size:.78rem;color:#64748B;margin:.15rem 0">
                {r['candidate_id']} · {snap.get('current_company','—')} · {snap['years_of_experience']}y exp
              </div>
              <div style="font-size:.78rem;color:#475569;margin:.2rem 0">📍 {snap['location']}</div>
              <div style="font-size:1.5rem;font-weight:800;color:#1D4ED8;margin:.4rem 0">
                {r['final_score']:.4f}
                <span style="font-size:.75rem;font-weight:400;color:#64748B"> final score</span>
              </div>
              <div style="font-size:.78rem">
                Confidence: <span class="{conf_cls_c}">{conf_c}</span>
              </div>
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
                    skill_html += f'<span class="tag tag-skill">{s}</span> '
                for s in missing_c[:3]:
                    skill_html += f'<span class="tag tag-miss">− {s}</span> '
                skill_html += "</div>"
                st.markdown(skill_html, unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            _render_candidate_compare(ra, "Candidate A")
        with col_b:
            _render_candidate_compare(rb, "Candidate B")

        # Side-by-side reasoning
        st.markdown("---")
        st.markdown("##### Recruiter Summary Comparison")
        rz_a, rz_b = st.columns(2)
        with rz_a:
            st.markdown(f"""
            <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
                 padding:.8rem 1rem;font-size:.83rem;color:#1E3A5F;line-height:1.6">
              <b>{ra['profile_snapshot']['current_title']} (#{ra['rank']})</b><br><br>
              {ra.get('reasoning','—')}
            </div>
            """, unsafe_allow_html=True)
        with rz_b:
            st.markdown(f"""
            <div style="background:#EFF6FF;border:1px solid #BFDBFE;border-radius:10px;
                 padding:.8rem 1rem;font-size:.83rem;color:#1E3A5F;line-height:1.6">
              <b>{rb['profile_snapshot']['current_title']} (#{rb['rank']})</b><br><br>
              {rb.get('reasoning','—')}
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

        _PLOT_FONT  = dict(family="Inter, sans-serif", size=12)
        _PLOT_PAPER = "white"
        _PLOT_BG    = "#F8FAFC"
        _PLOT_MAR   = dict(l=20, r=20, t=40, b=20)
        _BLUE_SEQ   = "Blues"
        _PRIMARY    = "#3B82F6"

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
                title_font_size=14,
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
        st.markdown("---")
        st.markdown("##### Confidence Distribution")
        conf_counts = Counter(confs_all)
        cc1, cc2, cc3 = st.columns(3)
        for col, level, color in [(cc1, "High", "#10B981"), (cc2, "Medium", "#F59E0B"), (cc3, "Low", "#EF4444")]:
            count = conf_counts.get(level, 0)
            pct = count / len(top100) * 100
            col.markdown(f"""
            <div class="metric-card">
              <div class="metric-value" style="color:{color}">{count}</div>
              <div class="metric-label">{level} Confidence</div>
              <div class="metric-sub">{pct:.0f}% of top-100</div>
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
        st.markdown("#### Format & Sanity Checks")
        check_items = [
            ("Scores monotonically non-increasing", sc.get("scores_non_increasing", False)),
            ("Ranks 1–100 each appear exactly once", sc.get("ranks_unique_1_to_100", False)),
            ("Candidate IDs all unique", sc.get("candidate_ids_unique", False)),
            ("All scores in [0, 1]", sc.get("scores_in_range", False)),
            ("No honeypots in top-100", sc.get("no_honeypots_in_top100", False)),
            (f"Top-10 ML/AI: {sc.get('top10_ml_candidates','?')}/10", sc.get("top10_ml_fraction", 0) >= 0.7),
        ]
        cols = st.columns(3)
        for i, (label, ok) in enumerate(check_items):
            icon = "✅" if ok else "❌"
            cols[i % 3].markdown(f"{icon} {label}")

        st.divider()
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("#### Top-10 Component Averages")
            comp_avgs = t10.get("component_averages", {})
            for comp, val in comp_avgs.items():
                label = comp.replace("_", " ").title()
                color = _score_color(val)
                pct = int(val * 100)
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;font-size:.84rem;padding:.22rem 0">
                  <span>{label}</span>
                  <b style="color:{color}">{val:.3f}</b>
                </div>
                <div class="bar-bg"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div>
                """, unsafe_allow_html=True)

        with col_r:
            st.markdown("#### Baseline Comparison")
            if bl:
                st.metric("Overlap @10 vs keyword model", f"{bl.get('overlap@10','?')}/10",
                          help="Low overlap = our model picks different (and better) candidates than keyword count")
                st.metric("Overlap @25", f"{bl.get('overlap@25','?')}/25")
                st.metric("Overlap @50", f"{bl.get('overlap@50','?')}/50")
                if bl.get("summary"):
                    st.markdown(f'<div style="font-size:.83rem;color:#374151">{bl["summary"]}</div>',
                                unsafe_allow_html=True)
            else:
                st.info("Rerun eval.py with `--candidates` to see baseline comparison.")

        st.divider()
        st.markdown("#### Error Detection")
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
