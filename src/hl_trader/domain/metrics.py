from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from hl_trader.domain.portfolio import PortfolioMetrics
from hl_trader.domain.trade_metrics import TradeMetrics


class ScoredMetric(StrEnum):
    SHARPE = "sharpe"
    PROFIT_FACTOR = "profit_factor"
    WIN_RATE = "win_rate"
    MAX_DRAWDOWN = "max_drawdown"
    EXPECTANCY_PCT = "expectancy_pct"
    TENURE_DAYS = "tenure_days"


@dataclass(frozen=True)
class TraderMetrics:
    portfolio: PortfolioMetrics
    trades: TradeMetrics

    def scored_values(self) -> dict[ScoredMetric, float | None]:
        return {
            ScoredMetric.SHARPE: self.portfolio.sharpe,
            ScoredMetric.PROFIT_FACTOR: self.trades.profit_factor,
            ScoredMetric.WIN_RATE: self.trades.win_rate,
            ScoredMetric.MAX_DRAWDOWN: self.portfolio.max_drawdown,
            ScoredMetric.EXPECTANCY_PCT: self.trades.expectancy_pct,
            ScoredMetric.TENURE_DAYS: self.portfolio.tenure_days,
        }
