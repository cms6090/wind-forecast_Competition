# 문서 목록

- [phase0_foundation.md](phase0_foundation.md) — 대회 산식(`src/metric.py`)과 제출 파일 생성·검증(`src/submission.py`) 코드 작성 및 단위 테스트
- [phase0_preprocessing.md](phase0_preprocessing.md) — `01_preprocessing.ipynb`: LDAPS/GFS pivot, 라벨 조인, SCADA 단위 검증(합 vs 평균) 및 parquet 캐시 저장
- [phase1_eda.md](phase1_eda.md) — `02_eda.ipynb`: 이용률 분포, 시간대/월별 발전 패턴, SCADA 파워커브(센서 이상치 발견·제외), 터빈 정지/결빙 의심 구간, 예보-실측 풍속 상관·편향 분석
- [phase2_features.md](phase2_features.md) — `03_features.ipynb`: 허브고도(117m) 멱법칙 외삽, 공기 밀도·결빙 점수, SCADA 기반 풍속 보정식과 파워커브(2022~2023만 fit), 예보 lag/lead → 피처 179개 생성. **피처별 근거 등급(A~D)**, 문헌 재검토로 도출한 추가 후보 피처와 REWS 기각 근거, 참고문헌 9건 포함
- [phase3_model_selection.md](phase3_model_selection.md) — `04_model_selection.ipynb`: 데이터 형태 측정(중소규모 tabular, 계단형 구조, 외삽 불필요) → 문헌 근거로 GBDT 선정. Ridge/LightGBM/XGBoost/CatBoost/잔차학습 6종 공정 비교. **LightGBM(L1 손실) 채택, 2024 홀드아웃 total_score 0.6074 (물리 베이스라인 +0.0357)**. 손실함수 L1 vs L2 대조 실험, FICR 밴드 분석, 재현성 검증
