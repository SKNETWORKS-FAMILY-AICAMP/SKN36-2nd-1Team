"""
KKeeper — 이탈 방지 전략 라이브러리 (pages/4_library.py · 주소: /library)

실험 관리(3_experiments.py)에서 '검증 완료'로 판정된 실험이 여기에 전략 카드로
자동으로 쌓여요. 판정별(효과 있음 / 판단 보류 / 효과 없음)로 필터링해서 볼 수 있어요.

원래 기획엔 '비용 대비 효과' 같은 필터도 있었지만, 지금 데이터엔 비용 정보가 없어서
실제로 계산할 수 있는 판정 기준(효과 있음·판단 보류·효과 없음)만 필터로 뒀어요.
"""

import sys
from html import escape
from pathlib import Path

import streamlit as st

# ui.py는 app.py와 같은 폴더에 있어요 (pages 폴더 안이 아니에요)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ui  # noqa: E402
import store  # noqa: E402 — 새로고침·재시작해도 라이브러리가 안 사라지게 파일에서 불러와요
from ui import compact
import json  # noqa: E402
from common.db import load_plans  # noqa: E402
from common.db import PLAN_STATUSES, load_plans, update_plan_status  # noqa: E402
from common.report import make_plan_pdf  # noqa: E402

st.set_page_config(page_title="라이브러리 · KKeeper", layout="wide", initial_sidebar_state="collapsed")
T = ui.init("library")
theme_name = ui.theme_name

STEP_NAMES = ["마케팅 설계", "고객 매칭", "실험 관리", "라이브러리"]

VERDICT_COLORS = {
    "light": {"good_bg": "#E6F6EC", "good_text": "#1F8B4C", "warn_bg": "#FDF3DF", "warn_text": "#9A6B0A",
              "bad_bg": "#FBEAEA", "bad_text": "#B23A32"},
    "dark": {"good_bg": "#1B2A20", "good_text": "#7EE2A8", "warn_bg": "#2A2418", "warn_text": "#E8C176",
             "bad_bg": "#2B1D1F", "bad_text": "#E8918C"},
}
V = VERDICT_COLORS[theme_name]

FILTERS = ["전체", "효과 있음", "판단 보류", "효과 없음"]
KIND_OF = {"효과 있음": "good", "판단 보류": "warn", "효과 없음": "bad"}


def choose(label: str, options: list, key: str, default, label_visibility: str = "visible"):
    if hasattr(st, "pills"):
        return st.pills(label, options, default=default, key=key, label_visibility=label_visibility)
    return st.radio(label, options, index=options.index(default), key=key, horizontal=True,
                     label_visibility=label_visibility)


def page_css() -> str:
    return f"""
<style>
  .st-key-kk-body {{ padding: 28px 64px 64px; }}
  .st-key-kk-body [data-testid="stVerticalBlock"] {{ gap: 20px !important; }}
  .st-key-kk-body [data-testid="stHorizontalBlock"] {{ gap: 20px !important; }}

  .st-key-kk-body button[data-variant="pills"],
  .st-key-kk-body [data-testid="stBaseButton-pills"], .st-key-kk-body [data-testid="stBaseButton-pillsActive"] {{
      min-height: 44px; padding: 0 18px !important; border-radius: 10px !important;
      font-family: 'IBM Plex Sans KR', sans-serif !important; font-size: 15px !important; }}
  .st-key-kk-body button[data-variant="pills"],
  .st-key-kk-body [data-testid="stBaseButton-pills"] {{
      background: transparent !important; border: 1px solid {T['chip_border']} !important; color: {T['badge_text']} !important; }}
  .st-key-kk-body button[data-variant="pills"][data-selected],
  .st-key-kk-body [data-testid="stBaseButton-pillsActive"] {{
      background: {T['accent_soft']} !important; border: 1px solid {T['accent']} !important; color: {T['accent']} !important; font-weight: 700 !important; }}

  div[class*="st-key-kkcard-lib"] {{ background: {T['surface']}; border: 1px solid {T['border']} !important;
                                     border-radius: 20px !important; padding: 20px 24px 26px !important; }}
  div[class*="st-key-kkcard-lib"] > div {{ border: none !important; }}
  div[class*="st-key-kk-lib-filter-gap"] {{ margin-bottom: 20px; }}
  .kk-lib-top {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 8px; }}
  .kk-lib-name {{ margin: 0 !important; font-size: 19px; font-weight: 700; color: {T['text']}; }}
  .kk-lib-target {{ margin: 0 0 10px !important; font-size: 14px; line-height: 1.5; color: {T['subtle']}; }}
  .kk-lib-divider {{ height: 1px; background: {T['line']}; margin-bottom: 10px; }}
  .kk-lib-stats {{ display: flex; justify-content: space-between; gap: 16px; }}
  .kk-lib-stat-label {{ font-size: 12px; color: {T['subtle']}; }}
  .kk-lib-stat-val {{ font-family: Rubik, sans-serif; font-size: 26px; font-weight: 700; }}
  .kk-lib-stat-unit {{ font-size: 14px; font-weight: 500; font-family: 'IBM Plex Sans KR', sans-serif; color: {T['subtle']}; }}

  .kk-stepper {{ margin: 0; padding: 0; list-style: none; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }}
  .kk-stepper li.s {{ display: flex; align-items: center; gap: 10px; padding: 8px 16px 8px 8px; border-radius: 999px;
                     border: 1px solid {T['tint_border']}; font-size: 14px; color: {T['subtle']}; }}
  .kk-stepper li.s.on {{ border-color: transparent; background: {T['accent_soft']}; color: {T['accent']}; font-weight: 700; }}
  .kk-stepper li.s i {{ font-style: normal; width: 26px; height: 26px; border-radius: 999px; background: {T['surface']};
                       font-family: Rubik, sans-serif; font-size: 12px; display: flex; align-items: center; justify-content: center; }}
  .kk-stepper li.s.on i {{ background: {T['accent']}; color: {T['accent_text']}; }}
  .kk-stepper li.l {{ width: 12px; height: 1px; background: {T['chip_border']}; }}

  .st-key-kk-empty-actions {{ margin-top: 20px; }}

  @media (max-width: 1100px) {{ .st-key-kk-body {{ padding: 24px 16px 48px; }} }}
</style>"""


