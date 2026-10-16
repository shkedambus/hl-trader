from datetime import datetime, timedelta, timezone

from hl_trader.domain.methodology import Methodology
from hl_trader.domain.style import Style
from hl_trader.pipeline import evaluate

NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)
ADDRESS = "0x" + "33" * 20
DAY_MS = 86_400_000


def ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


class FakeExchange:
    """Two years of steady growth and 45 profitable two-day trades."""

    def __init__(self) -> None:
        start = NOW - timedelta(days=700)
        times = [ms(start + timedelta(days=10 * i)) for i in range(71)]
        values = [str(10_000 + 500 * i + (300 if i % 3 else 0)) for i in range(71)]
        profits = [str(500 * i + (300 if i % 3 else 0)) for i in range(71)]
        window = {
            "accountValueHistory": [[t, v] for t, v in zip(times, values)],
            "pnlHistory": [[t, p] for t, p in zip(times, profits)],
        }
        self.portfolio_answer = [["allTime", window], ["perpAllTime", window]]
        self.fills = self._fills()

    def _fills(self) -> list[tuple[int, dict[str, object]]]:
        fills: list[tuple[int, dict[str, object]]] = []
        first_open = ms(NOW - timedelta(days=170))
        for trade in range(45):
            opened = first_open + trade * 3 * DAY_MS
            pnl = "40" if trade % 4 else "-20"
            closed = opened + 2 * DAY_MS
            fills.append((opened, self._fill(2 * trade, opened, "B", "0", "0")))
            fills.append((closed, self._fill(2 * trade + 1, closed, "A", "1", pnl)))
        return fills

    @staticmethod
    def _fill(tid: int, time: int, side: str, start: str, pnl: str) -> dict[str, object]:
        return {
            "coin": "ETH",
            "side": side,
            "time": time,
            "sz": "1",
            "px": "1000",
            "startPosition": start,
            "closedPnl": pnl,
            "fee": "0.5",
            "tid": tid,
        }

    async def portfolio(self, address: str) -> object:
        return self.portfolio_answer

    async def user_fills_by_time(self, address: str, *, start_time_ms: int) -> list[object]:
        return [fill for time, fill in self.fills if time >= start_time_ms]


async def test_evaluates_a_candidate_end_to_end():
    verdict = await evaluate(FakeExchange(), ADDRESS, Methodology(), now=NOW)

    assert verdict.selected, verdict.failed_checks
    assert verdict.style is Style.SWING
    assert verdict.confidence.round_trips == 45
    assert verdict.confidence.portfolio_points == 71
    assert verdict.methodology_version == "1"
