"""
대회 공식 평가 산식.

주의: 아래 metric() 함수의 계산 로직은 대회 규정에 명시된 산식 그대로이며,
한 글자도 수정하지 않는다. 노트북에서는 이 함수를 import해서 쓰고,
셀에 복사해서 쓰지 않는다 (CLAUDE.md 8번 규칙).

산식 요약 (자세한 설명은 CLAUDE.md 5번 섹션 참고):
    total_score = 0.5 * (1 - NMAE) + 0.5 * FICR

- NMAE(Normalized MAE, 정규화 절대오차): 시간별 |예측-실제| 오차를
  그룹 설비용량으로 나눈 값의 평균. 작을수록 좋다.
- FICR(Financial Impact Coverage Ratio, 정산금획득률): 오차율(=오차/설비용량)이
  6% 이내면 단가 4, 6~8%면 3, 8% 초과면 0으로 계산한 "정산금"을
  이론상 최대 정산금(오차 0일 때, 즉 항상 단가 4)으로 나눈 비율.
  실제 발전량(actual)으로 가중하므로, 발전량이 큰 시간대의 오차가 더 아프다.
- 채점 대상: 실제 발전량이 설비용량의 10% 이상인 시간대만 (저풍속 구간은 평가 제외).
"""

import numpy as np

# 예측 대상 3개 그룹 (CLAUDE.md 1번 섹션 참고)
TARGET_COLS = ["kpx_group_1", "kpx_group_2", "kpx_group_3"]

# 그룹별 설비용량 = 터빈 대수 x 정격출력을 1시간 기준 kWh로 환산한 값
# kpx_group_1/2: VESTAS V126 6기 x 3.6MW = 21.6MW -> 21,600 kWh
# kpx_group_3  : UNISON U136 5기 x 4.2MW = 21.0MW -> 21,000 kWh
CAPACITY_KWH = {"kpx_group_1": 21600, "kpx_group_2": 21600, "kpx_group_3": 21000}


def metric(answer_df, pred_df):
    """
    대회 공식 산식으로 점수를 계산한다.

    입력:
        answer_df: 정답(실제 발전량) DataFrame. TARGET_COLS 3개 컬럼(kWh)을 포함해야 함.
        pred_df  : 예측값 DataFrame. answer_df와 같은 행 순서(같은 시각)로
                   정렬되어 있어야 함. TARGET_COLS 3개 컬럼(kWh)을 포함해야 함.

    출력:
        (total_score, one_minus_nmae, ficr) 튜플.
        - total_score   : 최종 점수 (0~1, 클수록 좋음). 대회 순위 지표.
        - one_minus_nmae: 1 - NMAE (3개 그룹 평균). 값이 클수록 오차가 작다는 뜻.
        - ficr          : 정산금획득률 (3개 그룹 평균). 값이 클수록 좋음.

    주의:
        - answer_df와 pred_df는 반드시 같은 시각 순서로 정렬되어 있어야 한다
          (이 함수는 인덱스/시각을 다시 맞추지 않고 순서 그대로 비교한다).
        - 이 함수 자체는 test 기간 데이터를 다루지 않으므로 누수(4번 규칙)와 무관하다.
          누수 여부는 pred_df를 만드는 학습·추론 파이프라인에서 관리해야 한다.
    """
    group_nmae, group_ficr = [], []
    for col in TARGET_COLS:
        actual = answer_df[col].to_numpy(dtype=float)
        forecast = pred_df[col].to_numpy(dtype=float)
        capacity = CAPACITY_KWH[col]
        valid = actual >= capacity * 0.10          # 이용률 10% 이상 시간대만 평가
        actual, forecast = actual[valid], forecast[valid]
        error_rate = np.abs(forecast - actual) / capacity
        group_nmae.append(np.mean(error_rate))
        unit_price = np.select([error_rate <= 0.06, error_rate <= 0.08], [4.0, 3.0], default=0.0)
        group_ficr.append(np.sum(actual * unit_price) / np.sum(actual * 4.0))
    one_minus_nmae = 1 - np.mean(group_nmae)
    ficr = np.mean(group_ficr)
    return 0.5 * one_minus_nmae + 0.5 * ficr, one_minus_nmae, ficr


