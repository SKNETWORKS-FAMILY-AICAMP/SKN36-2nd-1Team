# Raw Data

전처리 및 가공 전의 KKBOX 원본 데이터를 저장한다.

## 파일 구성

| 파일명 | 설명 |
|---|---|
| `train_v2.csv` | 고객별 이탈 여부(`is_churn`) 데이터 |
| `members_v3.csv` | 고객의 도시, 연령, 성별, 가입 경로 및 가입일 데이터 |
| `transactions.csv` | 과거 결제·구독 거래 데이터 |
| `transactions_v2.csv` | 최근 결제·구독 거래 데이터 |
| `user_logs.csv` | 과거 음악 이용 로그 데이터 |
| `user_logs_v2.csv` | 최근 음악 이용 로그 데이터 |

## 데이터 활용

- `train_v2.csv`의 `is_churn`을 모델의 타깃으로 사용한다.
- `members_v3.csv`에서 고객 기본 정보와 가입 관련 피처를 생성한다.
- `transactions.csv`와 `transactions_v2.csv`를 결합하여 결제 및 구독 이력을 집계한다.
- `user_logs.csv`와 `user_logs_v2.csv`를 결합하여 고객별 음악 이용 행동을 집계한다.
- 모든 데이터는 고객 식별자인 `msno`를 기준으로 연결한다.

## 주의사항

- 원본 데이터는 직접 수정하지 않는다.
- 전처리 및 통합 결과는 `data/processed/`에 저장한다.
- 대용량 데이터는 청크 단위로 처리한다.
- 데이터 파일은 용량과 라이선스 문제로 Git에 업로드하지 않는다.
- 로컬 환경에서 각 파일을 해당 폴더에 별도로 배치한 후 사용한다.