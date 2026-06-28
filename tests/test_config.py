"""
Tests for backend/config_loader.py (Phase 1).
Run with: python -m pytest tests/test_config.py -v
"""

import sys
import os
import textwrap
import tempfile
from pathlib import Path

import pytest

# Make backend importable when running from repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config_loader import load_config, reset_cache, ConfigError, ScoringConfig


@pytest.fixture(autouse=True)
def clear_singleton():
    """Ensure each test starts with a fresh singleton."""
    reset_cache()
    yield
    reset_cache()


# ---------------------------------------------------------------------------
# Test 1: Loads default config without error
# ---------------------------------------------------------------------------
def test_loads_default_config():
    cfg = load_config()
    assert isinstance(cfg, ScoringConfig)


# ---------------------------------------------------------------------------
# Test 2: Component weights sum to 1.0
# ---------------------------------------------------------------------------
def test_component_weights_sum_to_one():
    cfg = load_config()
    weights = cfg.scoring.component_weights
    total = sum(vars(weights).values())
    assert abs(total - 1.0) < 1e-4, f"component_weights sum = {total}"


# ---------------------------------------------------------------------------
# Test 3: Behavioral sub-weights sum to 1.0
# ---------------------------------------------------------------------------
def test_behavioral_sub_weights_sum_to_one():
    cfg = load_config()
    bw = cfg.scoring.behavioral_sub_weights
    total = sum(vars(bw).values())
    assert abs(total - 1.0) < 1e-4, f"behavioral_sub_weights sum = {total}"


# ---------------------------------------------------------------------------
# Test 4: All required top-level keys are present and accessible
# ---------------------------------------------------------------------------
def test_required_top_level_keys():
    cfg = load_config()
    assert hasattr(cfg, "semantic")
    assert hasattr(cfg, "scoring")
    assert hasattr(cfg, "penalties")
    assert hasattr(cfg, "honeypot")


# ---------------------------------------------------------------------------
# Test 5: FAISS config is accessible via dot notation
# ---------------------------------------------------------------------------
def test_faiss_config_accessible():
    cfg = load_config()
    faiss = cfg.semantic.embedding.faiss
    assert faiss.top_k > 0, "top_k must be positive"
    assert faiss.index_type in ("flat", "ivf"), f"unexpected index_type: {faiss.index_type}"
    assert faiss.persist_index is True, "persist_index should be True"
    assert faiss.title_safety_net is True, "title_safety_net should be True"


# ---------------------------------------------------------------------------
# Test 6: RRF section is accessible and valid
# ---------------------------------------------------------------------------
def test_rrf_config_accessible():
    cfg = load_config()
    rrf = cfg.semantic.rrf
    assert rrf.enabled is True
    assert rrf.k > 0, "RRF k must be positive"
    assert rrf.top_embedding_k >= 100
    assert rrf.top_tfidf_k >= 100


# ---------------------------------------------------------------------------
# Test 7: Invalid YAML raises ConfigError with a clear message
# ---------------------------------------------------------------------------
def test_invalid_yaml_raises_config_error():
    bad_yaml = "this: is: not: valid: yaml: [unclosed"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as fh:
        fh.write(bad_yaml)
        tmp_path = fh.name
    try:
        with pytest.raises(ConfigError):
            load_config(path=tmp_path)
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Test 8: Config with weights not summing to 1.0 raises ConfigError
# ---------------------------------------------------------------------------
def test_bad_weights_raises_config_error():
    bad_config = textwrap.dedent("""\
        semantic:
          backend: "tfidf"
          embedding:
            model_name: "all-MiniLM-L6-v2"
            batch_size: 64
            normalize_embeddings: true
            faiss:
              index_type: "flat"
              nlist: 100
              nprobe: 10
              top_k: 100
              title_safety_net: true
              persist_index: true
            cache:
              enabled: false
              path: "outputs/embedding_cache"
            rule_blend: 0.75
            semantic_blend: 0.25
          rrf:
            enabled: false
            k: 60
            top_embedding_k: 100
            top_tfidf_k: 100
          tfidf:
            ngram_range: [1, 2]
            max_features: 8000
            min_df: 2
            sublinear_tf: true
            rule_blend: 0.85
            semantic_blend: 0.15
        scoring:
          component_weights:
            title_role: 0.50
            skill_match: 0.50
            production_evidence: 0.50   # intentionally sums to > 1
          behavioral_sub_weights:
            recency: 1.0
        penalties:
          honeypot_multiplier: 0.05
          consulting_only:
            career_fraction_threshold: 0.85
            penalty: 0.30
          wrong_domain:
            full_penalty: 0.45
            partial_penalty: 0.10
          cv_robotics_without_nlp:
            full_penalty: 0.30
            partial_penalty: 0.10
          job_hopping:
            short_stint_months: 18
            min_short_stints: 4
            penalty: 0.10
          behaviorally_unavailable:
            inactive_days_threshold: 180
            response_rate_threshold: 0.10
            penalty: 0.20
        honeypot:
          timeline_overlap_tolerance_days: 90
          single_flag_knockout_overlap_days: 365
          yoe_discrepancy_threshold_years: 3.0
          expert_skill_fraction_threshold: 0.90
          endorsement_suspicious_threshold: 900
          high_endorsement_count_min: 3
          duration_inflation_factor: 1.50
          min_career_span_months_for_duration_check: 12
          education_max_duration_years: 12
          perfect_behavioral_signals_threshold: 4
          min_flags_for_honeypot: 2
    """)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as fh:
        fh.write(bad_config)
        tmp_path = fh.name
    try:
        with pytest.raises(ConfigError, match="component_weights"):
            load_config(path=tmp_path)
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Test 9: Honeypot thresholds are accessible
# ---------------------------------------------------------------------------
def test_honeypot_thresholds_accessible():
    cfg = load_config()
    hp = cfg.honeypot
    assert hp.timeline_overlap_tolerance_days > 0
    assert hp.min_flags_for_honeypot >= 1
    assert hp.yoe_discrepancy_threshold_years > 0


# ---------------------------------------------------------------------------
# Test 10: Caching — second call returns same object without re-reading disk
# ---------------------------------------------------------------------------
def test_config_is_cached():
    cfg1 = load_config()
    cfg2 = load_config()
    assert cfg1 is cfg2, "load_config() should return the same object on repeated calls"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
