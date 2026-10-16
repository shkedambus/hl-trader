from __future__ import annotations

from decimal import Decimal

# Sizes and prices stay Decimal end to end, so their zero has to be a Decimal too.
ZERO = Decimal(0)

SECONDS_PER_HOUR = 3600.0
SECONDS_PER_DAY = 24 * SECONDS_PER_HOUR

METRIC_DECIMALS = 6


def clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def round_metric(value: float) -> float:
    return round(value, METRIC_DECIMALS)
