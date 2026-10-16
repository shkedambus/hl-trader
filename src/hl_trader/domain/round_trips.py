"""Replay fills into round trips: a position on one coin from zero back to zero."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from hl_trader.domain.numbers import ZERO

# HyperLiquid names the sides by book: B for bid, A for ask.
BUY = "B"
SELL = "A"


class Direction(StrEnum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True)
class Fill:
    """One execution, as HyperLiquid reports it.

    `start_position` is the signed position before the fill and is authoritative: a
    stream of fills replays without accumulating rounding error, and gaps where fills
    are missing become visible.
    """

    coin: str
    at: datetime
    side: str
    size: Decimal
    price: Decimal
    start_position: Decimal
    closed_pnl: float
    fee: float
    was_liquidated: bool

    @property
    def signed_size(self) -> Decimal:
        return self.size if self.side == BUY else -self.size


@dataclass(frozen=True)
class RoundTrip:
    """`opened_at` is None when the opening is not in the data, so hold time is unknown.

    `fully_seen` is False when part of the trip happened outside the data; its size and
    profit are then partial and it is left out of the trade metrics.
    """

    coin: str
    direction: Direction
    opened_at: datetime | None
    closed_at: datetime
    entry_notional: float
    realized_pnl: float
    fees: float
    was_liquidated: bool
    fully_seen: bool = True

    @property
    def hold_seconds(self) -> float | None:
        if self.opened_at is None:
            return None
        return (self.closed_at - self.opened_at).total_seconds()


def reconstruct_round_trips(fills: Iterable[Fill]) -> list[RoundTrip]:
    """Positions still open when the fills run out are dropped: nothing about them is settled."""
    trips: list[RoundTrip] = []
    for coin_fills in _group_by_coin(fills).values():
        trips.extend(_reconstruct_one_coin(coin_fills))
    trips.sort(key=lambda trip: trip.closed_at)
    return trips


def _group_by_coin(fills: Iterable[Fill]) -> dict[str, list[Fill]]:
    by_coin: dict[str, list[Fill]] = {}
    for fill in fills:
        by_coin.setdefault(fill.coin, []).append(fill)
    for coin_fills in by_coin.values():
        coin_fills.sort(key=lambda fill: fill.at)
    return by_coin


@dataclass
class _OpenTrip:
    coin: str
    direction: Direction
    opened_at: datetime | None
    entry_notional: Decimal = ZERO
    realized_pnl: float = 0.0
    fees: float = 0.0
    was_liquidated: bool = False
    fully_seen: bool = True

    def apply_fill(self, fill: Fill, *, added_size: Decimal) -> None:
        self.realized_pnl += fill.closed_pnl
        self.fees += fill.fee
        self.apply_size_only(fill, added_size=added_size)

    def apply_size_only(self, fill: Fill, *, added_size: Decimal) -> None:
        """A flip is one fill acting on two trips: profit settles the old, size opens the new."""
        self.entry_notional += added_size * fill.price
        self.was_liquidated = self.was_liquidated or fill.was_liquidated

    def close(self, closed_at: datetime) -> RoundTrip:
        return RoundTrip(
            coin=self.coin,
            direction=self.direction,
            opened_at=self.opened_at,
            closed_at=closed_at,
            entry_notional=float(self.entry_notional),
            realized_pnl=self.realized_pnl,
            fees=self.fees,
            was_liquidated=self.was_liquidated,
            fully_seen=self.fully_seen,
        )


def _reconstruct_one_coin(fills: list[Fill]) -> list[RoundTrip]:
    trips: list[RoundTrip] = []
    open_trip: _OpenTrip | None = None
    expected_position: Decimal | None = None

    for fill in fills:
        before = fill.start_position
        after = before + fill.signed_size
        if open_trip is not None and expected_position != before:
            # Fills are missing. If the gap passed through zero the trip ended inside it,
            # and letting it run on would hand the next position the wrong direction.
            open_trip.fully_seen = False
            if before == ZERO or _direction(before) != open_trip.direction:
                trips.append(open_trip.close(fill.at))
                open_trip = None
            else:
                open_trip.opened_at = None
        if open_trip is None and before != ZERO:
            open_trip = _OpenTrip(
                coin=fill.coin, direction=_direction(before), opened_at=None, fully_seen=False
            )
        if open_trip is None:
            open_trip = _OpenTrip(coin=fill.coin, direction=_direction(after), opened_at=fill.at)

        open_trip.apply_fill(fill, added_size=_size_added_to(open_trip.direction, before, after))
        expected_position = after
        if after == ZERO:
            trips.append(open_trip.close(fill.at))
            open_trip = None
        elif before != ZERO and _direction(after) != open_trip.direction:
            trips.append(open_trip.close(fill.at))
            open_trip = _OpenTrip(coin=fill.coin, direction=_direction(after), opened_at=fill.at)
            open_trip.apply_size_only(fill, added_size=abs(after))
    return trips


def _direction(position: Decimal) -> Direction:
    if position == ZERO:
        raise ValueError("a flat position has no direction")
    return Direction.LONG if position > ZERO else Direction.SHORT


def _size_added_to(direction: Direction, before: Decimal, after: Decimal) -> Decimal:
    """How much this fill added to the position, ignoring any part that reduced it."""
    if after != ZERO and _direction(after) != direction:
        return ZERO
    growth = abs(after) - abs(before)
    return growth if growth > ZERO else ZERO
