"""
JD understanding module.

Parses the target job description and returns a structured JobProfile
used by the scoring engine. The profile is derived from deep analysis
of the actual JD text, not keyword extraction alone.
"""

from dataclasses import dataclass, field
from typing import Set, Dict, FrozenSet


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
