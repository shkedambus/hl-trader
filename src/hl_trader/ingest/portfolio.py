from __future__ import annotations

from dataclasses import replace

from hl_trader.domain.portfolio import PortfolioPoint
from hl_trader.hl.parsing import (
    JsonObject,
    as_float,
    as_int,
    as_json_array,
    as_json_object,
    as_json_pair,
    from_epoch_ms,
)

ALL_TIME = "allTime"
PERP_ALL_TIME = "perpAllTime"


def parse_account_history(response: object) -> tuple[PortfolioPoint, ...]:
    """The whole-account history, each point carrying the futures profit as of then.

    The two histories are sampled at different moments, so the futures profit is the
    latest one at or before each point, and zero before futures trading started.
    """
    by_period = _parse_periods(response)
    futures = by_period.get(PERP_ALL_TIME, ())
    joined: list[PortfolioPoint] = []
    cursor, trading_pnl = 0, 0.0
    for point in by_period.get(ALL_TIME, ()):
        while cursor < len(futures) and futures[cursor].at <= point.at:
            trading_pnl = futures[cursor].cumulative_pnl
            cursor += 1
        joined.append(replace(point, trading_pnl=trading_pnl))
    return tuple(joined)


def _parse_periods(response: object) -> dict[str, tuple[PortfolioPoint, ...]]:
    """The answer is a list of `[period, window]` pairs.

    Each window keeps account value and profit in two arrays joined on timestamp.
    """
    periods: dict[str, tuple[PortfolioPoint, ...]] = {}
    for pair in as_json_array(response) or []:
        halves = as_json_pair(pair)
        if halves is None:
            continue
        period, window = halves[0], as_json_object(halves[1])
        if isinstance(period, str) and window is not None:
            periods[period] = _parse_points(window)
    return periods


def _parse_points(window: JsonObject) -> tuple[PortfolioPoint, ...]:
    account_values = _parse_history(window.get("accountValueHistory"))
    profits = _parse_history(window.get("pnlHistory"))
    points = [
        PortfolioPoint(
            at=from_epoch_ms(timestamp_ms),
            account_value=account_value,
            cumulative_pnl=profits[timestamp_ms],
            trading_pnl=profits[timestamp_ms],
        )
        for timestamp_ms, account_value in account_values.items()
        if timestamp_ms in profits
    ]
    points.sort(key=lambda point: point.at)
    return tuple(points)


def _parse_history(value: object) -> dict[int, float]:
    history: dict[int, float] = {}
    for entry in as_json_array(value) or []:
        halves = as_json_pair(entry)
        if halves is None:
            continue
        timestamp_ms, measurement = as_int(halves[0]), as_float(halves[1])
        if timestamp_ms is not None and measurement is not None:
            history[timestamp_ms] = measurement
    return history
