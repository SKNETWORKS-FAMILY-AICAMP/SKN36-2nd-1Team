"""KKeeper ① 마케팅 설계 — 하고 싶은 마케팅 방안과 적용 조건 입력 (주소: /marketing)."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ui  # noqa: E402
from common.constants import CHANNELS, GOALS, KINDS, LASTS, PERIODS, PLANS, default_levers  # noqa: E402
from common.experiment import WHATIF_LEVERS  # noqa: E402

st.set_page_config(page_title="마케팅 설계 · KKeeper", layout="wide", initial_sidebar_state="collapsed")
T = ui.init("marketing")
ss = st.session_state

FIELD_KEYS = {"name": "s_name", "kind": "s_kind", "goal": "s_goal", "desc": "s_desc", "period": "s_period",
              "last": "s_last", "plans": "s_plans", "channels": "s_channels"}


def restore_form() -> None:
    """다시 들어왔을 때 저장해 둔 전략(또는 임시 저장본)으로 입력칸을 채워요."""
    # Streamlit은 다른 페이지로 가면 이 화면 입력칸의 값을 지워요. 그래서 입력칸 값이 없을 때마다 채워 넣어요.
    if any(f"lv_{lever}" not in ss for lever in WHATIF_LEVERS):
        ss.pop("lever_base", None)          # 행동 목표 칸이 지워졌으면 기본값부터 다시 채워요
    if "s_name" in ss:
        return
    source = ss.get("strategy_draft") or ss.get("strategy")
    if source:
        for field, key in FIELD_KEYS.items():
            if field in source and key not in ss:
                ss[key] = source[field]
        saved = source.get("levers") or {}
        for lever in WHATIF_LEVERS:
            ss[f"lv_{lever}"] = int(saved.get(lever, 0))
        ss["lever_base"] = (source.get("kind"), source.get("goal"))


def sync_lever_defaults(kind: str, goal: str) -> dict:
    """유형·목적이 바뀌면 행동 목표를 새 기본값으로 다시 채워요."""
    base = (kind, goal)
    defaults = default_levers(kind, goal)
    if ss.get("lever_base") != base:
        for lever in WHATIF_LEVERS:
            ss[f"lv_{lever}"] = int(defaults.get(lever, 0))
        ss["lever_base"] = base
    return {lever: int(ss.get(f"lv_{lever}", defaults.get(lever, 0))) for lever in WHATIF_LEVERS}


def live_counts(values: dict, levers: dict) -> tuple[str, str, list[str]]:
    """입력 요약의 '조건에 맞는 위험 회원' 숫자. 데이터가 없으면 안내만."""
    try:
        from common.data import apply_conditions, load_assets
        from common.experiment import affected_mask
        risk = load_assets()["risk"]
    except Exception:
        return "-", "-", ["데이터 연결 후 예상 인원이 표시됩니다."]
    matched, notes = apply_conditions(risk, values)
    affected = int(affected_mask(matched, levers).sum()) if len(matched) else 0
    return f"{len(matched):,}명", f"{affected:,}명", notes


ui.render_header()
restore_form()

st.markdown("""
<style>
.st-key-kkbox-basic,
.kk-marketing-summary {
    min-height: 480px !important;
    height: auto !important;
    box-sizing: border-box !important;
}
</style>
""", unsafe_allow_html=True)

with st.container(key="kk-body"):
    st.markdown(ui.compact(ui.steps_html(1)), unsafe_allow_html=True)
    ui.html(ui.context_html(ss.get("strategy") or ss.get("strategy_draft"), None, None))

    ui.html(ui.page_title("마케팅 설계",
                          "마케팅 방안 입력 후, 적합한 고객 유형 매칭하기"))

    # 기본 정보와 입력 요약의 시작선을 맞추고, 카드 내용이 늘어나면 자연스럽게 확장
    left, right = st.columns([2.45, 1])
    with left:
        with st.container(key="kkbox-basic"):
            ui.html('<div class="kk kk-sechead"><div><span class="kk-secnum">01</span><span class="kk-sectitle">기본 정보</span></div></div>')
            name = st.text_input("전략 이름", key="s_name", placeholder="예: 장기 미접속 구독자 맞춤 플레이리스트 추천")
            kind = ui.choose("전략 유형", KINDS, "s_kind", "콘텐츠 추천") or "콘텐츠 추천"
            goal_now = ss.get("s_goal") or "이탈 방지"
            ui.html(f'<div class="kk" style="font-size:13px; font-weight:600; color:{T["text2"]}">목적 '
                    f'<span style="font-weight:400; color:{T["subtle"]}">· {GOALS.get(goal_now, "")}</span></div>')
            goal = ui.choose("목적", list(GOALS), "s_goal", "이탈 방지", label_visibility="collapsed") or "이탈 방지"
            desc = st.text_area("전략 설명", key="s_desc", height=90, placeholder="대상 고객, 제안 내용, 전달 방식을 입력하십시오.")

        with st.container(key="kkbox-cond"):
            ui.html('<div class="kk kk-sechead"><div><span class="kk-secnum">02</span><span class="kk-sectitle">적용 조건</span></div>'
                    '<span class="kk-cap">미설정 시 전체 위험 회원을 대상으로 매칭합니다.</span></div>')
            c1, c2 = st.columns(2)
            with c1:
                period = st.selectbox("구독 기간", PERIODS, key="s_period")
                plans = ui.choose("요금제", PLANS, "s_plans", [], multi=True) or []
            with c2:
                ss.setdefault("s_last", LASTS[2])
                last = st.selectbox("마지막 접속", LASTS, key="s_last")
                channels = ui.choose("전달 채널", CHANNELS, "s_channels", ["앱 푸시"], multi=True) or []

        levers = sync_lever_defaults(kind, goal)
        with st.container(key="kkbox-levers"):
            ui.html(f'<div class="kk kk-sechead"><div><span class="kk-secnum">03</span><span class="kk-sectitle">모델이 읽는 방식</span></div></div>'
                    f'<p class="kk" style="font-size:13px; color:{T["muted"]}; line-height:1.6">'
                    f'‘{ui.esc(kind)} · {ui.esc(goal)}’의 예상 효과를 아래 행동 목표에 따라 계산합니다. 필요 시 값을 조정할 수 있습니다.</p>')
            chips = [ui.badge(f'{WHATIF_LEVERS[k]["label"]} {v}%', "accent") for k, v in levers.items() if v]
            ui.html('<div class="kk" style="display:flex; gap:8px; flex-wrap:wrap">'
                    + ("".join(chips) or ui.badge("행동 목표 미설정 · 하나 이상 선택 필요", "warn")) + "</div>")
            with st.expander("조정하기"):
                cols = st.columns(3)
                for i, (key, info) in enumerate(WHATIF_LEVERS.items()):
                    with cols[i % 3]:
                        st.slider(f'{info["label"]} ({info["kind"]})', 0, info["max"], step=5, format="%d%%",
                                  key=f"lv_{key}", help=info["help"])
                st.caption("입력값은 전략 성공 시 예상되는 행동 변화 가정입니다. 해지·갱신 목표는 이탈과 직접 연계되어 효과가 크게 산정됩니다.")
            if st.button("계산 방식 확인 →", key="to-model"):
                st.switch_page(ui.PAGE_FILES["model"])
            levers = {lever: int(ss.get(f"lv_{lever}", 0)) for lever in WHATIF_LEVERS}

    values = {"name": name.strip(), "kind": kind, "goal": goal, "desc": desc.strip(), "period": period, "last": last,
              "plans": list(plans), "channels": list(channels), "levers": {k: v for k, v in levers.items() if v}}
    ss["strategy_draft"] = values            # 다른 페이지에 다녀와도 입력이 남도록 매번 저장

    with right:
        matched, affected, notes = live_counts(values, values["levers"])
        rows = [("유형", kind), ("목적", goal), ("구독 기간", period), ("접속", last),
                ("요금제", ", ".join(plans) or "전체"), ("채널", ", ".join(channels) or "-")]
        dl = "".join(f'<span style="color:{T["subtle"]}">{a}</span><span>{ui.esc(str(b))}</span>' for a, b in rows)
        note_html = "".join(f'<div class="kk-cap">{ui.esc(n)}</div>' for n in notes)
        ui.html(f"""<div class="kk kk-card kk-marketing-summary" style="display:flex; flex-direction:column; gap:16px">
