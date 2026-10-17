from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from hl_trader.domain.round_trips import Fill
from hl_trader.hl.parsing import (
    JsonObject,
    as_decimal,
    as_float,
    as_int,
    as_json_object,
    from_epoch_ms,
    to_epoch_ms,
)

# HyperLiquid caps userFillsByTime at 2000 fills per answer.
PAGE_SIZE = 2000


class FillsFetcher(Protocol):
    async def user_fills_by_time(self, address: str, *, start_time_ms: int) -> list[object]: ...


@dataclass(frozen=True)
class FillPage:
    fills: list[Fill]
    truncated: bool


async def fetch_fills(
    client: FillsFetcher, address: str, *, start_time_ms: int, max_pages: int
) -> FillPage:
    """Walk one account's fills forward; `truncated` means the pages ran out first."""
    fills: list[Fill] = []
    seen_trade_ids: set[int] = set()
    cursor = start_time_ms
    for _ in range(max_pages):
        rows = await client.user_fills_by_time(address, start_time_ms=cursor)
        fresh = _unseen_fills(rows, seen_trade_ids, address=address)
        fills.extend(fresh)
        if len(rows) < PAGE_SIZE or not fresh:
            return FillPage(fills=fills, truncated=False)
        cursor = max(to_epoch_ms(fill.at) for fill in fresh)
    return FillPage(fills=fills, truncated=True)


def _unseen_fills(rows: list[object], seen_trade_ids: set[int], *, address: str) -> list[Fill]:
    fresh: list[Fill] = []
    for row in rows:
        fill_object = as_json_object(row)
        trade_id = None if fill_object is None else as_int(fill_object.get("tid"))
        if fill_object is None or trade_id is None or trade_id in seen_trade_ids:
            continue
        fill = parse_fill(fill_object, address=address)
        if fill is not None:
            seen_trade_ids.add(trade_id)
            fresh.append(fill)
    return fresh


def parse_fill(fill: JsonObject, *, address: str) -> Fill | None:
    coin, side, timestamp_ms = fill.get("coin"), fill.get("side"), as_int(fill.get("time"))
    if not isinstance(coin, str) or not isinstance(side, str) or timestamp_ms is None:
        return None
    amounts = _decimals(fill, ("sz", "px", "startPosition"))
    if amounts is None:
        return None
    size, price, start_position = amounts
    return Fill(
        coin=coin,
        at=from_epoch_ms(timestamp_ms),
        side=side,
        size=size,
        price=price,
        start_position=start_position,
        closed_pnl=as_float(fill.get("closedPnl")) or 0.0,
        fee=as_float(fill.get("fee")) or 0.0,
        was_liquidated=_liquidated_this_account(fill, address),
    )


def _liquidated_this_account(fill: JsonObject, address: str) -> bool:
    """A liquidation mark may belong to the counterparty; only this account's counts."""
    liquidation = as_json_object(fill.get("liquidation"))
    if liquidation is None:
        return False
    liquidated_user = liquidation.get("liquidatedUser")
    return isinstance(liquidated_user, str) and liquidated_user.lower() == address.lower()


def _decimals(fill: JsonObject, keys: tuple[str, ...]) -> tuple[Decimal, ...] | None:
    values = [as_decimal(fill.get(key)) for key in keys]
    if any(value is None for value in values):
        return None
    return tuple(value for value in values if value is not None)
