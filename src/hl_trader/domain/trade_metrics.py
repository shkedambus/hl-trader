from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from hl_trader.domain.numbers import round_metric
from hl_trader.domain.round_trips import RoundTrip


@dataclass(frozen=True)
class TradeMetrics:
    """None means unmeasured rather than zero, e.g. a profit factor with no losing trade."""

    round_trips: int
    win_rate: float | None
    profit_factor: float | None
    expectancy_pct: float | None
    median_hold_s: float | None
    fills_count: int
    fills_per_day: float
    fills_truncated: bool
    liquidated_share: float | None
    coins: tuple[str, ...]


def build_trade_metrics(
    all_trips: Sequence[RoundTrip], *, fills_count: int, fills_truncated: bool, window_days: float
) -> TradeMetrics:
    trips = [trip for trip in all_trips if trip.fully_seen]
    profits = [trip.realized_pnl for trip in trips]
    gross_win = sum(profit for profit in profits if profit > 0)
    gross_loss = -sum(profit for profit in profits if profit < 0)
    holds = [hold for trip in trips if (hold := trip.hold_seconds) is not None]
    return TradeMetrics(
        round_trips=len(trips),
        win_rate=_ratio(sum(1 for profit in profits if profit > 0), len(trips)),
        profit_factor=round_metric(gross_win / gross_loss) if gross_loss > 0 else None,
        expectancy_pct=_expectancy_pct(trips),
        median_hold_s=round_metric(statistics.median(holds)) if holds else None,
        fills_count=fills_count,
        fills_per_day=round_metric(fills_count / max(window_days, 1.0)),
        fills_truncated=fills_truncated,
        liquidated_share=_liquidated_share(trips),
        coins=tuple(sorted({trip.coin for trip in trips})),
    )


def _expectancy_pct(trips: Sequence[RoundTrip]) -> float | None:
    """Average return on the money committed: comparable across account sizes."""
    returns = [trip.realized_pnl / trip.entry_notional for trip in trips if trip.entry_notional > 0]
    return round_metric(statistics.fmean(returns)) if returns else None


def _liquidated_share(trips: Sequence[RoundTrip]) -> float | None:
    total = sum(trip.entry_notional for trip in trips)
    if total <= 0:
        return None
    liquidated = sum(trip.entry_notional for trip in trips if trip.was_liquidated)
    return round_metric(liquidated / total)


def _ratio(part: int, whole: int) -> float | None:
    return round_metric(part / whole) if whole > 0 else None
