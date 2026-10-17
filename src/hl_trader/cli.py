from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

import httpx

from hl_trader.domain.methodology import Methodology
from hl_trader.domain.prefilter import select_candidates
from hl_trader.domain.verdict import Verdict, pick_tracked
from hl_trader.hl.info_client import InfoClient
from hl_trader.hl.leaderboard import LeaderboardClient
from hl_trader.ingest.leaderboard import parse_entries
from hl_trader.pipeline import evaluate
from hl_trader.report import format_verdict_row
from hl_trader.storage.db import apply_schema

HTTP_TIMEOUT_S = 60.0


async def scan(top: int) -> None:
    methodology = Methodology()
    now = datetime.now(timezone.utc)
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S) as http:
        rows = await LeaderboardClient(http).fetch_rows()
        entries = parse_entries(rows)
        candidates = select_candidates(entries, methodology.prefilter)
        print(f"рейтинг: {len(entries)} аккаунтов, после отсева: {len(candidates)} кандидатов")
        client = InfoClient(http)
        verdicts: list[Verdict] = []
        for candidate in candidates[:top]:
            verdict = await evaluate(client, candidate.address, methodology, now=now)
            verdicts.append(verdict)
            print(format_verdict_row(verdict))
    tracked = pick_tracked(verdicts, methodology.selection.tracked_limit)
    print(f"отобрано: {len(tracked)} из {len(verdicts)} оцененных")


def main() -> None:
    parser = argparse.ArgumentParser(prog="hl-trader")
    commands = parser.add_subparsers(dest="command", required=True)
    scan_parser = commands.add_parser("scan", help="отсев по рейтингу и оценка лучших кандидатов")
    scan_parser.add_argument("--top", type=int, default=10, help="сколько кандидатов оценить")
    commands.add_parser("db-init", help="создать таблицы в DATABASE_URL")
    args = parser.parse_args()

    if args.command == "scan":
        asyncio.run(scan(args.top))
    elif args.command == "db-init":
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            sys.exit("DATABASE_URL не задан")
        apply_schema(database_url)
        print("схема применена")
