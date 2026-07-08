"""
src/submission.py에 대한 단위 테스트.

실행: python tests/test_submission.py (프로젝트 루트에서)
실제 대회 sample_submission.csv 형식(2025-01-01 01:00 ~ 2026-01-01 00:00,
8,760행)을 흉내 낸 가짜 데이터로 테스트한다 (원본 data/ 파일은 건드리지 않음).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.metric import CAPACITY_KWH, TARGET_COLS
from src.submission import (
    N_SUBMISSION_ROWS,
    SUBMISSION_COLS,
    build_submission,
    save_submission,
    validate_submission,
)


def _make_fake_sample() -> pd.DataFrame:
    """실제 sample_submission.csv와 같은 형식(8,760행)의 가짜 템플릿을 만든다."""
    dtm = pd.date_range("2025-01-01 01:00:00", periods=N_SUBMISSION_ROWS, freq="h")
    return pd.DataFrame({
        "forecast_id": [f"forecast_{i+1:04d}" for i in range(N_SUBMISSION_ROWS)],
        "forecast_kst_dtm": dtm.strftime("%Y-%m-%d %H:%M:%S"),
        "kpx_group_1": 0,
        "kpx_group_2": 0,
        "kpx_group_3": 0,
    })


def test_build_submission_preserves_order_and_ids():
    """pred_df를 일부러 뒤섞어도, 결과는 sample_df의 시각 순서를 그대로 따라야 한다."""
    sample = _make_fake_sample()
    rng = np.random.default_rng(0)

    pred = pd.DataFrame({
        "forecast_kst_dtm": sample["forecast_kst_dtm"].sample(frac=1, random_state=1).values,
    })
    for col in TARGET_COLS:
        pred[col] = rng.uniform(0, CAPACITY_KWH[col], N_SUBMISSION_ROWS)

    result = build_submission(pred, dtm_col="forecast_kst_dtm", sample_df=sample)

    assert result.columns.tolist() == SUBMISSION_COLS
    assert len(result) == N_SUBMISSION_ROWS
    assert result["forecast_id"].tolist() == sample["forecast_id"].tolist(), "행 순서가 뒤섞였습니다"
    assert result["forecast_kst_dtm"].tolist() == sample["forecast_kst_dtm"].tolist()


def test_build_submission_clips_out_of_range_values():
    """음수/설비용량 초과 예측값은 build_submission이 자동으로 clip해야 한다."""
    sample = _make_fake_sample()
    pred = pd.DataFrame({"forecast_kst_dtm": sample["forecast_kst_dtm"]})
    pred["kpx_group_1"] = -100.0          # 음수
    pred["kpx_group_2"] = CAPACITY_KWH["kpx_group_2"] * 2  # 설비용량 초과
    pred["kpx_group_3"] = 500.0           # 정상 범위

    result = build_submission(pred, dtm_col="forecast_kst_dtm", sample_df=sample)

    assert (result["kpx_group_1"] >= 0).all()
    assert (result["kpx_group_2"] <= CAPACITY_KWH["kpx_group_2"]).all()
    assert (result["kpx_group_3"] == 500.0).all()


def test_validate_submission_passes_on_clean_file(tmp_path="."):
    """정상적으로 만든 제출 파일은 validate_submission을 통과해야 한다."""
    sample = _make_fake_sample()
    pred = pd.DataFrame({"forecast_kst_dtm": sample["forecast_kst_dtm"]})
    for col in TARGET_COLS:
        pred[col] = CAPACITY_KWH[col] * 0.3

    result = build_submission(pred, dtm_col="forecast_kst_dtm", sample_df=sample)
    out_path = Path(tmp_path) / "_test_submission_tmp.csv"
    save_submission(result, str(out_path))

    issues = validate_submission(str(out_path), sample_df=sample, raise_on_error=False)
    out_path.unlink()
    assert issues == [], f"정상 파일인데 검증 실패: {issues}"


def test_validate_submission_catches_wrong_row_count(tmp_path="."):
    """행 수가 8,760이 아니면 validate_submission이 문제로 잡아내야 한다."""
    sample = _make_fake_sample().iloc[:100].copy()  # 일부러 100행만 저장
    out_path = Path(tmp_path) / "_test_submission_bad.csv"
    sample[SUBMISSION_COLS].to_csv(out_path, index=False, encoding="utf-8-sig")

    issues = validate_submission(str(out_path), raise_on_error=False)
    out_path.unlink()
    assert any("행 수" in issue for issue in issues), f"행 수 오류를 잡아내지 못함: {issues}"


if __name__ == "__main__":
    test_build_submission_preserves_order_and_ids()
    test_build_submission_clips_out_of_range_values()
    test_validate_submission_passes_on_clean_file()
    test_validate_submission_catches_wrong_row_count()
    print("OK: test_submission.py 전체 통과")
