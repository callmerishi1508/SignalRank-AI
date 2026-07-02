"""
Resume parser — converts PDF / DOCX / TXT resume files into the same
structured dict schema used by candidates.jsonl, so the existing
ranking pipeline can score them without modification.

Schema produced matches backend/candidate_parser.py expectations.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Tech skill vocabulary (subset of jd_parser._SKILL_VOCAB) ─────────────────
_TECH_SKILLS = [
    "python", "java", "scala", "go", "golang", "rust", "c++", "javascript",
    "typescript", "sql", "r", "matlab", "swift", "kotlin", "ruby", "php",
    "machine learning", "deep learning", "neural network", "neural networks",
    "reinforcement learning", "transfer learning", "generative ai",
    "pytorch", "tensorflow", "keras", "jax", "scikit-learn", "xgboost",
    "lightgbm", "catboost", "huggingface", "transformers", "peft", "lora",
    "llm", "large language model", "gpt", "bert", "roberta", "t5",
    "fine-tuning", "finetuning", "rlhf", "dpo", "prompt engineering",
    "nlp", "natural language processing", "text classification",
    "named entity recognition", "ner", "sentiment analysis", "summarization",
    "information retrieval", "semantic search", "embedding", "embeddings",
    "dense retrieval", "bi-encoder", "cross-encoder", "reranking", "bm25",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus", "chroma",
    "elasticsearch", "opensearch", "vector search", "ann",
    "hybrid search", "sentence transformers", "rag",
    "retrieval augmented generation", "learning to rank",
    "computer vision", "image recognition", "object detection", "opencv",
    "speech recognition", "asr",
    "statistics", "probability", "linear algebra", "a/b testing",
    "pandas", "numpy", "scipy", "matplotlib", "spark", "kafka", "airflow",
    "dbt", "etl", "data pipeline", "data warehouse", "bigquery", "snowflake",
    "aws", "gcp", "azure", "google cloud", "kubernetes", "docker", "mlops",
    "mlflow", "wandb", "sagemaker", "ci/cd",
    "postgresql", "mysql", "mongodb", "redis", "fastapi", "flask", "django",
    "microservices", "distributed systems", "system design",
    "research", "publications", "phd",
]
# Longest-first so multi-word matches win
_TECH_SKILLS.sort(key=len, reverse=True)

_DEGREE_RE = re.compile(
    r"\b(B\.?Tech|B\.?E\.?|B\.?Sc|M\.?Tech|M\.?E\.?|M\.?Sc|MBA|BCA|MCA|"
    r"B\.?S\.?|M\.?S\.?|Ph\.?D\.?|Bachelor|Master|Doctorate)\b",
    re.I,
)
_YEAR_RE = re.compile(r"\b(19[7-9]\d|20[0-2]\d)\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-().]{7,15}\d)")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_GITHUB_RE = re.compile(r"github\.com/[\w.-]+", re.I)
_LINKEDIN_RE = re.compile(r"linkedin\.com/in/[\w.-]+", re.I)

_EXP_TOTAL_RE = re.compile(
    r"(\d+\.?\d*)\s*\+?\s*years?\s*(?:of\s+)?(?:experience|exp|work)?"
    r"|\bexperience[:\s]+(\d+\.?\d*)\s*years?",
    re.I,
)

_SECTION_HEADERS = re.compile(
    r"^(?:experience|work experience|employment|professional experience|"
    r"career|projects?|education|skills?|technical skills?|certifications?|"
    r"achievements?|publications?|summary|objective|profile|about)\s*$",
    re.I | re.MULTILINE,
)

_DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\w\s,]*"
    r"(?:19|20)\d{2}|\d{4})"
    r"\s*[-–to]+\s*"
    r"(?P<end>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\w\s,]*"
    r"(?:19|20)\d{2}|\d{4}|present|current|now|till date)",
    re.I,
)


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text_from_pdf(path: Path) -> str:
    import pdfplumber
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n".join(pages)


def extract_text_from_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix in (".docx", ".doc"):
        return extract_text_from_docx(path)
    # Plain text
    return path.read_text(encoding="utf-8", errors="replace")


# ── Resume parsing ────────────────────────────────────────────────────────────

def _extract_name(lines: List[str]) -> str:
    """Heuristic: name is usually in the first 1–3 non-empty lines, all-caps or title-case."""
    for line in lines[:5]:
        stripped = line.strip()
        if not stripped:
            continue
        if _EMAIL_RE.search(stripped) or _PHONE_RE.search(stripped):
            continue
        if re.match(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z.]+){0,3}$", stripped):
            return stripped
        if re.match(r"^[A-Z\s.]{4,40}$", stripped):
            return stripped.title()
    return lines[0].strip()[:60] if lines else "Unknown"


def _extract_email(text: str) -> str:
    m = _EMAIL_RE.search(text)
    return m.group(0) if m else ""


def _extract_skills(text: str) -> List[Dict]:
    found = []
    t_lower = text.lower()
    seen = set()
    for skill in _TECH_SKILLS:
        if re.search(r"\b" + re.escape(skill) + r"\b", t_lower) and skill not in seen:
            found.append({
                "name": skill,
                "proficiency_level": "intermediate",
                "years_of_experience": None,
                "endorsements": 0,
                "assessment_validated": False,
            })
            seen.add(skill)
    return found


def _extract_experience_years(text: str) -> float:
    for m in _EXP_TOTAL_RE.finditer(text):
        g = m.group(1) or m.group(2)
        if g:
            return float(g)
    # Estimate from year spans
    years = [int(y) for y in _YEAR_RE.findall(text)]
    if len(years) >= 2:
        span = max(years) - min(years)
        return float(max(0, min(span, 35)))
    return 3.0


_COMPANY_STOPWORDS = re.compile(
    r"\b(the|and|or|at|in|of|for|to|with|from|by|on|is|are|was|were|"
    r"has|have|had|be|been|being|will|would|could|should|may|might|"
    r"experience|responsibilities|achievements|description|summary|"
    r"skills|education|projects|certifications)\b",
    re.I,
)


def _extract_career_history(text: str) -> List[Dict]:
    """
    Heuristic extraction of job entries.
    Looks for date ranges and infers title/company from the same line or adjacent lines.
    """
    jobs = []
    lines = text.splitlines()

    for i, line in enumerate(lines):
        m = _DATE_RANGE_RE.search(line)
        if not m:
            continue

        start_str = m.group("start")
        end_str = m.group("end")

        sy = _YEAR_RE.search(start_str)
        ey = _YEAR_RE.search(end_str)
        if not sy:
            continue
        start_year = int(sy.group(0))
        is_current = end_str.lower().strip() in ("present", "current", "now", "till date")
        end_year = 2026 if is_current else (int(ey.group(0)) if ey else 2026)
        duration_months = max(1, (end_year - start_year) * 12)

        # Same line before the date: often "Title | Company | <date>"
        pre_date = line[:m.start()].strip()
        parts = re.split(r"[|,·@]", pre_date)
        parts = [p.strip() for p in parts if p.strip()]

        title = "Software Engineer"
        company = ""

        # Try to extract title and company from parts (pipe-separated is common)
        for part in parts:
            t = _TITLE_RE.search(part)
            if t and not title != "Software Engineer":
                title = t.group(0).strip()
            elif part and not company and len(part) > 1:
                # Non-title part likely company
                candidate_co = _COMPANY_STOPWORDS.sub("", part).strip()
                if candidate_co and candidate_co[0].isupper():
                    company = candidate_co

        # If we didn't find title/company, look at the previous non-empty line
        if title == "Software Engineer" or not company:
            for back in range(1, 4):
                prev = lines[i - back].strip() if i >= back else ""
                if not prev:
                    continue
                t = _TITLE_RE.search(prev)
                if t and title == "Software Engineer":
                    title = t.group(0).strip()
                    prev_parts = re.split(r"[|,·@]", prev)
                    prev_parts = [p.strip() for p in prev_parts if p.strip()]
                    for pp in prev_parts:
                        if pp and pp != title and not _TITLE_RE.search(pp) and len(pp) > 2:
                            c = _COMPANY_STOPWORDS.sub("", pp).strip()
                            if c and c[0].isupper():
                                company = c
                                break
                break

        if not company:
            company = "Unknown Company"

        # Collect description bullets
        desc_lines = []
        for j in range(i + 1, min(i + 12, len(lines))):
            ln = lines[j].strip()
            if not ln or _DATE_RANGE_RE.search(ln):
                break
            if ln.startswith(("-", "•", "◦", "*", "▪", "→", ">")):
                desc_lines.append(ln.lstrip("-•◦*▪→> "))

        jobs.append({
            "title": title,
            "company": company,
            "duration_months": duration_months,
            "start_year": start_year,
            "end_year": end_year,
            "is_current": is_current,
            "description": " ".join(desc_lines),
            "location": "",
        })

    # Deduplicate by start_year+company
    seen: set = set()
    unique = []
    for j in jobs:
        key = (j["start_year"], j.get("company", "").lower()[:10])
        if key not in seen:
            seen.add(key)
            unique.append(j)

    return sorted(unique, key=lambda x: x["start_year"], reverse=True)[:8]


_TITLE_PATTERNS = [
    r"((?:Senior|Junior|Lead|Staff|Principal|Head of|VP|Director|Manager|"
    r"Associate)?\s*(?:Software|ML|AI|Data|Research|NLP|Backend|Frontend|"
    r"Full.?Stack|DevOps|Platform|Applied|Product|Marketing|Sales)?\s*"
    r"(?:Engineer|Scientist|Developer|Analyst|Architect|Intern|Consultant|"
    r"Manager|Director|Lead|Researcher|Specialist))",
]

_TITLE_RE = re.compile("|".join(_TITLE_PATTERNS), re.I)


def _guess_job_title(context: str) -> str:
    m = _TITLE_RE.search(context)
    if m:
        return m.group(0).strip()
    return "Software Engineer"


def _guess_company(context: str) -> str:
    # Remove dates, bullets, known title words
    cleaned = _DATE_RANGE_RE.sub("", context)
    cleaned = _TITLE_RE.sub("", cleaned)
    cleaned = re.sub(r"[•\-–|·,]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # First capitalized phrase that's not a skill
    for chunk in cleaned.split():
        if chunk and chunk[0].isupper() and len(chunk) > 2:
            return chunk
    return "Unknown Company"


def _extract_education(text: str) -> List[Dict]:
    edus = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _DEGREE_RE.search(line)
        if not m:
            continue
        degree = m.group(0).strip()
        context = " ".join(lines[i:i + 3])
        # field of study
        fos_m = re.search(r"(?:in|of)\s+([A-Z][A-Za-z\s&]+?)(?:,|from|\d|$)", context)
        fos = fos_m.group(1).strip() if fos_m else "Engineering / Science"
        # institution
        inst_m = re.search(r"(?:from|at|,)\s+([A-Z][A-Za-z\s&.()]+?)(?:,|\d|$)", context)
        institution = inst_m.group(1).strip() if inst_m else ""
        # year
        yr_m = _YEAR_RE.search(context)
        yr = int(yr_m.group(0)) if yr_m else None
        edus.append({
            "degree": degree,
            "field_of_study": fos,
            "institution": institution,
            "graduation_year": yr,
        })
    return edus[:3]


def _current_title_from_career(career: List[Dict], default_title: str) -> str:
    if career:
        return career[0].get("title") or default_title
    return default_title


# ── Build candidate dict (matches candidates.jsonl schema) ───────────────────

def resume_text_to_candidate_dict(
    text: str,
    filename: str = "",
    candidate_id: Optional[str] = None,
) -> Dict:
    """
    Convert raw resume text into a candidate dict that matches the schema
    expected by backend/candidate_parser.py → load_candidates_list().
    """
    if not candidate_id:
        digest = hashlib.md5(text.encode()).hexdigest()[:8].upper()
        candidate_id = f"RESUME_{digest}"

    lines = [l for l in text.splitlines() if l.strip()]

    name = _extract_name(lines)
    email = _extract_email(text)
    skills = _extract_skills(text)
    career = _extract_career_history(text)
    yoe = _extract_experience_years(text)
    # Better YOE estimate: use career span (earliest start to now / latest end)
    if career:
        earliest = min(j["start_year"] for j in career)
        latest_end = max(
            (2026 if j["is_current"] else j["end_year"]) for j in career
        )
        career_span = max(0.0, float(latest_end - earliest))
        yoe = max(yoe, career_span)
    education = _extract_education(text)

    current_title = _current_title_from_career(career, "Software Engineer")

    # GitHub / LinkedIn
    gh = _GITHUB_RE.search(text)
    li = _LINKEDIN_RE.search(text)

    # Infer location from text (simple city lookup)
    location = ""
    for city in ["bangalore", "bengaluru", "hyderabad", "mumbai", "delhi",
                 "noida", "gurgaon", "pune", "chennai", "san francisco",
                 "new york", "seattle", "london", "remote"]:
        if city in text.lower():
            location = city.title()
            break

    # Build redrob_signals with sensible defaults
    # (resumes don't have behavioral data — we use neutral defaults)
    redrob_signals = {
        "days_since_last_active": 30,
        "application_response_rate": 0.5,
        "profile_completeness": min(1.0, len(skills) / 10),
        "notice_period_days": 30,
        "open_to_work": True,
        "actively_seeking": True,
        "recruiter_demand_score": 0.5,
        "github_activity_score": 0.6 if gh else 0.2,
        "publication_count": 1 if "publications" in text.lower() else 0,
        "response_speed_hours": 24,
        "interview_availability_score": 0.7,
        "salary_expectation_match": 0.5,
        "location_flexibility": 0.5,
        "skill_endorsement_count": sum(1 for s in skills if s.get("endorsements", 0) > 0),
        "assessment_score": 0.0,
    }

    # Build headline from title + skills
    top_skills = [s["name"] for s in skills[:4]]
    headline = f"{current_title} | {', '.join(top_skills)}" if top_skills else current_title

    return {
        "candidate_id": candidate_id,
        "source": "resume",
        "filename": filename,
        "profile": {
            "name": name,
            "email": email,
            "current_title": current_title,
            "headline": headline,
            "summary": text[:500].replace("\n", " ").strip(),
            "location": location,
            "country": "India" if any(
                c in location.lower() for c in
                ["bangalore", "bengaluru", "hyderabad", "mumbai", "delhi",
                 "noida", "gurgaon", "pune", "chennai"]
            ) else "",
            "years_of_experience": yoe,
            "github_url": gh.group(0) if gh else "",
            "linkedin_url": li.group(0) if li else "",
        },
        "career_history": career,
        "skills": skills,
        "education": education,
        "certifications": [],
        "redrob_signals": redrob_signals,
        "projects": [],
    }


def parse_resume_file(path: Path, candidate_id: Optional[str] = None) -> Dict:
    text = extract_text_from_file(path)
    return resume_text_to_candidate_dict(text, filename=path.name, candidate_id=candidate_id)


def parse_resume_files(paths: List[Path]) -> List[Dict]:
    results = []
    for i, path in enumerate(paths):
        try:
            cid = f"RESUME_{str(uuid.uuid4())[:8].upper()}"
            candidate = parse_resume_file(path, candidate_id=cid)
            results.append(candidate)
        except Exception as e:
            results.append({
                "candidate_id": f"RESUME_ERR_{i:04d}",
                "source": "resume",
                "filename": path.name,
                "error": str(e),
                "profile": {"name": path.stem, "current_title": "Unknown", "years_of_experience": 0},
                "career_history": [], "skills": [], "education": [],
                "certifications": [], "redrob_signals": {}, "projects": [],
            })
    return results
