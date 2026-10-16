from __future__ import annotations

from datetime import datetime, timedelta
from typing import Protocol

from hl_trader.domain.methodology import Methodology
from hl_trader.domain.metrics import TraderMetrics
from hl_trader.domain.portfolio import build_portfolio_metrics
from hl_trader.domain.round_trips import reconstruct_round_trips
from hl_trader.domain.trade_metrics import build_trade_metrics
from hl_trader.domain.verdict import Verdict, judge
from hl_trader.hl.parsing import to_epoch_ms
from hl_trader.ingest.fills import FillsFetcher, fetch_fills
from hl_trader.ingest.portfolio import parse_account_history

DEFAULT_MAX_FILL_PAGES = 5


class EvaluationClient(FillsFetcher, Protocol):
    async def portfolio(self, address: str) -> object: ...


async def collect_metrics(
    client: EvaluationClient,
    address: str,
    *,
    window_days: float,
    now: datetime,
    max_fill_pages: int = DEFAULT_MAX_FILL_PAGES,
) -> TraderMetrics:
    history = parse_account_history(await client.portfolio(address))
    page = await fetch_fills(
        client,
        address,
        start_time_ms=to_epoch_ms(now - timedelta(days=window_days)),
        max_pages=max_fill_pages,
    )
    return TraderMetrics(
        portfolio=build_portfolio_metrics(history, now=now, window_days=window_days),
        trades=build_trade_metrics(
            reconstruct_round_trips(page.fills),
            fills_count=len(page.fills),
            fills_truncated=page.truncated,
            window_days=window_days,
        ),
    )


async def evaluate(
    client: EvaluationClient, address: str, methodology: Methodology, *, now: datetime
) -> Verdict:
    metrics = await collect_metrics(
        client, address, window_days=methodology.selection.window_days, now=now
    )
    return judge(address, metrics, methodology)
