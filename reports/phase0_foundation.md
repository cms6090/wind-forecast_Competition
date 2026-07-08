# Phase 0-1. 평가 산식·제출 검증 코드 작성

## 1. 왜 (Why) — 이유와 근거

CLAUDE.md 11번 섹션(작업 워크플로우)에 따르면 Phase 0(기반 작업)은 모든 뒤 단계의 전제이며,
그중에서도 `src/metric.py`(대회 산식)와 `src/submission.py`(`validate_submission()`)는
**대회 규정 원문 그대로** 구현해야 하는, 틀리면 대회 전체를 망치는 코드다 (CLAUDE.md 8번:
"처음부터 .py로 작성하는 두 가지 예외").

이 코드를 가장 먼저 만드는 이유:
- 앞으로 모든 실험(피처, 모델, 튜닝)의 성공/실패 판단 기준이 이 산식이다. 산식이 틀리면
  이후 모든 실험 로그의 `total_score`가 의미 없어진다.
- 제출 파일 실수(컬럼 순서, 행 수, 시각 형식, 음수·초과값)는 하루 5회뿐인 제출 기회를
  낭비시키므로, 사람이 눈으로 확인하는 대신 자동 검증 함수로 강제한다 (CLAUDE.md 7번).

## 2. 어떻게 (How) — 과정

### 2-1. 실제 데이터 구조 확인 (경로 재확인)
CLAUDE.md는 `data/`가 플랫 구조(`data/ldaps_train.csv` 등)일 것으로 가정했지만,
실제로는 `data/train/`, `data/test/` 하위 폴더로 나뉘어 있었다.
- `data/train/`: `gfs_train.csv`, `ldaps_train.csv`, `scada_unison_train.csv`, `scada_vestas_train.csv`, `train_labels.csv`
- `data/test/`: `gfs_test.csv`, `ldaps_test.csv`
- `data/`: `sample_submission.csv`, `info.xlsx`, `data_description.md`

이 차이를 기록해두는 이유: 앞으로 `01_preprocessing.ipynb`에서 `DATA_DIR`을 하드코딩할 때
이 실제 경로(`data/train/`, `data/test/`)를 기준으로 삼아야 한다 (CLAUDE.md 2번 규칙).

`sample_submission.csv`를 읽어 확인한 결과: 8,760행, 컬럼 `forecast_id, forecast_kst_dtm,
kpx_group_1, kpx_group_2, kpx_group_3` (예측값은 전부 0으로 채워진 템플릿).

`train_labels.csv`를 읽어 확인한 결과: 26,304행(2022-01-01 01:00 ~ 2025-01-01 00:00,
3년치 시간 수), `kpx_group_3`은 결측이 8,766개로 2022년 한 해 전체(8,760시간)에 해당하는
빈칸 + 추가로 몇 개의 산발적 결측이 있음을 확인했다 (CLAUDE.md 8번 "라벨 결측 처리" 규칙과 일치).

### 2-2. `src/metric.py` 작성
CLAUDE.md 5번 섹션에 명시된 산식을 **한 글자도 바꾸지 않고** 그대로 옮겼다.
- `TARGET_COLS`, `CAPACITY_KWH`: 매직 넘버(21600, 21000)를 상수로 분리하고 출처(터빈 대수 x
  정격출력)를 주석으로 남겼다 (CLAUDE.md 8번 매직 넘버 금지 규칙).
- `metric(answer_df, pred_df)`: 산식 그대로. docstring에 입력(같은 시각 순서로 정렬된
  DataFrame이어야 함)과 출력(total_score, 1-NMAE, FICR)을 명시했다.
