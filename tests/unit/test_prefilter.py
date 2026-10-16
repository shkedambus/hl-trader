from hl_trader.domain.methodology import Prefilter
from hl_trader.domain.prefilter import LeaderboardEntry, WindowPerformance, select_candidates
from hl_trader.hl.parsing import JsonObject
from hl_trader.ingest.leaderboard import parse_entries


def entry(address: str, *, value: float, pnl: float, roi: float, volume: float) -> LeaderboardEntry:
    all_time = WindowPerformance(pnl=pnl, roi=roi, volume=volume)
    return LeaderboardEntry(address=address, account_value=value, all_time=all_time)


def test_tc_1_1_screens_out_violators_and_orders_by_priority() -> None:
    entries = [
        entry("0xa", value=50_000, pnl=40_000, roi=0.5, volume=5_000_000),
        entry("0xb", value=5_000, pnl=40_000, roi=0.5, volume=5_000_000),
        entry("0xc", value=80_000, pnl=900_000, roi=1.2, volume=90_000_000),
        entry("0xd", value=30_000, pnl=100_000, roi=0.3, volume=2_000_000),
        entry("0xe", value=60_000, pnl=1_000, roi=0.4, volume=10_000_000),
    ]

    candidates = select_candidates(entries, Prefilter())

    assert [candidate.address for candidate in candidates] == ["0xc", "0xa", "0xd"]


def test_parse_entries_skips_rows_without_all_time_window() -> None:
    rows: list[JsonObject] = [
        {
            "ethAddress": "0x" + "AB" * 20,
            "accountValue": "12000.5",
            "windowPerformances": [["allTime", {"pnl": "100", "roi": "0.3", "vlm": "2000000"}]],
        },
        {"ethAddress": "0x" + "cd" * 20, "accountValue": "1", "windowPerformances": []},
        {"ethAddress": "not-an-address", "accountValue": "1"},
    ]

    entries = parse_entries(rows)

    assert [e.address for e in entries] == ["0x" + "ab" * 20]
    assert entries[0].all_time.volume == 2_000_000