<div class="kk-eyebrow">입력 요약</div>
<div style="font-size:18px; font-weight:700; color:{T['text'] if name else T['muted']}">{ui.esc(name) or '[전략 이름]'}</div>
<div style="display:grid; grid-template-columns:72px 1fr; row-gap:10px; font-size:14px">{dl}</div>
<div style="height:1px; background:{T['border']}"></div>
<div style="display:flex; justify-content:space-between; gap:12px">
 <div><div class="kk-cap">조건에 맞는 위험 회원</div><div class="kk-num-font" style="font-size:26px; font-weight:700; color:{T['accent']}">{matched}</div></div>
 <div style="text-align:right"><div class="kk-cap">전략이 닿을 수 있는 고객</div><div class="kk-num-font" style="font-size:26px; font-weight:700">{affected}</div></div>
</div>{note_html}
<div class="kk-tip">다음 단계에서 조건에 맞는 고객을 선별하고,<br>네 가지 유형을 예상 효과순으로 제시합니다.</div>
</div>""")

        # 버튼은 박스 없이 입력 요약 바로 아래에 둬요
        msg = st.empty()
        f1, f2 = st.columns([1, 1.6], vertical_alignment="center")
        with f1:
            if st.button("임시 저장", key="s_save", **ui.WIDE):
                st.toast("임시 저장이 완료되었습니다.")
        with f2:
            if st.button("고객 매칭하기 →", type="primary", key="s_go", **ui.WIDE):
                if not values["name"]:
                    msg.error("전략 이름을 입력하십시오.")
                elif not values["levers"]:
                    msg.error("‘모델이 읽는 방식’에서 행동 목표를 하나 이상 선택하십시오.")
                else:
                    if ss.get("strategy") != values:
                        ss.pop("match", None)          # 전략이 바뀌면 이전 매칭 결과는 버려요
                        ss.pop("design", None)
                    ss["strategy"] = values
                    ss["strategy_draft"] = values
                    st.switch_page(ui.PAGE_FILES["matching"])
