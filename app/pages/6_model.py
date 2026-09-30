"""KKeeper 모델 — 이탈 예측 모델이 어떻게 판단하는지 보여 주는 참고 페이지 (주소: /model)."""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ui  # noqa: E402
from common.constants import THRESHOLD, seg_display  # noqa: E402
from common.data import load_assets, load_members, load_test_predictions  # noqa: E402

st.set_page_config(page_title="예측 모델 · KKeeper", layout="wide", initial_sidebar_state="collapsed")
T = ui.init("model")
ss = st.session_state

FEATURE_KO = {
    "activity_days": "활동일", "days_since_last_log": "마지막 접속 후 일수", "total_secs": "총 청취시간",
    "total_num_unq": "총 고유곡 수", "total_num_100": "총 완청 곡 수", "avg_daily_secs": "하루 평균 청취시간",
    "avg_daily_unq": "하루 고유곡 수", "avg_daily_complete": "하루 완청 곡 수", "complete_per_unq": "고유곡당 완청",
    "last_is_cancel": "마지막 거래 해지", "cancel_on_last_date": "마지막 날 해지", "last_auto_renew": "자동갱신 여부",
    "cancel_count": "해지 횟수", "avg_payment": "평균 결제금액", "tenure_date": "가입 기간(일)", "has_log": "청취 기록 있음",
    "bd_clean": "나이", "gender_status": "성별", "payment_plan_days": "요금제 일수", "plan_list_price": "요금제 가격",
    "actual_amount_paid": "실결제 금액", "is_auto_renew": "자동갱신", "transaction_count": "거래 횟수",
    "city": "도시", "registered_via": "가입 경로",
}


def ko(name: str) -> str:
    return FEATURE_KO.get(name, name)


# ─────────────────────────────────────────────
# 계산
# ─────────────────────────────────────────────
def evaluation_data() -> tuple[pd.DataFrame | None, str]:
    test = load_test_predictions()
    if test is not None and len(test):
        return test, f"테스트셋 {len(test):,}명"
    members = load_members()
    if "is_churn" in members.columns:
        df = pd.DataFrame({"y_true": members["is_churn"], "y_prob": members["churn_prob"]}).dropna()
        return df, f"분석 표본 {len(df):,}명"
    return None, ""


def metrics_at(df: pd.DataFrame, th: float) -> dict:
    pred = df["y_prob"] >= th
    y = df["y_true"] == 1
    tp, fn = int((pred & y).sum()), int((~pred & y).sum())
    fp, tn = int((pred & ~y).sum()), int((~pred & ~y).sum())
    return {"tp": tp, "fn": fn, "fp": fp, "tn": tn, "flagged": tp + fp,
            "recall": tp / (tp + fn) if tp + fn else np.nan, "precision": tp / (tp + fp) if tp + fp else np.nan}


@st.cache_data(show_spinner=False)
def auc_scores(df: pd.DataFrame) -> tuple[float, float]:
    from sklearn.metrics import average_precision_score, roc_auc_score
    y, p = df["y_true"].to_numpy(), df["y_prob"].to_numpy()
    if len(np.unique(y)) < 2:
        return np.nan, np.nan
    return float(roc_auc_score(y, p)), float(average_precision_score(y, p))


def contributions(model, X: pd.DataFrame) -> np.ndarray | None:
    """LightGBM이 계산하는 SHAP 값(각 피처가 이탈 쪽으로 민 정도, log-odds). 안 되면 None."""
    for predictor in (model, getattr(model, "booster_", None)):
        if predictor is None:
            continue
        try:
            out = np.asarray(predictor.predict(X, pred_contrib=True))
            if out.ndim == 2 and out.shape[1] == X.shape[1] + 1:
                return out[:, :-1]
        except Exception:
            continue
    return None


@st.cache_data(show_spinner="요인별 영향 계산 중…")
def global_importance() -> tuple[pd.DataFrame, str]:
    assets = load_assets()
    model, feats = assets["bundle"]["model"], assets["bundle"]["features"]
    sample = assets["kk"][feats].sample(min(2000, len(assets["kk"])), random_state=42)
    shap = contributions(model, sample)
    if shap is not None:
        imp = pd.DataFrame({"feature": feats, "value": np.abs(shap).mean(axis=0)})
        kind = "SHAP 평균 기여도 (|값| 평균, 표본 2,000명)"
    else:
        raw = getattr(model, "feature_importances_", None)
        if raw is None:
            return pd.DataFrame(), ""
        imp = pd.DataFrame({"feature": feats, "value": np.asarray(raw, dtype=float)})
        kind = "모델 내장 중요도 (SHAP 계산이 안 되는 모델이라 대신 표시)"
    imp["label"] = imp["feature"].map(ko)
    return imp.sort_values("value", ascending=False).head(10), kind


