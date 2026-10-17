from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

JsonObject = Mapping[str, object]

ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]{40}")


def normalize_address(value: object) -> str | None:
    if not isinstance(value, str) or not ADDRESS_RE.fullmatch(value):
        return None
    return value.lower()


def from_epoch_ms(timestamp_ms: int) -> datetime:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def to_epoch_ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def as_float(value: object) -> float | None:
    """HyperLiquid sends most numbers as strings."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def as_int(value: object) -> int | None:
    # bool is an int subclass, and True is not a timestamp.
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def as_decimal(value: object) -> Decimal | None:
    """Parse via str, so binary float rounding never enters a position size."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def as_json_array(value: object) -> list[object] | None:
    return value if isinstance(value, list) else None


def as_json_pair(value: object) -> tuple[object, object] | None:
    """Split a `[key, payload]` array, the shape HyperLiquid uses in place of an object."""
    array = as_json_array(value)
    if array is None or len(array) != 2:
        return None
    return array[0], array[1]


def as_json_object(value: object) -> JsonObject | None:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        return None
    return value


def require_json_array(value: object, *, field: str) -> list[object]:
    array = as_json_array(value)
    if array is None:
        raise ValueError(f"{field} must be an array")
    return array


def require_json_object(value: object, *, field: str) -> JsonObject:
    json_object = as_json_object(value)
    if json_object is None:
        raise ValueError(f"{field} must be an object")
    return json_object


def iter_json_objects(values: Iterable[object]) -> Iterator[JsonObject]:
    for value in values:
        json_object = as_json_object(value)
        if json_object is not None:
            yield json_object
