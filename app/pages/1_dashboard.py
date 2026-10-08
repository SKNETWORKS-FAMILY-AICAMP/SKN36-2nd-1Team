"""KKeeper 현황 — 전체 회원 이탈 현황과 진행 중인 실험 (주소: /dashboard)."""

from __future__ import annotations

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ui  # noqa: E402
from common import db  # noqa: E402
from common.constants import SEGMENTS, THRESHOLD, seg_display  # noqa: E402
from common.data import SEGMENT_SUMMARY_PATH, load_members, load_segment_counts  # noqa: E402

st.set_page_config(page_title="현황 · KKeeper", layout="wide", initial_sidebar_state="collapsed")
T = ui.init("dashboard")


# ─────────────────────────────────────────────
# 집계
# ─────────────────────────────────────────────
def probability_bins(members: pd.DataFrame) -> pd.DataFrame:
    """위험 기준선을 구간 경계에 넣어 회원 분포를 집계."""
    edges = [0, .10, THRESHOLD, .50, .75, 1.0000001]
    names = ["0–10%", f"10–{THRESHOLD * 100:.2f}%", f"{THRESHOLD * 100:.2f}–50%", "50–75%", "75–100%"]
    cols = ["churn_prob"] + (["is_churn"] if "is_churn" in members.columns else [])
    work = members[cols].dropna().copy()
    work["bin"] = pd.cut(work["churn_prob"], bins=edges, include_lowest=True, right=False, labels=names)
    agg = {"customer_count": ("churn_prob", "size")}
    if "is_churn" in work.columns:
        agg["actual_churn_rate"] = ("is_churn", "mean")
    grouped = work.groupby("bin", observed=False).agg(**agg).reset_index()
    grouped["probability_range"] = grouped["bin"].astype(str)
    grouped["member_share"] = grouped["customer_count"] / max(len(work), 1)
    return grouped


def activity_summary(members: pd.DataFrame) -> pd.DataFrame:
    metrics = {"activity_days": "활동일", "days_since_last_log": "마지막 접속 후"}
    available = [c for c in metrics if c in members.columns]
    if not available or "is_churn" not in members.columns:
        return pd.DataFrame()
    work = members[["is_churn", *available]].copy()
    for c in available:
        work[c] = pd.to_numeric(work[c], errors="coerce")
    g = work.groupby("is_churn")[available].mean().reset_index()
    g["status"] = g["is_churn"].map({0: "유지 회원", 1: "이탈 회원"})
    out = g.melt(id_vars=["is_churn", "status"], value_vars=available, var_name="metric", value_name="days")
    out["metric_name"] = out["metric"].map(metrics)
    return out


def renewal_summary(members: pd.DataFrame) -> pd.DataFrame:
    if "last_auto_renew" not in members.columns or "is_churn" not in members.columns:
        return pd.DataFrame()
    work = members[["last_auto_renew", "is_churn"]].copy()
    work["last_auto_renew"] = pd.to_numeric(work["last_auto_renew"], errors="coerce")
    work = work[work["last_auto_renew"].isin([0, 1])]
    out = work.groupby("last_auto_renew", as_index=False).agg(customer_count=("is_churn", "size"), churn_rate=("is_churn", "mean"))
    out["renewal"] = out["last_auto_renew"].map({0: "자동갱신 OFF", 1: "자동갱신 ON"})
    return out


# ─────────────────────────────────────────────
# 화면 조각
# ─────────────────────────────────────────────
def donut_svg(rate: float) -> str:
    c = 2 * 3.14159 * 46
    arc = max(0.0, min(1.0, rate)) * c
    return f"""<svg width="112" height="112" viewBox="0 0 112 112" role="img" aria-label="실제 이탈 비율 {rate * 100:.1f}%">
<circle cx="56" cy="56" r="46" fill="none" stroke="{T['good_bg']}" stroke-width="14"/>
<circle cx="56" cy="56" r="46" fill="none" stroke="{T['bad_text']}" stroke-width="14" stroke-linecap="round"
 stroke-dasharray="{arc:.1f} {c - arc:.1f}" transform="rotate(-90 56 56)"/>
<text x="56" y="54" text-anchor="middle" font-family="Rubik, sans-serif" font-size="17" font-weight="700" fill="{T['text']}">{rate * 100:.1f}%</text>
<text x="56" y="70" text-anchor="middle" font-family="IBM Plex Sans KR, sans-serif" font-size="10" fill="{T['muted']}">실제 이탈</text>
</svg>"""


