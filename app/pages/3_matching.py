"""KKeeper ② 고객 매칭 — 전략의 효과가 클 고객 유형을 이탈 모델로 찾아 순위를 매김 (주소: /matching)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ui  # noqa: E402
from common.constants import SEGMENTS, THRESHOLD, seg_display  # noqa: E402
from common.data import apply_conditions, load_assets  # noqa: E402
from common.experiment import CLUSTER_MARKETING, WHATIF_LEVERS, affected_mask, hypothesis, rank_segments  # noqa: E402

st.set_page_config(page_title="고객 매칭 · KKeeper", layout="wide", initial_sidebar_state="collapsed")
T = ui.init("matching")
ss = st.session_state

# 행동 목표 → 비교해서 보여줄 지표
LEVER_METRIC = {
    "song_variety": ("avg_daily_unq", "하루 고유곡 수", "up"),
    "activity_up": ("activity_days", "활동일", "up"),
    "listen_time": ("avg_daily_secs", "하루 청취시간(초)", "up"),
    "revisit": ("days_since_last_log", "마지막 접속 후 일수", "down"),
    "cancel_stop": ("last_is_cancel", "마지막 거래 해지 비율", "down"),
    "auto_renew_on": ("last_auto_renew", "자동갱신 켬 비율", "up"),
}


def cond_key(strategy: dict) -> tuple:
    return (strategy.get("period", "전체"), strategy.get("last", "전체"), tuple(strategy.get("plans") or []))


@st.cache_data(show_spinner="유형별 예상 효과 계산 중…")
def ranking(conditions: tuple, levers: tuple) -> pd.DataFrame:
    risk = load_assets()["risk"]
    matched, _ = apply_conditions(risk, {"period": conditions[0], "last": conditions[1], "plans": list(conditions[2])})
    return rank_segments(matched, dict(levers), load_assets()["bundle"])


def empty_state() -> None:
    ui.html(ui.page_title("고객 매칭", "마케팅 설계에서 전략을 먼저 입력하십시오."))
    ui.html(f'<div class="kk kk-card" style="border-style:dashed; color:{T["muted"]}; padding:48px">'
            '입력된 전략이 없습니다. 마케팅 방안 입력 후 네 가지 고객 유형을 예상 효과순으로 제시합니다.</div>')
    # 안내 박스와 버튼 사이 여백
    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    if st.button("마케팅 설계로 가기 →", type="primary", key="go-plan"):
        st.switch_page(ui.PAGE_FILES["marketing"])


def funnel_html(total: int, cond_text: str, matched: int, affected: int) -> str:
    arrow = (f'<div aria-hidden="true" style="display:flex; align-items:center; color:{T["num"]}">'
             f'{ui.icon("arrow", 22)}</div>')

    def box(label, value, on=False):
        style = f"border-color:{T['accent_line']}; background:{T['accent_soft']};" if on else ""
        color = f"color:{T['accent_on_soft']};" if on else ""
        return (f'<div class="kk-card" style="flex:1; padding:16px 18px; {style}"><div class="kk-cap" style="{color}">{label}</div>'
                f'<div class="kk-num-font" style="font-size:22px; font-weight:700; margin-top:6px; {color}">{value:,}명</div></div>')
    return (f'<div class="kk" style="display:flex; align-items:stretch; gap:10px">{box("위험 회원 전체", total)}{arrow}'
            f'{box(f"적용 조건 통과 · {cond_text}", matched)}{arrow}{box("전략이 영향을 줄 수 있는 고객", affected, True)}</div>')


def rank_rows_html(table: pd.DataFrame, selected: str) -> str:
    top = max(float(table["예상_감소"].max()), 1e-9)
    head = (f'<div style="display:grid; grid-template-columns:56px 1.7fr 100px 100px 110px 1.2fr; gap:16px; align-items:center; '
            f'padding:14px 22px; font-size:12px; color:{T["subtle"]}; border-bottom:1px solid {T["line"]}">'
            '<span>순위</span><span>고객 유형</span><span style="text-align:right">대상 인원</span><span style="text-align:right">영향 가능</span>'
            '<span style="text-align:right">평균 이탈확률</span><span>예상 이탈 감소 (모델)</span></div>')
    rows = []
    for _, r in table.iterrows():
        name = r["segment"]
        on = name == selected
        color = ui.seg_color(name)
        rank_style = (f"background:{T['accent']}; color:{T['accent_text']};" if r["순위"] == 1
                      else f"border:1px solid {T['chip_border']}; color:{T['muted']};")
        badges = ""
        if r["추천_일치"]:
            badges += ui.badge("추천 전략과 일치", "good")
        if r["효과_작음"] and r["대상_인원"] > 0:
            badges += ui.badge("효과 작음", "warn")
        if r["대상_인원"] == 0:
            badges += ui.badge("조건에 맞는 고객 없음", "neutral")
        sub = SEGMENTS[name]["description"]
        rows.append(
            f'<div style="display:grid; grid-template-columns:56px 1.7fr 100px 100px 110px 1.2fr; gap:16px; align-items:center; '
            f'padding:16px 22px; border-bottom:1px solid {T["line"]}; background:{T["accent_soft"] if on else "transparent"}">'
            f'<span class="kk-num-font" style="width:32px; height:32px; border-radius:10px; {rank_style} font-weight:700; display:flex; '
            f'align-items:center; justify-content:center">{int(r["순위"])}</span>'
            f'<span style="display:flex; flex-direction:column; gap:6px"><span style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; '
            f'font-size:16px; font-weight:700"><span class="kk-dot" style="width:10px; height:10px; background:{color}"></span>{seg_display(name)}{badges}</span>'
            f'<span style="font-size:13px; color:{T["accent_on_soft"] if on else T["muted"]}">{sub}</span></span>'
            f'<span style="text-align:right">{int(r["대상_인원"]):,}명</span><span style="text-align:right">{int(r["영향_가능"]):,}명</span>'
            f'<span class="kk-num-font" style="text-align:right">{ui.pct(r["평균_이탈확률"]) if r["대상_인원"] else "-"}</span>'
            f'<span style="display:flex; align-items:center; gap:10px">{ui.track(max(r["예상_감소"], 0) / top, color)}'
            f'<span class="kk-num-font" style="font-weight:700; white-space:nowrap">{max(r["예상_감소"], 0):,.1f}명</span></span></div>')
    return f'<div class="kk kk-card" style="padding:10; overflow:hidden">{head}{"".join(rows)}</div>'


def why_html(segment: str, part: pd.DataFrame, pool: pd.DataFrame, levers: dict) -> str:
    rows = []
    for lever, value in levers.items():
        if not value or lever not in LEVER_METRIC:
            continue
        col, label, direction = LEVER_METRIC[lever]
        if col not in part.columns:
            continue
        a = float(pd.to_numeric(part[col], errors="coerce").mean())
        b = float(pd.to_numeric(pool[col], errors="coerce").mean())
        top = max(a, b, 1e-9)
        room = "개선 여지 큼" if (direction == "up" and a < b) or (direction == "down" and a > b) else "이미 좋은 편"
        rows.append(
            f'<div style="display:grid; grid-template-columns:150px 1fr 120px; align-items:center; gap:14px; font-size:14px">'
            f'<span style="color:{T["text2"]}">{label}</span><span style="display:flex; flex-direction:column; gap:4px">'
            f'{ui.track(a / top, ui.seg_color(segment))}{ui.track(b / top, T["strong_border"])}</span>'
            f'<span style="text-align:right; color:{T["muted"]}; font-size:13px">{a:,.2f} / {b:,.2f}<br><span class="kk-cap">{room}</span></span></div>')
    legend = (f'<div style="display:flex; gap:16px; font-size:12px; color:{T["muted"]}"><span style="display:inline-flex; align-items:center; gap:6px">'
              f'<span style="width:10px; height:4px; border-radius:2px; background:{ui.seg_color(segment)}"></span>이 유형</span>'
              f'<span style="display:inline-flex; align-items:center; gap:6px"><span style="width:10px; height:4px; border-radius:2px; '
              f'background:{T["strong_border"]}"></span>조건 통과 고객 평균</span></div>')
    return "".join(rows) + legend if rows else '<div class="kk-cap">비교 가능한 지표가 없습니다.</div>'


SENS_STEPS = [10, 20, 30]


def sensitivity_html(conditions: tuple, levers: dict, current: pd.DataFrame) -> str:
    """켜 둔 행동 목표를 모두 10·20·30%로 바꿔 다시 계산해, 가정에 따라 순위가 흔들리는지 보여 줘요."""
    active = [k for k, v in levers.items() if v]
    tables = {}
    for step in SENS_STEPS:
        scen = {k: min(step, WHATIF_LEVERS[k]["max"]) for k in active}
        tables[step] = ranking(conditions, tuple(sorted(scen.items()))).set_index("segment")
    cur = current.set_index("segment")
    tops = {t["예상_감소"].idxmax() for t in tables.values()} | {cur["예상_감소"].idxmax()}

    def cell(t, name):
        r = t.loc[name]
        if r["대상_인원"] == 0:
            return '<span class="kk-cap">-</span>'
        weight = "700" if r["순위"] == 1 else "400"
        return (f'<span class="kk-num-font" style="font-weight:{weight}">{max(r["예상_감소"], 0):,.1f}명</span> '
                f'<span class="kk-cap">{int(r["순위"])}위</span>')

    rows = [[f'<span style="display:inline-flex; align-items:center; gap:8px"><span class="kk-dot" style="background:{ui.seg_color(n)}"></span>'
             f'{seg_display(n)}</span>'] + [cell(tables[s], n) for s in SENS_STEPS] + [cell(cur, n)]
            for n in current["segment"]]
    headers = ["고객 유형"] + [f"모두 +{s}%" for s in SENS_STEPS] + ["지금 설정"]
    if len(tops) == 1:
        verdict = ui.badge("조건 변경 후에도 1위 유지", "good")
        msg = (
            f"행동 변화 폭 10~30% 구간에서 "
            f"{seg_display(next(iter(tops)))}의 예상 효과가 가장 높아 순위가 유지됩니다."
        )
    else:
        verdict = ui.badge("조건 변경 시 1위 변동", "warn")
        msg = "행동 변화 폭에 따라 1위 유형이 달라집니다. 최종 효과는 A/B 테스트로 검증해야 합니다."
    labels = ", ".join(WHATIF_LEVERS[k]["label"] for k in active)
    return (f'<div class="kk" style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap">'
            f'<div><div class="kk-card-title">행동 지표별 이탈 예측 변화</div>'
            f'</div>'
            f'{verdict}</div>'
            f'<div style="height:16px"></div>'
            f'<div class="kk">{ui.table(headers, rows, right={1, 2, 3, 4})}</div>'
            f'<div class="kk kk-cap">{msg} 해지·갱신 목표는 대상 고객의 행동 전환 비율로 계산합니다.</div>')


def top_customers_html(part: pd.DataFrame) -> str:
    top = part.sort_values("churn_prob", ascending=False).head(5)
    rows = []
    for _, r in top.iterrows():
        m = str(r["msno"])
        masked = f"{m[:7]}…{m[-4:]}" if len(m) > 12 else m
        last = f'{float(r["days_since_last_log"]):.0f}일 전' if "days_since_last_log" in r and pd.notna(r["days_since_last_log"]) else "-"
        rows.append([ui.esc(masked), ui.pct(r["churn_prob"]), last])
    return ui.table(["회원 ID", "이탈확률", "마지막 접속"], rows, right={1, 2})


# ─────────────────────────────────────────────
ui.render_header()

# 선정 근거 / 상위 고객 카드 높이 통일
st.markdown("""
<style>
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-kkbox-why) {
    align-items: stretch !important;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-kkbox-why)
    > [data-testid="stColumn"] {
    align-self: stretch !important;
    display: flex !important;
    flex-direction: column !important;
}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-kkbox-why)
    > [data-testid="stColumn"] > div {
    flex: 1 1 auto !important;
    display: flex !important;
    flex-direction: column !important;
}
.st-key-kkbox-why,
.st-key-kkbox-top {
    min-height: 430px !important;
    height: 100% !important;
    box-sizing: border-box !important;
    flex: 1 1 auto !important;
}
</style>
""", unsafe_allow_html=True)

with st.container(key="kk-body"):
    strategy = ss.get("strategy")
    st.markdown(ui.compact(ui.steps_html(2)), unsafe_allow_html=True)
    if not strategy:
        empty_state()
        st.stop()

    try:
        assets = load_assets()
    except FileNotFoundError as error:
        ui.show_missing_files(error)
        st.stop()

    levers = strategy["levers"]
    risk = assets["risk"]
    matched, notes = apply_conditions(risk, strategy)
    table = ranking(cond_key(strategy), tuple(sorted(levers.items())))

    order = table["segment"].tolist()
    default = ss.get("match", {}).get("segment") or order[0]
    ss.setdefault("m_pick", seg_display(default))
    picked_display = ss.get("m_pick")
    selected = next((s for s in order if seg_display(s) == picked_display), order[0])

    ui.html(ui.context_html(strategy, f"{seg_display(selected)} · 고르는 중", None))
    ui.html(
        ui.page_title(
            "고객 매칭",
            "적용 조건에 따른 대상 선별 및 행동 목표 적용 효과 기반 유형별 순위 산정하기"
        )
    )

    cond_text = ", ".join(x for x in [strategy.get("period") if strategy.get("period") != "전체" else "",
                                      strategy.get("last") if strategy.get("last") != "전체" else "",
                                      "·".join(strategy.get("plans") or [])] if x) or "조건 없음"

    ui.html(funnel_html(len(risk), cond_text, len(matched), int(affected_mask(matched, levers).sum())))
    for n in notes:
        st.caption(n)

    # 요약 카드와 고객 유형 순위표 사이 여백
    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

    ui.html(rank_rows_html(table, selected))

    ui.html(
        f'<div class="kk kk-cap" style="padding-bottom:24px">'
        f'예상 이탈 감소는 모델 예측값이며, 실제 효과는 A/B 테스트로 검증합니다. '
        f'위험 기준 {THRESHOLD * 100:.2f}% 이상 고객만 포함합니다.'
        f'</div>'
    )

    with st.container(key="kkbox-sens"):
        ui.html(sensitivity_html(cond_key(strategy), levers, table))

    # 민감도 분석 박스와 고객 유형 선택 사이 여백
    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)

    options = [seg_display(s) for s in order if int(table.set_index("segment").loc[s, "대상_인원"]) > 0]

    options = [seg_display(s) for s in order if int(table.set_index("segment").loc[s, "대상_인원"]) > 0]
    if not options:
        st.warning("적용 조건에 해당하는 위험 회원이 없습니다. 마케팅 설계에서 조건을 확대하십시오.")
        if st.button("← 마케팅 설계로", key="back-empty"):
            st.switch_page(ui.PAGE_FILES["marketing"])
        st.stop()
    if ss.get("m_pick") not in options:
        ss["m_pick"] = options[0]

    ui.html(
        '<div class="kk" style="font-size:18px; font-weight:700; padding-bottom:16px">'
        '실험할 고객 유형'
        '</div>'
    )
    ui.choose("실험할 고객 유형", options, "m_pick", options[0], label_visibility="collapsed")
    selected = next(s for s in order if seg_display(s) == (ss.get("m_pick") or options[0]))
    part = matched[matched["segment"] == selected]

    # 고객 유형 선택 버튼과 분석 카드 사이 여백
    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    left, right = st.columns([1.2, 1])

    with left, st.container(key="kkbox-why"):
        row = table.set_index("segment").loc[selected]
        rec = CLUSTER_MARKETING.get(selected, {})
        title = "1위 선정 근거" if int(row["순위"]) == 1 else f"{seg_display(selected)} · {int(row['순위'])}위"
        ui.html(f'<div class="kk"><div class="kk-card-title">{title}</div>'
                f'<div class="kk-card-note">{seg_display(selected)} 고객과 조건 통과 고객 평균 비교 · 전략이 건드리는 지표</div></div>')
        ui.html(f'<div class="kk" style="display:flex; flex-direction:column; gap:12px">{why_html(selected, part, matched, levers)}</div>')
        match_badge = ui.badge("추천 전략과 일치", "good") if row["추천_일치"] else ui.badge("팀 추천 전략과 다름", "neutral")
        note = f'<div class="kk-cap" style="margin-top:6px">{ui.esc(rec.get("note", ""))}</div>' if rec.get("note") else ""
        ui.html(f'<div class="kk kk-tip"><div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap"><b>팀 추천 전략</b> · '
                f'{ui.esc(rec.get("name", "-"))} {match_badge}</div><div style="margin-top:4px">{ui.esc(rec.get("desc", ""))}</div>{note}</div>')
        if row["확률상승_비율"] > 0.3:
            ui.html('<div class="kk kk-warnbox">목표 적용 후 이탈확률이 상승한 고객 비중이 30%를 초과합니다. 모델의 역방향 해석 가능성을 검토하십시오.</div>')

    with right, st.container(key="kkbox-top"):
        ui.html('<div class="kk"><div class="kk-card-title">이탈확률 상위 고객</div>'
                '<div class="kk-card-note">이 유형에서 가장 위험한 회원 5명</div></div>')
        ui.html(f'<div class="kk">{top_customers_html(part)}</div>')
        ui.html('<div class="kk kk-cap">분류 기준 · 위험 회원 행동 17개 지표를 표준화해 K-Means 기반 4개 유형으로 분류했습니다.</div>')

    with st.container(key="kkfoot-match"):
        f1, f2, f3 = st.columns([1, 2.6, 1.4], vertical_alignment="center")
        with f1:
            if st.button("← 마케팅 설계", key="back"):
                st.switch_page(ui.PAGE_FILES["marketing"])
        f2.markdown(ui.compact(f'<div class="kk" style="text-align:right; font-size:14px; color:{T["muted"]}">실험 대상 '
                               f'<b style="color:{T["text"]}">{seg_display(selected)}</b> · {len(part):,}명</div>'), unsafe_allow_html=True)
        with f3:
            if st.button("A/B 테스트 설계하기 →", type="primary", key="go-exp", **ui.WIDE):
                hyp = hypothesis(part, levers, assets["bundle"])
                ss["match"] = {"segment": selected, "n": len(part), "conditions": cond_key(strategy), **hyp}
                ss.pop("design", None)
                ss["exp_view"] = "design"
                st.switch_page(ui.PAGE_FILES["experiments"])
    
