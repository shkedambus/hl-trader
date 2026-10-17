"""Selection parameters, defaults from SRS appendix A.

Every verdict records the `version` it was computed under.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from hl_trader.domain.metrics import ScoredMetric
from hl_trader.domain.numbers import SECONDS_PER_DAY, SECONDS_PER_HOUR, clip01


@dataclass(frozen=True)
class Prefilter:
    min_account_value: float = 10_000.0
    min_roi_all_time: float = 0.2
    min_volume_all_time: float = 1_000_000.0
    min_edge_ratio: float = 0.002
    # Normalisation points for the queue priority, not screening thresholds.
    roi_reference: float = 1.0
    volume_reference: float = 100_000_000.0


@dataclass(frozen=True)
class Filters:
    min_tenure_days: float = 90.0
    min_round_trips: int = 10
    min_account_value: float = 10_000.0
    max_liquidated_share: float = 0.05
    min_median_hold_s: float = SECONDS_PER_HOUR


@dataclass(frozen=True)
class Bounds:
    """Linear map onto 0..1; `floor` exceeds `ceiling` for metrics where less is better."""

    floor: float
    ceiling: float

    def normalise(self, value: float) -> float:
        return clip01((value - self.floor) / (self.ceiling - self.floor))


@dataclass(frozen=True)
class ScoreTerm:
    weight: float
    bounds: Bounds


def _default_score_terms() -> dict[ScoredMetric, ScoreTerm]:
    return {
        ScoredMetric.SHARPE: ScoreTerm(0.30, Bounds(0.0, 2.0)),
        ScoredMetric.PROFIT_FACTOR: ScoreTerm(0.20, Bounds(1.0, 2.5)),
        ScoredMetric.WIN_RATE: ScoreTerm(0.15, Bounds(0.4, 0.7)),
        ScoredMetric.MAX_DRAWDOWN: ScoreTerm(0.15, Bounds(0.5, 0.0)),
        ScoredMetric.EXPECTANCY_PCT: ScoreTerm(0.10, Bounds(0.0, 0.05)),
        # One good year proves little, so full marks need two years of history.
        ScoredMetric.TENURE_DAYS: ScoreTerm(0.10, Bounds(90.0, 730.0)),
    }


@dataclass(frozen=True)
class ConfidenceTargets:
    round_trips: int = 40
    portfolio_points: int = 60
    truncation_penalty: float = 0.5


@dataclass(frozen=True)
class StyleBounds:
    market_maker_max_hold_s: float = 5 * 60
    market_maker_min_fills_per_day: float = 200.0
    hft_max_hold_s: float = 15 * 60
    intraday_max_hold_s: float = 8 * SECONDS_PER_HOUR
    swing_max_hold_s: float = 5 * SECONDS_PER_DAY


@dataclass(frozen=True)
class Selection:
    min_score: float = 0.5
    min_confidence: float = 0.3
    window_days: float = 180.0
    tracked_limit: int = 60


@dataclass(frozen=True)
class Methodology:
    version: str = "1"
    prefilter: Prefilter = Prefilter()
    filters: Filters = Filters()
    score_terms: Mapping[ScoredMetric, ScoreTerm] = field(default_factory=_default_score_terms)
    confidence: ConfidenceTargets = ConfidenceTargets()
    styles: StyleBounds = StyleBounds()
    selection: Selection = Selection()