def compare_html(members: pd.DataFrame) -> str:
    total = len(members)
    risk = int(members["risk"].sum())
    left = f"""<div style="display:flex; flex-direction:column; gap:10px">
<span class="kk-eyebrow">모델 예측 · 아직 이탈 전</span>
<span style="display:flex; align-items:baseline; gap:8px"><span class="kk-num-font" style="font-size:32px; font-weight:700; color:{T['accent']}">{risk:,}명</span>
<span style="font-size:13px; color:{T['muted']}">위험 회원 ({risk / max(total, 1) * 100:.1f}%)</span></span>
<span class="kk-cap">이탈확률 {THRESHOLD * 100:.2f}% 이상 · 전체 회원 {total:,}명 중</span></div>"""
    if "is_churn" not in members.columns:
        right = (f'<div class="kk-cap" style="text-align:right">실제 이탈 여부(is_churn) 컬럼이 없어<br>실측 결과를 표시할 수 없습니다.</div>')
        middle = ""
    else:
        churn = int(members["is_churn"].sum())
        rate = churn / max(total, 1)
        middle = f'<div style="display:flex; flex-direction:column; align-items:center; gap:6px">{donut_svg(rate)}<span class="kk-cap">분석 표본 기준</span></div>'
        right = f"""<div style="display:flex; flex-direction:column; gap:10px; align-items:flex-end; text-align:right">
<span class="kk-eyebrow">실측 결과</span>
<span style="display:flex; align-items:baseline; gap:8px"><span class="kk-num-font" style="font-size:24px; font-weight:700; color:{T['bad_text']}">{churn:,}명</span>
<span style="font-size:13px; color:{T['muted']}">실제 이탈 ({rate * 100:.2f}%)</span></span>
<span style="display:flex; align-items:baseline; gap:8px"><span class="kk-num-font" style="font-size:24px; font-weight:700; color:{T['good_text']}">{total - churn:,}명</span>
<span style="font-size:13px; color:{T['muted']}">유지 회원</span></span></div>"""
    return (f'<div class="kk kk-card" style="display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:32px; padding:26px 36px">'
            f'{left}{middle}{right}</div>')


def strip_html(total: int, c: dict) -> str:
    def cell(label, value, color=None):
        style = f"color:{color};" if color else ""
        return (f'<div><div class="kk-kpi-label">{label}</div>'
                f'<div class="kk-num-font" style="font-size:21px; font-weight:700; margin-top:6px; {style}">{value}</div></div>')
    running, waiting, verified = c["running"], c["waiting"], c["verified"]
    cells = [cell("전체 회원", f"{total:,}명"), cell("진행 중인 실험", f"{running}건"),
             cell("결과 입력 대기", f"{waiting}건", T["warn_text"]), cell("검증된 전략", f"{verified}건", T["good_text"])]
    return '<div class="kk kk-strip">' + "<span></span>".join(cells) + "</div>"


def chart_head(title: str, note: str, badge: str = "") -> None:
    b = ui.badge(badge, "accent") if badge else ""
    ui.html(f'<div class="kk" style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px">'
            f'<div><div class="kk-card-title">{title}</div><div class="kk-card-note">{note}</div></div>{b}</div>')


def segments_html(counts: pd.DataFrame) -> str:
    counts = counts.set_index("segment")
    top = max(float(counts["인원"].max()) if len(counts) else 0, 1)
    rows = []
    for name in SEGMENTS:
        n = float(counts["인원"].get(name, 0) or 0) if len(counts) else 0
        p = counts["평균_이탈확률"].get(name) if len(counts) and "평균_이탈확률" in counts else None
        color = ui.seg_color(name)
        prob = f" · 평균 {ui.pct(p)}" if p is not None and pd.notna(p) else ""
        rows.append(f'<div style="display:flex; flex-direction:column; gap:6px; padding:14px 2px">'
                    f'<span style="display:flex; justify-content:space-between; font-size:14px">'
                    f'<span style="display:inline-flex; align-items:center; gap:8px"><span class="kk-dot" style="background:{color}"></span>{seg_display(name)}</span>'
                    f'<span style="color:{T["muted"]}">{int(n):,}명{prob}</span></span>{ui.track(n / top, color, 6)}</div>')
    return "".join(rows)


