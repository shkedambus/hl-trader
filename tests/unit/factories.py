from __future__ import annotations

from dataclasses import replace
from typing import Any

from hl_trader.domain.metrics import TraderMetrics
from hl_trader.domain.numbers import SECONDS_PER_DAY
from hl_trader.domain.portfolio import PortfolioMetrics
from hl_trader.domain.trade_metrics import TradeMetrics


def strong_trader(**trade_changes: Any) -> TraderMetrics:
    """A trader who passes every filter and threshold of methodology version 1."""
    portfolio = PortfolioMetrics(
        tenure_days=400.0, account_value=250_000.0, sharpe=1.5, max_drawdown=0.15, points=60
    )
    trades = TradeMetrics(
        round_trips=45,
        win_rate=0.6,
        profit_factor=2.0,
        expectancy_pct=0.03,
        median_hold_s=2 * SECONDS_PER_DAY,
        fills_count=400,
        fills_per_day=2.2,
        fills_truncated=False,
        liquidated_share=0.0,
        coins=("BTC", "ETH"),
    )
    return TraderMetrics(portfolio=portfolio, trades=replace(trades, **trade_changes))


def with_portfolio(metrics: TraderMetrics, **changes: Any) -> TraderMetrics:
    return replace(metrics, portfolio=replace(metrics.portfolio, **changes))
