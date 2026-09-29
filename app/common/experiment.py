"""KKeeper 마케팅 시뮬레이션 공통 함수.

노트북에서 검증한 Starbucks 행동 변화 모델과 KKBOX 이탈 모델을
Streamlit 화면에서도 동일하게 사용할 수 있도록 분리한 모듈입니다.
시뮬레이션 결과를 파일이나 데이터베이스에 저장하는 책임은 갖지 않습니다.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


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
        a, b = group_a[col], group_b[col]
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



def lever_eligible(customers):
    """레버마다 적용 대상이 되는 고객 수"""
    return {
        "auto_renew_on": int((customers["last_auto_renew"] == 0).sum()),
        "cancel_stop": int((customers["last_is_cancel"] == 1).sum()),
        "activity_up": int((customers["activity_days"] > 0).sum()),
        "revisit": int((customers["days_since_last_log"] > 0).sum()),
    }


def apply_levers(X, levers, seed=42):
    """레버 설정대로 이탈 모델 입력 피처를 바꾼다."""
    X = X.copy()
    rng = np.random.default_rng(seed)

    def flip(cols, from_v, to_v, pct):
        idx = X.index[X[cols[0]] == from_v]
        n = int(round(len(idx) * pct / 100))
        if n > 0:
            chosen = rng.choice(idx, size=n, replace=False)
            for c in cols:
                if c in X:
                    X.loc[chosen, c] = to_v

    if levers.get("auto_renew_on"):
        flip(["last_auto_renew"], 0, 1, levers["auto_renew_on"])
    if levers.get("cancel_stop"):
        flip(["last_is_cancel", "cancel_on_last_date"], 1, 0, levers["cancel_stop"])

    if levers.get("activity_up"):
        f = 1 + levers["activity_up"] / 100
        for c in ["total_secs", "total_num_100", "total_num_unq"]:
            X[c] = X[c] * f
        X["activity_days"] = (X["activity_days"] * f).clip(upper=90).round()
        d = X["activity_days"].replace(0, np.nan)
        X["avg_daily_secs"] = X["total_secs"] / d
        X["avg_daily_complete"] = X["total_num_100"] / d
        X["avg_daily_unq"] = X["total_num_unq"] / d

    if levers.get("revisit"):
        X["days_since_last_log"] = (X["days_since_last_log"] * (1 - levers["revisit"] / 100)).round()

    return X


WHATIF_METRICS = {
    "last_auto_renew": "자동갱신 켬 비율",
    "last_is_cancel": "마지막 거래 해지 비율",
    "activity_days": "평균 활동일",
    "days_since_last_log": "마지막 접속 후 평균 일수",
}


def whatif_customers(customers, levers, churn_bundle, seed=42):

    model, feats = churn_bundle["model"], churn_bundle["features"]
    X_before = customers[feats]
    X_after = apply_levers(X_before, levers, seed)

    change = model.predict_proba(X_after)[:, 1] - model.predict_proba(X_before)[:, 1]
    before = customers["churn_prob"].to_numpy()
    after = np.clip(before + change, 0, 1)

    behavior = pd.DataFrame({
        "행동 지표": list(WHATIF_METRICS.values()),
        "현재": [X_before[c].mean() for c in WHATIF_METRICS],
        "목표 적용 후": [X_after[c].mean() for c in WHATIF_METRICS],
    })

    return {
        "summary": {
            "고객수": len(customers),
            "현재_평균이탈확률": before.mean(),
            "목표후_평균이탈확률": after.mean(),
            "현재_예상이탈자": before.sum(),
            "목표후_예상이탈자": after.sum(),
            "예상_감소인원": before.sum() - after.sum(),
            "확률상승_고객비율": float((change > 1e-9).mean()),
        },
        "behavior": behavior,
    }



CLUSTER_GOALS = {
    "저활동·단기 구독형": "이용 활성화",
    "반복 거래·취소 위험형": "즉각적 이탈 방어",
    "장기 플랜·고결제 고위험형": "고가치 고객 유지",
    "장기 관계·고빈도 거래형": "충성도 강화",
}

CLUSTER_MARKETING = {
    "저활동·단기 구독형": [
        {"id": "reco_playlist", "name": "개인화 추천·플레이리스트",
         "desc": "최근 이용 콘텐츠 기반으로 음악과 플레이리스트를 추천해 청취를 늘립니다.",
         "levers": {"activity_up": 15}},
        {"id": "revisit_msg", "name": "미접속 재방문 유도 메시지",
         "desc": "일정 기간 접속하지 않으면 재방문을 유도하는 메시지를 보냅니다.",
         "levers": {"revisit": 30}},
        {"id": "mission", "name": "이용 유도 미션 프로모션",
         "desc": "연속 이용·신규 콘텐츠 청취 미션으로 이용 습관을 만듭니다.",
         "levers": {"activity_up": 10, "revisit": 20}},
    ],
    "반복 거래·취소 위험형": [
        {"id": "retention_offer", "name": "취소 시점 리텐션 오퍼",
         "desc": "취소를 시도할 때 할인·무료 이용기간 연장을 즉시 제안합니다.",
         "levers": {"cancel_stop": 30}},
        {"id": "pause_plan", "name": "일시정지·저가 플랜 전환",
         "desc": "취소 화면에서 해지 대신 일시정지나 저가 플랜을 제안합니다.",
         "levers": {"cancel_stop": 20, "revisit": 15}},
        {"id": "reason_offer", "name": "취소 사유별 맞춤 혜택",
         "desc": "취소 사유(가격·콘텐츠·이용경험)를 수집해 원인에 맞는 혜택을 제공합니다.",
         "levers": {"cancel_stop": 25}},
    ],
    "장기 플랜·고결제 고위험형": [
        {"id": "early_renewal", "name": "선제적 갱신·장기구독 할인",
         "desc": "이탈 위험이 높아지는 시점에 갱신 혜택과 장기구독 할인을 제안합니다.",
         "levers": {"auto_renew_on": 20}},
        {"id": "vip", "name": "VIP·독점 콘텐츠 혜택",
         "desc": "고결제 고객에게 독점·선공개 콘텐츠 등 차별화된 보상을 제공합니다.",
         "levers": {"auto_renew_on": 10, "activity_up": 5}},
        {"id": "resubscribe", "name": "만료 전 재구독 캠페인",
         "desc": "이용권 만료일 이전에 개인화된 재구독·갱신 캠페인을 집중 실행합니다.",
         "levers": {"auto_renew_on": 15}},
    ],
    "장기 관계·고빈도 거래형": [
        {"id": "loyalty", "name": "장기 고객 로열티 리워드",
         "desc": "가입 기간과 이용 실적에 따른 보상으로 관계를 유지합니다.",
         "levers": {"auto_renew_on": 15}},
        {"id": "membership", "name": "전용 할인·멤버십 등급",
         "desc": "장기 고객 전용 할인과 멤버십 등급 혜택을 강화합니다.",
         "levers": {"auto_renew_on": 10, "activity_up": 5}},
        {"id": "recap", "name": "개인화 청취 리캡",
         "desc": "누적 이용기간·청취 기록을 돌아보는 콘텐츠로 이용을 다시 활성화합니다.",
         "levers": {"activity_up": 10, "revisit": 15}},
    ],
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
    active = int((customers["activity_days"] > 0).sum())
    return {
        "song_variety": active,
        "activity_up": active,
        "listen_time": active,
        "revisit": int((customers["days_since_last_log"] > 0).sum()),
        "cancel_stop": int((customers["last_is_cancel"] == 1).sum()),
        "auto_renew_on": int((customers["last_auto_renew"] == 0).sum()),
    }


def _sync_totals(X, orig):
    """하루 평균 × 활동일 = 총량이 되도록 맞춘다"""
    d = X["activity_days"]
    ok = d > 0
    X.loc[ok, "total_secs"] = X.loc[ok, "avg_daily_secs"] * d[ok]
    X.loc[ok, "total_num_unq"] = (X.loc[ok, "avg_daily_unq"] * d[ok]).round()
    X.loc[ok, "total_num_100"] = (X.loc[ok, "avg_daily_complete"] * d[ok]).round()
    X.loc[ok, "complete_per_unq"] = X.loc[ok, "total_num_100"] / X.loc[ok, "total_num_unq"].replace(0, np.nan)
    for c in ["total_secs", "total_num_unq", "total_num_100", "complete_per_unq"]:
        X.loc[~ok, c] = orig.loc[~ok, c]
    return X


def apply_levers(X, levers, seed=42):
    """레버 설정대로 이탈 모델 입력 피처를 바꾼다."""
    orig = X
    X = X.copy()
    rng = np.random.default_rng(seed)

    def flip(cols, from_v, to_v, pct):
        idx = X.index[X[cols[0]] == from_v]
        n = int(round(len(idx) * pct / 100))
        if n > 0:
            chosen = rng.choice(idx, size=n, replace=False)
            for c in cols:
                X.loc[chosen, c] = to_v

    if levers.get("song_variety"):
        X["avg_daily_unq"] *= 1 + levers["song_variety"] / 100
    if levers.get("listen_time"):
        X["avg_daily_secs"] *= 1 + levers["listen_time"] / 100
    if levers.get("activity_up"):
        X["activity_days"] = (X["activity_days"] * (1 + levers["activity_up"] / 100)).clip(upper=90).round()
    if levers.get("revisit"):
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

from scipy.stats import norm


def required_n_per_group(p1, p2, alpha=0.05, power=0.8):
    """두 그룹 이탈률 차이(p1 vs p2)를 확인하는 데 필요한 그룹당 인원"""
    if abs(p1 - p2) < 1e-9:
        return None
    z_a = norm.ppf(1 - alpha / 2)
    z_b = norm.ppf(power)
    n = (z_a + z_b) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / (p1 - p2) ** 2
    return int(np.ceil(n))


