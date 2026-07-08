# 제3회 풍력발전량 예측 AI 경진대회 — 태백가덕산 KPX 그룹별 Day-ahead Forecasting

기상 예보 데이터(LDAPS, GFS)와 터빈 SCADA 실측 데이터를 활용해 **2025년 1년간(8,760시간) KPX 그룹별 시간당 풍력 발전량(kWh)** 을 예측하는 [DACON 대회](https://dacon.io/competitions/official/236727) 프로젝트입니다.

## 예측 대상

태백가덕산 풍력발전단지 (강원 태백, 산악 지형)

| 그룹 | 구성 | 설비용량 |
|---|---|---:|
| `kpx_group_1` | VESTAS V126 1~6호기 | 21.6 MW |
| `kpx_group_2` | VESTAS V126 7~12호기 | 21.6 MW |
| `kpx_group_3` | UNISON U136 1~5호기 | 21.0 MW |

전 터빈 허브 높이 117 m. 학습 기간은 2022~2024년, 평가 기간은 2025년 전체입니다.

## 평가 방식

```
total_score = 0.5 × (1 − NMAE) + 0.5 × FICR(정산금획득률)
```

- **NMAE**: 시간별 절대 오차를 그룹 설비용량으로 나눈 평균 (3개 그룹 평균)
- **FICR**: 시간별 오차율이 설비용량의 6% 이내면 단가 4, 6~8%면 3, 초과 시 0으로 정산한 금액 / 이론상 최대 정산금 (실제 발전량 가중)
- 실제 발전량이 설비용량의 **10% 이상인 시간대만 채점** 대상
- 산식 구현: [`src/metric.py`](src/metric.py) (대회 공식 산식 그대로, 수정 금지)

**대회 평가 구조**

- 리더보드: 평가 데이터의 40%가 Public, 60%가 Private — **1차 평가는 Private Score 100%** (제출은 1일 최대 5회, ~2026-08-14 10:00)
- 2차 평가: Private 상위 30팀이 산출물 제출 → 검증 통과 상위 20팀 오프라인 발표 → **최종 = Private 50% + 발표평가 50%**

## 저장소 구조

```
wind-forecast/
├── CLAUDE.md                  # Claude Code 작업 규칙·도메인 지식·워크플로우 정의
├── 01_preprocessing.ipynb     # 데이터 로딩·pivot·조인·캐시 생성
├── 02_eda.ipynb               # 탐색적 데이터 분석
├── 03_features.ipynb          # 문헌 기반 피처 생성
├── 04_model_selection.ipynb   # 모델 비교·선택
├── 05_tuning.ipynb            # 하이퍼파라미터 튜닝
├── train.ipynb                # 최종 학습 코드 — 모델을 models/에 저장 (2차 평가 제출물)
├── inference.ipynb            # 최종 추론 코드 — 모델 로딩 → 제출 파일 생성 (2차 평가 제출물)
├── src/
│   ├── metric.py              # 대회 평가 산식 (수정 금지)
│   ├── submission.py          # 제출 파일 생성 + 검증 (validate_submission)
│   └── ...                    # train/inference가 공유하는 전처리·피처 함수
├── models/                    # 학습된 모델 파일 (Private Score 재현용)
├── experiments/log.csv        # 실험 로그 (점수·설정·커밋 해시·public score)
├── reports/                   # 분석 문서·그림 (이유·과정·결과 기록)
├── submissions/               # 제출 파일 (submission_expNNN.csv)
├── requirements.txt           # 라이브러리 버전 고정
└── data/                      # 대회 데이터 (git 미추적 — 아래 참조)
```

대회 산출물 규정에 따라 **학습(`train.ipynb`)과 추론(`inference.ipynb`) 코드를 분리**했으며, 전처리·피처 로직은 `src/` 모듈로 공유해 두 코드 간 불일치를 방지합니다. 노트북은 위에서부터 셀을 순서대로 실행(Restart & Run All)하며 따라갈 수 있도록 작성되어 있고, 각 셀에 목적(마크다운)과 근거(주석)가 함께 기록됩니다. 자세한 작업 규칙은 [`CLAUDE.md`](CLAUDE.md)를 참조하세요.

## 데이터

**대회 데이터는 용량(약 330MB, 개별 파일 최대 124MB)과 재배포 제한 때문에 저장소에 포함하지 않습니다.** 대회 페이지에서 직접 내려받아 `data/` 폴더에 배치하세요:

```
data/
├── ldaps_train.csv / ldaps_test.csv     # LDAPS 예보 (1.5km 해상도, 16개 격자)
├── gfs_train.csv / gfs_test.csv         # GFS 예보 (0.25° 해상도, 9개 격자)
├── train_labels.csv                     # KPX 그룹별 실제 발전량 (kWh)
├── scada_vestas_train.csv               # VESTAS SCADA (10분 단위)
├── scada_unison_train.csv               # UNISON SCADA (10분 단위)
├── sample_submission.csv                # 제출 양식 (8,760행)
├── info.xlsx                            # 터빈·그룹 메타 정보
└── data_description.md                  # 데이터 명세서
```

모든 CSV는 `utf-8-sig` 인코딩이며 시간은 KST 기준입니다. 전처리 캐시는 `data/processed/`에 parquet으로 생성됩니다.

**외부 데이터·사전 학습 모델은 사용하지 않았습니다.** (사용하게 될 경우 대회 규정에 따라 출처·수집 시점·라이선스·전처리 코드를 `external_data/`에 포함하고 이 문서에 기재합니다.)

## 개발 환경

- OS: (사용 OS 기재 — 예: Windows 11 / Ubuntu 22.04)
- Python: (버전 기재 — 예: 3.11.x)
- 라이브러리: `requirements.txt` 참조 (버전 고정)

```bash
# 1. 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. 패키지 설치
pip install -r requirements.txt
```

Jupyter 노트북 커널은 이 가상환경(venv)의 Python으로 선택합니다.

## 실행 방법 (Private Score 재현)

1. `data/`에 대회 데이터 배치 (위 참조)
2. **학습**: `train.ipynb`를 처음부터 끝까지 실행 → 전처리·피처 생성 후 모델이 `models/`에 저장됨 (랜덤 시드 고정으로 재현 가능)
3. **추론**: `inference.ipynb`를 처음부터 끝까지 실행 → `models/`의 모델을 로딩해 `submissions/`에 제출 파일 생성
4. 생성된 제출 파일은 `validate_submission()` 검증(행 수 8,760, 시각 형식, 결측·음수·설비용량 초과 여부)을 자동 통과해야 함

분석 과정을 보려면 `01_preprocessing.ipynb` ~ `05_tuning.ipynb`를 순서대로 참조하세요.

## 접근 방법 요약

- **피처**: 허브 높이(117m)에 맞춘 바람 정보가 핵심 — GFS 80/100m 바람, 멱법칙 고도 외삽 풍속, 풍속의 세제곱(P ∝ v³), 공기 밀도(기온·기압), 연직 시어, 풍향 sin/cos, LDAPS·GFS 격자 통계 등
- **누수 방지 (Data Leakage 규칙 준수)**: 각 예측에는 예측기준시점 이전에 활용 가능했던 정보만 사용 — 예보는 제공된 `data_available_kst_dtm`(전일 13:00 KST) 기준으로만 사용, SCADA는 학습 기간 전용(파워커브 추정·예보 보정 학습에만 활용), 평가 데이터는 추론 전용(전처리 스케일러 등 모든 통계는 train에서만 fit), 검증은 시간 기반 분할(2024년 홀드아웃)
- **점수 최적화**: NMAE(연속 지표)로 개선 방향을 잡고, FICR의 6%/8% 계단 특성을 고려한 후처리·튜닝(목적함수 = 대회 total_score). Public 40%에 과적합하지 않도록 로컬 검증 점수를 기준으로 제출 관리

실험별 상세 근거와 결과는 `reports/`의 문서와 `experiments/log.csv`에 기록되어 있습니다.

## 대회 규정 준수 사항

- **Data Leakage 방지**: 모든 예측은 예측기준시점 이전에 생성·공개된 정보만 사용합니다. 평가 기간의 실측·SCADA·사후 보정자료·재분석자료는 사용하지 않으며, 평가 데이터셋은 추론(제출 파일 생성) 목적으로만 사용합니다.
- **모델 실행 방식**: 외부 API 기반 모델 추론(OpenAI, Gemini, HF Inference API 등)은 사용하지 않으며, 모든 모델은 로컬에서 가중치를 직접 로드해 학습·추론합니다.
- **사용 언어**: Python
- **인코딩**: 코드·주석·CSV 모두 UTF-8 (제출 파일은 utf-8-sig)
- `data/` 원본 파일은 수정하지 않습니다 (읽기 전용 취급)
- 제출 파일은 Excel로 열어 재저장하지 않습니다 (시간 형식 손상)
