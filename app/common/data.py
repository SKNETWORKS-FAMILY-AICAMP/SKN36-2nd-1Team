"""KKeeper 데이터·모델 불러오기 (모든 페이지 공통).

폴더 구조
---------
프로젝트/
├─ app/                     ← 이 앱
├─ data/processed/          ← 노트북이 만든 CSV
│   ├─ kkbox_scored.csv               (필수) 전체 회원 피처 + churn_prob [+ is_churn]
│   ├─ kkbox_dashboard_customers.csv  (선택) 대시보드용. 없으면 kkbox_scored.csv를 씀
│   ├─ risk_segments.csv              (필수) msno, segment  ← K-Means 4개 유형
│   ├─ risk_segment_summary.csv       (선택) 유형별 요약. 없으면 직접 계산
│   └─ test_predictions.csv           (선택) y_true, y_prob  ← 모델 페이지 성능 지표용
└─ models/
    └─ lgbm_final.joblib              (필수) {"model", "features", "categories"}
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st

from common.constants import SEGMENTS, THRESHOLD

APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = APP_DIR.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "models"

SCORED_PATH = DATA_DIR / "kkbox_scored.csv"
DASHBOARD_PATHS = [DATA_DIR / "kkbox_dashboard_customers.csv", SCORED_PATH]
SEGMENTS_PATH = DATA_DIR / "risk_segments.csv"
SEGMENT_SUMMARY_PATH = DATA_DIR / "risk_segment_summary.csv"
TEST_PRED_PATH = DATA_DIR / "test_predictions.csv"
CHURN_MODEL_PATH = MODEL_DIR / "lgbm_final.joblib"


def _as_binary(series: pd.Series) -> pd.Series:
    """CSV에서 bool·문자·정수로 섞일 수 있는 값을 0/1로 통일."""
    if pd.api.types.is_bool_dtype(series):
        return series.astype(int)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.map({"true": 1, "false": 0, "1": 1, "0": 0, "yes": 1, "no": 0,
                           "위험": 1, "일반": 0}).fillna(0).astype(int)


def _require(paths: list[Path]) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError("\n".join(missing))


# ─────────────────────────────────────────────
# 대시보드(전체 회원)
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_members() -> pd.DataFrame:
    """전체 회원: msno, churn_prob, is_churn(있으면), risk, segment(위험 회원만)."""
    path = next((p for p in DASHBOARD_PATHS if p.exists()), None)
    if path is None:
        raise FileNotFoundError(" 또는 ".join(str(p) for p in DASHBOARD_PATHS))
    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    if not {"msno", "churn_prob"}.issubset(df.columns):
        raise ValueError(f"{path.name}에 msno, churn_prob 컬럼이 필요합니다.")
    df["churn_prob"] = pd.to_numeric(df["churn_prob"], errors="coerce").clip(0, 1)
    if "is_churn" in df.columns:
        df["is_churn"] = _as_binary(df["is_churn"])
    df["risk"] = _as_binary(df["risk"]) if "risk" in df.columns else df["churn_prob"].ge(THRESHOLD).astype(int)
    if "segment" not in df.columns and SEGMENTS_PATH.exists():
        seg = pd.read_csv(SEGMENTS_PATH, encoding="utf-8-sig", usecols=lambda c: c in {"msno", "segment"})
        df = df.merge(seg.drop_duplicates("msno"), on="msno", how="left")
    return df


# ─────────────────────────────────────────────
# 모델 + 피처 (매칭·실험·모델 페이지)
# ─────────────────────────────────────────────
def _restore_categories(kk: pd.DataFrame, bundle: dict) -> pd.DataFrame:
    saved = bundle.get("categories", {}) or {}
    if isinstance(saved, dict):
        for col, values in saved.items():
            if col in kk.columns:
                kk[col] = pd.Categorical(kk[col], categories=list(values))
    else:
        for col in saved:
            if col in kk.columns:
                kk[col] = kk[col].astype("category")
    return kk


@st.cache_resource(show_spinner="데이터와 모델을 불러오는 중…")
def load_assets() -> dict:
    """이탈 모델과 위험 회원 피처를 한 번만 불러와요.

    돌려주는 값
      bundle : 이탈 모델 묶음 {"model", "features", ...}
      kk     : 전체 회원 피처 (범주형 복원 완료)
      risk   : 위험 회원 피처 + segment  ← 매칭·실험의 모집단
    """
    _require([SCORED_PATH, SEGMENTS_PATH, CHURN_MODEL_PATH])
    bundle = joblib.load(CHURN_MODEL_PATH)
    kk = pd.read_csv(SCORED_PATH, low_memory=False)
    kk = _restore_categories(kk, bundle)
    if "is_churn" in kk.columns:
        kk["is_churn"] = _as_binary(kk["is_churn"])

    seg = pd.read_csv(SEGMENTS_PATH, encoding="utf-8-sig")
    seg = seg[["msno", "segment"]].drop_duplicates("msno")
    risk = kk.merge(seg, on="msno", how="inner")
    risk = risk[risk["segment"].isin(SEGMENTS)].copy()
    return {"bundle": bundle, "kk": kk, "risk": risk}


def segment_summary(risk: pd.DataFrame) -> pd.DataFrame:
    """유형별 요약 (매칭 화면·대시보드). CSV가 있으면 인원 이외 값은 CSV 대신 직접 계산해 일관성 유지."""
    cols = {
        "activity_days": "평균_활동일",
        "days_since_last_log": "마지막접속후_평균일수",
        "cancel_count": "평균_해지횟수",
        "avg_payment": "평균_결제금액",
    }
    rows = []
    for name in SEGMENTS:
        part = risk[risk["segment"] == name]
        row = {"segment": name, "인원": len(part),
               "평균_이탈확률": part["churn_prob"].mean() if len(part) else np.nan,
               "예상_이탈자": part["churn_prob"].sum()}
        for c, label in cols.items():
            row[label] = part[c].mean() if c in part.columns and len(part) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def load_segment_counts() -> pd.DataFrame:
    """대시보드용 가벼운 유형별 인원 (모델을 안 불러와도 되게)."""
    if SEGMENT_SUMMARY_PATH.exists():
        s = pd.read_csv(SEGMENT_SUMMARY_PATH, encoding="utf-8-sig")
        count_col = next((c for c in ["인원", "고객수", "customer_count"] if c in s.columns), None)
        prob_col = next((c for c in ["평균_이탈확률", "avg_churn_prob", "churn_prob"] if c in s.columns), None)
        if "segment" in s.columns and count_col:
            out = pd.DataFrame({"segment": s["segment"], "인원": pd.to_numeric(s[count_col], errors="coerce")})
            out["평균_이탈확률"] = pd.to_numeric(s[prob_col], errors="coerce") if prob_col else np.nan
            return out[out["segment"].isin(SEGMENTS)]
    members = load_members()
    if "segment" not in members.columns:
        return pd.DataFrame(columns=["segment", "인원", "평균_이탈확률"])
    part = members[members["segment"].isin(SEGMENTS)]
    return part.groupby("segment", as_index=False).agg(인원=("msno", "size"), 평균_이탈확률=("churn_prob", "mean"))


@st.cache_data(show_spinner=False)
def load_test_predictions() -> pd.DataFrame | None:
    """모델 성능 지표용 (y_true, y_prob). 없으면 None."""
    if not TEST_PRED_PATH.exists():
        return None
    df = pd.read_csv(TEST_PRED_PATH)
    if not {"y_true", "y_prob"}.issubset(df.columns):
        return None
    return pd.DataFrame({"y_true": _as_binary(df["y_true"]), "y_prob": pd.to_numeric(df["y_prob"], errors="coerce")}).dropna()


# ─────────────────────────────────────────────
# 적용 조건 (마케팅 설계 ② 적용 조건)
# ─────────────────────────────────────────────
TENURE_COLS = ["tenure_date", "tenure_days", "tenure"]
PLAN_COLS = ["plan_type", "plan_name", "plan"]


def apply_conditions(df: pd.DataFrame, cond: dict) -> tuple[pd.DataFrame, list[str]]:
    """마케팅 설계의 적용 조건으로 고객을 추려요. 데이터에 없는 조건은 건너뛰고 안내 문구를 돌려줘요."""
    notes: list[str] = []
    out = df
    period = cond.get("period", "전체")
    if period != "전체":
        col = next((c for c in TENURE_COLS if c in out.columns), None)
        if col:
            t = pd.to_numeric(out[col], errors="coerce")
            mask = {"3개월 미만": t < 90, "3~12개월": (t >= 90) & (t < 365), "1년 이상": t >= 365}[period]
            out = out[mask.fillna(False)]
        else:
            notes.append("구독 기간 컬럼(tenure_date)이 없어 해당 조건을 제외하고 계산했습니다.")
    last = cond.get("last", "전체")
    if last != "전체":
        if "days_since_last_log" in out.columns:
            days = {"7일 이상 미접속": 7, "14일 이상 미접속": 14, "30일 이상 미접속": 30}[last]
            out = out[pd.to_numeric(out["days_since_last_log"], errors="coerce") >= days]
        else:
            notes.append("마지막 접속 컬럼(days_since_last_log)이 없어 해당 조건을 제외하고 계산했습니다.")
    plans = cond.get("plans") or []
    if plans:
        col = next((c for c in PLAN_COLS if c in out.columns), None)
        if col:
            out = out[out[col].astype(str).isin(plans)]
        else:
            notes.append("요금제 컬럼(plan_type)이 없어 해당 조건을 제외하고 계산했습니다.")
    return out, notes
