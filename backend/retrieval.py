"""
Semantic retrieval layer.

Two-stage candidate pool construction:
  1. FAISS (sentence-transformers embeddings) + TF-IDF → RRF merge → candidate pool
  2. Rule-based reranking (scorer.py) on the pool

Features:
  - Embedding cache: embeddings.npy + candidate_ids.npy + index.faiss + metadata.json
  - Cache invalidation by file mtime
  - Graceful fallback to TF-IDF-only when faiss-cpu / sentence-transformers absent
  - Title safety net: any tier-1-title candidate is always included in pool
  - RRF fusion when both backends available
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from backend.candidate_parser import CandidateProfile
from backend.config_loader import ScoringConfig, load_config
from backend.jd_parser import JD_PROFILE, JobProfile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional heavy imports — detected at module load
# ---------------------------------------------------------------------------

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False
    logger.warning("sentence-transformers not found — embedding backend disabled")

try:
    import faiss  # type: ignore
    _FAISS_AVAILABLE = True
except ImportError:
    _FAISS_AVAILABLE = False
    logger.warning("faiss-cpu not found — embedding backend disabled")

_EMBEDDING_BACKEND_OK = _ST_AVAILABLE and _FAISS_AVAILABLE

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    _TFIDF_AVAILABLE = True
except ImportError:
    _TFIDF_AVAILABLE = False
    logger.warning("scikit-learn not found — TF-IDF backend disabled")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class RetrievalResult:
    """Outcome of one retrieval call, passed to the scoring layer."""

    # Candidate pool (ordered by retrieval rank, not final rank)
    profiles: List[CandidateProfile]

    # Semantic similarity scores: candidate_id → float in [0, 1]
    # For FAISS backend: cosine similarity to JD embedding
    # For TF-IDF backend: TF-IDF cosine similarity
    # For candidates not retrieved: 0.0
    similarities: Dict[str, float]

    # Backend actually used
    backend_used: str   # "embedding+rrf", "embedding", "tfidf", "combined"

    # Timing metadata
    retrieval_time_sec: float = 0.0

    # Number of candidates scored (before pool selection)
    n_total: int = 0


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

class _EmbeddingCache:
    """
    Manages the on-disk embedding cache.

    Files stored in cache_dir/:
      embeddings.npy      — (N, D) float32 matrix
      candidate_ids.npy   — (N,) array of candidate_id strings
      index.faiss         — FAISS IndexFlatIP (optional, if persist_index=True)
      metadata.json       — {source_path, source_mtime, n_candidates, model}
    """

    def __init__(self, cache_dir: Path, model_name: str, persist_index: bool) -> None:
        self.cache_dir = cache_dir
        self.model_name = model_name
        self.persist_index = persist_index

        self._emb_path = cache_dir / "embeddings.npy"
        self._ids_path = cache_dir / "candidate_ids.npy"
        self._idx_path = cache_dir / "index.faiss"
        self._meta_path = cache_dir / "metadata.json"

    def is_valid(self, source_path: Path) -> bool:
        """Return True if cache files exist and source hasn't changed."""
        required = [self._emb_path, self._ids_path, self._meta_path]
        if not all(p.exists() for p in required):
            return False
        try:
            meta = json.loads(self._meta_path.read_text())
        except (json.JSONDecodeError, OSError):
            return False
        current_mtime = source_path.stat().st_mtime
        return (
            meta.get("source_mtime") == current_mtime
            and meta.get("model") == self.model_name
        )

    def load(self) -> Tuple[np.ndarray, List[str]]:
        embeddings = np.load(str(self._emb_path))
        ids_raw = np.load(str(self._ids_path), allow_pickle=True)
        candidate_ids = [str(x) for x in ids_raw]
        return embeddings, candidate_ids

    def load_index(self) -> Optional["faiss.Index"]:
        if not _FAISS_AVAILABLE:
            return None
        if self._idx_path.exists():
            try:
                return faiss.read_index(str(self._idx_path))
            except Exception as exc:
                logger.warning(f"Failed to load cached FAISS index: {exc}")
        return None

    def save(
        self,
        embeddings: np.ndarray,
        candidate_ids: List[str],
        source_path: Path,
        index: Optional["faiss.Index"] = None,
    ) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        np.save(str(self._emb_path), embeddings.astype(np.float32))
        np.save(str(self._ids_path), np.array(candidate_ids, dtype=object))

        if index is not None and self.persist_index and _FAISS_AVAILABLE:
            faiss.write_index(index, str(self._idx_path))

        meta = {
            "source_path": str(source_path),
            "source_mtime": source_path.stat().st_mtime,
            "n_candidates": len(candidate_ids),
            "model": self.model_name,
        }
        self._meta_path.write_text(json.dumps(meta, indent=2))
        logger.info(f"[cache] saved {len(candidate_ids)} embeddings → {self.cache_dir}")


