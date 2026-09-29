"""KKeeper DB 연결과 마케팅 계획 저장·조회."""

import json
import os

import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = os.getenv(
    "KK_DB_URL",
    "mysql+pymysql://team1:team1234@127.0.0.1:3308/skn36-2nd-1team-db?charset=utf8mb4",
)

_engine = None


def get_engine():
    """DB 연결을 한 번만 만들어서 재사용한다."""
    global _engine
    if _engine is None:
        _engine = create_engine(DB_URL, pool_pre_ping=True)
    return _engine


CREATE_PLAN_TABLE = """
CREATE TABLE IF NOT EXISTS marketing_plan (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    title                  VARCHAR(200) NOT NULL,
    description            TEXT,
    status                 VARCHAR(20)  NOT NULL DEFAULT '계획',
    segment_name           VARCHAR(100) NOT NULL,
    cluster_goal           VARCHAR(100),
    marketing_id           VARCHAR(50),
    marketing_name         VARCHAR(200),
    goals                  JSON,
    customer_count         INT,
    churn_rate_before      DOUBLE,
    churn_rate_after       DOUBLE,
    expected_churn_before  DOUBLE,
    expected_churn_after   DOUBLE,
    reduced_customers      DOUBLE,
    created_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) DEFAULT CHARSET = utf8mb4
"""


def init_db():
    """마케팅 계획 테이블이 없으면 만든다."""
    with get_engine().begin() as conn:
        conn.execute(text(CREATE_PLAN_TABLE))


def ping():
    """연결 확인용. 1이 나오면 성공."""
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT 1")).scalar()


# ── 마케팅 계획 저장·조회 ──
PLAN_COLUMNS = [
    "title", "description", "status", "segment_name", "cluster_goal",
    "marketing_id", "marketing_name", "goals", "customer_count",
    "churn_rate_before", "churn_rate_after",
    "expected_churn_before", "expected_churn_after", "reduced_customers",
]

PLAN_STATUSES = ["계획", "진행 중", "완료", "보류"]


def save_plan(payload):
    """마케팅 계획 하나를 저장하고 새 번호(id)를 돌려준다."""
    init_db()
    row = {c: payload.get(c) for c in PLAN_COLUMNS}
    row["goals"] = json.dumps(payload.get("goals", {}), ensure_ascii=False)
    row["status"] = row["status"] or "계획"

    cols = ", ".join(PLAN_COLUMNS)
    vals = ", ".join(f":{c}" for c in PLAN_COLUMNS)
    with get_engine().begin() as conn:
        result = conn.execute(text(f"INSERT INTO marketing_plan ({cols}) VALUES ({vals})"), row)
        return result.lastrowid


def load_plans():
    """저장된 계획을 최신순으로 불러온다."""
    init_db()
    with get_engine().connect() as conn:
        return pd.read_sql(text("SELECT * FROM marketing_plan ORDER BY created_at DESC, id DESC"), conn)


def update_plan_status(plan_id, status):
    """계획의 상태를 바꾼다."""
    if status not in PLAN_STATUSES:
        raise ValueError(f"알 수 없는 상태입니다: {status}")
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE marketing_plan SET status = :status WHERE id = :id"),
            {"status": status, "id": int(plan_id)},
        )