"""
JD understanding module.

Parses the target job description and returns a structured JobProfile
used by the scoring engine. The profile is derived from deep analysis
of the actual JD text, not keyword extraction alone.
"""

import re
from dataclasses import dataclass, field
from typing import Set, Dict, FrozenSet, List, Optional, Tuple


@dataclass
class JobProfile:
    title: str
    seniority: str
    experience_min: float
    experience_max: float
    experience_ideal_min: float
    experience_ideal_max: float

    required_skills: FrozenSet[str]
    nice_to_have_skills: FrozenSet[str]
    disqualifying_skill_domains: FrozenSet[str]

    # Preferred title keywords (any token match = good signal)
    tier1_title_tokens: FrozenSet[str]
    tier2_title_tokens: FrozenSet[str]

    # Career background signals
    disqualifying_firms: FrozenSet[str]
    preferred_industries: FrozenSet[str]

    # Location
    tier1_locations: FrozenSet[str]
    tier2_locations: FrozenSet[str]

    # Production evidence keywords in career descriptions
    production_keywords: FrozenSet[str]

    # Behavioral constraints
    notice_period_preferred_max: int   # days — hard preference
    notice_period_acceptable_max: int  # days — still in scope
    preferred_work_modes: FrozenSet[str]

    # Scoring weights
    weights: Dict[str, float]