# ---------------------------------------------------------------------------
# FAISS index construction
# ---------------------------------------------------------------------------

def _build_faiss_index(embeddings: np.ndarray, index_type: str, nlist: int) -> "faiss.Index":
    d = embeddings.shape[1]
    if index_type == "ivf" and embeddings.shape[0] >= nlist * 2:
        quantizer = faiss.IndexFlatIP(d)
        index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
        index.train(embeddings)
    else:
        index = faiss.IndexFlatIP(d)
    index.add(embeddings)
    return index


# ---------------------------------------------------------------------------
# RRF fusion
# ---------------------------------------------------------------------------

def _rrf_merge(
    ranked_lists: List[List[str]],
    k: int,
    top_n: int,
) -> List[str]:
    """
    Reciprocal Rank Fusion.

    Args:
        ranked_lists: Each element is a list of candidate_ids in rank order (best first).
        k: RRF smoothing constant.
        top_n: Number of candidates to return.

    Returns:
        List of candidate_ids sorted by descending RRF score.
    """
    scores: Dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, cid in enumerate(ranked, 1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
    return sorted_ids[:top_n]


# ---------------------------------------------------------------------------
# Title safety net
# ---------------------------------------------------------------------------

def _title_safety_ids(profiles: List[CandidateProfile], jd: JobProfile) -> Set[str]:
    """Return candidate_ids whose current_title matches a tier-1 JD title token."""
    safe = set()
    for cp in profiles:
        title_lower = cp.current_title.lower()
        if any(tok in title_lower for tok in jd.tier1_title_tokens):
            safe.add(cp.candidate_id)
    return safe


# ---------------------------------------------------------------------------
# SemanticRetriever
# ---------------------------------------------------------------------------

class SemanticRetriever:
    """
    Builds a candidate pool using semantic retrieval + optional RRF fusion.

    Usage:
        retriever = SemanticRetriever(config)
        retriever.fit(profiles, source_path)     # encode + index
        result = retriever.retrieve(profiles)    # return pool
    """

    def __init__(
        self,
        config: Optional[ScoringConfig] = None,
        jd: Optional[JobProfile] = None,
    ) -> None:
        self.config = config or load_config()
        self.jd = jd or JD_PROFILE

        sem = self.config.semantic
        emb = sem.embedding

        self.backend = sem.backend
        self.model_name: str = emb.model_name
        self.batch_size: int = emb.batch_size
        self.normalize: bool = emb.normalize_embeddings

        faiss_cfg = emb.faiss
        self.index_type: str = faiss_cfg.index_type
        self.nlist: int = faiss_cfg.nlist
        self.nprobe: int = faiss_cfg.nprobe
        self.top_k: int = faiss_cfg.top_k
        self.title_safety_net: bool = faiss_cfg.title_safety_net
        self.persist_index: bool = faiss_cfg.persist_index

        cache_cfg = emb.cache
        self.cache_enabled: bool = cache_cfg.enabled
        self.cache_path = Path(cache_cfg.path)

        rrf_cfg = sem.rrf
        self.rrf_enabled: bool = rrf_cfg.enabled
        self.rrf_k: int = rrf_cfg.k
        self.top_embedding_k: int = rrf_cfg.top_embedding_k
        self.top_tfidf_k: int = rrf_cfg.top_tfidf_k

        tfidf_cfg = sem.tfidf
        self.tfidf_ngram: tuple = tuple(tfidf_cfg.ngram_range)
        self.tfidf_max_features: int = tfidf_cfg.max_features
        self.tfidf_min_df: int = tfidf_cfg.min_df
        self.tfidf_sublinear: bool = tfidf_cfg.sublinear_tf

        # Runtime state
        self._model: Optional["SentenceTransformer"] = None
        self._faiss_index: Optional["faiss.Index"] = None
        self._emb_matrix: Optional[np.ndarray] = None
        self._emb_ids: List[str] = []
        self._tfidf_vectorizer: Optional["TfidfVectorizer"] = None
        self._tfidf_matrix = None    # sparse
        self._tfidf_ids: List[str] = []
        self._fitted: bool = False

    # -----------------------------------------------------------------------
    # JD text helpers
    # -----------------------------------------------------------------------

    def _jd_embedding_text(self) -> str:
        from backend.jd_parser import JD_TEXT_FOR_EMBEDDING
        return JD_TEXT_FOR_EMBEDDING

    # -----------------------------------------------------------------------
    # Fit (encode + index all candidates)
    # -----------------------------------------------------------------------

    def fit(
        self,
        profiles: List[CandidateProfile],
        source_path: Optional[Path] = None,
    ) -> None:
        """
        Encode all candidate profiles and build retrieval indices.

        Args:
            profiles: All parsed candidates.
            source_path: Path to candidates.jsonl (used for cache invalidation).
        """
        t0 = time.time()
        use_backend = self._resolve_backend()
        logger.info(f"[retrieval] fitting {len(profiles)} candidates, backend={use_backend}")

        texts = [cp.profile_text for cp in profiles]
        ids = [cp.candidate_id for cp in profiles]

        if use_backend in ("embedding", "embedding+rrf"):
            self._fit_embedding(profiles, texts, ids, source_path)

        if use_backend in ("tfidf", "embedding+rrf"):
            self._fit_tfidf(texts, ids)

        self._fitted = True
        logger.info(f"[retrieval] fit complete in {time.time() - t0:.1f}s")

    def _resolve_backend(self) -> str:
        forced = self.backend
        if forced == "embedding" and not _EMBEDDING_BACKEND_OK:
            logger.warning("[retrieval] embedding backend unavailable — falling back to tfidf")
            return "tfidf"
        if forced == "embedding":
            if self.rrf_enabled and _TFIDF_AVAILABLE:
                return "embedding+rrf"
            return "embedding"
        return forced if _TFIDF_AVAILABLE else "embedding"

    def _fit_embedding(
        self,
        profiles: List[CandidateProfile],
        texts: List[str],
        ids: List[str],
        source_path: Optional[Path],
    ) -> None:
        cache = _EmbeddingCache(self.cache_path, self.model_name, self.persist_index)

        if self.cache_enabled and source_path and cache.is_valid(source_path):
            logger.info("[retrieval] loading embeddings from cache")
            embeddings, cached_ids = cache.load()
            self._faiss_index = cache.load_index()
            self._emb_matrix = embeddings
            self._emb_ids = cached_ids
            if self._faiss_index is None:
                logger.info("[retrieval] rebuilding FAISS index (not cached)")
                self._faiss_index = _build_faiss_index(embeddings, self.index_type, self.nlist)
            return

        logger.info(f"[retrieval] encoding {len(texts)} candidates with {self.model_name}")
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)

        embeddings = self._model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=self.normalize,
            show_progress_bar=True,
        ).astype(np.float32)

        logger.info("[retrieval] building FAISS index")
        index = _build_faiss_index(embeddings, self.index_type, self.nlist)
        if self.index_type == "ivf":
            index.nprobe = self.nprobe

        self._faiss_index = index
        self._emb_matrix = embeddings
        self._emb_ids = ids

        if self.cache_enabled and source_path:
            save_index = index if self.persist_index else None
            cache.save(embeddings, ids, source_path, index=save_index)

    def _fit_tfidf(self, texts: List[str], ids: List[str]) -> None:
        from backend.jd_parser import JD_TEXT_FOR_TFIDF
        logger.info("[retrieval] fitting TF-IDF vectoriser")
        all_texts = [JD_TEXT_FOR_TFIDF] + texts
        self._tfidf_vectorizer = TfidfVectorizer(
            ngram_range=self.tfidf_ngram,
            max_features=self.tfidf_max_features,
            min_df=self.tfidf_min_df,
            sublinear_tf=self.tfidf_sublinear,
        )
        matrix = self._tfidf_vectorizer.fit_transform(all_texts)
        self._tfidf_matrix = matrix[1:]   # drop the JD row; keep candidate rows
        self._tfidf_ids = ids
        logger.info(f"[retrieval] TF-IDF matrix: {matrix.shape}")

    # -----------------------------------------------------------------------
    # Retrieve (query → pool)
    # -----------------------------------------------------------------------

    def retrieve(
        self,
        profiles: List[CandidateProfile],
        min_pool_size: int = 100,
    ) -> RetrievalResult:
        """
        Query the indices and return a candidate pool.

        Args:
            profiles: All candidates (same list passed to fit()).
            min_pool_size: Minimum pool size regardless of top_k setting.

        Returns:
            RetrievalResult with pool + similarity scores.
        """
        if not self._fitted:
            raise RuntimeError("SemanticRetriever.fit() must be called before retrieve()")

        t0 = time.time()
        n_total = len(profiles)
        id_to_profile: Dict[str, CandidateProfile] = {cp.candidate_id: cp for cp in profiles}
        effective_k = max(min_pool_size, self.top_k)

        backend = self._resolve_backend()
        similarities: Dict[str, float] = {}
        pool_ids: List[str] = []

        if backend == "embedding+rrf":
            emb_ranked, emb_sims = self._query_embedding(effective_k)
            tfidf_ranked, tfidf_sims = self._query_tfidf(effective_k)
            similarities.update(tfidf_sims)
            similarities.update(emb_sims)  # embedding scores win in case of conflict
            pool_ids = _rrf_merge(
                [emb_ranked, tfidf_ranked],
                k=self.rrf_k,
                top_n=effective_k,
            )
            backend_used = "embedding+rrf"

        elif backend == "embedding":
            pool_ids, emb_sims = self._query_embedding(effective_k)
            similarities.update(emb_sims)
            backend_used = "embedding"

        else:  # tfidf
            pool_ids, tfidf_sims = self._query_tfidf(n_total)  # score all
            similarities.update(tfidf_sims)
            pool_ids = pool_ids[:effective_k]
            backend_used = "tfidf"

        # Title safety net — add tier-1-title candidates unconditionally
        if self.title_safety_net and backend != "tfidf":
            safety_ids = _title_safety_ids(profiles, self.jd)
            pool_id_set = set(pool_ids)
            for sid in safety_ids:
                if sid not in pool_id_set:
                    pool_ids.append(sid)
                    pool_id_set.add(sid)

        # Build profile list preserving retrieved order
        pool_profiles = [
            id_to_profile[cid]
            for cid in pool_ids
            if cid in id_to_profile
        ]

        return RetrievalResult(
            profiles=pool_profiles,
            similarities=similarities,
            backend_used=backend_used,
            retrieval_time_sec=time.time() - t0,
            n_total=n_total,
        )

    def _query_embedding(
        self, top_k: int
    ) -> Tuple[List[str], Dict[str, float]]:
        """Return (ranked_ids, similarities) from FAISS query."""
        jd_text = self._jd_embedding_text()
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        jd_emb = self._model.encode(
            [jd_text], normalize_embeddings=self.normalize
        ).astype(np.float32)

        k = min(top_k, len(self._emb_ids))
        distances, indices = self._faiss_index.search(jd_emb, k)

        ranked_ids = []
        sims: Dict[str, float] = {}
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._emb_ids):
                continue
            cid = self._emb_ids[idx]
            ranked_ids.append(cid)
            sims[cid] = float(np.clip(dist, 0.0, 1.0))

        return ranked_ids, sims

    def _query_tfidf(
        self, top_k: int
    ) -> Tuple[List[str], Dict[str, float]]:
        """Return (ranked_ids, similarities) from TF-IDF query."""
        from backend.jd_parser import JD_TEXT_FOR_TFIDF
        jd_vec = self._tfidf_vectorizer.transform([JD_TEXT_FOR_TFIDF])
        sims_array = cosine_similarity(jd_vec, self._tfidf_matrix).flatten()

        top_indices = np.argsort(sims_array)[::-1][:top_k]
        ranked_ids = [self._tfidf_ids[i] for i in top_indices]
        sims: Dict[str, float] = {
            self._tfidf_ids[i]: float(sims_array[i]) for i in top_indices
        }
        return ranked_ids, sims

    # -----------------------------------------------------------------------
    # Convenience: fit+retrieve in one call
    # -----------------------------------------------------------------------

    def fit_and_retrieve(
        self,
        profiles: List[CandidateProfile],
        source_path: Optional[Path] = None,
        min_pool_size: int = 100,
    ) -> RetrievalResult:
        self.fit(profiles, source_path=source_path)
        return self.retrieve(profiles, min_pool_size=min_pool_size)
