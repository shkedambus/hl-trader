"""Client for the weighted HyperLiquid info endpoint.

Weights follow
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx
from aiolimiter import AsyncLimiter

from hl_trader.hl.parsing import as_json_array

DEFAULT_API_URL = "https://api.hyperliquid.xyz/info"
# The exchange allows 1200 per minute per IP; 100 stay in reserve for retries (NFR-2).
WEIGHT_BUDGET_PER_MIN = 1100
WEIGHT_PORTFOLIO = 20
WEIGHT_FILLS_BASE = 20
FILLS_PER_EXTRA_WEIGHT = 20
HTTP_TOO_MANY_REQUESTS = 429


class RateLimitExhausted(RuntimeError):
    def __init__(self, attempts: int) -> None:
        super().__init__(f"still rate limited after {attempts} attempts")
        self.attempts = attempts


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    first_delay_s: float = 1.0
    backoff_factor: float = 2.0

    def delay_before(self, attempt: int) -> float:
        return self.first_delay_s * self.backoff_factor ** (attempt - 1)


class InfoClient:
    """Every request takes its weight from one shared budget before it is sent.

    Fills cost extra weight that is known only from the answer, so the extra is taken
    from the budget afterwards and delays the next request instead.
    """

    def __init__(
        self,
        http: httpx.AsyncClient,
        *,
        url: str = DEFAULT_API_URL,
        limiter: AsyncLimiter | None = None,
        retry: RetryPolicy = RetryPolicy(),
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._http = http
        self._url = url
        self._limiter = limiter or AsyncLimiter(WEIGHT_BUDGET_PER_MIN, 60)
        self._retry = retry
        self._sleep = sleep

    async def portfolio(self, address: str) -> object:
        return await self._post({"type": "portfolio", "user": address}, WEIGHT_PORTFOLIO)

    async def user_fills_by_time(self, address: str, *, start_time_ms: int) -> list[object]:
        body = {
            "type": "userFillsByTime",
            "user": address,
            "startTime": start_time_ms,
            "aggregateByTime": True,
        }
        answer = as_json_array(await self._post(body, WEIGHT_FILLS_BASE)) or []
        extra = len(answer) // FILLS_PER_EXTRA_WEIGHT
        if extra:
            await self._limiter.acquire(extra)
        return answer

    async def _post(self, body: dict[str, object], weight: int) -> object:
        for attempt in range(1, self._retry.max_attempts + 1):
            await self._limiter.acquire(weight)
            response = await self._http.post(self._url, json=body)
            if response.status_code != HTTP_TOO_MANY_REQUESTS:
                response.raise_for_status()
                result: object = response.json()
                return result
            if attempt < self._retry.max_attempts:
                await self._sleep(self._retry.delay_before(attempt))
        raise RateLimitExhausted(self._retry.max_attempts)
