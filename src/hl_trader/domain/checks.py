from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Criterion(StrEnum):
    TENURE_DAYS = "tenure_days"
    ROUND_TRIPS = "round_trips"
    ACCOUNT_VALUE = "account_value"
    LIQUIDATED_SHARE = "liquidated_share"
    MEDIAN_HOLD_S = "median_hold_s"
    SCORE = "score"
    CONFIDENCE = "confidence"


class Comparison(StrEnum):
    AT_LEAST = ">="
    AT_MOST = "<="


@dataclass(frozen=True)
class Check:
    """One threshold with the actual value, so a rejection can show by how much it failed."""

    criterion: Criterion
    actual: float | None
    comparison: Comparison
    threshold: float

    @property
    def passed(self) -> bool:
        if self.actual is None:
            return False
        if self.comparison is Comparison.AT_LEAST:
            return self.actual >= self.threshold
        return self.actual <= self.threshold
