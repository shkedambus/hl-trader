"""FR-6: trading style by median holding time."""

from __future__ import annotations

from enum import StrEnum

from hl_trader.domain.methodology import StyleBounds
from hl_trader.domain.trade_metrics import TradeMetrics


class Style(StrEnum):
    UNKNOWN = "unknown"
    MARKET_MAKER = "market_maker"
    HFT = "hft"
    INTRADAY = "intraday"
    SWING = "swing"
    POSITION = "position"


# Signals from a market maker or an HFT account reach a person too late to repeat.
FOLLOWABLE_STYLES = frozenset({Style.INTRADAY, Style.SWING, Style.POSITION})


def classify_style(trades: TradeMetrics, bounds: StyleBounds) -> Style:
    median_hold = trades.median_hold_s
    if median_hold is None:
        return Style.UNKNOWN
    if (
        median_hold < bounds.market_maker_max_hold_s
        and trades.fills_per_day >= bounds.market_maker_min_fills_per_day
    ):
        return Style.MARKET_MAKER
    if median_hold < bounds.hft_max_hold_s:
        return Style.HFT
    if median_hold < bounds.intraday_max_hold_s:
        return Style.INTRADAY
    if median_hold < bounds.swing_max_hold_s:
        return Style.SWING
    return Style.POSITION
