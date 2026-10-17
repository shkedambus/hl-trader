from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta

from hl_trader.domain.numbers import SECONDS_PER_DAY, round_metric

SECONDS_PER_YEAR = 365.0 * SECONDS_PER_DAY
# Capital below this cannot carry a meaningful return: funding drift on a dust-sized
# account would otherwise read as thousands of percent.
MIN_CAPITAL_AT_RISK_USD = 100.0
MIN_RETURNS_FOR_SHARPE = 3


@dataclass(frozen=True)
class PortfolioPoint:
    """`account_value` and `cumulative_pnl` cover the whole account, spot included;
    `trading_pnl` is the futures profit alone."""

    at: datetime
    account_value: float
    cumulative_pnl: float
    trading_pnl: float


@dataclass(frozen=True)
class PortfolioMetrics:
    """HyperLiquid returns tens of points for a whole account life, so `max_drawdown` is
    a lower bound and `sharpe` is noisy; `points` lets the confidence weigh both."""

    tenure_days: float
    account_value: float
    sharpe: float | None
    max_drawdown: float | None
    points: int


def build_portfolio_metrics(
    points: tuple[PortfolioPoint, ...], *, now: datetime, window_days: float
) -> PortfolioMetrics:
    if not points:
        return PortfolioMetrics(
            tenure_days=0.0, account_value=0.0, sharpe=None, max_drawdown=None, points=0
        )
    window = _since(points, now - timedelta(days=window_days))
    return PortfolioMetrics(
        tenure_days=round_metric((now - points[0].at).total_seconds() / SECONDS_PER_DAY),
        account_value=points[-1].account_value,
        sharpe=_annualised_sharpe(points),
        max_drawdown=_deepest_fall(window),
        points=len(points),
    )


def _interval_returns(points: tuple[PortfolioPoint, ...]) -> list[float]:
    """Futures profit over the capital at risk, per interval between points.

    Account value also moves on deposits and withdrawals: whatever it moved beyond the
    total profit is a net flow, counted as arriving mid-interval (Modified Dietz).
    Intervals with next to no capital are skipped, and a loss is capped at the capital.
    """
    returns: list[float] = []
    for previous, current in zip(points, points[1:]):
        profit = current.trading_pnl - previous.trading_pnl
        total_profit = current.cumulative_pnl - previous.cumulative_pnl
        net_flow = (current.account_value - previous.account_value) - total_profit
        capital = previous.account_value + net_flow / 2
        if min(previous.account_value, capital) < MIN_CAPITAL_AT_RISK_USD:
            continue
        returns.append(max(profit / capital, -1.0))
    return returns


def _annualised_sharpe(points: tuple[PortfolioPoint, ...]) -> float | None:
    returns = _interval_returns(points)
    if len(returns) < MIN_RETURNS_FOR_SHARPE:
        return None
    spread = statistics.stdev(returns)
    if spread == 0:
        return None
    periods = _periods_per_year(points)
    if periods is None:
        return None
    return round_metric(statistics.fmean(returns) / spread * math.sqrt(periods))


def _periods_per_year(points: tuple[PortfolioPoint, ...]) -> float | None:
    """Annualise by the interval the data actually has, which is neither daily nor even."""
    span_seconds = (points[-1].at - points[0].at).total_seconds()
    if span_seconds <= 0:
        return None
    return SECONDS_PER_YEAR / (span_seconds / (len(points) - 1))


def _deepest_fall(points: tuple[PortfolioPoint, ...]) -> float | None:
    """Deepest fall of the compounded return index from its peak, 0..1.

    Built from flow-adjusted returns, so deposits and withdrawals do not move it.
    """
    returns = _interval_returns(points)
    if not returns:
        return None
    deepest = 0.0
    index = peak = 1.0
    for interval_return in returns:
        index *= 1 + interval_return
        peak = max(peak, index)
        deepest = max(deepest, 1 - index / peak)
    return round_metric(deepest)


def _since(points: tuple[PortfolioPoint, ...], start: datetime) -> tuple[PortfolioPoint, ...]:
    """Points from the last one at or before `start` onwards, so the crossing interval counts."""
    opening = max((i for i, point in enumerate(points) if point.at <= start), default=0)
    return points[opening:]
