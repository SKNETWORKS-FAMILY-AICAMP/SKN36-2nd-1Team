"""KKeeper 마케팅 시뮬레이션 공통 함수.

노트북에서 검증한 Starbucks 행동 변화 모델과 KKBOX 이탈 모델을
Streamlit 화면에서도 동일하게 사용할 수 있도록 분리한 모듈입니다.
시뮬레이션 결과를 파일이나 데이터베이스에 저장하는 책임은 갖지 않습니다.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.model_selection import train_test_split


def get_segment_customers(kk, risk_segments, segment_name):
    """선택한 군집 고객의 피처와 이탈확률을 가져온다."""
    ids = risk_segments.loc[risk_segments["segment"] == segment_name, "msno"]
    return kk.loc[kk["msno"].isin(ids)].copy()


def split_ab(customers, seed=42, n_bins=5):
    """
    이탈확률 구간별로 반씩 나눠 두 그룹의 확률 분포를 비슷하게 만든다.

    seed   : 나누는 결과를 고정하는 값. 바꾸면 다른 조합으로 나뉨
    n_bins : 이탈확률을 몇 구간으로 나눌지
    """
    if len(customers) < 2:
        raise ValueError("그룹 분할에는 고객이 2명 이상 필요합니다.")
    if len(customers) < n_bins * 2:
        return train_test_split(customers, test_size=0.5, random_state=seed)
    bins = pd.qcut(customers["churn_prob"].rank(method="first"), n_bins, labels=False)
    group_a, group_b = train_test_split(customers, test_size=0.5, stratify=bins, random_state=seed)
    return group_a, group_b


BALANCE_COLS = {
    "churn_prob": "평균 이탈확률",
    "activity_days": "평균 활동일",
    "days_since_last_log": "마지막 접속 후 일수",
    "cancel_count": "평균 해지 횟수",
    "avg_payment": "평균 결제금액",
}


def balance_table(group_a, group_b):
    """두 그룹의 주요 지표 평균과 표준화 차이를 비교한다."""
    rows = []
    for col, label in BALANCE_COLS.items():
        if col not in group_a.columns:
            continue
        a = pd.to_numeric(group_a[col], errors="coerce")
        b = pd.to_numeric(group_b[col], errors="coerce")
        pooled = np.sqrt((a.var() + b.var()) / 2)
        smd = (a.mean() - b.mean()) / pooled if pooled > 0 else 0.0
        rows.append({"지표": label, "그룹 A": a.mean(), "그룹 B": b.mean(), "표준화 차이": smd})
    return pd.DataFrame(rows)

OFFER_TYPE_MAP = {
    "구독료 할인": "discount",
    "무료 이용 혜택": "bogo",
    "콘텐츠 추천": "informational",
    "단순 안내": "informational",
}

CHANNEL_MAP = {
    "이메일": "email",
    "앱 푸시": "mobile",
    "문자": "mobile",
    "웹": "web",
    "소셜": "social",
}

FEATURE_LABELS = {
    "activity_days": "평균 활동일",
    "total_secs": "평균 총 청취시간",
    "total_num_100": "평균 완청 곡 수",
    "total_num_unq": "평균 고유 곡 수",
    "days_since_last_log": "마지막 접속 후 평균일수",
}



def restore_churn_categories(
    kk: pd.DataFrame,
    churn_bundle: dict[str, Any],
) -> pd.DataFrame:
    """저장된 이탈 모델과 같은 범주형 자료형을 KKBOX 데이터에 적용합니다."""
    restored = kk.copy()
    saved_categories = churn_bundle.get("categories", {})

    if isinstance(saved_categories, dict):
        for column, category_values in saved_categories.items():
            if column not in restored.columns:
                continue
            restored[column] = pd.Categorical(
                restored[column],
                categories=list(category_values),
            )
    else:
        for column in saved_categories:
            if column in restored.columns:
                restored[column] = restored[column].astype("category")

    return restored


def select_segment(
    kk: pd.DataFrame,
    risk_segments: pd.DataFrame,
    segment_name: str,
) -> pd.DataFrame:
    """선택한 위험 고객 집단의 KKBOX 원본 피처를 반환합니다."""
    segment_ids = risk_segments.loc[
        risk_segments["segment"].eq(segment_name),
        "msno",
    ]
    return kk.loc[kk["msno"].isin(segment_ids)].copy()


def make_behavior_customers(selected_customers: pd.DataFrame) -> pd.DataFrame:
    """KKBOX 고객 정보를 Starbucks 행동 모델 입력 형태로 변환합니다."""
    return pd.DataFrame(
        {
            "age": selected_customers["bd_clean"],
            "gender": selected_customers["gender_status"].map(
                {"male": "M", "female": "F"}
            ),
            "tenure_days": selected_customers["tenure_date"],
        },
        index=selected_customers.index,
    )


def campaign_to_offer(
    channel: str,
    offer_name: str,
    benefit_pct: float,
    duration: int,
) -> dict[str, Any]:
    """화면에서 입력한 캠페인을 행동 모델 피처로 변환합니다."""
    if channel not in CHANNEL_MAP:
        raise ValueError(f"지원하지 않는 발송 채널입니다: {channel}")
    if offer_name not in OFFER_TYPE_MAP:
        raise ValueError(f"지원하지 않는 마케팅 유형입니다: {offer_name}")
    if not 0 <= benefit_pct <= 50:
        raise ValueError("할인율은 0~50 사이로 입력해야 합니다.")
    if not 3 <= int(duration) <= 10:
        raise ValueError("캠페인 유효기간은 3~10일 사이여야 합니다.")

    offer_type = OFFER_TYPE_MAP[offer_name]
    offer = {
        "offer_type": offer_type,
        "email": 0,
        "mobile": 0,
        "social": 0,
        "web": 0,
        "benefit": 0.0,
        "duration": int(duration),
    }
    offer[CHANNEL_MAP[channel]] = 1

    if offer_type == "discount":
        offer["benefit"] = float(benefit_pct) / 100
    elif offer_type == "bogo":
        offer["benefit"] = 1.0

    return offer


def behavior_lift(
    behavior_customers: pd.DataFrame,
    offer: dict[str, Any],
    behavior_bundle: dict[str, Any],
) -> pd.DataFrame:
    """캠페인이 없을 때와 있을 때의 예측 행동 비율을 계산합니다."""
    model = behavior_bundle["model"]
    features = behavior_bundle["features"]
    categories = behavior_bundle["categories"]

    campaign_on = behavior_customers.copy()
    campaign_off = behavior_customers.copy()

    for column, value in offer.items():
        campaign_on[column] = value

    campaign_off["offer_type"] = "none"
    for channel in ["email", "mobile", "social", "web"]:
        campaign_off[channel] = 0
    campaign_off["benefit"] = 0.0
    campaign_off["duration"] = 0

    for column, category_values in categories.items():
        campaign_on[column] = pd.Categorical(
            campaign_on[column],
            categories=category_values,
        )
        campaign_off[column] = pd.Categorical(
            campaign_off[column],
            categories=category_values,
        )

    prediction_on = np.clip(
        model.predict(campaign_on[features]),
        1e-8,
        None,
    )
    prediction_off = np.clip(
        model.predict(campaign_off[features]),
        1e-8,
        None,
    )

    return pd.DataFrame(
        {
            "behavior_before": prediction_off,
            "behavior_after": prediction_on,
            "lift": prediction_on / prediction_off,
        },
        index=behavior_customers.index,
    )


def apply_behavior(
    churn_features: pd.DataFrame,
    lift: pd.Series | np.ndarray,
) -> pd.DataFrame:
    """행동 증가율을 KKBOX 청취 활동 피처에만 적용합니다."""
    after = churn_features.copy()
    lift = pd.Series(lift, index=after.index, dtype=float)

    if lift.isna().any():
        raise ValueError("일부 고객의 행동 변화율을 찾을 수 없습니다.")

    if "total_secs" in after.columns:
        after["total_secs"] = (
            after["total_secs"].astype(float).mul(lift).clip(lower=0)
        )

    for column in ["total_num_100", "total_num_unq"]:
        if column in after.columns:
            after[column] = (
                after[column].astype(float).mul(lift).round().clip(lower=0)
            )

    if "activity_days" in after.columns:
        after["activity_days"] = (
            after["activity_days"]
            .astype(float)
            .mul(lift)
            .round()
            .clip(lower=0, upper=90)
        )

    if {"days_since_last_log", "has_log"}.issubset(after.columns):
        has_log_mask = after["has_log"].eq(1)
        after.loc[has_log_mask, "days_since_last_log"] = (
            after.loc[has_log_mask, "days_since_last_log"]
            .astype(float)
            .div(lift.loc[has_log_mask])
            .round()
            .clip(lower=0)
        )

    derived_features = {
        "avg_daily_secs": "total_secs",
        "avg_daily_complete": "total_num_100",
        "avg_daily_unq": "total_num_unq",
    }
    if "activity_days" in after.columns:
        valid_days = after["activity_days"] > 0
        for derived, total in derived_features.items():
            if derived not in after.columns or total not in after.columns:
                continue
            after.loc[valid_days, derived] = (
                after.loc[valid_days, total]
                / after.loc[valid_days, "activity_days"]
            )
            after.loc[~valid_days, derived] = churn_features.loc[
                ~valid_days,
                derived,
            ]

    return after


def boot_range(
    prob_before: pd.Series | np.ndarray,
    prob_after: pd.Series | np.ndarray,
    n_boot: int = 1000,
    seed: int = 42,
) -> np.ndarray:
    """고객 구성 변화에 따른 예상 감소 인원의 95% 범위를 계산합니다."""
    rng = np.random.default_rng(seed)
    diff = np.asarray(prob_before, dtype=float) - np.asarray(
        prob_after,
        dtype=float,
    )
    n = len(diff)
    if n == 0:
        return np.array([np.nan, np.nan])

    sums = np.array(
        [diff[rng.integers(0, n, n)].sum() for _ in range(n_boot)]
    )
    return np.percentile(sums, [2.5, 97.5])


def simulate_segment(
    *,
    kk: pd.DataFrame,
    risk_segments: pd.DataFrame,
    churn_bundle: dict[str, Any],
    behavior_bundle: dict[str, Any],
    segment_name: str,
    channel: str,
    offer_name: str,
    benefit_pct: float,
    duration: int,
    n_boot: int = 1000,
    seed: int = 42,
) -> dict[str, pd.DataFrame]:
    """선택 집단에 마케팅을 적용하고 행동·이탈 변화를 반환합니다."""
    selected_customers = select_segment(kk, risk_segments, segment_name)
    if selected_customers.empty:
        raise ValueError(f"선택한 분류에 고객이 없습니다: {segment_name}")

    churn_model = churn_bundle["model"]
    churn_features = churn_bundle["features"]
    behavior_customers = make_behavior_customers(selected_customers)
    offer = campaign_to_offer(
        channel=channel,
        offer_name=offer_name,
        benefit_pct=benefit_pct,
        duration=duration,
    )
    behavior_result = behavior_lift(
        behavior_customers=behavior_customers,
        offer=offer,
        behavior_bundle=behavior_bundle,
    )

    x_before = selected_customers[churn_features].copy()
    x_after = apply_behavior(x_before, behavior_result["lift"])

    model_prob_before = churn_model.predict_proba(x_before)[:, 1]
    model_prob_after = churn_model.predict_proba(x_after)[:, 1]
    model_probability_change = model_prob_after - model_prob_before

    prob_before = selected_customers["churn_prob"].to_numpy()
    raw_prob_after = prob_before + model_probability_change
    prob_after = np.clip(raw_prob_after, 0, 1)

    detail = pd.DataFrame(
        {
            "msno": selected_customers["msno"].values,
            "segment": segment_name,
            "lift": behavior_result["lift"].values,
            "prob_before": prob_before,
            "model_prob_before": model_prob_before,
            "model_prob_after": model_prob_after,
            "model_probability_change": model_probability_change,
            "prob_after": prob_after,
        },
        index=selected_customers.index,
    )
    detail["churn_reduction"] = detail["prob_before"] - detail["prob_after"]

    expected_before = detail["prob_before"].sum()
    expected_after = detail["prob_after"].sum()
    reduced_customers = expected_before - expected_after
    churn_rate_before = detail["prob_before"].mean()
    churn_rate_after = detail["prob_after"].mean()
    churn_change_rate = (
        (expected_after / expected_before - 1) * 100
        if expected_before > 0
        else np.nan
    )
    range_low, range_high = boot_range(
        detail["prob_before"],
        detail["prob_after"],
        n_boot=n_boot,
        seed=seed,
    )

    summary = pd.DataFrame(
        [
            {
                "분류": segment_name,
                "발송채널": channel,
                "혜택유형": offer_name,
                "혜택률(%)": float(benefit_pct),
                "기간(일)": int(duration),
                "고객수": len(detail),
                "평균_행동변화율(%)": (detail["lift"].mean() - 1) * 100,
                "현재_평균이탈확률": churn_rate_before,
                "캠페인후_평균이탈확률": churn_rate_after,
                "이탈률_변화(%p)": (churn_rate_after - churn_rate_before) * 100,
                "현재_예상이탈자": expected_before,
                "캠페인후_예상이탈자": expected_after,
                "예상_감소인원": reduced_customers,
                "감소인원_하한(95%)": range_low,
                "감소인원_상한(95%)": range_high,
                "예상이탈_변화율(%)": churn_change_rate,
                "이탈확률_무변화비율(%)": (
                    np.isclose(model_probability_change, 0, atol=1e-12).mean()
                    * 100
                ),
                "확률범위_제한고객수": int(
                    ((raw_prob_after < 0) | (raw_prob_after > 1)).sum()
                ),
            }
        ]
    )

    feature_changes = []
    for column, label in FEATURE_LABELS.items():
        if column not in x_before.columns or column not in x_after.columns:
            continue
        before_mean = x_before[column].mean()
        after_mean = x_after[column].mean()
        change_pct = (
            (after_mean / before_mean - 1) * 100
            if before_mean != 0
            else np.nan
        )
        feature_changes.append(
            {
                "metric_key": column,
                "행동 지표": label,
                "캠페인 전": before_mean,
                "캠페인 후": after_mean,
                "변화율(%)": change_pct,
            }
        )

    return {
        "summary": summary,
        "feature_changes": pd.DataFrame(feature_changes),
        "detail": detail,
    }



def whatif_probs(customers, levers, churn_bundle, seed=42):
    """고객별 현재 이탈확률과 행동 목표를 적용한 뒤의 예상 이탈확률."""
    model, feats = churn_bundle["model"], churn_bundle["features"]
    X_before = customers[feats]
    X_after = apply_levers(X_before, levers, seed)
    change = model.predict_proba(X_after)[:, 1] - model.predict_proba(X_before)[:, 1]
    before = customers["churn_prob"].to_numpy(dtype=float)
    after = np.clip(before + change, 0, 1)
    return before, after, change, X_before, X_after


def whatif_customers(customers, levers, churn_bundle, seed=42):
    """행동 목표를 달성했을 때 이탈률이 어떻게 바뀌는지 모델로 계산 (가설용)."""
    before, after, change, X_before, X_after = whatif_probs(customers, levers, churn_bundle, seed)
    metrics = {c: label for c, label in WHATIF_METRICS.items() if c in X_before.columns}
    behavior = pd.DataFrame({
        "행동 지표": list(metrics.values()),
        "현재": [float(pd.to_numeric(X_before[c], errors="coerce").mean()) for c in metrics],
        "목표 적용 후": [float(pd.to_numeric(X_after[c], errors="coerce").mean()) for c in metrics],
    })
    return {
        "summary": {
            "고객수": len(customers),
            "현재_평균이탈확률": float(before.mean()) if len(before) else 0.0,
            "목표후_평균이탈확률": float(after.mean()) if len(after) else 0.0,
            "현재_예상이탈자": float(before.sum()),
            "목표후_예상이탈자": float(after.sum()),
            "예상_감소인원": float(before.sum() - after.sum()),
            "확률상승_고객비율": float((change > 1e-9).mean()) if len(change) else 0.0,
        },
        "behavior": behavior,
    }


# ── 행동 목표(레버): 방향 점검을 통과한 것만 ──
WHATIF_LEVERS = {
    "song_variety":  {"label": "하루 고유곡 증가", "max": 50, "kind": "행동",
                      "help": "하루 평균 듣는 서로 다른 곡 수가 몇 % 늘어나는지"},
    "activity_up":   {"label": "활동일 증가", "max": 50, "kind": "행동",
                      "help": "90일 중 음악을 들은 날이 몇 % 늘어나는지"},
    "listen_time":   {"label": "하루 청취시간 증가", "max": 50, "kind": "행동",
                      "help": "하루 평균 청취시간이 몇 % 늘어나는지 (모델 반응이 작은 편)"},
    "revisit":       {"label": "재접속 유도", "max": 80, "kind": "행동",
                      "help": "마지막 접속 후 경과일이 몇 % 줄어드는지"},
    "cancel_stop":   {"label": "해지 철회", "max": 30, "kind": "계약",
                      "help": "마지막 거래가 해지인 고객 중 몇 %가 해지를 철회하는지 (가정)"},
    "auto_renew_on": {"label": "자동갱신 전환", "max": 30, "kind": "계약",
                      "help": "자동갱신을 끈 고객 중 몇 %가 다시 켜는지 (가정)"},
}


def lever_eligible(customers):
    """레버마다 적용 대상이 되는 고객 수"""
    return {k: int(m.sum()) for k, m in lever_masks(customers).items()}


def lever_masks(customers):
    """레버마다 적용 대상 고객 표시(True/False)."""
    def col(name, default=0):
        if name in customers.columns:
            return pd.to_numeric(customers[name], errors="coerce").fillna(default)
        return pd.Series(default, index=customers.index)

    active = col("activity_days") > 0
    return {
        "song_variety": active,
        "activity_up": active,
        "listen_time": active,
        "revisit": col("days_since_last_log") > 0,
        "cancel_stop": col("last_is_cancel") == 1,
        "auto_renew_on": col("last_auto_renew", 1) == 0,
    }


def _sync_totals(X, orig):
    """하루 평균 × 활동일 = 총량이 되도록 맞춘다 (해당 컬럼이 모델 피처에 있을 때만)."""
    if "activity_days" not in X.columns:
        return X
    d = pd.to_numeric(X["activity_days"], errors="coerce")
    ok = d > 0
    pairs = [("total_secs", "avg_daily_secs", False), ("total_num_unq", "avg_daily_unq", True),
             ("total_num_100", "avg_daily_complete", True)]
    for total, daily, rounded in pairs:
        if total in X.columns and daily in X.columns:
            value = X.loc[ok, daily] * d[ok]
            X.loc[ok, total] = value.round() if rounded else value
    if {"complete_per_unq", "total_num_100", "total_num_unq"}.issubset(X.columns):
        X.loc[ok, "complete_per_unq"] = X.loc[ok, "total_num_100"] / X.loc[ok, "total_num_unq"].replace(0, np.nan)
        # 0으로 나눠 새로 생긴 빈 값은 원래 값으로 채워요 (없던 결측을 만들지 않게)
        X["complete_per_unq"] = X["complete_per_unq"].fillna(orig["complete_per_unq"])
    for c in ["total_secs", "total_num_unq", "total_num_100", "complete_per_unq"]:
        if c in X.columns:
            X.loc[~ok, c] = orig.loc[~ok, c]
    return X


def apply_levers(X, levers, seed=42):
    """레버 설정대로 이탈 모델 입력 피처를 바꾼다. 모델 피처에 없는 레버는 건너뛴다."""
    orig = X
    X = X.copy()
    rng = np.random.default_rng(seed)

    def flip(cols, from_v, to_v, pct):
        cols = [c for c in cols if c in X.columns]
        if not cols:
            return
        idx = X.index[X[cols[0]] == from_v]
        n = int(round(len(idx) * pct / 100))
        if n > 0:
            chosen = rng.choice(idx, size=n, replace=False)
            for c in cols:
                X.loc[chosen, c] = to_v

    if levers.get("song_variety") and "avg_daily_unq" in X.columns:
        X["avg_daily_unq"] = X["avg_daily_unq"] * (1 + levers["song_variety"] / 100)
    if levers.get("listen_time") and "avg_daily_secs" in X.columns:
        X["avg_daily_secs"] = X["avg_daily_secs"] * (1 + levers["listen_time"] / 100)
    if levers.get("activity_up") and "activity_days" in X.columns:
        X["activity_days"] = (X["activity_days"] * (1 + levers["activity_up"] / 100)).clip(upper=90).round()
    if levers.get("revisit") and "days_since_last_log" in X.columns:
        X["days_since_last_log"] = (X["days_since_last_log"] * (1 - levers["revisit"] / 100)).round()
    if levers.get("cancel_stop"):
        flip(["last_is_cancel", "cancel_on_last_date"], 1, 0, levers["cancel_stop"])
    if levers.get("auto_renew_on"):
        flip(["last_auto_renew"], 0, 1, levers["auto_renew_on"])

    return _sync_totals(X, orig)


WHATIF_METRICS = {
    "avg_daily_unq": "하루 평균 고유곡 수",
    "activity_days": "평균 활동일",
    "avg_daily_secs": "하루 평균 청취시간(초)",
    "days_since_last_log": "마지막 접속 후 평균 일수",
    "last_is_cancel": "마지막 거래 해지 비율",
    "last_auto_renew": "자동갱신 켬 비율",
}


# ── 군집별 전략: 팀원 marketing.ipynb 기준, 방향 점검 결과 반영 ──
CLUSTER_GOALS = {
    "저활동·단기 구독형": "이용 활성화",
    "반복 거래·취소 위험형": "즉각적 이탈 방어",
    "장기 플랜·고결제 고위험형": "고가치 고객 유지",
    "장기 관계·고빈도 거래형": "충성도 강화",
}

CLUSTER_MARKETING = {
    "저활동·단기 구독형": {
        "id": "c0_reco", "name": "개인화 추천을 통한 서비스 이용 활성화",
        "desc": "개인화 음악 추천으로 더 다양한 곡을, 더 자주 듣도록 유도합니다.",
        "core": {"song_variety": 10, "activity_up": 10},
        "aux": {"listen_time": 0, "revisit": 0},
        "note": "하루 청취시간은 모델 반응이 작아 보조 목표로 두었습니다.",
    },
    "반복 거래·취소 위험형": {
        "id": "c1_retention", "name": "취소 시점 Retention Offer",
        "desc": "취소 의사를 보인 고객에게 일시정지·할인·플랜 변경을 제안해 실제 취소를 막습니다.",
        "core": {"cancel_stop": 20},
        "aux": {"song_variety": 0, "activity_up": 0},
        "note": "연간 취소 빈도(cancel_per_year)는 이탈 모델에 없는 피처라 해지 철회로 표현했습니다.",
    },
    "장기 플랜·고결제 고위험형": {
        "id": "c2_renewal", "name": "만료 전 선제적 갱신 캠페인",
        "desc": "장기 플랜 종료 전 개인화된 갱신 혜택으로 자동갱신 전환을 유도합니다.",
        "core": {"auto_renew_on": 20},
        "aux": {},
        "note": "만료까지 남은 기간(days_to_expire)은 누수 문제로 모델에서 제외돼 자동갱신 전환으로 표현했습니다. "
                "이 군집은 이미 활발히 이용해 청취 관련 목표는 효과가 거의 없습니다.",
    },
    "장기 관계·고빈도 거래형": {
        "id": "c3_loyalty", "name": "Loyalty Reward를 통한 충성도 강화",
        "desc": "이용 실적 기반 보상과 장기 고객 혜택으로 지속적인 이용을 유도합니다.",
        "core": {"activity_up": 10, "revisit": 20},
        "aux": {"song_variety": 0, "auto_renew_on": 0},
        "note": "",
    },
}


def required_n_per_group(p1, p2, alpha=0.05, power=0.8):
    """두 그룹 이탈률 차이(p1 vs p2)를 확인하는 데 필요한 그룹당 인원"""
    if abs(p1 - p2) < 1e-9:
        return None
    z_a = norm.ppf(1 - alpha / 2)
    z_b = norm.ppf(power)
    n = (z_a + z_b) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p1 - p2) ** 2
    return int(np.ceil(n))




# ═════════════════════════════════════════════
# 새 흐름: 마케팅 설계 → 고객 매칭 → A/B 테스트 → 라이브러리
# ═════════════════════════════════════════════
def affected_mask(customers, levers):
    """켜진 행동 목표 중 하나라도 적용될 수 있는 고객."""
    masks = lever_masks(customers)
    mask = pd.Series(False, index=customers.index)
    for key, value in levers.items():
        if value and key in masks:
            mask |= masks[key]
    return mask


def rank_segments(risk, levers, churn_bundle, cluster_marketing=None, seed=42):
    """유형 4가지 각각에 같은 행동 목표를 적용해 예상 이탈 감소 순으로 순위를 매긴다.

    risk : 적용 조건까지 통과한 위험 회원 (segment 컬럼 포함)
    """
    cluster_marketing = cluster_marketing if cluster_marketing is not None else CLUSTER_MARKETING
    active = {k for k, v in levers.items() if v}
    rows = []
    for name in CLUSTER_MARKETING:
        part = risk[risk["segment"] == name]
        row = {"segment": name, "대상_인원": len(part), "영향_가능": 0, "평균_이탈확률": np.nan,
               "목표후_이탈확률": np.nan, "예상_감소": 0.0, "확률상승_비율": 0.0}
        if len(part):
            res = whatif_customers(part, levers, churn_bundle, seed)["summary"]
            row.update({
                "영향_가능": int(affected_mask(part, levers).sum()),
                "평균_이탈확률": res["현재_평균이탈확률"],
                "목표후_이탈확률": res["목표후_평균이탈확률"],
                "예상_감소": res["예상_감소인원"],
                "확률상승_비율": res["확률상승_고객비율"],
            })
        core = set((cluster_marketing.get(name) or {}).get("core", {}))
        row["추천_일치"] = bool(core & active)
        row["추천_전략"] = (cluster_marketing.get(name) or {}).get("name", "")
        rows.append(row)

    table = pd.DataFrame(rows).sort_values("예상_감소", ascending=False).reset_index(drop=True)
    table["순위"] = np.arange(1, len(table) + 1)
    top = table["예상_감소"].max()
    table["효과_작음"] = (table["예상_감소"] <= max(top, 0) * 0.15) | (table["예상_감소"] <= 0)
    return table


def hypothesis(customers, levers, churn_bundle, seed=42):
    """실험 전 가설: 실험군 예상 이탈률(목표 달성 시) vs 대조군 예상 이탈률(현재)."""
    s = whatif_customers(customers, levers, churn_bundle, seed)["summary"]
    p_ctrl, p_treat = s["현재_평균이탈확률"], s["목표후_평균이탈확률"]
    return {
        "p_ctrl": p_ctrl,
        "p_treat": p_treat,
        "reduced": s["예상_감소인원"],
        "required_n": required_n_per_group(p_ctrl, p_treat) if p_treat < p_ctrl else None,
    }


def two_prop_test(n_t, x_t, n_c, x_c):
    """실험군·대조군 이탈률 차이 검정 (두 비율 z-검정).

    diff > 0 이면 실험군 이탈률이 더 낮다(좋다)는 뜻이에요.
    """
    n_t, x_t, n_c, x_c = int(n_t), int(x_t), int(n_c), int(x_c)
    if min(n_t, n_c) <= 0:
        raise ValueError("두 그룹의 인원은 각각 1명 이상이어야 합니다.")
    if not (0 <= x_t <= n_t and 0 <= x_c <= n_c):
        raise ValueError("이탈자 수는 0명 이상이며 그룹 인원을 초과할 수 없습니다.")
    p_t, p_c = x_t / n_t, x_c / n_c
    diff = p_c - p_t
    pool = (x_t + x_c) / (n_t + n_c)
    se_pool = np.sqrt(pool * (1 - pool) * (1 / n_t + 1 / n_c))
    z = diff / se_pool if se_pool > 0 else 0.0
    p_value = float(2 * (1 - norm.cdf(abs(z))))
    se = np.sqrt(p_t * (1 - p_t) / n_t + p_c * (1 - p_c) / n_c)
    return {"n_t": n_t, "x_t": x_t, "n_c": n_c, "x_c": x_c, "p_t": p_t, "p_c": p_c,
            "diff": diff, "z": float(z), "p_value": p_value,
            "ci_low": float(diff - 1.96 * se), "ci_high": float(diff + 1.96 * se)}


def decide_verdict(test, required_n=None, alpha=0.05):
    """판정 규칙

    - 효과 있음 : 실험군 이탈률이 낮고, p < 0.05
    - 효과 없음 : 실험군 이탈률이 오히려 높고 p < 0.05 (역효과)
                  또는 차이가 없는데(p ≥ 0.05) 필요 인원을 채운 경우
    - 판단 보류 : 차이가 없는데 필요 인원이 모자란 경우 (인원을 늘려 다시 볼 가치가 있음)
    """
    p, diff = test["p_value"], test["diff"]
    if p < alpha and diff > 0:
        return "효과 있음", "실험군 이탈률이 대조군보다 낮으며, 우연일 가능성은 5% 미만입니다."
    if p < alpha and diff < 0:
        return "효과 없음", "실험군 이탈률이 더 높아 전략의 역효과 가능성이 있습니다."
    enough = required_n is not None and min(test["n_t"], test["n_c"]) >= required_n
    if enough:
        return "효과 없음", "필요 인원을 충족했으나 두 그룹 간 차이가 명확하지 않습니다."
    return "판단 보류", "그룹 간 차이가 명확하지 않고 표본이 부족합니다. 표본 확대 후 재실험이 필요합니다."


def simulate_ab(treat, ctrl, levers, churn_bundle, seed=42):
    """시연 모드: 실험군은 목표 달성 후 확률, 대조군은 현재 확률로 이탈 여부를 뽑은 가상 결과."""
    rng = np.random.default_rng(seed + 7)
    _, after_t, _, _, _ = whatif_probs(treat, levers, churn_bundle, seed)
    before_c = ctrl["churn_prob"].to_numpy(dtype=float)
    return {
        "n_t": len(treat), "x_t": int((rng.random(len(after_t)) < after_t).sum()),
        "n_c": len(ctrl), "x_c": int((rng.random(len(before_c)) < before_c).sum()),
    }
