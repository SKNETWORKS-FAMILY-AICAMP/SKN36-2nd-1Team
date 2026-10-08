"""KKeeper 마케팅 시뮬레이션 공통 함수.

KKBOX 이탈 모델을 Streamlit 화면에서 공통으로 쓰기 위해 분리한 모듈입니다.
시뮬레이션 결과를 파일이나 데이터베이스에 저장하는 책임은 갖지 않습니다.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.model_selection import train_test_split


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
