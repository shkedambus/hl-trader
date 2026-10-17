import pytest

from hl_trader.domain.checks import Criterion
from hl_trader.domain.methodology import Methodology
from hl_trader.domain.metrics import ScoredMetric
from hl_trader.domain.numbers import SECONDS_PER_DAY, SECONDS_PER_HOUR
from hl_trader.domain.scoring import compute_confidence, compute_score
from hl_trader.domain.style import Style, classify_style
from hl_trader.domain.verdict import Verdict, judge, pick_tracked
from hl_trader.report import describe_check, rejection_reasons
from tests.unit.factories import strong_trader, with_portfolio

METHODOLOGY = Methodology()


def failed_criteria(verdict: Verdict) -> list[Criterion]:
    return [check.criterion for check in verdict.failed_checks]


def test_strong_trader_is_selected() -> None:
    verdict = judge("0xa", strong_trader(), METHODOLOGY)

    assert verdict.selected, rejection_reasons(verdict)
    assert verdict.style is Style.SWING


def test_tc_3_1_short_tenure_rejects_with_actual_value_and_threshold() -> None:
    verdict = judge("0xa", with_portfolio(strong_trader(), tenure_days=60.0), METHODOLOGY)

    assert not verdict.selected
    assert failed_criteria(verdict) == [Criterion.TENURE_DAYS]
    assert rejection_reasons(verdict) == ["стаж, дней: 60 при пороге >= 90"]


def test_tc_3_2_liquidations_reject_even_the_best_metrics() -> None:
    best = with_portfolio(
        strong_trader(win_rate=0.9, profit_factor=5.0, expectancy_pct=0.1, liquidated_share=0.08),
        sharpe=4.0,
        max_drawdown=0.0,
        tenure_days=800.0,
    )
    verdict = judge("0xa", best, METHODOLOGY)

    assert not verdict.selected
    assert verdict.score.value == 1.0
    assert failed_criteria(verdict) == [Criterion.LIQUIDATED_SHARE]


def test_tc_4_1_score_matches_manual_calculation_and_contributions_add_up() -> None:
    result = compute_score(strong_trader(), METHODOLOGY.score_terms)

    manual = (
        0.30 * (1.5 / 2.0)
        + 0.20 * ((2.0 - 1.0) / 1.5)
        + 0.15 * ((0.6 - 0.4) / 0.3)
        + 0.15 * ((0.5 - 0.15) / 0.5)
        + 0.10 * (0.03 / 0.05)
        + 0.10 * ((400 - 90) / 640)
    )
    assert result.value == pytest.approx(manual, abs=1e-6)
    assert sum(result.contributions.values()) == pytest.approx(result.value, abs=1e-6)


def test_tc_4_2_unmeasured_metric_drops_out_and_weights_renormalise() -> None:
    result = compute_score(with_portfolio(strong_trader(), sharpe=None), METHODOLOGY.score_terms)

    assert result.unmeasured == (ScoredMetric.SHARPE,)
    assert ScoredMetric.SHARPE not in result.contributions
    assert sum(result.contributions.values()) == pytest.approx(result.value, abs=1e-6)
    full = compute_score(strong_trader(), METHODOLOGY.score_terms).contributions
    rest = sum(value for metric, value in full.items() if metric is not ScoredMetric.SHARPE)
    assert result.value == pytest.approx(rest / 0.70, abs=1e-6)


def test_tc_4_3_score_does_not_depend_on_other_traders() -> None:
    reference = judge("0xref", strong_trader(), METHODOLOGY).score.value
    for i in range(500):
        judge(f"0x{i}", with_portfolio(strong_trader(), sharpe=i / 100), METHODOLOGY)

    assert judge("0xref", strong_trader(), METHODOLOGY).score.value == reference


def test_tc_5_1_confidence_grows_with_trades_and_score_stays_the_same() -> None:
    traders = [strong_trader(round_trips=n) for n in (10, 20, 40)]
    confidences = [compute_confidence(t, METHODOLOGY.confidence).value for t in traders]
    scores = {compute_score(t, METHODOLOGY.score_terms).value for t in traders}

    assert confidences == sorted(confidences)
    assert len(scores) == 1


def test_tc_5_2_incomplete_fill_history_halves_confidence() -> None:
    complete = compute_confidence(strong_trader(round_trips=20), METHODOLOGY.confidence)
    truncated = compute_confidence(
        strong_trader(round_trips=20, fills_truncated=True), METHODOLOGY.confidence
    )

    assert truncated.value == pytest.approx(complete.value / 2)
    assert truncated.history_complete is False


@pytest.mark.parametrize(
    ("median_hold_s", "fills_per_day", "style"),
    [
        (2 * 60, 250.0, Style.MARKET_MAKER),
        (10 * 60, 50.0, Style.HFT),
        (3 * SECONDS_PER_HOUR, 10.0, Style.INTRADAY),
        (2 * SECONDS_PER_DAY, 2.0, Style.SWING),
        (10 * SECONDS_PER_DAY, 0.5, Style.POSITION),
    ],
)
def test_tc_6_1_style_by_median_hold(
    median_hold_s: int, fills_per_day: float, style: Style
) -> None:
    trades = strong_trader(median_hold_s=median_hold_s, fills_per_day=fills_per_day).trades

    assert classify_style(trades, METHODOLOGY.styles) is style


def test_tc_7_1_low_confidence_rejects_an_otherwise_selected_trader() -> None:
    weak_evidence = with_portfolio(strong_trader(round_trips=15), points=47)
    verdict = judge("0xa", weak_evidence, METHODOLOGY)

    assert verdict.confidence.value == pytest.approx(0.29, abs=0.01)
    assert not verdict.selected
    assert failed_criteria(verdict) == [Criterion.CONFIDENCE]


def test_tc_7_2_hft_is_never_selected_and_tracking_keeps_top_n() -> None:
    hft = judge("0xhft", strong_trader(median_hold_s=10 * 60), METHODOLOGY)
    assert hft.style is Style.HFT
    assert not hft.selected

    verdicts = [
        judge(f"0x{i:02d}", with_portfolio(strong_trader(), sharpe=1.0 + i / 100), METHODOLOGY)
        for i in range(70)
    ]
    tracked = pick_tracked(verdicts, limit=60)

    assert len(tracked) == 60
    assert {v.address for v in tracked} == {f"0x{i:02d}" for i in range(10, 70)}


def test_check_wording_shows_large_numbers_without_exponent() -> None:
    verdict = judge("0xa", with_portfolio(strong_trader(), account_value=5_000.0), METHODOLOGY)

    assert describe_check(verdict.failed_checks[0]) == (
        "стоимость счета, $: 5 000 при пороге >= 10 000"
    )
