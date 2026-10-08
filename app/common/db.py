"""KKeeper 저장소 — 실험(A/B 테스트)과 결과를 저장·조회.

- 환경변수 KK_DB_URL이 있으면 그 DB를 써요 (SQLAlchemy 필요).
    예) KK_DB_URL=mysql+pymysql://<계정>:<비밀번호>@127.0.0.1:3308/skn36-2nd-1team-db?charset=utf8mb4
- 없으면 프로젝트/data/kkeeper.db (SQLite 파일)에 저장해요. 설치 없이 바로 돌아가요.

테이블
  experiment         실험 하나 = 전략 + 대상 + 가설 + 설계 + 결과 + 판정
  experiment_member  실험에 배정된 고객 (msno, 실험군 T / 대조군 C)
  marketing_plan     이전 버전(행동 시나리오 → 계획 저장)의 표. 있으면 라이브러리에서 읽기만 해요.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SQLITE_PATH = PROJECT_ROOT / "data" / "kkeeper.db"
DB_URL = os.getenv("KK_DB_URL", "").strip()
USE_SQLITE = not DB_URL or DB_URL.startswith("sqlite")

# (컬럼, SQLite 타입, MySQL 타입)
COLUMNS = [
    ("title", "TEXT NOT NULL", "VARCHAR(200) NOT NULL"),
    ("status", "TEXT NOT NULL", "VARCHAR(20) NOT NULL"),          # 진행 중 · 완료
    # 1 마케팅 설계
    ("strategy_kind", "TEXT", "VARCHAR(50)"),
    ("strategy_goal", "TEXT", "VARCHAR(50)"),
    ("strategy_desc", "TEXT", "TEXT"),
    ("conditions", "TEXT", "TEXT"),                               # JSON {period, last, plans}
    ("levers", "TEXT", "TEXT"),                                   # JSON {레버: %}
    # 2 고객 매칭 · 가설
    ("segment", "TEXT NOT NULL", "VARCHAR(100) NOT NULL"),
    ("hyp_p_ctrl", "REAL", "DOUBLE"),                             # 대조군(현재) 예상 이탈률
    ("hyp_p_treat", "REAL", "DOUBLE"),                            # 실험군(목표 달성) 예상 이탈률
    ("hyp_reduced", "REAL", "DOUBLE"),
    ("required_n", "INTEGER", "INT"),
    # 3 실험 설계
    ("channel", "TEXT", "VARCHAR(100)"),
    ("start_date", "TEXT", "VARCHAR(10)"),
    ("end_date", "TEXT", "VARCHAR(10)"),
    ("metric", "TEXT", "VARCHAR(200)"),
    ("seed", "INTEGER", "INT"),
    ("n_treat", "INTEGER", "INT"),
    ("n_ctrl", "INTEGER", "INT"),
    # 3 결과 · 판정
    ("obs_n_treat", "INTEGER", "INT"),
    ("obs_x_treat", "INTEGER", "INT"),                            # 실험군 이탈자 수
    ("obs_n_ctrl", "INTEGER", "INT"),
    ("obs_x_ctrl", "INTEGER", "INT"),                             # 대조군 이탈자 수
    ("p_value", "REAL", "DOUBLE"),
    ("ci_low", "REAL", "DOUBLE"),
    ("ci_high", "REAL", "DOUBLE"),
    ("verdict", "TEXT", "VARCHAR(20)"),                           # 효과 있음 · 판단 보류 · 효과 없음
    ("is_simulated", "INTEGER", "INT"),
    ("note", "TEXT", "TEXT"),
    ("created_at", "TEXT", "VARCHAR(19)"),
    ("updated_at", "TEXT", "VARCHAR(19)"),
]
COLUMN_NAMES = [c[0] for c in COLUMNS]
JSON_FIELDS = ("conditions", "levers")


def _ddl() -> list[str]:
    if USE_SQLITE:
        cols = ",\n".join(f"  {n} {t}" for n, t, _ in COLUMNS)
        return [f"CREATE TABLE IF NOT EXISTS experiment (\n  id INTEGER PRIMARY KEY AUTOINCREMENT,\n{cols}\n)",
                "CREATE TABLE IF NOT EXISTS experiment_member (experiment_id INTEGER NOT NULL, msno TEXT NOT NULL, grp TEXT NOT NULL)",
                "CREATE INDEX IF NOT EXISTS ix_member_exp ON experiment_member (experiment_id)"]
    cols = ",\n".join(f"  {n} {t}" for n, _, t in COLUMNS)
    return [f"CREATE TABLE IF NOT EXISTS experiment (\n  id INT AUTO_INCREMENT PRIMARY KEY,\n{cols}\n) DEFAULT CHARSET = utf8mb4",
            "CREATE TABLE IF NOT EXISTS experiment_member (experiment_id INT NOT NULL, msno VARCHAR(100) NOT NULL, "
            "grp CHAR(1) NOT NULL, INDEX ix_member_exp (experiment_id)) DEFAULT CHARSET = utf8mb4"]


# ─────────────────────────────────────────────
# 연결 (SQLite: 표준 라이브러리 / 그 밖: SQLAlchemy)
# ─────────────────────────────────────────────
_engine = None
_ready = False


def _sa_engine():
    global _engine
    if _engine is None:
        from sqlalchemy import create_engine
        _engine = create_engine(DB_URL, pool_pre_ping=True)
    return _engine


@contextmanager
def _conn():
    """with _conn() as run: run(sql, params) → rows(list[dict]) 형태로 통일."""
    if USE_SQLITE:
        SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(SQLITE_PATH)
        con.row_factory = sqlite3.Row
        try:
            def run(sql, params=None, many=False):
                cur = con.executemany(sql, params) if many else con.execute(sql, params or {})
                rows = [dict(r) for r in cur.fetchall()] if cur.description else []
                return rows, cur.lastrowid
            yield run
            con.commit()
        finally:
            con.close()
    else:
        from sqlalchemy import text
        with _sa_engine().begin() as con:
            def run(sql, params=None, many=False):
                res = con.execute(text(sql), params if many else (params or {}))
                rows = [dict(r._mapping) for r in res.fetchall()] if res.returns_rows else []
                return rows, getattr(res, "lastrowid", None)
            yield run


def init_db() -> None:
    global _ready
    if _ready:
        return
    with _conn() as run:
        for sql in _ddl():
            run(sql)
    _ready = True


def db_label() -> str:
    return "SQLite (data/kkeeper.db)" if USE_SQLITE else "외부 DB (KK_DB_URL)"


# ─────────────────────────────────────────────
# 값 변환
# ─────────────────────────────────────────────
def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean(value):
    if isinstance(value, (datetime,)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "item"):          # numpy 숫자
        return value.item()
    return value


def _dump(fields: dict) -> dict:
    row = {}
    for name in COLUMN_NAMES:
        if name not in fields:
            continue
        value = fields[name]
        if name in JSON_FIELDS and not isinstance(value, str):
            value = json.dumps(value or {}, ensure_ascii=False)
        row[name] = _clean(value)
    return row


def _load(row: dict) -> dict:
    row = dict(row)
    for f in JSON_FIELDS:
        try:
            row[f] = json.loads(row.get(f) or "{}")
        except (TypeError, ValueError):
            row[f] = {}
    return row


# ─────────────────────────────────────────────
# 실험
# ─────────────────────────────────────────────
def create_experiment(payload: dict, treat_ids, ctrl_ids) -> int:
    """실험을 만들고 배정된 고객까지 저장해요. 새 실험 번호를 돌려줘요."""
    init_db()
    now = _now()
    row = _dump({"is_simulated": 0, **payload, "status": payload.get("status") or "진행 중",
                 "created_at": now, "updated_at": now})
    cols = ", ".join(row)
    vals = ", ".join(f":{c}" for c in row)
    with _conn() as run:
        _, exp_id = run(f"INSERT INTO experiment ({cols}) VALUES ({vals})", row)
        members = ([{"e": exp_id, "m": str(m), "g": "T"} for m in treat_ids]
                   + [{"e": exp_id, "m": str(m), "g": "C"} for m in ctrl_ids])
        for i in range(0, len(members), 5000):
            run("INSERT INTO experiment_member (experiment_id, msno, grp) VALUES (:e, :m, :g)", members[i:i + 5000], many=True)
    return int(exp_id)


def update_experiment(exp_id: int, fields: dict) -> None:
    init_db()
    row = _dump({**fields, "updated_at": _now()})
    sets = ", ".join(f"{c} = :{c}" for c in row)
    with _conn() as run:
        run(f"UPDATE experiment SET {sets} WHERE id = :_id", {**row, "_id": int(exp_id)})


def delete_experiment(exp_id: int) -> None:
    init_db()
    with _conn() as run:
        run("DELETE FROM experiment_member WHERE experiment_id = :i", {"i": int(exp_id)})
        run("DELETE FROM experiment WHERE id = :i", {"i": int(exp_id)})


def get_experiment(exp_id: int) -> dict | None:
    init_db()
    with _conn() as run:
        rows, _ = run("SELECT * FROM experiment WHERE id = :i", {"i": int(exp_id)})
    return _load(rows[0]) if rows else None


def list_experiments() -> list[dict]:
    """최신순 실험 목록."""
    init_db()
    with _conn() as run:
        rows, _ = run("SELECT * FROM experiment ORDER BY created_at DESC, id DESC")
    return [_load(r) for r in rows]


def get_members(exp_id: int) -> pd.DataFrame:
    init_db()
    with _conn() as run:
        rows, _ = run("SELECT msno, grp FROM experiment_member WHERE experiment_id = :i", {"i": int(exp_id)})
    return pd.DataFrame(rows, columns=["msno", "grp"])


def _as_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return date.max


def is_waiting(exp: dict) -> bool:
    """진행 중인데 종료일이 지나 결과 입력만 남은 실험."""
    return exp["status"] == "진행 중" and bool(exp.get("end_date")) and _as_date(exp["end_date"]) < date.today()


def counts() -> dict:
    """대시보드 운영 현황 숫자."""
    exps = list_experiments()
    running = [e for e in exps if e["status"] == "진행 중"]
    return {
        "running": len(running),
        "waiting": sum(1 for e in running if is_waiting(e)),
        "verified": sum(1 for e in exps if e.get("verdict") == "효과 있음" and not e.get("is_simulated")),
        "total": len(exps),
    }


# ─────────────────────────────────────────────
# 이전 버전 호환 — marketing_plan (읽기 전용)
# ─────────────────────────────────────────────
def load_legacy_plans() -> pd.DataFrame:
    try:
        with _conn() as run:
            rows, _ = run("SELECT * FROM marketing_plan ORDER BY id DESC")
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()