# 유형별 고객 프로필: (회원 데이터 컬럼, risk_segment_summary.csv 컬럼, 표시 이름, 형식)
PROFILE_METRICS = [
    ("churn_prob", "평균_이탈확률", "평균 이탈확률", "pct"),
    ("activity_days", "평균_활동일", "활동일 (90일 중)", "days"),
    ("days_since_last_log", "마지막접속후_평균일수", "마지막 접속 후", "days"),
    ("cancel_count", "평균_해지횟수", "평균 해지 횟수", "count"),
    ("avg_payment", "평균_결제금액", "평균 결제금액", "money"),
    ("last_auto_renew", None, "자동갱신 켬 비율", "pct"),
    ("last_is_cancel", None, "마지막 거래가 해지인 비율", "pct"),
]


def segment_profiles(members: pd.DataFrame) -> list[tuple]:
    """유형별 평균 지표. 회원 데이터에 컬럼이 있으면 거기서, 없으면 risk_segment_summary.csv에서 가져와요."""
    part = members[members["segment"].isin(SEGMENTS)] if "segment" in members.columns else members.iloc[0:0]
    summary = None
    if SEGMENT_SUMMARY_PATH.exists():
        summary = pd.read_csv(SEGMENT_SUMMARY_PATH, encoding="utf-8-sig")
        summary = summary[summary["segment"].isin(SEGMENTS)].set_index("segment") if "segment" in summary.columns else None
    rows = []
    for col, csv_col, label, fmt in PROFILE_METRICS:
        if col in part.columns and len(part):
            values = pd.to_numeric(part[col], errors="coerce")
            by_seg = values.groupby(part["segment"]).mean()
            vals = {name: by_seg.get(name) for name in SEGMENTS}
            overall = values.mean()
        elif summary is not None and csv_col and csv_col in summary.columns:
            col_vals = pd.to_numeric(summary[csv_col], errors="coerce")
            vals = {name: col_vals.get(name) for name in SEGMENTS}
            weights = pd.to_numeric(summary.get("인원"), errors="coerce") if "인원" in summary.columns else None
            overall = (col_vals * weights).sum() / weights.sum() if weights is not None and weights.sum() else col_vals.mean()
        else:
            continue
        rows.append((label, fmt, vals, overall))
    return rows


def _fmt(value, fmt: str) -> str:
    if value is None or pd.isna(value):
        return "-"
    return {"pct": f"{value * 100:.1f}%", "days": f"{value:,.1f}일", "count": f"{value:.2f}회",
            "money": f"{value:,.0f}"}[fmt]


def profile_html(rows: list[tuple], counts: pd.DataFrame) -> str:
    headers = ["지표"] + [f'<span style="display:inline-flex; align-items:center; gap:6px"><span class="kk-dot" '
                          f'style="background:{ui.seg_color(n)}"></span>{seg_display(n)}</span>' for n in SEGMENTS] + ["위험 회원 전체"]
    body = []
    for label, fmt, vals, overall in rows:
        present = [v for v in vals.values() if v is not None and pd.notna(v)]
        top = max(present) if present else None
        cells = [(f"<b>{_fmt(v, fmt)}</b>" if v is not None and pd.notna(v) and v == top else _fmt(v, fmt))
                 for v in (vals[n] for n in SEGMENTS)]
        body.append([f'<span style="color:{T["text2"]}">{label}</span>', *cells,
                     f'<span style="color:{T["muted"]}">{_fmt(overall, fmt)}</span>'])
    table_html = ui.table(headers, body, right={1, 2, 3, 4, 5}) if body else '<div class="kk-cap">프로필 생성에 필요한 컬럼이 없습니다.</div>'

    size = counts.set_index("segment")["인원"] if len(counts) else pd.Series(dtype=float)
    cards = "".join(
        f'<div style="padding:14px 16px; border-radius:12px; background:{T["seg_bg"][i]}; display:flex; flex-direction:column; gap:6px">'
        f'<span style="display:flex; justify-content:space-between; align-items:center; font-size:14px; font-weight:700">'
        f'<span style="display:inline-flex; align-items:center; gap:8px"><span class="kk-dot" style="background:{T["seg"][i]}"></span>'
        f'{seg_display(n)}</span><span class="kk-num-font" style="font-size:13px; color:{T["muted"]}">{int(size.get(n, 0) or 0):,}명</span></span>'
        f'<span style="font-size:13px; color:{T["text2"]}; line-height:1.5">{SEGMENTS[n]["description"]}</span></div>'
        for i, n in enumerate(SEGMENTS))
    return (f'<div class="kk" style="display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:12px">{cards}</div>'
            f'<div class="kk" style="padding-top:20px">{table_html}</div>'
            f'<div class="kk kk-cap">굵은 숫자는 네 유형 중 최댓값을 나타냅니다. 분류 기준 · 위험 회원의 거래·구독, 결제, 서비스 이용 행동 '
            f'17개 지표를 표준화한 뒤 K-Means 기반 4개 유형으로 분류했습니다.</div>')


