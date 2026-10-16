"""FR-3...FR-5: filters, score and confidence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from hl_trader.domain.checks import Check, Comparison, Criterion
from hl_trader.domain.methodology import ConfidenceTargets, Filters, ScoreTerm
from hl_trader.domain.metrics import ScoredMetric, TraderMetrics
from hl_trader.domain.numbers import clip01, round_metric


@dataclass(frozen=True)
class Score:
    value: float
    contributions: Mapping[ScoredMetric, float]
    unmeasured: tuple[ScoredMetric, ...]


@dataclass(frozen=True)
class ConfidenceBreakdown:
    value: float
    round_trips: int
    portfolio_points: int
    history_complete: bool


def check_filters(metrics: TraderMetrics, filters: Filters) -> tuple[Check, ...]:
    portfolio, trades = metrics.portfolio, metrics.trades
    # Nothing traded means nothing liquidated; such an account fails on round trips instead.
    liquidated_share = trades.liquidated_share if trades.liquidated_share is not None else 0.0
    at_least, at_most = Comparison.AT_LEAST, Comparison.AT_MOST
    return (
        Check(Criterion.TENURE_DAYS, portfolio.tenure_days, at_least, filters.min_tenure_days),
        Check(Criterion.ROUND_TRIPS, trades.round_trips, at_least, filters.min_round_trips),
        Check(
            Criterion.ACCOUNT_VALUE, portfolio.account_value, at_least, filters.min_account_value
        ),
        Check(Criterion.LIQUIDATED_SHARE, liquidated_share, at_most, filters.max_liquidated_share),
        Check(Criterion.MEDIAN_HOLD_S, trades.median_hold_s, at_least, filters.min_median_hold_s),
    )


def compute_score(metrics: TraderMetrics, terms: Mapping[ScoredMetric, ScoreTerm]) -> Score:
    """Weighted sum of normalised metrics on an absolute scale, independent of other traders.

    An unmeasured metric drops out with its weight and the rest are renormalised, so the
    contributions add up to the score.
    """
    values = metrics.scored_values()
    measured = {metric: value for metric, value in values.items() if value is not None}
    unmeasured = tuple(metric for metric, value in values.items() if value is None)
    total_weight = sum(terms[metric].weight for metric in measured)
    if total_weight <= 0:
        return Score(value=0.0, contributions={}, unmeasured=unmeasured)
    contributions = {
        metric: terms[metric].weight / total_weight * terms[metric].bounds.normalise(value)
        for metric, value in measured.items()
    }
    return Score(
        value=round_metric(sum(contributions.values())),
        contributions=contributions,
        unmeasured=unmeasured,
    )


def compute_confidence(metrics: TraderMetrics, targets: ConfidenceTargets) -> ConfidenceBreakdown:
    """How much data stands behind the score; it never enters the score."""
    round_trips, points = metrics.trades.round_trips, metrics.portfolio.points
    history_complete = not metrics.trades.fills_truncated
    evidence = clip01(round_trips / targets.round_trips) * clip01(points / targets.portfolio_points)
    if not history_complete:
        evidence *= targets.truncation_penalty
    return ConfidenceBreakdown(
        value=round_metric(evidence),
        round_trips=round_trips,
        portfolio_points=points,
        history_complete=history_complete,
    )
