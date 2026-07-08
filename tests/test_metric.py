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

from src.metric import CAPACITY_KWH, TARGET_COLS, metric, metric_by_group


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


if __name__ == "__main__":
    test_perfect_prediction_gives_score_1()
    test_low_utilization_hours_are_excluded()
    test_ficr_step_function_bands()
    print("OK: test_metric.py 전체 통과")
