"""FR-7: the verdict on one trader and the choice of whom to track."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from hl_trader.domain.checks import Check, Comparison, Criterion
from hl_trader.domain.methodology import Methodology
from hl_trader.domain.metrics import TraderMetrics
from hl_trader.domain.scoring import (
    ConfidenceBreakdown,
    Score,
    check_filters,
    compute_confidence,
    compute_score,
)
from hl_trader.domain.style import FOLLOWABLE_STYLES, Style, classify_style


@dataclass(frozen=True)
class Verdict:
    address: str
    methodology_version: str
    score: Score
    confidence: ConfidenceBreakdown
    style: Style
    checks: tuple[Check, ...]

    @property
    def failed_checks(self) -> tuple[Check, ...]:
        return tuple(check for check in self.checks if not check.passed)

    @property
    def followable_style(self) -> bool:
        return self.style in FOLLOWABLE_STYLES

    @property
    def selected(self) -> bool:
        return self.followable_style and not self.failed_checks


def judge(address: str, metrics: TraderMetrics, methodology: Methodology) -> Verdict:
    score = compute_score(metrics, methodology.score_terms)
    confidence = compute_confidence(metrics, methodology.confidence)
    selection = methodology.selection
    checks = (
        *check_filters(metrics, methodology.filters),
        Check(Criterion.SCORE, score.value, Comparison.AT_LEAST, selection.min_score),
        Check(
            Criterion.CONFIDENCE, confidence.value, Comparison.AT_LEAST, selection.min_confidence
        ),
    )
    return Verdict(
        address=address,
        methodology_version=methodology.version,
        score=score,
        confidence=confidence,
        style=classify_style(metrics.trades, methodology.styles),
        checks=checks,
    )


def pick_tracked(verdicts: Iterable[Verdict], limit: int) -> list[Verdict]:
    selected = [verdict for verdict in verdicts if verdict.selected]
    selected.sort(key=lambda verdict: (-verdict.score.value, verdict.address))
    return selected[:limit]