- `metric_by_group(answer_df, pred_df)`: 산식 자체는 그대로 두고, 3개 그룹 평균을 내기 전
  단계의 그룹별 NMAE/FICR을 딕셔너리로 돌려주는 **추가** 함수. CLAUDE.md 5번 실험 로그 규칙이
  "그룹별 분해 지표를 반드시 남긴다"고 요구하기 때문에 필요했다. ("자체 지표를 추가로 만들어도
  되지만 산식 자체는 건드리지 않는다"는 CLAUDE.md 명시 허용 범위 내의 추가.)

### 2-3. `src/submission.py` 작성
CLAUDE.md 7번 체크리스트를 그대로 함수로 옮겼다.
- `build_submission(pred_df, dtm_col, sample_df)`: 예측값을 `sample_submission` 형식에
  병합한다. **판단**: 시각 매칭은 "행 순서가 같다"고 가정하지 않고, `pd.to_datetime`으로
  파싱한 뒤 값으로 merge한다 (문자열 비교나 위치 기반 결합은 pred_df가 다른 순서로 정렬돼
  있을 때 조용히 틀린 값을 붙이는 사고로 이어지므로 배제). 병합 후 결측이 하나라도 있으면
  즉시 `ValueError`를 던져 실수를 조기에 드러낸다. `forecast_id`/`forecast_kst_dtm`은
  sample_df의 원본 문자열을 그대로 보존한다(다시 포맷팅하지 않음 — 시각 형식 손상 방지).
  마지막에 `clip(0, capacity)`로 음수·설비용량 초과값을 제거한다 (CLAUDE.md 5번 후처리 기본기).
  - **판단**: `sample_submission.csv` 경로를 함수 안에 하드코딩하지 않고, 이미 로딩된
    `sample_df`를 인자로 받게 했다. 경로 상수는 노트북/`src/config.py`에서 관리하라는
    CLAUDE.md 2번 규칙을 지키기 위함.
- `save_submission(submission_df, out_path)`: `utf-8-sig` 인코딩 + `index=False` 저장만
  담당하는 아주 얇은 함수. 저장 로직을 한 곳에 모아 인코딩 실수를 원천 차단하기 위해 분리했다.
- `validate_submission(path, sample_df=None, raise_on_error=True)`: CLAUDE.md 7번 체크리스트
  7개 항목(컬럼 순서, 행 수 8,760, 시각 형식 정규식, id 컬럼 일치, 결측·음수·용량초과)을
  전부 검사한다. 기본값은 `raise_on_error=True`로, 문제가 있으면 노트북 셀 실행이 즉시
  멈추도록 했다 — "제출 파일 생성 직후 반드시 실행" 규칙을 사람이 결과를 눈으로 훑어보지
  않아도 강제하기 위함.

### 2-4. 단위 테스트 (`tests/test_metric.py`, `tests/test_submission.py`)
pytest가 아직 설치돼 있지 않아(venv가 비어 있었음) 순수 `assert` 기반으로 작성해
`python tests/test_metric.py` 형태로 바로 실행 가능하게 했다.

- `test_metric.py`:
  1. 예측이 실제와 완전히 같으면 `total_score = 1-NMAE = FICR = 1.0`인지 확인
  2. 이용률 10% 미만 시간대는 완전히 틀려도 점수에 전혀 영향을 주지 않는지 확인
     (산식의 "채점 제외" 조건이 실제로 작동하는지 검증 — 이 부분을 틀리면 저풍속 구간
     오차까지 점수에 반영돼 실제보다 낮은 점수가 나올 수 있다)
  3. FICR의 계단 구조(오차율 5%→단가4, 7%→단가3, 9%→단가0)가 정확한 경계에서
     바뀌는지 확인 (CLAUDE.md 5번 "FICR은 계단식이다" 설명을 코드로 검증)
- `test_submission.py`:
  1. `pred_df`를 일부러 무작위로 섞어도 `build_submission`이 `sample_df`의 시각 순서를
     정확히 복원하는지 확인 (병합 로직의 핵심 위험 지점)
  2. 음수/설비용량 초과 입력이 clip되는지 확인
  3. 정상 파일이 `validate_submission`을 통과하는지 확인
  4. 행 수가 틀린 파일을 `validate_submission`이 실제로 잡아내는지 확인

**venv 환경 준비**: `venv/`에 `pip`만 있고 numpy/pandas가 없었어서 `numpy==2.5.1`,
`pandas==3.0.3`을 설치했다. 이후 패키지가 추가될 때마다 `requirements.txt`를 갱신한다
(CLAUDE.md 12-3번 규칙).

**검증한 것**:
- `venv/Scripts/python.exe tests/test_metric.py`, `tests/test_submission.py` 둘 다
  예외 없이 통과 (종료 코드 0).
- 가짜 데이터가 아니라 실제 `data/sample_submission.csv`로도 스모크 테스트를 돌려
  `build_submission` → `save_submission` → `validate_submission` 전체 흐름이
  문제(issues) 없이 통과하는 것을 확인했다 (테스트 후 생성 파일은 삭제함, 실제
  제출용 파일이 아니므로 `submissions/`에 남기지 않았다).

### 시도했다가 버린 방법
- `validate_submission`이 파일 경로 안에서 `sample_submission.csv`를 직접 읽게 하는
  방법도 고려했으나, 경로를 함수 내부에 하드코딩하게 돼 CLAUDE.md 2번 규칙(경로는 노트북/
  config에서 상수화)에 어긋나서 `sample_df`를 인자로 받는 방식으로 바꿨다.
- pytest 도입도 고려했으나 아직 개발 초기 단계라 의존성을 늘리지 않기 위해 순수 assert로
  충분하다고 판단했다. 나중에 테스트가 많아지면 재검토한다.

## 3. 결과 (Result)

| 파일 | 역할 | 테스트 결과 |
|---|---|---|
| `src/metric.py` | 대회 산식 (`metric`, `metric_by_group`) | 3개 단위 테스트 통과 |
| `src/submission.py` | 제출 생성(`build_submission`, `save_submission`) + 검증(`validate_submission`) | 4개 단위 테스트 통과 + 실제 sample_submission.csv 스모크 테스트 통과 |
| `requirements.txt` | numpy, pandas 등 버전 고정 | - |

## 4. 해석과 다음 단계 (So what)

- 데이터 경로가 CLAUDE.md의 가정(플랫 구조)과 달리 `data/train/`, `data/test/` 하위 폴더임을
  확인했으므로, 다음 단계인 `01_preprocessing.ipynb`의 `DATA_DIR` 관련 상수들은 이 실제 구조를
  기준으로 잡아야 한다.
- 산식과 제출 검증이 코드로 고정됐으므로, 앞으로의 모든 실험은 이 두 모듈을 import해서
  일관된 기준으로 비교할 수 있다.
- 다음 단계: Phase 0의 나머지 항목인 `01_preprocessing.ipynb` 작성(로딩 → pivot → 조인 →
  `data/processed/` parquet 캐시)으로 이어간다. 이 작업은 LDAPS/GFS 원본 CSV의 실제 컬럼
  구조를 먼저 확인해야 하므로, 다음 사이클에서 `data_description.md`와 원본 CSV 헤더를
  검토하는 것부터 시작한다.
