"""
src/metric.py에 대한 단위 테스트.

pytest 없이도 실행 가능하도록 순수 assert로 작성했다.
실행: python tests/test_metric.py (프로젝트 루트에서)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.metric import CAPACITY_KWH, TARGET_COLS, group_score, metric, metric_by_group


def _make_df(values: dict) -> pd.DataFrame:
    return pd.DataFrame(values)


def test_perfect_prediction_gives_score_1():
    """예측이 실제와 완전히 같으면 NMAE=0, FICR=1, total_score=1이어야 한다."""
    n = 100
    rng = np.random.default_rng(0)
    answer = _make_df({col: rng.uniform(CAPACITY_KWH[col] * 0.2, CAPACITY_KWH[col], n) for col in TARGET_COLS})
    pred = answer.copy()

    total_score, one_minus_nmae, ficr = metric(answer, pred)

    assert np.isclose(total_score, 1.0), f"완벽 예측인데 total_score={total_score}"
    assert np.isclose(one_minus_nmae, 1.0), f"완벽 예측인데 1-NMAE={one_minus_nmae}"
    assert np.isclose(ficr, 1.0), f"완벽 예측인데 FICR={ficr}"


def test_low_utilization_hours_are_excluded():
    """이용률 10% 미만 시간대는 예측이 완전히 틀려도 점수에 영향을 주면 안 된다."""
    col = "kpx_group_1"
    capacity = CAPACITY_KWH[col]
    other_cols = [c for c in TARGET_COLS if c != col]

    # 이용률 10% 미만(=0.05 * capacity)인 시간 1개 + 채점 대상 시간 1개
    answer = _make_df({
        col: [capacity * 0.05, capacity * 0.5],
        **{c: [CAPACITY_KWH[c] * 0.5, CAPACITY_KWH[c] * 0.5] for c in other_cols},
    })
    # 10% 미만 시간대는 완전히 틀리게, 채점 대상 시간대는 정확하게 예측
    pred = answer.copy()
    pred.loc[0, col] = 0.0

    _, one_minus_nmae, _ = metric(answer, pred)
    assert np.isclose(one_minus_nmae, 1.0), (
        "이용률 10% 미만 시간대의 오차가 점수에 반영되고 있습니다 (채점 제외 규칙 위반)"
    )


def test_ficr_step_function_bands():
    """오차율 6%/8% 경계에서 단가가 계단식(4 -> 3 -> 0)으로 바뀌는지 확인한다."""
    col = "kpx_group_1"
    capacity = CAPACITY_KWH[col]
    other_cols = [c for c in TARGET_COLS if c != col]
    actual_value = capacity * 0.5  # 이용률 50% (채점 대상)

    def ficr_for_error_rate(error_rate: float) -> float:
        answer = _make_df({
            col: [actual_value],
            **{c: [CAPACITY_KWH[c] * 0.5] for c in other_cols},
        })
        pred = answer.copy()
        pred.loc[0, col] = actual_value + capacity * error_rate
        by_group = metric_by_group(answer, pred)
        return by_group[col]["ficr"]

    assert np.isclose(ficr_for_error_rate(0.05), 1.0), "오차율 5%는 단가 4(만점) 구간이어야 한다"
    assert np.isclose(ficr_for_error_rate(0.07), 0.75), "오차율 7%는 단가 3(3/4점) 구간이어야 한다"
    assert np.isclose(ficr_for_error_rate(0.09), 0.0), "오차율 9%는 단가 0 구간이어야 한다"


def test_group_score_matches_metric_by_group():
    """group_score()가 metric_by_group()과 완전히 같은 nmae/ficr를 내는지 확인한다.

    group_score()는 교차검증에서 그룹 하나만 떼어 평가하려고 추가한 '입구'일 뿐이므로,
    기존 산식과 값이 한 자리도 달라선 안 된다.
    """
    n = 500
    rng = np.random.default_rng(7)
    answer = _make_df({col: rng.uniform(0, CAPACITY_KWH[col], n) for col in TARGET_COLS})
    pred = _make_df({col: answer[col] + rng.normal(0, CAPACITY_KWH[col] * 0.05, n) for col in TARGET_COLS})

    by_group = metric_by_group(answer, pred)
    for col in TARGET_COLS:
        _, nmae, ficr = group_score(answer[col].to_numpy(), pred[col].to_numpy(), CAPACITY_KWH[col])
        assert np.isclose(nmae, by_group[col]["nmae"]), f"{col} nmae 불일치"
        assert np.isclose(ficr, by_group[col]["ficr"]), f"{col} ficr 불일치"


def test_total_score_decomposes_into_group_mean():
    """대회 total_score = 그룹별 점수의 단순 평균, 이라는 항등식을 확인한다.

    이 항등식이 성립하기 때문에 '그룹별로 따로 하이퍼파라미터를 골라도
    전체 total_score를 정확히 최적화하는 것'이 된다 (05_tuning.ipynb의 전제).
    """
    n = 500
    rng = np.random.default_rng(11)
    answer = _make_df({col: rng.uniform(0, CAPACITY_KWH[col], n) for col in TARGET_COLS})
    pred = _make_df({col: answer[col] + rng.normal(0, CAPACITY_KWH[col] * 0.08, n) for col in TARGET_COLS})

    total_score, _, _ = metric(answer, pred)
    per_group = [group_score(answer[col].to_numpy(), pred[col].to_numpy(), CAPACITY_KWH[col])[0]
                 for col in TARGET_COLS]

    assert np.isclose(total_score, np.mean(per_group)), \
        f"total_score({total_score})가 그룹별 점수 평균({np.mean(per_group)})과 다릅니다"


def test_group_score_returns_nan_when_no_scored_hours():
    """채점 대상(이용률 10% 이상) 시간이 하나도 없으면 nan을 반환해야 한다.

    교차검증 폴드가 저풍속 구간에만 걸리는 경우를 대비한 방어 코드다.
    """
    cap = CAPACITY_KWH["kpx_group_1"]
    actual = np.full(10, cap * 0.05)      # 전부 이용률 5% -> 채점 대상 0개
    score, nmae, ficr = group_score(actual, actual, cap)
    assert np.isnan(score) and np.isnan(nmae) and np.isnan(ficr)


def test_group_score_ignores_nan_actuals():
    """actual이 NaN인 행(kpx_group_3의 2022년 등)은 자동으로 제외되어야 한다."""
    cap = CAPACITY_KWH["kpx_group_3"]
    actual = np.array([np.nan, cap * 0.5, np.nan, cap * 0.8])
    forecast = np.array([0.0, cap * 0.5, 0.0, cap * 0.8])   # NaN 행은 완전히 틀리게 예측
    score, nmae, ficr = group_score(actual, forecast, cap)
    assert np.isclose(nmae, 0.0) and np.isclose(ficr, 1.0), "NaN 행이 점수에 섞여 들어갔습니다"


if __name__ == "__main__":
    test_perfect_prediction_gives_score_1()
    test_low_utilization_hours_are_excluded()
    test_ficr_step_function_bands()
    test_group_score_matches_metric_by_group()
    test_total_score_decomposes_into_group_mean()
    test_group_score_returns_nan_when_no_scored_hours()
    test_group_score_ignores_nan_actuals()
    print("OK: test_metric.py 전체 통과")