def head_html() -> str:
    steps = []
    for i, name in enumerate(STEP_NAMES):
        if i:
            steps.append('<li class="l" aria-hidden="true"></li>')
        on = " on" if i == 3 else ""
        steps.append(f'<li class="s{on}"><i>{i + 1:02d}</i>{name}</li>')
    return f"""
<section class="kk-page" style="padding-bottom:0; flex-direction:row; align-items:flex-end; justify-content:space-between; flex-wrap:wrap; gap:24px">
  <div style="display:flex; flex-direction:column; gap:12px">
    <h1 class="kk-h2 kk-title" style="font-size:40px">이탈 방지 전략 라이브러리</h1>
    <p class="kk-desc" style="font-size:17px">실험으로 검증된 전략이 쌓이는 곳이에요. 효과가 확인된 전략부터 다시 활용해 보세요.</p>
  </div>
  <ol class="kk-stepper" aria-label="진행 단계">{''.join(steps)}</ol>
</section>"""


def verdict_badge(verdict: str, kind: str) -> str:
    bg = {"good": V["good_bg"], "warn": V["warn_bg"], "bad": V["bad_bg"]}[kind]
    color = {"good": V["good_text"], "warn": V["warn_text"], "bad": V["bad_text"]}[kind]
    return (f'<span style="flex-shrink:0; padding:5px 12px; border-radius:999px; background:{bg}; '
            f'color:{color}; font-size:12px; font-weight:700">{escape(verdict)}</span>')


def strategy_card_html(item: dict) -> str:
    lift_color = {"good": V["good_text"], "warn": T["text"], "bad": V["bad_text"]}[item["kind"]]
    return f"""<div class="kk">
  <div class="kk-lib-top">
    <h3 class="kk-lib-name">{escape(item['name'])}</h3>
    {verdict_badge(item['verdict'], item['kind'])}
  </div>
  <p class="kk-lib-target">적용 대상 · {escape(item['target'])}</p>
  <div class="kk-lib-divider"></div>
  <div class="kk-lib-stats">
    <div>
      <div class="kk-lib-stat-label">실측 유지율 상승분</div>
      <div class="kk-lib-stat-val" style="color:{lift_color}">{item['lift']:+.0f}%p</div>
    </div>
    <div style="text-align:right">
      <div class="kk-lib-stat-label">실험 고객</div>
      <div class="kk-lib-stat-val" style="color:{T['text']}">{item['n']:,}<span class="kk-lib-stat-unit">명</span></div>
    </div>
  </div>
</div>"""


def empty_state_html() -> str:
    return '<div class="kk-empty">아직 검증된 전략이 없어요. 실험 관리에서 실험을 만들고 결과를 입력하면 여기에 전략 카드로 쌓여요.</div>'

def plan_card_html(p) -> str:
    before, after = p["churn_rate_before"] * 100, p["churn_rate_after"] * 100
    badge = (f'<span style="flex-shrink:0; padding:5px 12px; border-radius:999px; '
             f'background:{T["accent_soft"]}; color:{T["accent"]}; font-size:12px; font-weight:700">'
             f'{escape(str(p["status"]))}</span>')
    return f"""<div class="kk">
  <div class="kk-lib-top">
    <h3 class="kk-lib-name">{escape(str(p['title']))}</h3>
    {badge}
  </div>
  <p class="kk-lib-target">적용 대상 · {escape(str(p['segment_name']))} · {escape(str(p['marketing_name']))}</p>
  <div class="kk-lib-divider"></div>
  <div class="kk-lib-stats">
    <div>
      <div class="kk-lib-stat-label">예상 이탈률</div>
      <div class="kk-lib-stat-val" style="color:{T['text']}">{before:.1f}<span class="kk-lib-stat-unit">% →</span> {after:.1f}<span class="kk-lib-stat-unit">%</span></div>
    </div>
    <div style="text-align:right">
      <div class="kk-lib-stat-label">예상 감소</div>
      <div class="kk-lib-stat-val" style="color:{T['accent']}">{p['reduced_customers']:,.1f}<span class="kk-lib-stat-unit">명</span></div>
    </div>
  </div>
</div>"""