def experiments_list() -> list[dict]:
    try:
        return [e for e in db.list_experiments() if e["status"] == "진행 중"]
    except Exception as error:  # DB가 없어도 대시보드는 떠야 해요
        st.warning(f"실험 저장소에 연결할 수 없습니다: {error}")
        return []


# ─────────────────────────────────────────────
# 화면
# ─────────────────────────────────────────────
ui.render_header()

# 현황 페이지 전용: 같은 행의 카드 높이와 행 사이 여백 통일
st.markdown("""
<style>
.st-key-kkbox-dist, .st-key-kkbox-seg {
    min-height: 380px !important;
    box-sizing: border-box !important;
}
.st-key-kkbox-seg > div:last-child {
    margin-top: auto !important;
    margin-bottom: auto !important;
}
.st-key-kkbox-activity, .st-key-kkbox-renewal {
    min-height: 300px !important;
    box-sizing: border-box !important;
}
.st-key-kkbox-running, .st-key-kkbox-newflow {
    min-height: 310px !important;
    box-sizing: border-box !important;
}
</style>
""", unsafe_allow_html=True)

with st.container(key="kk-body"):
    try:
        members = load_members()
    except (FileNotFoundError, ValueError) as error:
        ui.show_missing_files(error)
        st.stop()

    total = len(members)
    risk_count = int(members["risk"].sum())
    try:
        c = db.counts()
    except Exception:
        c = {"running": 0, "waiting": 0, "verified": 0, "total": 0}

    # 히어로
    with st.container(key="kkbox-hero"):
        left, right = st.columns([3, 1], vertical_alignment="center")
        with left:
            ui.html(f"""<div class="kk" style="display:flex; flex-direction:column; gap:14px">
<span class="kk-badge neutral" style="align-self:flex-start"><span class="kk-dot" style="background:#9C7EDB"></span>음악 스트리밍 구독자 이탈 방지</span>
<h1 style="font-size:34px; font-weight:700; letter-spacing:-0.02em; line-height:1.3">이탈 위험 구독자 <span style="color:{T['accent']}">{risk_count:,}명</span></h1>
<p style="font-size:14px; color:{T['muted']}">KKBox 회원 {total:,}명 중 이탈확률이 위험 기준 {THRESHOLD * 100:.2f}% 이상인 회원</p></div>""")
            b1, b2, _ = st.columns([1.2, 1.4, 2])
            with b1:
                if st.button("마케팅 방안 입력하기 →", type="primary", key="go-plan", **ui.WIDE):
                    st.switch_page(ui.PAGE_FILES["marketing"])
            with b2:
                if st.button("위험 기준 확인", key="go-model", **ui.WIDE):
                    st.switch_page(ui.PAGE_FILES["model"])
        right.markdown(ui.compact(f"""<div class="kk" style="display:flex; justify-content:center">
<svg width="180" height="180" viewBox="0 0 200 200" aria-hidden="true">
<circle cx="100" cy="100" r="96" fill="#9C7EDB" fill-opacity="0.1"/><circle cx="100" cy="100" r="80" fill="#1F1E24" stroke="#4A4A52" stroke-width="1.5"/>
<circle cx="100" cy="100" r="64" fill="none" stroke="#FFFFFF" stroke-opacity="0.1"/><circle cx="100" cy="100" r="50" fill="none" stroke="#FFFFFF" stroke-opacity="0.08"/>
<circle cx="100" cy="100" r="30" fill="#9C7EDB"/><circle cx="100" cy="100" r="3" fill="{T['bg']}"/>
<circle cx="22" cy="54" r="9" fill="{T['seg_bg'][1]}" stroke="#CC9EB8" stroke-width="1.5"/><circle cx="178" cy="148" r="11" fill="{T['seg_bg'][2]}" stroke="#93BBA3" stroke-width="1.5"/>
<circle cx="170" cy="36" r="7" fill="{T['seg_bg'][3]}" stroke="#8A9BCC" stroke-width="1.5"/></svg></div>"""), unsafe_allow_html=True)

    # 예측 대 실제 · 운영 현황
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    ui.html(compare_html(members))
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    ui.html(strip_html(total, c))

    # 이탈확률 분포 · 위험 회원 유형
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    left, right = st.columns([1.55, 1])
    with left, st.container(key="kkbox-dist"):
        chart_head("예측 이탈확률 분포", "확률 구간별 회원 비중과 실제 이탈률을 확인합니다.",
                   f"위험 기준 {THRESHOLD * 100:.2f}%")
        bins = probability_bins(members)
        tooltip = [alt.Tooltip("probability_range:N", title="예측확률"),
                   alt.Tooltip("customer_count:Q", title="회원 수", format=","),
                   alt.Tooltip("member_share:Q", title="전체 비중", format=".1%")]
        if "actual_churn_rate" in bins.columns:
            tooltip.append(alt.Tooltip("actual_churn_rate:Q", title="실제 이탈률", format=".1%"))
        order = bins["probability_range"].tolist()
        base = alt.Chart(bins).encode(
            x=alt.X("probability_range:N", sort=order, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("member_share:Q", title=None, scale=alt.Scale(type="sqrt", domain=[0, 1]), axis=alt.Axis(format=".0%", tickCount=4)),
            tooltip=tooltip,
        )
        chart = (base.mark_area(color=T["accent"], opacity=.13, interpolate="monotone")
                 + base.mark_line(color=T["accent"], strokeWidth=3, interpolate="monotone")
                 + base.mark_circle(color=T["accent"], size=75)).properties(height=240)
        st.altair_chart(ui.altair_theme(chart), **ui.WIDE, theme=None)
        ui.html('<div class="kk kk-cap">세로축은 분포 편중을 고려한 제곱근 눈금을 적용했습니다.</div>')

    with right, st.container(key="kkbox-seg"):
        chart_head("위험 회원 유형 4가지", "K-Means 기반 유형이며, 고객 매칭에서 전략별 우선순위를 산정합니다.")
        try:
            counts = load_segment_counts()
        except Exception:
            counts = pd.DataFrame(columns=["segment", "인원", "평균_이탈확률"])
        ui.html(f'<div class="kk">{segments_html(counts)}</div>')

    # 유형별 고객 프로필 (네 유형이 어떤 고객인지)
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    with st.container(key="kkbox-profile"):
        chart_head("유형별 고객 프로필", "K-Means로 분류한 네 가지 위험 회원 유형을 비교합니다.")
        ui.html(profile_html(segment_profiles(members), counts))

    # 이용·결제 행동
    activity, renewal = activity_summary(members), renewal_summary(members)
    if not activity.empty or not renewal.empty:
        st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
        left, right = st.columns([1.55, 1])
        with left, st.container(key="kkbox-activity"):
            chart_head("청취 활동 비교", "유지 회원과 이탈 회원의 지표별 평균 일수를 비교합니다.")
            if activity.empty:
                st.caption("activity_days · days_since_last_log 컬럼이 없습니다.")
            else:
                dots = alt.Chart(activity).mark_circle(size=200, opacity=.95).encode(
                    x=alt.X("days:Q", title="평균 일수", scale=alt.Scale(zero=True)),
                    y=alt.Y("metric_name:N", title=None, sort=["활동일", "마지막 접속 후"]),
                    yOffset=alt.YOffset("status:N", sort=["유지 회원", "이탈 회원"]),
                    color=alt.Color("status:N", sort=["유지 회원", "이탈 회원"],
                                    scale=alt.Scale(domain=["유지 회원", "이탈 회원"], range=[T["good_text"], T["bad_text"]])),
                    tooltip=[alt.Tooltip("status:N", title="회원 상태"), alt.Tooltip("metric_name:N", title="지표"),
                             alt.Tooltip("days:Q", title="평균 일수", format=",.1f")],
                ).properties(height=220)
                st.altair_chart(ui.altair_theme(dots), **ui.WIDE, theme=None)
        with right, st.container(key="kkbox-renewal"):
            chart_head("자동갱신별 실제 이탈률", "마지막 거래의 자동갱신 설정에 따른 관측값입니다.")
            if renewal.empty:
                st.caption("last_auto_renew 컬럼이 없습니다.")
            else:
                rb = alt.Chart(renewal).encode(
                    x=alt.X("churn_rate:Q", title="실제 이탈률", axis=alt.Axis(format=".0%"),
                            scale=alt.Scale(domain=[0, min(1, max(.5, float(renewal["churn_rate"].max()) * 1.2))])),
                    y=alt.Y("renewal:N", title=None, sort=["자동갱신 OFF", "자동갱신 ON"]),
                    tooltip=[alt.Tooltip("renewal:N", title="자동갱신"), alt.Tooltip("customer_count:Q", title="회원 수", format=","),
                             alt.Tooltip("churn_rate:Q", title="실제 이탈률", format=".2%")],
                )
                chart = rb.mark_bar(size=3, color=T["tint_border"]) + rb.mark_circle(size=230, color=T["accent"])
                st.altair_chart(ui.altair_theme(chart.properties(height=220)), **ui.WIDE, theme=None)

    # 진행 중인 실험 · 새 전략 검증하기
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    left, right = st.columns([1.55, 1])
    with left, st.container(key="kkbox-running"):
        chart_head("진행 중인 실험", "결과 입력 후 판정 결과가 라이브러리에 저장됩니다.")
        running = experiments_list()
        if not running:
            ui.html(f'<div class="kk kk-cap">진행 중인 실험이 없습니다.</div>')
        for e in running[:4]:
            waiting = db.is_waiting(e)
            b = ui.badge("결과 입력 대기", "warn") if waiting else ui.badge("진행 중", "accent")
            row_l, row_r = st.columns([5, 1.2], vertical_alignment="center")
            row_l.markdown(ui.compact(
                f'<div class="kk" style="display:flex; align-items:center; gap:14px">{b}<div style="display:flex; flex-direction:column; gap:3px">'
                f'<span style="font-size:15px; font-weight:700">{ui.esc(e["title"])}</span>'
                f'<span style="font-size:13px; color:{T["muted"]}">{seg_display(e["segment"])} · 실험군 {int(e.get("n_treat") or 0):,}명 / '
                f'대조군 {int(e.get("n_ctrl") or 0):,}명 · 종료일 {e.get("end_date") or "-"}</span></div></div>'), unsafe_allow_html=True)
            with row_r:
                if st.button("결과 입력 →" if waiting else "보기 →", key=f"open-{e['id']}", **ui.WIDE):
                    st.session_state["open_exp"] = e["id"]
                    st.session_state["exp_view"] = "results"
                    st.switch_page(ui.PAGE_FILES["experiments"])

    with right, st.container(key="kkbox-newflow"):
        chart_head("새 전략 검증", "4단계 검증 절차")
        steps = ["하고 싶은 마케팅 방안 입력", "효과가 클 고객 유형 매칭", "실험군 · 대조군 A/B 테스트", "판정 결과를 라이브러리에 저장"]
        ui.html('<div class="kk" style="display:flex; flex-direction:column; gap:10px">' + "".join(
            f'<div style="display:flex; align-items:center; gap:12px; font-size:14px"><span style="width:26px; height:26px; border-radius:999px; '
            f'background:{T["accent_soft"]}; color:{T["accent_on_soft"]}; font-family:Rubik; font-weight:700; font-size:12px; display:flex; '
            f'align-items:center; justify-content:center">{i}</span>{s}</div>' for i, s in enumerate(steps, 1)) + "</div>")
        if st.button("시작하기 →", type="primary", key="go-start", **ui.WIDE):
            st.switch_page(ui.PAGE_FILES["marketing"])