def calibration(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["bin"] = pd.cut(work["y_prob"], bins=np.linspace(0, 1, 11), include_lowest=True)
    g = work.groupby("bin", observed=True).agg(pred=("y_prob", "mean"), actual=("y_true", "mean"), n=("y_true", "size")).reset_index()
    return g[g["n"] > 0]


# ─────────────────────────────────────────────
# 화면
# ─────────────────────────────────────────────
ui.render_header()

# 모델 페이지: 위험 기준 / 혼동행렬 두 카드의 외곽 높이 통일
st.markdown("""
<style>
.st-key-kkbox-threshold,
.st-key-kkbox-confusion {
    height: 320px !important;
    min-height: 320px !important;
    box-sizing: border-box !important;
}
/* 마지막 행의 두 컬럼을 같은 높이로 늘림 */
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-kkbox-lookup) {
    align-items: stretch !important;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-kkbox-lookup)
    > [data-testid="stColumn"] {
    align-self: stretch !important;
    display: flex !important;
    flex-direction: column !important;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-kkbox-lookup)
    > [data-testid="stColumn"] > div {
    flex: 1 1 auto !important;
    display: flex !important;
    flex-direction: column !important;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-kkbox-lookup)
    > [data-testid="stColumn"] > div > [data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-kkbox-lookup)
    > [data-testid="stColumn"] > div > [data-testid="stVerticalBlockBorderWrapper"] {
    flex: 1 1 auto !important;
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
}
.st-key-kkbox-lookup,
.st-key-kkbox-limits {
    min-height: 580px !important;
    box-sizing: border-box !important;
    flex: 1 1 auto !important;
    height: 100% !important;
}
/* 세 지표 값: 같은 23px, 유형도 줄바꿈 없이 표시 */
.kk-model-customer-kpis .kk-kpi-val,
.kk-model-customer-kpis .kk-model-segment {
    font-family: Rubik, 'IBM Plex Sans KR', sans-serif !important;
    font-size: 23px !important;
    font-weight: 700 !important;
    line-height: 1.35 !important;
    letter-spacing: -0.035em;
    white-space: nowrap !important;
}
/* 상단 성능 지표 카드 제목 크기 */
.kk-model-metrics .kk-kpi-label {
    font-size: 15px !important;
    font-weight: 600 !important;
}

</style>
""", unsafe_allow_html=True)

with st.container(key="kk-body"):
    try:
        eval_df, eval_label = evaluation_data()
    except (FileNotFoundError, ValueError) as error:
        ui.show_missing_files(error)
        st.stop()

    chips = "".join(ui.badge(t, "neutral") for t in ["LightGBM", "KKBox 데이터", eval_label or "평가 데이터 없음"])
    ui.html(f'<div class="kk" style="display:flex; justify-content:space-between; align-items:flex-end; gap:24px; flex-wrap:wrap">'
            f'{ui.page_title("고객 이탈 예측 모델 분석", "LightGBM 모델의 성능과 주요 영향 요인을 분석하여 고객 위험도 평가와 전략 매칭에 활용", "참고 · 예측 모델" )}'
            f'<div style="display:flex; gap:8px">{chips}</div></div>')

    # 페이지 소개와 평가 지표 사이 여백
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    if eval_df is None:
        st.info("실제 이탈 여부(is_churn) 또는 test_predictions.csv(y_true, y_prob)가 없어 성능 지표를 계산할 수 없습니다.")
    else:
        if eval_label.startswith("분석 표본"):
            st.caption("data/processed/test_predictions.csv(y_true, y_prob)가 없어 전체 분석 표본으로 계산했습니다. "
                       "학습 데이터가 포함되면 성능이 과대평가될 수 있습니다. 테스트셋 예측 저장 시 해당 데이터로 계산합니다.")
        # 평가 데이터 안내문과 지표 카드 사이 여백
        if eval_label.startswith("분석 표본"):
            st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        roc, pr = auc_scores(eval_df)
        base = metrics_at(eval_df, THRESHOLD)
        ui.html(f"""<div class="kk kk-model-metrics" style="display:grid; grid-template-columns:repeat(4,1fr); gap:16px">
<div class="kk-card">{ui.kpi("ROC-AUC", f"{roc:.3f}", "이탈·유지 회원 구분 성능")}</div>
<div class="kk-card">{ui.kpi("PR-AUC", f"{pr:.3f}", "불균형 데이터 평가 지표")}</div>
<div class="kk-card">{ui.kpi(f"재현율 · 기준 {THRESHOLD * 100:.2f}%", ui.pct(base["recall"]), "실제 이탈자 중 위험 회원 탐지 비율", T["accent"])}</div>
<div class="kk-card">{ui.kpi(f"정밀도 · 기준 {THRESHOLD * 100:.2f}%", ui.pct(base["precision"]), "위험으로 본 회원 중 실제 이탈 비율", T["accent"])}</div></div>""")

        # 상단 지표 카드와 위험 기준/혼동행렬 카드 사이 여백
        st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
        left, right = st.columns([1.4, 1])
        with left, st.container(key="kkbox-threshold"):
            ui.html('<div class="kk"><div class="kk-card-title">위험 기준 조정</div>'
                    '<div class="kk-card-note">기준 하향 시 캠페인 대상 및 오탐이 증가합니다. 변경값은 시뮬레이션에만 적용됩니다.</div></div>')
            th = st.slider("위험 기준", 0.05, 0.95, float(THRESHOLD), 0.01, format="%.2f", key="m_th")
            m = metrics_at(eval_df, th)
            ui.html(f"""<div class="kk" style="display:grid; grid-template-columns:repeat(3,1fr); gap:10px">
<div class="kk-card" style="padding:14px; background:{T['input_bg']}">{ui.kpi("위험 회원", f"{m['flagged']:,}명")}</div>
<div class="kk-card" style="padding:14px; background:{T['input_bg']}">{ui.kpi("재현율", ui.pct(m['recall']))}</div>
<div class="kk-card" style="padding:14px; background:{T['input_bg']}">{ui.kpi("정밀도", ui.pct(m['precision']))}</div></div>""")
        with right, st.container(key="kkbox-confusion"):
            ui.html(f'<div class="kk"><div class="kk-card-title">혼동행렬</div><div class="kk-card-note">기준 {th * 100:.2f}% · {eval_label}</div></div>')

            def cell(n, label, good):
                bg = f"background:{T['accent_soft']}; color:{T['accent_on_soft']};" if good else f"background:{T['input_bg']}; border:1px solid {T['line']};"
                return (f'<div style="height:84px; border-radius:12px; {bg} display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px">'
                        f'<span class="kk-num-font" style="font-size:20px; font-weight:700">{n:,}</span><span style="font-size:12px">{label}</span></div>')
            ui.html(f"""<div class="kk" style="display:grid; grid-template-columns:80px 1fr 1fr; gap:8px; font-size:13px">
<span></span><span style="text-align:center; color:{T['muted']}">위험으로 예측</span><span style="text-align:center; color:{T['muted']}">일반으로 예측</span>
<span style="align-self:center; color:{T['muted']}">실제 이탈</span>{cell(m['tp'], '정탐', True)}{cell(m['fn'], '미탐', False)}
<span style="align-self:center; color:{T['muted']}">실제 유지</span>{cell(m['fp'], '오탐', False)}{cell(m['tn'], '정상 분류', True)}</div>""")

    # 평가 카드와 요인/보정 그래프 사이 여백
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    # 요인 · 보정
    try:
        assets = load_assets()
    except FileNotFoundError as error:
        assets = None
        st.caption(f"모델 파일이 없어 요인 분석과 개별 고객 분석을 생략합니다: {error}")

    left, right = st.columns([1.4, 1])
    if assets is not None:
        with left, st.container(key="kkbox-shap"):
            imp, kind = global_importance()
            ui.html(f'<div class="kk"><div class="kk-card-title">이탈에 영향을 주는 요인</div><div class="kk-card-note">{kind}</div></div>')
            if imp.empty:
                st.caption("이 모델은 요인 중요도를 계산할 수 없습니다.")
            else:
                bars = alt.Chart(imp).mark_bar(cornerRadiusEnd=4, color=T["seg"][0]).encode(
                    x=alt.X("value:Q", title=None, axis=None),
                    y=alt.Y("label:N", sort="-x", title=None),
                    tooltip=[alt.Tooltip("label:N", title="요인"), alt.Tooltip("value:Q", title="영향", format=".4f")],
                ).properties(height=300)
                st.altair_chart(ui.altair_theme(bars), **ui.WIDE, theme=None)
    if eval_df is not None:
        with right, st.container(key="kkbox-calib"):
            ui.html('<div class="kk"><div class="kk-card-title">예측 확률 신뢰도</div>'
                    '<div class="kk-card-note">점선에 가까울수록 예측 확률과 실제 이탈률이 일치합니다.</div></div>')
            cal = calibration(eval_df)
            line = alt.Chart(cal).mark_line(point=True, color=T["accent"]).encode(
                x=alt.X("pred:Q", title="예측 이탈확률", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format=".0%")),
                y=alt.Y("actual:Q", title="실제 이탈률", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format=".0%")),
                tooltip=[alt.Tooltip("pred:Q", title="예측", format=".1%"), alt.Tooltip("actual:Q", title="실제", format=".1%"),
                         alt.Tooltip("n:Q", title="회원 수", format=",")])
            diag = alt.Chart(pd.DataFrame({"x": [0, 1], "y": [0, 1]})).mark_line(strokeDash=[4, 4], color=T["strong_border"]).encode(x="x:Q", y="y:Q")
            st.altair_chart(ui.altair_theme((diag + line).properties(height=300)), **ui.WIDE, theme=None)

    # 그래프 카드와 계산 과정 사이 여백
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)

    # 계산 과정
    with st.container(key="kkbox-pipeline"):
        ui.html('<div class="kk"><div class="kk-card-title">고객 매칭 산정 방식</div>'
                '<div class="kk-card-note">고객을 4개 유형으로 나눈 뒤, 1단계 입력이 2단계 추천 순위와 3단계 실험 가설이 되는 과정</div></div>')
        arrow = f'<div aria-hidden="true" style="display:flex; align-items:center; color:{T["num"]}">{ui.icon("arrow", 22)}</div>'

        def box(eyebrow, title, sub, tone=""):
            styles = {"warn": (T["warn_line"], T["warn_bg"], T["warn_text"]), "accent": (T["accent_line"], T["accent_soft"], T["accent_on_soft"])}
            bd, bg, fg = styles.get(tone, (T["chip_border"], T["input_bg"], T["subtle"]))
            return (f'<div style="flex:1; padding:16px; border-radius:14px; border:1px solid {bd}; background:{bg}; display:flex; flex-direction:column; gap:6px">'
                    f'<span style="font-size:12px; color:{fg}">{eyebrow}</span><span style="font-size:15px; font-weight:700">{title}</span>'
                    f'<span style="font-size:12px; color:{fg if tone else T["muted"]}">{sub}</span></div>')
        ui.html('<div class="kk" style="display:flex; align-items:stretch; gap:10px">'
                + arrow.join([
                    box("사전 준비 · 별도 모델", "고객 유형 4가지", "K-Means · 거래·결제·이용 행동<br> 17개 지표 표준화"),
                    box("1단계 입력", "전략 유형 · 목적", "예: 콘텐츠 추천 · 재방문 유도"),
                    box("행동 목표로 변환", "행동 변화 가정", "예: 고유곡 +10% · 활동일 +10%<br>(팀 가정값 · 조정 가능)", "warn"),
                    box("유형마다 적용", "이탈 모델", "LightGBM으로 목표 적용 전·후<br> 이탈확률 계산", "accent"),
                    box("2단계 · 3단계", "추천 순위 · 실험 가설", "유형별 예상 이탈 감소 → 필요 인원 계산"),
                ]) + "</div>")

    # 계산 과정과 고객 조회/주의점 카드 사이 여백
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    left, right = st.columns([1, 1])
    if assets is not None:
        with left, st.container(key="kkbox-lookup"):
            ui.html('<div class="kk"><div class="kk-card-title">개별 고객 분석</div>'
                    '<div class="kk-card-note">회원 ID 입력 시 이탈확률과 판단 근거(SHAP)를 제공합니다.</div></div>')
            c1, c2 = st.columns([3, 1.3], vertical_alignment="bottom")
            with c2:
                if st.button("예시 회원", key="m_sample", **ui.WIDE):
                    risk = assets["risk"]
                    ss["m_msno"] = str(risk.sort_values("churn_prob", ascending=False)["msno"].iloc[0]) if len(risk) else ""
            with c1:
                msno = st.text_input("회원 ID (msno)", key="m_msno", placeholder="msno 입력")
            if msno:
                kk = assets["kk"]
                row = kk[kk["msno"].astype(str) == msno.strip()]
                if row.empty:
                    st.warning("해당 회원을 찾을 수 없습니다.")
                else:
                    r = row.iloc[0]
                    seg_row = assets["risk"][assets["risk"]["msno"].astype(str) == msno.strip()]
                    seg = seg_display(seg_row["segment"].iloc[0]) if len(seg_row) else "위험 회원 아님"
                    risky = r["churn_prob"] >= THRESHOLD
                    ui.html(f'<div class="kk kk-model-customer-kpis" style="display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px">'
                            f'{ui.kpi("이탈확률", ui.pct(r["churn_prob"]), color=T["accent"] if risky else None)}'
                            f'{ui.kpi("판정", "위험" if risky else "일반")}'
                            f'<div style="min-width:0"><div class="kk-kpi-label">유형</div>'
                            f'<div class="kk-model-segment" style="font-weight:700; margin-top:6px">{ui.esc(seg)}</div></div></div>')
                    feats = assets["bundle"]["features"]
                    shap = contributions(assets["bundle"]["model"], row[feats])
                    if shap is not None:
                        contrib = pd.Series(shap[0], index=feats)
                        top = contrib.reindex(contrib.abs().sort_values(ascending=False).index).head(6)
                        rows = []
                        for f, v in top.items():
                            val = r[f]
                            shown = f"{float(val):,.2f}" if isinstance(val, (int, float, np.number)) and not isinstance(val, bool) else ui.esc(str(val))
                            direction = (f'<span style="color:{T["bad_text"]}">▲ 이탈 쪽</span>' if v > 0
                                         else f'<span style="color:{T["good_text"]}">▼ 유지 쪽</span>')
                            rows.append([ko(f), shown, direction, f"{v:+.3f}"])
                        ui.html(f'<div class="kk">{ui.table(["요인", "이 회원 값", "방향", "SHAP"], rows, right={1, 3})}</div>')
                    else:
                        st.caption("이 모델은 회원별 판단 근거(SHAP)를 계산할 수 없습니다.")

    with right, st.container(key="kkbox-limits"):
        ui.html('<div class="kk"><div class="kk-card-title">한계와 주의점</div></div>')
        items = [
            ("상관관계 기반 분석", "모델은 행동과 이탈 간 상관관계를 학습합니다. 인과관계는 A/B 테스트로 검증해야 합니다."),
            ("행동 변화 폭 가정", "‘고유곡 +10%’ 등의 목표는 팀에서 설정한 가정값이며 실제 캠페인 결과와 다를 수 있습니다."),
            ("매칭 순위 가설", "전략의 실제 효과는 3단계 A/B 테스트의 실측 결과로 판정합니다."),
            ("시연 모드의 한계", "이탈 모델 기반 가상 결과로, ‘시뮬레이션’ 표시가 적용됩니다."),
            ("역방향 반응 고객", "일부 고객은 목표 적용 후 이탈확률이 상승할 수 있습니다. 비중이 30%를 초과하면 매칭 화면에 경고가 표시됩니다."),
            ("데이터 기간", "KKBox 과거 기록으로 학습한 모델이므로 현재 고객 행동과 차이가 있을 수 있습니다."),
        ]
        ui.html('<div class="kk" style="display:flex; flex-direction:column; gap:8px">' + "".join(
            f'<div style="display:flex; gap:12px; padding:12px 14px; border-radius:12px; background:{T["input_bg"]}">'
            f'<span class="kk-num-font" style="font-weight:700; color:{T["warn_text"]}">{i}</span><div style="display:flex; flex-direction:column; gap:3px">'
            f'<span style="font-size:14px; font-weight:700">{t}</span><span style="font-size:13px; color:{T["muted"]}; line-height:1.5">{d}</span></div></div>'
            for i, (t, d) in enumerate(items, 1)) + "</div>")