@st.dialog("계획 상세", width="large")
def show_plan_detail(p: dict) -> None:
    goals = json.loads(p["goals"]) if p["goals"] else {}
    before, after = p["churn_rate_before"] * 100, p["churn_rate_after"] * 100

    st.markdown(f"### {p['title']}")
    st.caption(f"상태: {p['status']} · 저장일 {p['created_at']} · 계획 번호 #{p['id']}")

    st.markdown("#### 대상과 전략")
    st.markdown(
        f"- **군집** · {p['segment_name']} ({int(p['customer_count'] or 0):,}명)\n"
        f"- **핵심 목표** · {p.get('cluster_goal') or '-'}\n"
        f"- **전략** · {p['marketing_name']}"
    )

    st.markdown("#### 목표 설정")
    goal_rows = [{"행동 목표": k, "목표값": f"{v}%"} for k, v in goals.items() if v]
    if goal_rows:
        st.dataframe(goal_rows, hide_index=True, use_container_width=True)
    else:
        st.caption("설정한 목표가 없어요.")

    st.markdown("#### 예상 결과")
    c1, c2, c3 = st.columns(3)
    c1.metric("현재 예상 이탈률", f"{before:.1f}%")
    c2.metric("목표 달성 시", f"{after:.1f}%", f"{after - before:+.2f}%p", delta_color="inverse")
    c3.metric("예상 감소 인원", f"{p['reduced_customers']:,.1f}명")
    st.caption(
        f"예상 이탈자 {p['expected_churn_before']:,.1f}명 → {p['expected_churn_after']:,.1f}명 "
        "· 모델 기반 What-if 예측"
    )

    st.markdown("#### 내용")
    st.write(p["description"] or "(작성한 내용 없음)")

def render_plans() -> None:
    try:
        plans = load_plans()
    except Exception as error:
        st.warning(f"저장한 계획을 불러오지 못했습니다: {error}")
        return

    st.markdown(
        compact(f'<div class="kk"><h2 class="kk-h2">저장한 계획 ({len(plans)})</h2>'
                f'<p class="kk-desc">목표 시뮬레이션에서 저장한, 아직 실행 전인 계획이에요.</p></div>'),
        unsafe_allow_html=True,
    )
    if plans.empty:
        st.caption("아직 저장한 계획이 없어요.")
        return

    cols = st.columns(2, gap="medium")
    for i, (_, p) in enumerate(plans.iterrows()):
        with cols[i % 2]:
            with st.container(key=f"kkcard-lib-plan-{p['id']}"):
                st.markdown(compact(plan_card_html(p)), unsafe_allow_html=True)
                if st.button("상세 보기", key=f"plan_detail_{p['id']}", use_container_width=True):
                    show_plan_detail(p.to_dict())

def library_page() -> None:
    ss = st.session_state
    store.load_into(ss)
    library = ss.get("strategy_library", [])
    st.markdown(compact(page_css()), unsafe_allow_html=True)
    st.markdown(compact(f'<div class="kk">{head_html()}</div>'), unsafe_allow_html=True)

    with st.container(key="kk-body"):
        render_plans()
        st.markdown(compact('<div class="kk"><h2 class="kk-h2">검증된 전략</h2></div>'), unsafe_allow_html=True)
        if not library:
            st.markdown(compact(f'<div class="kk">{empty_state_html()}</div>'), unsafe_allow_html=True)
            with st.container(key="kk-empty-actions"):
                if st.button("실험 관리로 가기", type="primary"):
                    st.switch_page("pages/3_experiments.py")
            return

        counts = {f: sum(1 for it in library if f == "전체" or it["verdict"] == f) for f in FILTERS}
        tab_labels = [f"{f} ({counts[f]})" for f in FILTERS]
        with st.container(key="kk-lib-filter-gap"):
            picked = choose("판정 필터", tab_labels, "lib_filter", tab_labels[0])
        selected = FILTERS[tab_labels.index(picked)] if picked in tab_labels else "전체"

        shown = library if selected == "전체" else [it for it in library if it["verdict"] == selected]

        cols = st.columns(2, gap="medium")
        for i, item in enumerate(shown):
            with cols[i % 2]:
                with st.container(key=f"kkcard-lib-{item['exp_id']}"):
                    st.markdown(compact(strategy_card_html(item)), unsafe_allow_html=True)


# ─────────────────────────────────────────────

ui.render_header()
library_page()
