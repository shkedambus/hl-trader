"""FR-1: screen the leaderboard before any request that costs rate-limit weight."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

from hl_trader.domain.methodology import Prefilter
from hl_trader.domain.numbers import clip01


@dataclass(frozen=True)
class WindowPerformance:
    pnl: float
    roi: float
    volume: float


@dataclass(frozen=True)
class LeaderboardEntry:
    address: str
    account_value: float
    all_time: WindowPerformance


@dataclass(frozen=True)
class Candidate:
    entry: LeaderboardEntry
    priority: float

    @property
    def address(self) -> str:
        return self.entry.address


def edge_ratio(entry: LeaderboardEntry) -> float:
    """Profit per dollar traded over the account's whole life."""
    if entry.all_time.volume <= 0:
        return 0.0
    return entry.all_time.pnl / entry.all_time.volume


def passes_prefilter(entry: LeaderboardEntry, thresholds: Prefilter) -> bool:
    all_time = entry.all_time
    return (
        entry.account_value >= thresholds.min_account_value
        and all_time.pnl > 0
        and all_time.roi > thresholds.min_roi_all_time
        and all_time.volume >= thresholds.min_volume_all_time
        and edge_ratio(entry) >= thresholds.min_edge_ratio
    )


def queue_priority(entry: LeaderboardEntry, thresholds: Prefilter) -> float:
    """Order in which candidates get the paid requests, not a quality estimate.

    Leaderboard figures cannot tell skill from one lucky leveraged bet; they only show
    who is profitable enough, with enough volume, to be worth the budget first.
    """
    return clip01(entry.all_time.roi / thresholds.roi_reference) * _volume_factor(
        entry.all_time.volume, thresholds.volume_reference
    )


def select_candidates(
    entries: Iterable[LeaderboardEntry], thresholds: Prefilter
) -> list[Candidate]:
    candidates = [
        Candidate(entry=entry, priority=queue_priority(entry, thresholds))
        for entry in entries
        if passes_prefilter(entry, thresholds)
    ]
    # Many accounts hit the priority ceiling; among them the larger profit goes first.
    candidates.sort(
        key=lambda candidate: (
            -candidate.priority,
            -candidate.entry.all_time.pnl,
            candidate.address,
        )
    )
    return candidates


def _volume_factor(volume: float, reference: float) -> float:
    # Volume spans orders of magnitude: $1M -> $10M should count as much as $10M -> $100M.
    if volume <= 0 or reference <= 1:
        return 0.0
    return clip01(math.log10(volume) / math.log10(reference))