def load_jd_profile() -> JobProfile:
    """
    Returns the structured profile for the Senior AI Engineer JD.
    Derived from careful reading of data/raw/job_description.md.
    """

    required_skills = frozenset({
        # Embeddings / retrieval
        "embeddings", "embedding", "dense retrieval", "bi-encoder",
        "sentence transformers", "sentence-transformers",
        "openai embeddings", "bge", "e5", "cohere embed",
        "semantic search", "semantic retrieval",
        "vector search", "vector similarity", "ann", "approximate nearest neighbor",
        # Vector databases / infrastructure
        "faiss", "pinecone", "weaviate", "qdrant", "milvus", "chroma", "chromadb",
        "elasticsearch", "opensearch", "solr", "annoy", "nmslib", "scann",
        "hybrid search", "bm25", "sparse retrieval",
        # NLP / IR
        "nlp", "natural language processing", "information retrieval",
        "text ranking", "document ranking", "passage ranking",
        "ranking", "re-ranking", "reranking", "cross-encoder",
        "learning to rank", "ltr", "lambdamart", "listwise", "pairwise",
        "recommendation", "recommender", "collaborative filtering",
        # Evaluation
        "ndcg", "mrr", "mean reciprocal rank", "map", "mean average precision",
        "evaluation framework", "offline evaluation", "online evaluation",
        "a/b testing", "ab testing", "retrieval quality", "embedding drift",
        # Production / MLOps
        "production ml", "production deployment", "model serving",
        "mlops", "feature store", "online learning",
        # Core
        "python", "machine learning", "deep learning",
        "neural network", "transformer", "bert", "roberta", "t5",
        # RAG / LLM
        "rag", "retrieval augmented generation",
        "llm", "large language model",
        "fine-tuning", "fine tuning", "finetuning",
    })

    nice_to_have_skills = frozenset({
        "lora", "qlora", "peft", "parameter efficient fine-tuning",
        "xgboost", "gradient boosting", "lightgbm", "catboost",
        "distributed systems", "apache kafka", "apache spark", "flink",
        "kubernetes", "docker", "mlflow", "wandb", "dvc",
        "redis", "mongodb", "postgresql",
        "pytorch", "tensorflow", "jax",
        "huggingface", "hugging face",
        "open source", "open-source",
        "scala", "java",
    })

    # Skills that indicate CV / speech / robotics without NLP overlap
    disqualifying_skill_domains = frozenset({
        "computer vision", "image recognition", "image classification",
        "object detection", "yolo", "image segmentation", "opencv",
        "convolutional neural network", "cnn",
        "speech recognition", "asr", "automatic speech recognition",
        "text to speech", "tts", "speech synthesis", "audio processing",
        "robotics", "ros", "robot operating system",
        "autonomous driving", "autonomous vehicle", "lidar",
    })

    # Title tokens: any of these appearing in a job title = ML/AI tier 1
    tier1_title_tokens = frozenset({
        "ml engineer", "machine learning engineer",
        "ai engineer", "artificial intelligence engineer",
        "nlp engineer", "nlp scientist", "natural language",
        "search engineer", "ranking engineer",
        "recommendation engineer", "retrieval engineer",
        "applied scientist", "applied ml", "applied ai",
        "research engineer", "research scientist",
        "information retrieval",
        "senior data scientist", "staff data scientist", "principal data scientist",
        "senior ml", "staff ml", "principal ml", "lead ml",
        "senior ai", "staff ai", "principal ai",
        "mlops engineer",
    })

    tier2_title_tokens = frozenset({
        "data scientist",
        "junior ml", "junior ai", "junior data scientist",
        "ml platform", "ml infrastructure",
        "data engineer ml", "data engineer ai",
        "software engineer ml", "software engineer ai",
        "backend ml", "backend ai",
    })

    # Known large consulting firms (consulting-only career = penalty)
    disqualifying_firms = frozenset({
        "tcs", "tata consultancy", "tata consultancy services",
        "infosys", "wipro", "accenture", "cognizant",
        "cognizant technology solutions", "capgemini",
        "hcl", "hcl technologies", "tech mahindra",
        "hexaware", "mphasis", "l&t infotech", "ltimindtree",
        "mindtree", "niit technologies", "kpit",
    })

    preferred_industries = frozenset({
        "technology", "software", "internet", "e-commerce",
        "artificial intelligence", "machine learning", "data",
        "saas", "platform", "fintech", "edtech", "healthtech",
        "media", "gaming", "cloud", "semiconductor",
    })

    tier1_locations = frozenset({
        "pune", "noida", "gurgaon", "gurugram",
        "delhi", "new delhi", "delhi ncr", "ncr",
    })

    tier2_locations = frozenset({
        "hyderabad", "mumbai", "bangalore", "bengaluru", "chennai",
        "kolkata", "ahmedabad", "jaipur",
    })

    production_keywords = frozenset({
        "deployed", "production", "serving", "served",
        "scale", "million", "billion", "k users", "real users",
        "latency", "throughput", "qps", "tps", "p99", "p95",
        "a/b test", "ab test", "online experiment",
        "shipped", "launched", "released",
        "end-to-end", "end to end",
        "ranking system", "retrieval system", "search system",
        "recommendation system", "recommender system",
        "real-time", "real time", "online inference",
        "model in production", "production model",
        "index refresh", "embedding refresh",
    })

    weights = {
        "title_role": 0.25,
        "skill_match": 0.20,
        "production_evidence": 0.15,
        "behavioral": 0.15,
        "experience_fit": 0.10,
        "domain_fit": 0.10,
        "location": 0.05,
    }

    return JobProfile(
        title="Senior AI Engineer",
        seniority="senior",
        experience_min=3.0,
        experience_max=15.0,
        experience_ideal_min=5.0,
        experience_ideal_max=9.0,
        required_skills=required_skills,
        nice_to_have_skills=nice_to_have_skills,
        disqualifying_skill_domains=disqualifying_skill_domains,
        tier1_title_tokens=tier1_title_tokens,
        tier2_title_tokens=tier2_title_tokens,
        disqualifying_firms=disqualifying_firms,
        preferred_industries=preferred_industries,
        tier1_locations=tier1_locations,
        tier2_locations=tier2_locations,
        production_keywords=production_keywords,
        notice_period_preferred_max=30,
        notice_period_acceptable_max=90,
        preferred_work_modes=frozenset({"hybrid", "flexible", "remote"}),
        weights=weights,
    )


# Singleton — parse once, reuse across all candidates
JD_PROFILE: JobProfile = load_jd_profile()

