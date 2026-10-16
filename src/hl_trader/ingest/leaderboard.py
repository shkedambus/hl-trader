from __future__ import annotations

from collections.abc import Iterable

from hl_trader.domain.prefilter import LeaderboardEntry, WindowPerformance
from hl_trader.hl.parsing import (
    JsonObject,
    as_float,
    as_json_array,
    as_json_object,
    as_json_pair,
    normalize_address,
)

ALL_TIME_WINDOW = "allTime"


def parse_entries(rows: Iterable[JsonObject]) -> list[LeaderboardEntry]:
    """Drop unusable rows and keep the last row per address."""
    by_address: dict[str, LeaderboardEntry] = {}
    for row in rows:
        entry = parse_entry(row)
        if entry is not None:
            by_address[entry.address] = entry
    return list(by_address.values())


def parse_entry(row: JsonObject) -> LeaderboardEntry | None:
    address = normalize_address(row.get("ethAddress"))
    account_value = as_float(row.get("accountValue"))
    all_time = _find_window(row.get("windowPerformances"), ALL_TIME_WINDOW)
    if address is None or account_value is None or all_time is None:
        return None
    return LeaderboardEntry(address=address, account_value=account_value, all_time=all_time)


def _find_window(windows: object, period: str) -> WindowPerformance | None:
    for pair in as_json_array(windows) or []:
        halves = as_json_pair(pair)
        if halves is not None and halves[0] == period:
            return _parse_performance(halves[1])
    return None


def _parse_performance(value: object) -> WindowPerformance | None:
    performance = as_json_object(value)
    if performance is None:
        return None
    pnl = as_float(performance.get("pnl"))
    roi = as_float(performance.get("roi"))
    volume = as_float(performance.get("vlm"))
    if pnl is None or roi is None or volume is None:
        return None
    return WindowPerformance(pnl=pnl, roi=roi, volume=volume)
