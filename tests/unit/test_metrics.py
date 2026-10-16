from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from hl_trader.domain.portfolio import PortfolioPoint, build_portfolio_metrics
from hl_trader.domain.round_trips import BUY, SELL, Direction, Fill, reconstruct_round_trips
from hl_trader.domain.trade_metrics import build_trade_metrics
from hl_trader.ingest.fills import parse_fill

TRADER = "0x" + "11" * 20
COUNTERPARTY = "0x" + "22" * 20
START = datetime(2026, 1, 1, tzinfo=timezone.utc)


def fill(
    hours: float, side: str, size: str, start: str, *, pnl: float = 0.0, liq: bool = False
) -> Fill:
    return Fill(
        coin="BTC",
        at=START + timedelta(hours=hours),
        side=side,
        size=Decimal(size),
        price=Decimal("100"),
        start_position=Decimal(start),
        closed_pnl=pnl,
        fee=0.0,
        was_liquidated=liq,
    )


def test_round_trip_from_open_to_flat_with_scale_in() -> None:
    trips = reconstruct_round_trips(
        [fill(0, BUY, "1", "0"), fill(1, BUY, "1", "1"), fill(5, SELL, "2", "2", pnl=30.0)]
    )

    assert len(trips) == 1
    assert trips[0].direction is Direction.LONG
    assert trips[0].entry_notional == 200.0
    assert trips[0].realized_pnl == 30.0
    assert trips[0].hold_seconds == 5 * 3600


def test_flip_closes_one_trip_and_opens_the_opposite() -> None:
    trips = reconstruct_round_trips(
        [
            fill(0, BUY, "1", "0"),
            fill(2, SELL, "3", "1", pnl=10.0),
            fill(4, BUY, "2", "-2", pnl=-5.0),
        ]
    )

    assert [(t.direction, t.realized_pnl) for t in trips] == [
        (Direction.LONG, 10.0),
        (Direction.SHORT, -5.0),
    ]


def test_trip_opened_before_the_data_is_not_fully_seen() -> None:
    trips = reconstruct_round_trips([fill(0, SELL, "1", "1", pnl=10.0)])

    assert trips[0].fully_seen is False
    assert (
        build_trade_metrics(
            trips, fills_count=1, fills_truncated=False, window_days=180
        ).round_trips
        == 0
    )


def test_trade_metrics_win_rate_profit_factor_expectancy() -> None:
    trips = reconstruct_round_trips(
        [
            fill(0, BUY, "1", "0"),
            fill(2, SELL, "1", "1", pnl=20.0),
            fill(3, BUY, "1", "0"),
            fill(4, SELL, "1", "1", pnl=-10.0),
        ]
    )

    metrics = build_trade_metrics(
        all_trips=trips, fills_count=4, fills_truncated=False, window_days=180
    )

    assert metrics.round_trips == 2
    assert metrics.win_rate == 0.5
    assert metrics.profit_factor == 2.0
    assert metrics.expectancy_pct == pytest.approx(0.05)
    assert metrics.median_hold_s == 1.5 * 3600


def test_tc_2_2_two_history_points_give_no_sharpe_rather_than_zero() -> None:
    points = (
        PortfolioPoint(START, 10_000.0, 0.0, 0.0),
        PortfolioPoint(START + timedelta(days=30), 11_000.0, 1_000.0, 1_000.0),
    )

    metrics = build_portfolio_metrics(points, now=START + timedelta(days=31), window_days=180)

    assert metrics.sharpe is None
    assert metrics.points == 2


def test_drawdown_ignores_a_withdrawal() -> None:
    points = (
        PortfolioPoint(START, 10_000.0, 0.0, 0.0),
        PortfolioPoint(START + timedelta(days=10), 12_000.0, 2_000.0, 2_000.0),
        PortfolioPoint(START + timedelta(days=20), 2_000.0, 2_000.0, 2_000.0),
        PortfolioPoint(START + timedelta(days=30), 1_800.0, 1_800.0, 1_800.0),
    )

    metrics = build_portfolio_metrics(points, now=START + timedelta(days=30), window_days=180)

    assert metrics.max_drawdown == pytest.approx(0.1, abs=1e-6)


def test_tc_2_3_counterparty_liquidation_is_not_counted() -> None:
    row = {
        "coin": "BTC",
        "side": "B",
        "time": 1_760_000_000_000,
        "sz": "0.5",
        "px": "60000",
        "startPosition": "0",
        "closedPnl": "0",
        "fee": "1.2",
        "tid": 1,
        "liquidation": {"liquidatedUser": COUNTERPARTY, "markPx": "60000", "method": "market"},
    }

    as_counterparty = parse_fill(row, address=TRADER)
    as_liquidated = parse_fill(row, address=COUNTERPARTY)

    assert as_counterparty is not None and as_counterparty.was_liquidated is False
    assert as_liquidated is not None and as_liquidated.was_liquidated is True
