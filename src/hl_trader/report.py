"""Russian wording of verdicts for people to read."""

from __future__ import annotations

from collections.abc import Mapping

from hl_trader.domain.checks import Check, Criterion
from hl_trader.domain.verdict import Verdict

CRITERION_LABELS: Mapping[Criterion, str] = {
    Criterion.TENURE_DAYS: "стаж, дней",
    Criterion.ROUND_TRIPS: "завершенных сделок",
    Criterion.ACCOUNT_VALUE: "стоимость счета, $",
    Criterion.LIQUIDATED_SHARE: "доля ликвидированного объема",
    Criterion.MEDIAN_HOLD_S: "медианное удержание, с",
    Criterion.SCORE: "оценка",
    Criterion.CONFIDENCE: "уверенность",
}


def describe_check(check: Check) -> str:
    actual = "нет данных" if check.actual is None else _format_number(check.actual)
    label = CRITERION_LABELS[check.criterion]
    return f"{label}: {actual} при пороге {check.comparison} {_format_number(check.threshold)}"


def rejection_reasons(verdict: Verdict) -> list[str]:
    reasons = [describe_check(check) for check in verdict.failed_checks]
    if not verdict.followable_style:
        reasons.append(f"стиль {verdict.style}: сделки не повторить вручную")
    return reasons


def format_verdict_row(verdict: Verdict) -> str:
    status = "ОТОБРАН " if verdict.selected else "отклонен"
    reasons = rejection_reasons(verdict)
    return (
        f"{verdict.address}  {status}  оценка {verdict.score.value:.2f}"
        f"  уверенность {verdict.confidence.value:.2f}  {verdict.style:<12}"
        f" {reasons[0] if reasons else ''}"
    )


def _format_number(value: float) -> str:
    if abs(value) >= 1000:
        return f"{value:,.0f}".replace(",", " ")
    return f"{value:.4g}"