# Concatenated JD text for TF-IDF similarity (pre-built)
JD_TEXT_FOR_TFIDF = """
senior ai engineer machine learning embeddings sentence transformers vector search
faiss pinecone weaviate qdrant milvus elasticsearch opensearch python
ndcg mrr map evaluation framework ab testing production deployment
retrieval ranking recommendation system nlp natural language processing
information retrieval rag retrieval augmented generation llm large language model
fine-tuning learning to rank hybrid search bm25 dense retrieval
applied ml applied ai research engineer production ml mlops
pytorch tensorflow huggingface bert transformer neural network deep learning
series a startup founding team product company 5 to 9 years experience
"""

# Richer natural-language JD text for sentence-transformer embedding.
# Structured as prose so the model encodes semantic context rather than
# just a keyword bag. Used by SemanticRetriever._jd_embedding_text().
JD_TEXT_FOR_EMBEDDING = """
We are looking for a Senior AI Engineer to join the founding team of a Series A
product-focused startup. The role requires deep expertise in semantic search,
dense retrieval, and ranking systems built for production at scale.

The ideal candidate has hands-on experience building and deploying embedding-based
retrieval pipelines using sentence-transformers, FAISS, Pinecone, Weaviate, or
similar vector databases. They understand bi-encoders and cross-encoders, can
implement BM25 hybrid search, and know how to evaluate retrieval quality using
NDCG, MRR, MAP, and A/B testing.

Strong Python skills are essential. Experience with NLP, natural language
processing, information retrieval, RAG (retrieval-augmented generation), and
LLM fine-tuning is highly valued. The candidate should have shipped ranking or
recommendation systems to real users — not just research prototypes. Production
ML experience with deployed models at meaningful scale (millions of users or
high QPS) is a strong positive signal.

We expect 5–9 years of total experience in ML/AI engineering roles at product
companies. Candidates from consulting-only backgrounds or with purely academic
research careers will not be considered. The role is based in Pune, Noida,
Bangalore, or Hyderabad, with a hybrid work arrangement.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Dynamic JD Parser — parses any job description text without an LLM
# ─────────────────────────────────────────────────────────────────────────────

# Comprehensive tech skill vocabulary, organised by domain.
# Any term found in a JD's requirements section is treated as required.
_SKILL_VOCAB: List[str] = sorted([
    # Languages
    "python", "java", "scala", "go", "golang", "rust", "c++", "c#", "r",
    "javascript", "typescript", "sql", "bash", "shell", "matlab", "julia",
    "swift", "kotlin", "ruby", "php", "perl",
    # ML / AI core
    "machine learning", "deep learning", "neural network", "neural networks",
    "reinforcement learning", "supervised learning", "unsupervised learning",
    "transfer learning", "self-supervised", "contrastive learning",
    "generative ai", "generative model", "diffusion model",
    "pytorch", "tensorflow", "keras", "jax", "scikit-learn", "sklearn",
    "xgboost", "lightgbm", "catboost", "gradient boosting",
    "random forest", "decision tree", "svm", "support vector",
    "huggingface", "hugging face", "transformers", "diffusers", "peft", "lora",
    "llm", "large language model", "gpt", "claude", "gemini", "llama",
    "bert", "roberta", "t5", "gpt-4", "gpt4", "chatgpt", "openai",
    "fine-tuning", "fine tuning", "finetuning", "rlhf", "dpo",
    "prompt engineering", "prompt tuning", "instruction tuning",
    # NLP / IR / Search
    "nlp", "natural language processing", "text classification",
    "named entity recognition", "ner", "sentiment analysis",
    "question answering", "summarization", "translation", "tokenization",
    "information retrieval", "semantic search", "lexical search",
    "embedding", "embeddings", "dense retrieval", "sparse retrieval",
    "bi-encoder", "cross-encoder", "reranking", "re-ranking",
    "bm25", "tfidf", "tf-idf", "inverted index",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus", "chroma", "chromadb",
    "elasticsearch", "opensearch", "solr", "algolia", "typesense",
    "vector search", "vector database", "ann", "approximate nearest neighbor",
    "hybrid search", "semantic similarity", "sentence transformers",
    "learning to rank", "ltr", "ranking", "ndcg", "mrr", "map",
    "rag", "retrieval augmented generation", "knowledge base",
    "recommendation", "recommender", "collaborative filtering",
    # Computer Vision
    "computer vision", "image recognition", "image classification",
    "object detection", "image segmentation", "yolo", "opencv",
    "cnn", "convolutional", "resnet", "vit", "vision transformer",
    # Speech / Audio
    "speech recognition", "asr", "tts", "text to speech", "audio processing",
    "whisper", "wav2vec",
    # Data Science / Analytics
    "statistics", "probability", "linear algebra", "calculus",
    "data analysis", "exploratory data analysis", "feature engineering",
    "hypothesis testing", "a/b testing", "causal inference", "experiment design",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn", "plotly",
    "tableau", "power bi", "looker", "metabase",
    # Data Engineering
    "spark", "apache spark", "hadoop", "kafka", "apache kafka",
    "airflow", "apache airflow", "dbt", "flink", "apache flink",
    "etl", "data pipeline", "data warehouse", "data lake",
    "redshift", "bigquery", "snowflake", "databricks", "delta lake",
    "s3", "gcs", "blob storage",
    # Cloud / MLOps
    "aws", "gcp", "azure", "google cloud", "amazon web services",
    "kubernetes", "docker", "terraform", "helm",
    "mlops", "mlflow", "kubeflow", "wandb", "dvc", "sagemaker", "vertex ai",
    "ci/cd", "devops", "github actions", "jenkins",
    "monitoring", "observability", "prometheus", "grafana",
    # Databases / Backend
    "postgresql", "mysql", "mongodb", "redis", "cassandra", "dynamodb",
    "rest api", "graphql", "fastapi", "flask", "django", "fastapi",
    "microservices", "distributed systems", "system design",
    # Research
    "research", "publications", "phd", "arxiv", "experimentation",
    "ablation", "benchmark", "evaluation", "metrics",
    # Product / Management
    "product management", "roadmap", "stakeholder", "cross-functional",
    "agile", "scrum", "jira",
], key=len, reverse=True)  # longest-first so multi-word terms match before substrings

# Seniority signals
_SENIORITY_MAP = {
    "staff":       ("staff",     10, 18, 8, 14),
    "principal":   ("principal", 10, 20, 9, 15),
    "distinguished":("senior",   12, 25, 10, 18),
    "fellow":      ("fellow",    15, 30, 12, 20),
    "lead":        ("lead",      7,  15, 6,  10),
    "senior":      ("senior",    5,  12, 5,   9),
    "mid":         ("mid",       2,  6,  3,   5),
    "junior":      ("junior",    0,  3,  1,   2),
    "intern":      ("intern",    0,  1,  0,   1),
    "manager":     ("manager",   5,  15, 6,  12),
    "director":    ("director",  8,  20, 8,  15),
    "vp":          ("vp",        10, 25, 10, 18),
    "head of":     ("head",      8,  20, 8,  15),
}

_LOCATION_TIER1 = {
    # US
    "san francisco", "new york", "seattle", "boston", "austin", "chicago",
    "los angeles", "la", "nyc", "sf", "mountain view", "menlo park", "palo alto",
    "sunnyvale", "santa clara", "san jose", "cambridge ma", "cambridge",
    # India
    "bangalore", "bengaluru", "hyderabad", "mumbai", "delhi", "noida",
    "gurgaon", "gurugram", "pune", "chennai",
    # UK
    "london",
    # Europe
    "berlin", "amsterdam", "paris", "zurich", "stockholm",
    # Canada
    "toronto", "vancouver", "montreal",
    # Singapore / SEA
    "singapore",
}
_LOCATION_TIER2 = {
    "remote", "hybrid", "anywhere", "worldwide", "global",
    "kolkata", "ahmedabad", "jaipur", "kochi", "coimbatore",
    "new delhi", "delhi ncr", "ncr",
}

_SECTION_HEADERS_REQUIRED = re.compile(
    r"(?:requirements?|required qualifications?|must.have|you will need|"
    r"what you.ll bring|minimum qualifications?|basic qualifications?|"
    r"what we.re looking for|responsibilities)",
    re.I,
)
_SECTION_HEADERS_NICE = re.compile(
    r"(?:preferred|nice.to.have|bonus|plus|good.to.have|"
    r"additional qualifications?|preferred qualifications?)",
    re.I,
)


def _extract_title(text: str) -> str:
    """Extract job title from JD text."""
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    # Common patterns: "Job Title: X", "Role: X", or just the first non-empty line
    for line in lines[:6]:
        m = re.match(r"(?:job title|title|role|position)[:\s]+(.+)", line, re.I)
        if m:
            return m.group(1).strip()
    # First short line (likely the title)
    for line in lines[:3]:
        if 3 <= len(line.split()) <= 10 and not line.endswith(":"):
            return line
    return lines[0][:80] if lines else "Job Role"


def _extract_seniority(title: str, text_lower: str) -> Tuple[str, float, float, float, float]:
    """Return (seniority_label, exp_min, exp_max, ideal_min, ideal_max)."""
    combined = (title + " " + text_lower[:500]).lower()
    for key, vals in _SENIORITY_MAP.items():
        if key in combined:
            return vals
    # Default: mid-level
    return ("mid", 2, 10, 3, 7)


def _extract_experience(text_lower: str) -> Tuple[float, float, float, float]:
    """Parse experience range from text."""
    patterns = [
        r"(\d+)\s*[-–to]+\s*(\d+)\s*(?:\+)?\s*years?",
        r"(\d+)\+?\s*years?\s*(?:of\s+)?(?:experience|exp)",
        r"minimum\s+(?:of\s+)?(\d+)\s*years?",
        r"at\s+least\s+(\d+)\s*years?",
    ]
    found: List[Tuple[float, float]] = []
    for pat in patterns:
        for m in re.finditer(pat, text_lower):
            g = m.groups()
            lo = float(g[0])
            hi = float(g[1]) if len(g) > 1 and g[1] else lo + 4
            found.append((lo, hi))
    if found:
        lo = min(f[0] for f in found)
        hi = max(f[1] for f in found)
        return lo, max(hi, lo + 4), lo, hi
    return 2.0, 15.0, 3.0, 8.0


def _split_into_sections(text: str) -> Tuple[str, str, str]:
    """Return (required_section, preferred_section, full_text) from JD."""
    lines = text.splitlines()
    req_lines, nice_lines, other_lines = [], [], []
    mode = "other"
    for line in lines:
        if _SECTION_HEADERS_REQUIRED.search(line):
            mode = "req"
        elif _SECTION_HEADERS_NICE.search(line):
            mode = "nice"
        elif re.match(r"^[A-Z][^a-z]{3,}$|^#{1,3}\s", line.strip()):
            mode = "other"
        if mode == "req":
            req_lines.append(line)
        elif mode == "nice":
            nice_lines.append(line)
        else:
            other_lines.append(line)
    req = "\n".join(req_lines) or text
    nice = "\n".join(nice_lines)
    return req, nice, text


def _extract_skills_from_text(text: str) -> FrozenSet[str]:
    """Find known skill terms in text (longest-match, case-insensitive)."""
    t = text.lower()
    found = set()
    for skill in _SKILL_VOCAB:
        if re.search(r"\b" + re.escape(skill) + r"\b", t):
            found.add(skill)
    return frozenset(found)


def _infer_title_tokens(title: str, required_skills: FrozenSet[str]) -> Tuple[FrozenSet[str], FrozenSet[str]]:
    """Generate tier1/tier2 title tokens that match this role."""
    title_l = title.lower()
    words = {w.strip(".,()-") for w in title_l.split() if len(w) > 2}
    stop = {"the", "and", "for", "with", "of", "in", "a", "an", "at"}
    tier1 = words - stop

    # Domain-specific expansions
    ml_skills = {"machine learning", "deep learning", "nlp", "pytorch", "tensorflow",
                 "llm", "bert", "embedding", "rag", "neural network"}
    ds_skills = {"statistics", "data analysis", "pandas", "r", "tableau", "power bi"}
    cv_skills = {"computer vision", "image recognition", "object detection", "opencv"}
    de_skills = {"spark", "airflow", "kafka", "dbt", "etl", "data pipeline"}
    se_skills = {"microservices", "kubernetes", "docker", "distributed systems"}

    if required_skills & ml_skills:
        tier1.update({"machine learning", "ml", "ai", "deep learning", "applied ml",
                      "applied ai", "research engineer", "applied scientist"})
        tier1.update({w for w in title_l.split() if len(w) > 2} - stop)
    if required_skills & ds_skills:
        tier1.update({"data scientist", "data science", "statistician", "analyst"})
    if required_skills & cv_skills:
        tier1.update({"computer vision", "cv engineer", "vision engineer"})
    if required_skills & de_skills:
        tier1.update({"data engineer", "platform engineer", "analytics engineer"})
    if required_skills & se_skills:
        tier1.update({"software engineer", "backend engineer", "platform engineer",
                      "site reliability", "sre"})

    # Generic tier2: any engineer/scientist title
    tier2 = {"software engineer", "engineer", "scientist", "developer",
              "analyst", "specialist"}

    return frozenset(tier1), frozenset(tier2 - tier1)


def _extract_locations(text_lower: str) -> Tuple[FrozenSet[str], FrozenSet[str]]:
    def _loc_match(loc: str) -> bool:
        return bool(re.search(r"\b" + re.escape(loc) + r"\b", text_lower))
    tier1 = {loc for loc in _LOCATION_TIER1 if _loc_match(loc)}
    tier2 = {loc for loc in _LOCATION_TIER2 if _loc_match(loc)}
    if not tier1 and not tier2:
        tier2 = frozenset({"remote"})
    return frozenset(tier1), frozenset(tier2)


def _infer_disqualifying_domains(
    title: str, required_skills: FrozenSet[str]
) -> FrozenSet[str]:
    """
    Infer skill domains that would be red flags for this role.
    Only flag domains that are clearly orthogonal to the JD.
    """
    title_l = title.lower()
    disq: set = set()

    # If role is NOT a CV role, flag pure CV-only skills
    cv_signals = {"computer vision", "image recognition", "object detection", "opencv", "cnn"}
    if not (required_skills & cv_signals) and "vision" not in title_l:
        disq.update({"robotics", "ros", "autonomous driving", "lidar", "autonomous vehicle"})

    # If role is NOT a speech/audio role
    audio_signals = {"speech recognition", "asr", "tts", "audio processing"}
    if not (required_skills & audio_signals) and "speech" not in title_l and "audio" not in title_l:
        disq.update({"speech recognition", "asr", "text to speech", "tts",
                     "audio processing", "automatic speech recognition"})

    return frozenset(disq)


def parse_jd_text(text: str) -> "ParsedJD":
    """
    Parse any job description text into a JobProfile + embedding texts.

    No LLM required. Uses vocabulary matching, regex, and heuristics.
    Returns a ParsedJD with .profile, .embedding_text, .tfidf_text, and .extracted (debug dict).
    """
    req_section, nice_section, full = _split_into_sections(text)

    title = _extract_title(text)
    seniority_label, exp_min, exp_max, ideal_min, ideal_max = _extract_seniority(title, text.lower())
    exp_min_r, exp_max_r, ideal_min_r, ideal_max_r = _extract_experience(text.lower())
    # Prefer regex extraction if found
    if ideal_min_r > 0:
        exp_min, exp_max, ideal_min, ideal_max = exp_min_r, exp_max_r, ideal_min_r, ideal_max_r

    required_skills = _extract_skills_from_text(req_section or text)
    nice_skills = _extract_skills_from_text(nice_section)
    nice_skills -= required_skills

    tier1_locs, tier2_locs = _extract_locations(text.lower())
    tier1_tokens, tier2_tokens = _infer_title_tokens(title, required_skills)
    disq_domains = _infer_disqualifying_domains(title, required_skills)

    production_keywords = frozenset({
        "deployed", "production", "serving", "shipped", "launched",
        "scale", "million", "billion", "real users", "latency", "throughput",
        "qps", "tps", "p99", "p95", "a/b test", "ab test", "online experiment",
        "end-to-end", "real-time", "model in production",
    })

    weights = {
        "title_role": 0.25, "skill_match": 0.20, "production_evidence": 0.15,
        "behavioral": 0.15, "experience_fit": 0.10, "domain_fit": 0.10, "location": 0.05,
    }

    profile = JobProfile(
        title=title,
        seniority=seniority_label,
        experience_min=max(0.0, exp_min - 1),
        experience_max=exp_max + 3,
        experience_ideal_min=ideal_min,
        experience_ideal_max=ideal_max,
        required_skills=required_skills,
        nice_to_have_skills=nice_skills,
        disqualifying_skill_domains=disq_domains,
        tier1_title_tokens=tier1_tokens,
        tier2_title_tokens=tier2_tokens,
        disqualifying_firms=frozenset(),
        preferred_industries=frozenset({
            "technology", "software", "internet", "saas", "platform",
            "fintech", "edtech", "healthtech", "ai", "data",
        }),
        tier1_locations=tier1_locs,
        tier2_locations=tier2_locs,
        production_keywords=production_keywords,
        notice_period_preferred_max=30,
        notice_period_acceptable_max=90,
        preferred_work_modes=frozenset({"hybrid", "flexible", "remote"}),
        weights=weights,
    )

    # Use the actual JD text for embedding (richer than a keyword bag)
    embedding_text = text[:3000].strip()
    tfidf_text = " ".join(required_skills | nice_skills) + " " + title

    return ParsedJD(
        profile=profile,
        embedding_text=embedding_text,
        tfidf_text=tfidf_text,
        extracted={
            "title": title,
            "seniority": seniority_label,
            "experience": f"{ideal_min:.0f}–{ideal_max:.0f} years (ideal)",
            "required_skills": sorted(required_skills)[:20],
            "nice_to_have": sorted(nice_skills)[:10],
            "locations": sorted(tier1_locs | tier2_locs),
        },
    )


class ParsedJD:
    def __init__(self, profile: JobProfile, embedding_text: str,
                 tfidf_text: str, extracted: dict):
        self.profile = profile
        self.embedding_text = embedding_text
        self.tfidf_text = tfidf_text
        self.extracted = extracted


# ─────────────────────────────────────────────────────────────────────────────
# Active JD registry — lets the Streamlit UI swap in a custom JD at runtime
# without modifying the singleton below.
# ─────────────────────────────────────────────────────────────────────────────
_active_parsed_jd: Optional["ParsedJD"] = None


def set_active_jd(parsed: Optional["ParsedJD"]) -> None:
    global _active_parsed_jd
    _active_parsed_jd = parsed


def get_active_jd_profile() -> JobProfile:
    return _active_parsed_jd.profile if _active_parsed_jd else JD_PROFILE


def get_active_jd_embedding_text() -> str:
    return _active_parsed_jd.embedding_text if _active_parsed_jd else JD_TEXT_FOR_EMBEDDING


def get_active_jd_tfidf_text() -> str:
    return _active_parsed_jd.tfidf_text if _active_parsed_jd else JD_TEXT_FOR_TFIDF
