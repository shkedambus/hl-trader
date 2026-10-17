from __future__ import annotations

import httpx

from hl_trader.hl.parsing import (
    JsonObject,
    iter_json_objects,
    require_json_array,
    require_json_object,
)

DEFAULT_LEADERBOARD_URL = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"


class LeaderboardClient:
    """The public leaderboard dump: tens of megabytes, but outside the weighted info
    endpoint, so it costs no rate-limit budget (FR-1)."""

    def __init__(self, http: httpx.AsyncClient, url: str = DEFAULT_LEADERBOARD_URL) -> None:
        self._http = http
        self._url = url

    async def fetch_rows(self) -> list[JsonObject]:
        response = await self._http.get(self._url)
        response.raise_for_status()
        payload = require_json_object(response.json(), field="leaderboard response")
        rows = require_json_array(payload.get("leaderboardRows"), field="leaderboardRows")
        return list(iter_json_objects(rows))
