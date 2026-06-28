"""
Loads scoring.yaml and exposes a validated, dot-accessible ScoringConfig.
All backend modules must import from here — no raw yaml.load() elsewhere.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "scoring.yaml"

# Module-level singleton — populated on first call to load_config().
_CACHED_CONFIG: "ScoringConfig | None" = None


class ConfigError(ValueError):
    """Raised when scoring.yaml is missing required keys or has invalid values."""


class _NS:
    """Recursive namespace: wraps a dict and exposes keys as attributes."""

    def __init__(self, data: dict) -> None:
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, _NS(value))
            else:
                setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __repr__(self) -> str:  # pragma: no cover
        return f"_NS({vars(self)})"


class ScoringConfig:
    """
    Thin wrapper around the parsed YAML dict.
    Access top-level sections as attributes: cfg.semantic, cfg.scoring, etc.
    """

    def __init__(self, data: dict) -> None:
        self._data = data
        self.semantic = _NS(data["semantic"])
        self.scoring = _NS(data["scoring"])
        self.penalties = _NS(data["penalties"])
        self.honeypot = _NS(data["honeypot"])

    # Convenience pass-throughs so callers can do cfg["semantic"] too.
    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def raw(self) -> dict:
        return self._data


def _validate(data: dict) -> None:
    """Raise ConfigError on obviously broken configs."""
    required_top_keys = {"semantic", "scoring", "penalties", "honeypot"}
    missing = required_top_keys - data.keys()
    if missing:
        raise ConfigError(f"scoring.yaml missing required top-level keys: {missing}")

    weights = data["scoring"].get("component_weights", {})
    total = round(sum(weights.values()), 6)
    if abs(total - 1.0) > 1e-4:
        raise ConfigError(
            f"scoring.component_weights must sum to 1.0, got {total}. "
            f"Weights: {weights}"
        )

    bw = data["scoring"].get("behavioral_sub_weights", {})
    if bw:
        btotal = round(sum(bw.values()), 6)
        if abs(btotal - 1.0) > 1e-4:
            raise ConfigError(
                f"scoring.behavioral_sub_weights must sum to 1.0, got {btotal}."
            )

    # Verify FAISS config is accessible
    try:
        _ = data["semantic"]["embedding"]["faiss"]["top_k"]
    except KeyError as exc:
        raise ConfigError(f"scoring.yaml missing faiss config key: {exc}") from exc

    # Verify RRF section present
    if "rrf" not in data["semantic"]:
        raise ConfigError("scoring.yaml missing semantic.rrf section")


def load_config(path: str | Path | None = None) -> ScoringConfig:
    """
    Load (and cache) the scoring config from YAML.

    Args:
        path: Optional override for the config file path.
              Defaults to config/scoring.yaml in the repo root.

    Returns:
        ScoringConfig instance.
    """
    global _CACHED_CONFIG

    if path is None and _CACHED_CONFIG is not None:
        return _CACHED_CONFIG

    config_path = Path(path) if path is not None else _DEFAULT_CONFIG_PATH

    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        try:
            data = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Failed to parse {config_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Config file did not parse to a dict: {config_path}")

    _validate(data)
    cfg = ScoringConfig(data)

    if path is None:
        _CACHED_CONFIG = cfg

    return cfg


def reset_cache() -> None:
    """Clear the module-level singleton (useful in tests)."""
    global _CACHED_CONFIG
    _CACHED_CONFIG = None