def metric_by_group(answer_df, pred_df):
    """
    그룹별로 분해된 NMAE/FICR을 반환한다 (실험 로그의 "그룹별 지표" 컬럼용, CLAUDE.md 5번).

    metric()과 완전히 같은 계산을 하되, 3개 그룹 평균을 내기 전 단계의
    그룹별 리스트를 그대로 돌려준다는 점만 다르다. 산식 자체는 metric()과 동일.

    출력:
        dict: {"kpx_group_1": {"nmae": ..., "ficr": ...}, ...}
    """
    result = {}
    for col in TARGET_COLS:
        actual = answer_df[col].to_numpy(dtype=float)
        forecast = pred_df[col].to_numpy(dtype=float)
        capacity = CAPACITY_KWH[col]
        valid = actual >= capacity * 0.10
        actual, forecast = actual[valid], forecast[valid]
        error_rate = np.abs(forecast - actual) / capacity
        nmae = np.mean(error_rate)
        unit_price = np.select([error_rate <= 0.06, error_rate <= 0.08], [4.0, 3.0], default=0.0)
        ficr = np.sum(actual * unit_price) / np.sum(actual * 4.0)
        result[col] = {"nmae": nmae, "ficr": ficr}
    return result


def group_score(actual, forecast, capacity):
    """
    한 그룹만 떼어 내서 그 그룹의 점수를 계산한다 (교차검증 폴드 평가용).

    왜 이 함수가 필요한가:
        metric()은 3개 그룹을 한꺼번에 받도록 되어 있다. 그런데 교차검증에서는
        그룹마다 학습 가능한 기간이 다르고(kpx_group_3는 2023년부터), 폴드도 달라진다.
        그래서 "그룹 하나 + 그 그룹의 예측"만으로 점수를 낼 수 있어야 한다.

    이렇게 해도 되는 이유 (산식에서 유도한 항등식):
        total_score = 0.5*(1 - mean_g NMAE_g) + 0.5*(mean_g FICR_g)
                    = mean_g [ 0.5*(1 - NMAE_g) + 0.5*FICR_g ]
        즉 대회 점수는 '그룹별 점수의 단순 평균'으로 정확히 분해된다.
        따라서 그룹별로 따로 하이퍼파라미터를 골라 각 그룹 점수를 최대화하면
        전체 total_score도 최대가 된다. (그룹 간 상호작용이 없다.)

    입력:
        actual   : 그 그룹의 실제 발전량 배열 [kWh]. NaN이 섞여 있어도 된다(자동 제외).
        forecast : 같은 길이의 예측값 배열 [kWh].
        capacity : 그 그룹의 설비용량 [kWh/h]. 예: 21600.

    출력:
        (score, nmae, ficr) 튜플.
        - score = 0.5*(1 - nmae) + 0.5*ficr  (그 그룹의 total_score 기여분)
        - 채점 대상(actual >= capacity*0.10)이 하나도 없으면 (nan, nan, nan)을 반환한다.

    주의:
        metric()의 계산 로직과 완전히 동일하다(그룹 루프 안의 내용을 그대로 옮긴 것).
        산식을 바꾼 것이 아니라 '한 그룹만 계산하는 입구'를 추가한 것이다.
        tests/test_metric.py에서 metric_by_group()과 값이 일치하는지 검증한다.
    """
    actual = np.asarray(actual, dtype=float)
    forecast = np.asarray(forecast, dtype=float)

    valid = actual >= capacity * 0.10          # 이용률 10% 이상 시간대만 평가 (NaN은 False가 되어 자동 제외)
    if not np.any(valid):
        return float("nan"), float("nan"), float("nan")

    actual, forecast = actual[valid], forecast[valid]
    error_rate = np.abs(forecast - actual) / capacity
    nmae = np.mean(error_rate)
    unit_price = np.select([error_rate <= 0.06, error_rate <= 0.08], [4.0, 3.0], default=0.0)
    ficr = np.sum(actual * unit_price) / np.sum(actual * 4.0)
    return 0.5 * (1.0 - nmae) + 0.5 * ficr, nmae, ficr
