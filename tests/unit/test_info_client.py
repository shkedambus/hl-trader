import httpx
import pytest

from hl_trader.hl.info_client import InfoClient, RateLimitExhausted, RetryPolicy


def client_answering(
    statuses: list[int], body: object = None
) -> tuple[InfoClient, list[httpx.Request], list[float]]:
    requests: list[httpx.Request] = []
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(statuses[len(requests) - 1], json=body)

    async def record_sleep(seconds: float) -> None:
        delays.append(seconds)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return InfoClient(http, sleep=record_sleep), requests, delays


async def test_tc_n2_1_retries_on_429_with_growing_delay() -> None:
    client, requests, delays = client_answering([429, 429, 429, 200], body=[])

    assert await client.portfolio("0xa") == []
    assert len(requests) == 4
    assert delays == [1.0, 2.0, 4.0]
    assert delays == sorted(delays)


async def test_gives_up_after_the_last_attempt() -> None:
    client, _, delays = client_answering([429] * 5)

    with pytest.raises(RateLimitExhausted):
        await client.portfolio("0xa")
    assert len(delays) == RetryPolicy().max_attempts - 1
