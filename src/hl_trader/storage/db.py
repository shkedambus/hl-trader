from __future__ import annotations

from importlib import resources

import psycopg


def apply_schema(database_url: str) -> None:
    ddl = resources.files("hl_trader.storage").joinpath("schema.sql").read_text()
    with psycopg.connect(database_url) as connection:
        connection.execute(ddl)
