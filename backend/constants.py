"""Shared constants across all backend modules."""

from datetime import date

# Fixed reference date for all recency and age calculations.
# A fixed date (not date.today()) keeps scoring deterministic regardless
# of when the pipeline runs — critical for reproducible submissions.
REFERENCE_DATE = date(2026, 6, 25)
