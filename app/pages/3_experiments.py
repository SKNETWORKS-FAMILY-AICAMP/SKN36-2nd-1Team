"""KKeeper — 마케팅 시나리오 비교 페이지.

고객 매칭 화면에서 선택한 위험 고객 집단에 두 마케팅 시나리오를
적용하고, 예상 행동 변화와 이탈률 변화를 같은 기준에서 비교합니다.

이 화면은 실제 A/B 실험이 아니라 모델 기반 예측 비교입니다.
시뮬레이션 결과는 로컬 파일에 저장하지 않으며, 저장 버튼을 누르면
데이터베이스 저장 계층에 넘길 payload를 생성합니다.
"""

from __future__ import annotations

import math
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

import altair as alt
import joblib
import numpy as np
import pandas as pd
import streamlit as st
from common.db import save_plan  # noqa: E402

try:
    from streamlit_sortables import sort_items
except ImportError:
    sort_items = None


# 프로젝트/app/pages/3_experiments.py 기준
APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = APP_DIR.parent
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

import ui  # noqa: E402
from common.experiment import (  # noqa: E402
    CLUSTER_GOALS, CLUSTER_MARKETING, WHATIF_LEVERS, balance_table, get_segment_customers, lever_eligible,
    restore_churn_categories, simulate_segment, split_ab, whatif_customers,
)
from ui import compact  # noqa: E402

st.set_page_config(
    page_title="마케팅 비교 · KKeeper",
    layout="wide",
    initial_sidebar_state="collapsed",
)
T = ui.init("experiments")

STEP_NAMES = ["위험 고객 선택", "마케팅 비교", "결과 저장", "저장 목록"]

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "models"
KKBOX_PATH = DATA_DIR / "kkbox_scored.csv"
SEGMENTS_PATH = DATA_DIR / "risk_segments.csv"
CHURN_MODEL_PATH = MODEL_DIR / "lgbm_final.joblib"
BEHAVIOR_MODEL_PATH = MODEL_DIR / "behavior_model.joblib"

CHANNELS = ["이메일", "앱 푸시", "문자", "웹", "소셜"]
OFFERS = ["구독료 할인", "무료 이용 혜택", "콘텐츠 추천", "단순 안내"]


def choose(
    label: str,
    options: list[str],
    key: str,
    default: str,
    label_visibility: str = "visible",
) -> str:
    """최신 Streamlit에서는 pills, 이전 버전에서는 radio를 사용합니다."""
    if hasattr(st, "pills"):
        return st.pills(
            label,
            options,
            default=default,
            key=key,
            label_visibility=label_visibility,
        )
    return st.radio(
        label,
        options,
        index=options.index(default),
        key=key,
        horizontal=True,
        label_visibility=label_visibility,
    )


@st.cache_resource(show_spinner=False)
def load_simulation_assets() -> dict[str, Any]:
    """100,000명 데이터와 두 모델을 화면 실행 중 한 번만 불러옵니다."""
    required_paths = [
        KKBOX_PATH,
        SEGMENTS_PATH,
        CHURN_MODEL_PATH,
        BEHAVIOR_MODEL_PATH,
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError("\n".join(missing))

    churn_bundle = joblib.load(CHURN_MODEL_PATH)
    behavior_bundle = joblib.load(BEHAVIOR_MODEL_PATH)
    kk = pd.read_csv(KKBOX_PATH)
    kk = restore_churn_categories(kk, churn_bundle)
    risk_segments = pd.read_csv(SEGMENTS_PATH, encoding="utf-8-sig")

    return {
        "kk": kk,
        "risk_segments": risk_segments,
        "churn_bundle": churn_bundle,
        "behavior_bundle": behavior_bundle,
    }


def page_css() -> str:
    return f"""
<style>
  .st-key-kk-body {{ padding: 28px 64px 64px; }}
  .st-key-kk-body [data-testid="stVerticalBlock"] {{ gap: 16px !important; }}
  .st-key-kk-body [data-testid="stHorizontalBlock"] {{ gap: 18px !important; }}

  .kk-stepper {{ margin:0; padding:0; list-style:none; display:flex; align-items:center;
                 gap:4px; flex-wrap:wrap; }}
  .kk-stepper li.s {{ display:flex; align-items:center; gap:10px; padding:8px 16px 8px 8px;
                      border-radius:999px; border:1px solid {T['tint_border']};
                      font-size:14px; color:{T['subtle']}; }}
  .kk-stepper li.s.on {{ border-color:transparent; background:{T['accent_soft']};
                         color:{T['accent']}; font-weight:700; }}
  .kk-stepper li.s i {{ font-style:normal; width:26px; height:26px; border-radius:999px;
                       background:{T['surface']}; font-family:Rubik,sans-serif; font-size:12px;
                       display:flex; align-items:center; justify-content:center; }}
  .kk-stepper li.s.on i {{ background:{T['accent']}; color:{T['accent_text']}; }}
  .kk-stepper li.l {{ width:12px; height:1px; background:{T['chip_border']}; }}

  .kk-target {{ padding:22px 24px; border:1px solid {T['accent']}; border-radius:18px;
                background:{T['surface']}; display:flex; justify-content:space-between;
                align-items:center; gap:24px; flex-wrap:wrap; }}
  .kk-target-copy {{ display:flex; flex-direction:column; gap:6px; }}
  .kk-target-eyebrow {{ font-size:12px; font-weight:700; color:{T['accent']}; }}
  .kk-target-title {{ margin:0; font-size:22px; font-weight:700; color:{T['text']}; }}
  .kk-target-desc {{ font-size:13px; line-height:1.55; color:{T['muted']}; }}
  .kk-target-metrics {{ display:flex; gap:10px; flex-wrap:wrap; }}
  .kk-target-metric {{ min-width:138px; padding:12px 14px; border-radius:12px;
                       background:{T['tint']}; border:1px solid {T['tint_border']}; }}
  .kk-target-metric span {{ display:block; margin-bottom:5px; font-size:11px; color:{T['subtle']}; }}
  .kk-target-metric b {{ font-family:Rubik,'IBM Plex Sans KR',sans-serif;
                         font-size:18px; color:{T['text']}; }}

  .kk-panel-head {{ display:flex; justify-content:space-between; align-items:baseline;
                    gap:16px; flex-wrap:wrap; margin-bottom:18px; }}
  .kk-panel-head h2 {{ margin:0; font-size:20px; color:{T['text']}; }}
  .kk-panel-head span {{ font-size:12px; color:{T['subtle']}; }}
  .kk-help {{ padding:12px 14px; border-radius:11px; background:{T['accent_soft']};
              color:{T['tip_text']}; font-size:12px; line-height:1.55; }}

  div[class*="st-key-kk-builder"] {{ padding:22px 24px; border-radius:18px;
                                      border:1px solid {T['border']}; background:{T['surface']}; }}
  div[class*="st-key-kk-builder"] [data-testid="stForm"] {{ border:none; padding:0; }}
  div[class*="st-key-kk-builder"] [data-testid="stForm"] > div {{ gap:14px !important; }}
  div[class*="st-key-kk-drag-board"] iframe {{ border-radius:18px !important; }}

  .kk-wait {{ min-height:130px; padding:30px; display:flex; flex-direction:column;
              align-items:center; justify-content:center; text-align:center; gap:8px;
              border:1px dashed {T['tint_border']}; border-radius:18px; background:{T['tint']}; }}
  .kk-wait b {{ font-size:16px; color:{T['text']}; }}
  .kk-wait span {{ font-size:13px; line-height:1.55; color:{T['muted']}; }}

  .kk-result-title {{ display:flex; align-items:center; justify-content:space-between;
                      gap:12px; flex-wrap:wrap; margin:10px 0 2px; }}
  .kk-result-title h2 {{ margin:0; font-size:24px; color:{T['text']}; }}
  .kk-result-badge {{ padding:6px 12px; border-radius:999px; background:{T['accent_soft']};
                      color:{T['accent']}; font-size:12px; font-weight:700; }}
  .kk-winner {{ padding:17px 19px; border-radius:14px; background:{T['accent_soft']};
                border:1px solid {T['tint_border']}; color:{T['tip_text']};
                font-size:14px; line-height:1.6; }}

  .st-key-kk-body [data-testid="stMetric"] {{ padding:16px 18px; border-radius:14px;
                                               border:1px solid {T['border']};
                                               background:{T['surface']}; }}
  .st-key-kk-body [data-testid="stMetricLabel"] p {{ color:{T['subtle']} !important; }}
  .st-key-kk-body [data-testid="stMetricValue"] {{ color:{T['text']} !important; }}

  div[class*="st-key-kk-save"] {{ margin-top:4px; padding:22px 24px; border-radius:18px;
                                   border:1px solid {T['border']}; background:{T['surface']}; }}

  .st-key-kk-body [data-testid="stBaseButton-primary"],
  .st-key-kk-body [data-testid="stBaseButton-secondary"] {{ min-height:46px !important;
      border-radius:12px !important; font-family:'IBM Plex Sans KR',sans-serif !important; }}
  .st-key-kk-body [data-testid="stBaseButton-primary"] {{ background:{T['accent']} !important;
      border:none !important; color:{T['accent_text']} !important; }}
  .st-key-kk-body [data-testid="stBaseButton-secondary"] {{ background:transparent !important;
      border:1px solid {T['secondary_border']} !important; color:{T['text']} !important; }}

  @media (max-width:1100px) {{
    .st-key-kk-body {{ padding:24px 16px 48px; }}
    .kk-target {{ align-items:flex-start; }}
  }}
    .kk-split {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
  .kk-group {{ padding:18px 20px; border-radius:16px; border:1px solid {T['border']};
               background:{T['surface']}; }}
  .kk-group h3 {{ margin:0 0 12px; font-size:17px; color:{T['text']}; }}
  .kk-group-metrics {{ display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:10px; }}
  .kk-balance-ok {{ color:{T['accent']}; font-weight:700; }}
  @media (max-width:760px) {{ .kk-split {{ grid-template-columns:1fr; }} }}
</style>
"""


def sortable_css() -> str:
    """streamlit-sortables iframe 안의 시나리오 보드 스타일입니다."""
    return f"""
    .sortable-component {{
        display:grid;
        grid-template-columns:1fr 1.12fr 1fr;
        gap:14px;
        padding:0;
        background:transparent;
        color:{T['text']};
        font-family:'IBM Plex Sans KR',sans-serif;
    }}
    .sortable-container {{
        min-width:0;
        min-height:190px;
        padding:16px;
        border-radius:16px;
        border:1px dashed {T['accent']};
        background:{T['accent_soft']};
    }}
    .sortable-container:nth-child(2) {{
        border-style:solid;
        border-color:{T['border']};
        background:{T['surface']};
    }}
    .sortable-container-header {{
        margin:0 0 12px;
        padding:0 2px 11px;
        border-bottom:1px solid {T['line']};
        color:{T['text']};
        font-size:15px;
        font-weight:700;
    }}
    .sortable-container-body {{ min-height:120px; }}
    .sortable-container:first-child .sortable-container-body:not(:has(.sortable-item))::before,
    .sortable-container:last-child .sortable-container-body:not(:has(.sortable-item))::before {{
        content:'마케팅 카드 1장을 이곳으로 드래그하세요';
        min-height:116px;
        display:flex;
        align-items:center;
        justify-content:center;
        padding:0 14px;
        color:{T['muted']};
        font-size:12px;
        text-align:center;
        pointer-events:none;
    }}
    .sortable-container:nth-child(2) .sortable-container-body:not(:has(.sortable-item))::before {{
        content:'위 양식에서 마케팅 카드를 먼저 만드세요';
        min-height:116px;
        display:flex;
        align-items:center;
        justify-content:center;
        color:{T['muted']};
        font-size:12px;
        text-align:center;
    }}
    .sortable-item, .sortable-item:hover {{
        min-height:92px;
        margin:0 0 9px;
        padding:14px 15px;
        border-radius:12px;
        border:1px solid {T['tint_border']};
        background:{T['tint']};
        color:{T['text']};
        font-size:13px;
        font-weight:650;
        line-height:1.55;
        white-space:pre-line;
        cursor:grab;
        box-shadow:none;
    }}
    .sortable-item:hover {{ border-color:{T['accent']}; }}
    @media (max-width:760px) {{
        .sortable-component {{ grid-template-columns:1fr; }}
        .sortable-container {{ min-height:145px; }}
        .sortable-container-body {{ min-height:80px; }}
    }}
    """


def head_html() -> str:
    steps = []
    for index, name in enumerate(STEP_NAMES):
        if index:
            steps.append('<li class="l" aria-hidden="true"></li>')
        active = " on" if index == 1 else ""
        steps.append(f'<li class="s{active}"><i>{index + 1:02d}</i>{name}</li>')
    return f"""
<section class="kk-page" style="padding-bottom:0; flex-direction:row; align-items:flex-end;
 justify-content:space-between; flex-wrap:wrap; gap:24px">
  <div style="display:flex; flex-direction:column; gap:12px">
    <h1 class="kk-h2 kk-title" style="font-size:36px">마케팅 시나리오 비교</h1>
    <p class="kk-desc" style="font-size:16px">같은 위험 고객 집단에 서로 다른 마케팅을 적용해 예상 변화를 비교해요.</p>
  </div>
  <ol class="kk-stepper" aria-label="진행 단계">{''.join(steps)}</ol>
</section>"""


def selected_segment() -> dict[str, Any] | None:
    matched = st.session_state.get("matched_segment")
    if matched:
        return matched
    matched_list = st.session_state.get("matched_segments") or []
    return matched_list[0] if matched_list else None


def target_html(segment: dict[str, Any]) -> str:
    name = escape(str(segment.get("name") or segment.get("segment") or "선택 고객"))
    description = escape(str(segment.get("trait") or "선택한 위험 고객 집단입니다."))
    customer_count = int(segment.get("size", 0))
    churn_prob = float(segment.get("churn_prob", 0))
    expected_churn = float(segment.get("expected_churn", customer_count * churn_prob))
    return f"""

<section class="kk kk-target">
  <div class="kk-target-copy">
    <span class="kk-target-eyebrow">SIMULATION TARGET</span>
    <h2 class="kk-target-title">{name}</h2>
    <span class="kk-target-desc">{description}</span>
  </div>
  <div class="kk-target-metrics">
    <div class="kk-target-metric"><span>대상 고객</span><b>{customer_count:,}명</b></div>
    <div class="kk-target-metric"><span>현재 예상 이탈률</span><b>{churn_prob * 100:.1f}%</b></div>
    <div class="kk-target-metric"><span>현재 예상 이탈자</span><b>{expected_churn:,.1f}명</b></div>
  </div>
</section>"""
def ensure_split(segment_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """같은 군집·같은 seed면 다시 나누지 않고 세션에 저장된 결과를 씁니다."""
    ss = st.session_state
    seed = ss.setdefault("split_seed", 42)
    key = (segment_name, seed)
    if ss.get("split_key") != key:
        assets = load_simulation_assets()
        customers = get_segment_customers(assets["kk"], assets["risk_segments"], segment_name)
        ss["split_groups"] = split_ab(customers, seed=seed)
        ss["split_key"] = key
    return ss["split_groups"]


def group_html(name: str, group: pd.DataFrame) -> str:
    metrics = [
        ("고객 수", f"{len(group):,}명"),
        ("평균 이탈확률", f"{group['churn_prob'].mean() * 100:.1f}%"),
        ("예상 이탈자", f"{group['churn_prob'].sum():,.1f}명"),
    ]
    cells = "".join(
        f'<div class="kk-target-metric"><span>{label}</span><b>{value}</b></div>'
        for label, value in metrics
    )
    return f'<div class="kk-group"><h3>{name}</h3><div class="kk-group-metrics">{cells}</div></div>'


def render_split(segment_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    st.markdown(
        compact(
            '<div class="kk kk-panel-head"><h2>실험 그룹 나누기</h2>'
            '<span>이탈확률이 비슷하도록 구간별로 반씩 나눴어요.</span></div>'
        ),
        unsafe_allow_html=True,
    )
    group_a, group_b = ensure_split(segment_name)
    st.markdown(
        compact(f'<div class="kk kk-split">{group_html("그룹 A", group_a)}{group_html("그룹 B", group_b)}</div>'),
        unsafe_allow_html=True,
    )

    table = balance_table(group_a, group_b)
    balanced = bool((table["표준화 차이"].abs() < 0.1).all())
    with st.expander("두 그룹 균형 확인" + (" · 균형 양호" if balanced else " · 차이 있음")):
        st.dataframe(
            table.style.format({"그룹 A": "{:,.3f}", "그룹 B": "{:,.3f}", "표준화 차이": "{:+.3f}"}),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("표준화 차이의 절댓값이 0.1 미만이면 두 그룹이 비슷하다고 봅니다.")

    if st.button("다른 조합으로 다시 나누기", key="resplit"):
        st.session_state["split_seed"] = st.session_state.get("split_seed", 42) + 1
        st.rerun()

    return group_a, group_b


MODES = ["마케팅 비교", "가상 A/B 테스트", "행동 시나리오"]
MODE_HELP = {
    "마케팅 비교": "선택한 군집 전체에 두 마케팅을 각각 적용해 어느 쪽이 이탈을 더 줄이는지 비교합니다.",
    "가상 A/B 테스트": "군집을 이탈확률이 비슷한 두 그룹으로 나누고, 한 그룹에만 마케팅을 적용해 효과를 확인합니다.",
    "행동 시나리오": "고객 행동의 목표치를 정하면, 그 목표를 달성했을 때 이탈률이 어떻게 바뀌는지 모델로 계산합니다.",
}

def render_mode_select() -> str:
    st.markdown(
        compact('<div class="kk kk-panel-head"><h2>실험 방식</h2></div>'),
        unsafe_allow_html=True,
    )
    mode = choose("실험 방식", MODES, "exp_mode", MODES[0], label_visibility="collapsed") or MODES[0]
    st.markdown(compact(f'<div class="kk kk-help">{MODE_HELP[mode]}</div>'), unsafe_allow_html=True)
    return mode


def render_single_campaign_select() -> dict[str, Any] | None:
    cards = st.session_state["marketing_cards"]
    if not cards:
        return None
    labels = [campaign_label(card).replace("\n", " · ") for card in cards]
    picked = st.selectbox(
        "그룹 A에 적용할 마케팅",
        [""] + labels,
        key="group_campaign",
        format_func=lambda v: v or "마케팅 카드를 선택하세요",
    )
    return cards[labels.index(picked)] if picked else None


def ensure_group_result(group_a: pd.DataFrame, campaign: dict[str, Any]) -> dict[str, Any]:
    ss = st.session_state
    key = (ss.get("split_key"), campaign_signature(campaign))
    if ss.get("group_result_key") != key:
        assets = load_simulation_assets()
        temp_segments = group_a[["msno","churn_prob"]].assign(segment="__group_a__")
        with st.spinner("그룹 A에 마케팅을 적용해 계산하고 있습니다..."):
            ss["group_result"] = simulate_segment(
                kk=assets["kk"],
                risk_segments=temp_segments,
                churn_bundle=assets["churn_bundle"],
                behavior_bundle=assets["behavior_bundle"],
                segment_name="__group_a__",
                **campaign,
            )
        ss["group_result_key"] = key
    return ss["group_result"]


def render_group_results(group_a: pd.DataFrame, group_b: pd.DataFrame, result: dict[str, Any]) -> None:
    row = result["summary"].iloc[0]
    rate_a_before = group_a["churn_prob"].mean() * 100
    rate_a_after = float(row["캠페인후_평균이탈확률"]) * 100
    rate_b = group_b["churn_prob"].mean() * 100
    churn_a_after = float(row["캠페인후_예상이탈자"])
    churn_b = group_b["churn_prob"].sum()

    st.markdown(
        compact(
            '<div class="kk kk-result-title"><h2>그룹 효과 검증 결과</h2>'
            '<span class="kk-result-badge">모델 기반 예측</span></div>'
        ),
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "그룹 A (마케팅 적용) 예상 이탈률",
        f"{rate_a_after:.2f}%",
        f"{rate_a_after - rate_a_before:+.2f}%p",
        delta_color="inverse",
    )
    c2.metric("그룹 B (미적용) 예상 이탈률", f"{rate_b:.2f}%")
    c3.metric("두 그룹 차이", f"{rate_a_after - rate_b:+.2f}%p", delta_color="inverse")

    d1, d2, d3 = st.columns(3)
    d1.metric("그룹 A 예상 이탈자", f"{churn_a_after:,.1f}명")
    d2.metric("그룹 B 예상 이탈자", f"{churn_b:,.1f}명")
    d3.metric("그룹 A 평균 행동 변화", f"{float(row['평균_행동변화율(%)']):+.1f}%")

    st.caption(
        "두 그룹은 적용 전 이탈확률이 비슷하도록 나눴기 때문에, 적용 후 차이를 마케팅 효과로 해석합니다. "
        "실제 실험이 아니라 모델로 예측한 값입니다."
    )

def render_whatif_results(result: dict[str, Any]) -> None:
    s = result["summary"]
    before, after = s["현재_평균이탈확률"] * 100, s["목표후_평균이탈확률"] * 100

    st.markdown(
        compact('<div class="kk kk-result-title"><h2>행동 시나리오 결과</h2>'
                '<span class="kk-result-badge">모델 기반 What-if</span></div>'),
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("현재 예상 이탈률", f"{before:.2f}%")
    c2.metric("목표 달성 시 예상 이탈률", f"{after:.2f}%", f"{after - before:+.2f}%p", delta_color="inverse")
    c3.metric("예상 감소 인원", f"{s['예상_감소인원']:,.1f}명")

    st.dataframe(
        result["behavior"].style.format({"현재": "{:,.3f}", "목표 적용 후": "{:,.3f}"}),
        use_container_width=True, hide_index=True,
    )
    if s["확률상승_고객비율"] > 0.3:
        st.warning("일부 고객은 목표를 적용했는데 이탈확률이 올라갔습니다. 모델이 이 행동을 반대로 해석했을 수 있어요.")
    st.caption("모델이 학습한 관계(상관관계)를 바탕으로 계산한 값이며, 실제 효과는 A/B 테스트로 확인해야 합니다.")


def render_marketing_pick(segment_name: str) -> dict[str, Any] | None:
    strategy = CLUSTER_MARKETING.get(segment_name)
    if not strategy:
        st.info("이 군집에 등록된 전략이 없습니다.")
        return None
    goal = CLUSTER_GOALS.get(segment_name, "")
    st.markdown(
        compact(f'<div class="kk kk-panel-head"><h2>추천 전략</h2>'
                f'<span>이 군집의 핵심 목표 · <b>{escape(goal)}</b></span></div>'
                f'<div class="kk kk-help"><b>{escape(strategy["name"])}</b><br>{escape(strategy["desc"])}</div>'),
        unsafe_allow_html=True,
    )
    if strategy.get("note"):
        st.caption(strategy["note"])
    return strategy


def _goal_slider(sid: str, key: str, default: int, eligible: dict[str, int]) -> int:
    info, n = WHATIF_LEVERS[key], eligible[key]
    return st.slider(
        f"{info['label']} (대상 {n:,}명)",
        min_value=0, max_value=info["max"], value=int(default), step=5, format="%d%%",
        help=info["help"], key=f"goal_{sid}_{key}", disabled=(n == 0),
    )

def render_goal_sliders(strategy: dict[str, Any], eligible: dict[str, int]) -> dict[str, int]:
    st.markdown(
        compact('<div class="kk kk-panel-head"><h2>행동 목표 설정</h2>'
                '<span>핵심 목표에 기본값이 채워져 있어요. 필요하면 조정하세요.</span></div>'),
        unsafe_allow_html=True,
    )
    levers = {}
    core = list(strategy["core"].items())
    for col, (key, default) in zip(st.columns(len(core)), core):
        with col:
            levers[key] = _goal_slider(strategy["id"], key, default, eligible)

    if strategy["aux"]:
        with st.expander("보조 목표 추가"):
            aux = list(strategy["aux"].items())
            for col, (key, default) in zip(st.columns(len(aux)), aux):
                with col:
                    levers[key] = _goal_slider(strategy["id"], key, default, eligible)

    if any(levers.get(k) for k in ("cancel_stop", "auto_renew_on")):
        st.info("해지·갱신 목표는 이탈과 직결돼 효과가 크게 계산됩니다. "
                "대상 고객 중 몇 %가 실제로 행동을 바꿀지는 가정입니다.")
    return levers


def build_plan_payload(segment, marketing, levers, result, title, description) -> dict[str, Any]:
    s = result["summary"]
    return json_safe({
        "title": title.strip(),
        "description": description.strip(),
        "status": "계획",
        "segment_name": segment.get("segment") or segment.get("name"),
        "marketing_id": marketing["id"],
        "marketing_name": marketing["name"],
        "goals": {WHATIF_LEVERS[k]["label"]: v for k, v in levers.items()},
        "customer_count": s["고객수"],
        "churn_rate_before": s["현재_평균이탈확률"],
        "churn_rate_after": s["목표후_평균이탈확률"],
        "expected_churn_before": s["현재_예상이탈자"],
        "expected_churn_after": s["목표후_예상이탈자"],
        "reduced_customers": s["예상_감소인원"],
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })


def render_plan_save(segment, marketing, levers, result) -> None:
    with st.container(key="kk-save"):
        st.markdown(
            compact('<div class="kk kk-panel-head"><h2>마케팅 계획 저장</h2>'
                    '<span>목표와 예상 결과, 선택 이유를 함께 남겨요.</span></div>'),
            unsafe_allow_html=True,
        )
        title = st.text_input("계획 제목", value=f"{segment.get('name')} · {marketing['name']}",
                              key="plan_title", max_chars=120)
        description = st.text_area("설명", key="plan_description", height=110, max_chars=1000,
                                   placeholder="이 마케팅과 목표를 고른 이유, 기대하는 점을 적어주세요.")
        if st.button("계획 저장", type="primary", key="plan_save"):
            if not title.strip():
                st.error("계획 제목을 입력해 주세요.")
                return
            payload = build_plan_payload(segment, marketing, levers, result, title, description)
            try:
                plan_id = save_plan(payload)
            except Exception as error:
                st.error(f"저장 중 오류가 발생했습니다: {error}")
            else:
                st.success(f"계획이 저장되었습니다. (계획 번호 {plan_id})")
                st.page_link("pages/4_library.py", label="라이브러리에서 보기 →")


def render_whatif(segment: dict[str, Any], segment_name: str) -> None:
    assets = load_simulation_assets()
    customers = get_segment_customers(assets["kk"], assets["risk_segments"], segment_name)

    marketing = render_marketing_pick(segment_name)
    if not marketing:
        return
    levers = render_goal_sliders(marketing, lever_eligible(customers))
    if not any(levers.values()):
        st.info("목표값을 하나 이상 설정하면 결과가 계산됩니다.")
        return

    result = whatif_customers(customers, levers, assets["churn_bundle"])
    render_whatif_results(result)
    render_plan_save(segment, marketing, levers, result)


def campaign_label(campaign: dict[str, Any]) -> str:
    benefit = (
        f"할인율 {campaign['benefit_pct']:.0f}%"
        if campaign["offer_name"] == "구독료 할인"
        else "혜택 강도 자동 적용"
    )
    return (
        f"{campaign['channel']} · {campaign['offer_name']}\n"
        f"{benefit} · {campaign['duration']}일"
    )


def campaign_signature(campaign: dict[str, Any]) -> tuple[Any, ...]:
    return (
        campaign["channel"],
        campaign["offer_name"],
        float(campaign["benefit_pct"]),
        int(campaign["duration"]),
    )


def sync_board_with_cards() -> list[dict[str, Any]]:
    """새 카드가 추가돼도 기존 A/B 배치를 유지합니다."""
    ss = st.session_state
    labels = [campaign_label(card) for card in ss["marketing_cards"]]
    board = ss.get("marketing_board")
    if not board or len(board) != 3:
        board = [
            {"header": "시나리오 A", "items": []},
            {"header": "만든 마케팅 카드", "items": labels},
            {"header": "시나리오 B", "items": []},
        ]
    else:
        placed = set(board[0]["items"] + board[2]["items"])
        board[1]["items"] = [label for label in labels if label not in placed]
        board[0]["items"] = [label for label in board[0]["items"] if label in labels]
        board[2]["items"] = [label for label in board[2]["items"] if label in labels]
    ss["marketing_board"] = board
    return board


def render_campaign_builder() -> None:
    ss = st.session_state
    with st.container(key="kk-builder"):
        st.markdown(
            compact(
                '<div class="kk kk-panel-head"><h2>마케팅 카드 만들기</h2>'
                '<span>입력 양식은 고정이고 조합은 자유롭게 만들 수 있어요.</span></div>'
            ),
            unsafe_allow_html=True,
        )

        channel = choose("발송 채널", CHANNELS, "mk_channel", "앱 푸시")
        offer_name = choose("마케팅 유형", OFFERS, "mk_offer", "구독료 할인")

        left, right = st.columns(2)
        with left:
            if offer_name == "구독료 할인":
                benefit_pct = st.slider(
                    "할인율",
                    min_value=0,
                    max_value=50,
                    value=30,
                    step=5,
                    format="%d%%",
                    key="mk_benefit_discount",
                )
            else:
                benefit_pct = 0
                st.slider(
                    "할인율",
                    min_value=0,
                    max_value=50,
                    value=0,
                    disabled=True,
                    help="구독료 할인을 선택했을 때만 사용합니다.",
                    key="mk_benefit_disabled",
                )
        with right:
            duration = st.slider(
                "캠페인 유효기간",
                min_value=3,
                max_value=10,
                value=7,
                step=1,
                format="%d일",
                key="mk_duration",
            )

        submitted = st.button(
            "+ 마케팅 카드 만들기",
            key="mk_add_card",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            campaign = {
                "channel": channel,
                "offer_name": offer_name,
                "benefit_pct": float(benefit_pct),
                "duration": int(duration),
            }
            signatures = {campaign_signature(card) for card in ss["marketing_cards"]}
            if campaign_signature(campaign) in signatures:
                st.info("같은 조건의 마케팅 카드가 이미 있습니다.")
            else:
                ss["marketing_cards"].append(campaign)
                sync_board_with_cards()
                st.rerun()

        st.markdown(
            compact(
                '<div class="kk kk-help">앱 푸시와 문자는 행동 모델에서 같은 mobile 채널로, '
                '콘텐츠 추천과 단순 안내는 같은 informational 유형으로 계산됩니다.</div>'
            ),
            unsafe_allow_html=True,
        )


def campaign_from_label(label: str) -> dict[str, Any] | None:
    return next(
        (
            card
            for card in st.session_state["marketing_cards"]
            if campaign_label(card) == label
        ),
        None,
    )


def render_scenario_board() -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    board = sync_board_with_cards()
    st.markdown(
        compact(
            '<div class="kk kk-panel-head"><h2>마케팅 시나리오 배치</h2>'
            '<span>A와 B에 각각 카드 한 장을 드래그하면 바로 계산됩니다.</span></div>'
        ),
        unsafe_allow_html=True,
    )

    if sort_items is None:
        st.warning("드래그 기능을 사용하려면 streamlit-sortables를 설치해 주세요.")
        labels = [campaign_label(card) for card in st.session_state["marketing_cards"]]
        left, right = st.columns(2)
        with left:
            label_a = st.selectbox("시나리오 A", [""] + labels, key="fallback_a")
        with right:
            label_b = st.selectbox("시나리오 B", [""] + labels, key="fallback_b")
        return campaign_from_label(label_a), campaign_from_label(label_b)

    with st.container(key="kk-drag-board"):
        result = sort_items(
            board,
            multi_containers=True,
            direction="horizontal",
            custom_style=sortable_css(),
        )
    if result and len(result) == 3:
        st.session_state["marketing_board"] = result
        board = result

    items_a = board[0]["items"]
    items_b = board[2]["items"]
    if len(items_a) > 1 or len(items_b) > 1:
        st.error("시나리오 A와 B에는 마케팅 카드를 한 장씩만 넣어 주세요.")
        return None, None

    campaign_a = campaign_from_label(items_a[0]) if len(items_a) == 1 else None
    campaign_b = campaign_from_label(items_b[0]) if len(items_b) == 1 else None
    return campaign_a, campaign_b


def run_comparison(
    segment_name: str,
    campaign_a: dict[str, Any],
    campaign_b: dict[str, Any],
) -> dict[str, Any]:
    assets = load_simulation_assets()
    common = {
        "kk": assets["kk"],
        "risk_segments": assets["risk_segments"],
        "churn_bundle": assets["churn_bundle"],
        "behavior_bundle": assets["behavior_bundle"],
        "segment_name": segment_name,
    }
    result_a = simulate_segment(**common, **campaign_a)
    result_b = simulate_segment(**common, **campaign_b)
    return {"A": result_a, "B": result_b}


def ensure_comparison(
    segment_name: str,
    campaign_a: dict[str, Any],
    campaign_b: dict[str, Any],
) -> dict[str, Any]:
    ss = st.session_state
    result_key = (
        segment_name,
        campaign_signature(campaign_a),
        campaign_signature(campaign_b),
    )
    if ss.get("comparison_key") != result_key:
        with st.spinner("두 마케팅을 적용해 고객 행동과 이탈률을 계산하고 있습니다..."):
            ss["comparison_result"] = run_comparison(
                segment_name,
                campaign_a,
                campaign_b,
            )
        ss["comparison_key"] = result_key
        ss["simulation_title"] = (
            f"{segment_name} · {campaign_a['offer_name']} vs {campaign_b['offer_name']}"
        )
        ss["simulation_description"] = ""
    return ss["comparison_result"]


def summary_row(result: dict[str, pd.DataFrame]) -> pd.Series:
    return result["summary"].iloc[0]


def render_results(
    segment: dict[str, Any],
    campaign_a: dict[str, Any],
    campaign_b: dict[str, Any],
    comparison: dict[str, Any],
) -> None:
    row_a = summary_row(comparison["A"])
    row_b = summary_row(comparison["B"])
    baseline_rate = float(row_a["현재_평균이탈확률"]) * 100
    rate_a = float(row_a["캠페인후_평균이탈확률"]) * 100
    rate_b = float(row_b["캠페인후_평균이탈확률"]) * 100
    reduced_a = float(row_a["예상_감소인원"])
    reduced_b = float(row_b["예상_감소인원"])

    winner = "A" if reduced_a > reduced_b else "B" if reduced_b > reduced_a else "동일"
    difference = abs(reduced_a - reduced_b)

    st.markdown(
        compact(
            '<div class="kk kk-result-title"><h2>시뮬레이션 결과</h2>'
            '<span class="kk-result-badge">모델 기반 예측 비교</span></div>'
        ),
        unsafe_allow_html=True,
    )

    baseline_col, a_col, b_col = st.columns(3)
    baseline_col.metric("현재 예상 이탈률", f"{baseline_rate:.2f}%")
    a_col.metric(
        "시나리오 A 예상 이탈률",
        f"{rate_a:.2f}%",
        f"{rate_a - baseline_rate:+.2f}%p",
        delta_color="inverse",
    )
    b_col.metric(
        "시나리오 B 예상 이탈률",
        f"{rate_b:.2f}%",
        f"{rate_b - baseline_rate:+.2f}%p",
        delta_color="inverse",
    )

    current_col, result_a_col, result_b_col = st.columns(3)
    current_col.metric(
        "현재 예상 이탈자",
        f"{float(row_a['현재_예상이탈자']):,.2f}명",
    )
    result_a_col.metric(
        "A 예상 이탈자",
        f"{float(row_a['캠페인후_예상이탈자']):,.2f}명",
        f"-{reduced_a:,.2f}명",
        delta_color="inverse",
    )
    result_b_col.metric(
        "B 예상 이탈자",
        f"{float(row_b['캠페인후_예상이탈자']):,.2f}명",
        f"-{reduced_b:,.2f}명",
        delta_color="inverse",
    )

    if winner == "동일":
        winner_text = "두 시나리오의 예상 이탈 감소 효과가 같습니다."
    else:
        winner_text = (
            f"시나리오 {winner}가 다른 시나리오보다 예상 이탈자를 "
            f"약 {difference:,.2f}명 더 감소시키는 것으로 추정됩니다."
        )
    st.markdown(
        compact(f'<div class="kk kk-winner"><b>비교 결과</b> · {escape(winner_text)}</div>'),
        unsafe_allow_html=True,
    )

    result_table = pd.DataFrame(
        [
            {
                "구분": "현재 기준",
                "마케팅": "적용하지 않음",
                "예상 이탈률(%)": baseline_rate,
                "예상 이탈자": float(row_a["현재_예상이탈자"]),
                "예상 감소 인원": np.nan,
                "감소 인원 95% 범위": "-",
                "평균 행동 변화율(%)": np.nan,
            },
            {
                "구분": "시나리오 A",
                "마케팅": campaign_label(campaign_a).replace("\n", " · "),
                "예상 이탈률(%)": rate_a,
                "예상 이탈자": float(row_a["캠페인후_예상이탈자"]),
                "예상 감소 인원": reduced_a,
                "감소 인원 95% 범위": (
                    f"{float(row_a['감소인원_하한(95%)']):.2f}~"
                    f"{float(row_a['감소인원_상한(95%)']):.2f}명"
                ),
                "평균 행동 변화율(%)": float(row_a["평균_행동변화율(%)"]),
            },
            {
                "구분": "시나리오 B",
                "마케팅": campaign_label(campaign_b).replace("\n", " · "),
                "예상 이탈률(%)": rate_b,
                "예상 이탈자": float(row_b["캠페인후_예상이탈자"]),
                "예상 감소 인원": reduced_b,
                "감소 인원 95% 범위": (
                    f"{float(row_b['감소인원_하한(95%)']):.2f}~"
                    f"{float(row_b['감소인원_상한(95%)']):.2f}명"
                ),
                "평균 행동 변화율(%)": float(row_b["평균_행동변화율(%)"]),
            },
        ]
    )
    st.dataframe(
        result_table.style.format(
            {
                "예상 이탈률(%)": "{:.2f}",
                "예상 이탈자": "{:,.2f}",
                "예상 감소 인원": "{:,.2f}",
                "평균 행동 변화율(%)": "{:+.2f}",
            },
            na_rep="-",
        ),
        use_container_width=True,
        hide_index=True,
    )

    feature_a = comparison["A"]["feature_changes"].copy()
    feature_b = comparison["B"]["feature_changes"].copy()
    behavior_compare = feature_a[
        ["metric_key", "행동 지표", "캠페인 전", "캠페인 후", "변화율(%)"]
    ].rename(
        columns={"캠페인 후": "A 적용 후", "변화율(%)": "A 변화율(%)"}
    )
    behavior_compare = behavior_compare.merge(
        feature_b[["metric_key", "캠페인 후", "변화율(%)"]].rename(
            columns={"캠페인 후": "B 적용 후", "변화율(%)": "B 변화율(%)"}
        ),
        on="metric_key",
        how="outer",
    )

    st.markdown("#### 고객 행동 변화 비교")
    chart_data = behavior_compare.melt(
        id_vars=["행동 지표"],
        value_vars=["A 변화율(%)", "B 변화율(%)"],
        var_name="시나리오",
        value_name="변화율",
    )
    chart_data["시나리오"] = chart_data["시나리오"].str[0]
    chart = (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("행동 지표:N", title=None, sort=None),
            y=alt.Y("변화율:Q", title="변화율 (%)"),
            color=alt.Color(
                "시나리오:N",
                title="시나리오",
                scale=alt.Scale(range=[T["accent"], "#CC9EB8"]),
            ),
            xOffset="시나리오:N",
            tooltip=[
                alt.Tooltip("행동 지표:N"),
                alt.Tooltip("시나리오:N"),
                alt.Tooltip("변화율:Q", format=".2f"),
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(chart, use_container_width=True)

    with st.expander("행동 지표의 정확한 전·후 값 보기"):
        st.dataframe(
            behavior_compare.drop(columns="metric_key").style.format(
                {
                    "캠페인 전": "{:,.2f}",
                    "A 적용 후": "{:,.2f}",
                    "B 적용 후": "{:,.2f}",
                    "A 변화율(%)": "{:+.2f}",
                    "B 변화율(%)": "{:+.2f}",
                },
                na_rep="-",
            ),
            use_container_width=True,
            hide_index=True,
        )

    unchanged = max(
        float(row_a["이탈확률_무변화비율(%)"]),
        float(row_b["이탈확률_무변화비율(%)"]),
    )
    if unchanged >= 50:
        st.info(
            "이 집단은 활동 기록이 없는 고객이 많아 일부 고객은 활동량에 행동 증가율을 "
            "적용해도 이탈확률이 변하지 않습니다. 결과를 보수적으로 해석해 주세요."
        )

    render_save_form(
        segment=segment,
        campaign_a=campaign_a,
        campaign_b=campaign_b,
        comparison=comparison,
        winner=winner,
    )


def json_safe(value: Any) -> Any:
    """numpy/pandas 값을 데이터베이스 JSON 컬럼에 넣을 수 있게 변환합니다."""
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if math.isnan(float(value)) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def scenario_payload(
    label: str,
    campaign: dict[str, Any],
    result: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    row = result["summary"].iloc[0].to_dict()
    feature_changes = result["feature_changes"].drop(columns="metric_key").to_dict("records")
    return json_safe(
        {
            "scenario_label": label,
            "channel": campaign["channel"],
            "offer_name": campaign["offer_name"],
            "benefit_pct": campaign["benefit_pct"],
            "duration": campaign["duration"],
            "behavior_lift_pct": row["평균_행동변화율(%)"],
            "churn_rate_after": row["캠페인후_평균이탈확률"],
            "expected_churn_after": row["캠페인후_예상이탈자"],
            "reduced_customers": row["예상_감소인원"],
            "reduction_low": row["감소인원_하한(95%)"],
            "reduction_high": row["감소인원_상한(95%)"],
            "churn_change_rate_pct": row["예상이탈_변화율(%)"],
            "feature_changes": feature_changes,
        }
    )


def build_save_payload(
    *,
    title: str,
    description: str,
    segment: dict[str, Any],
    campaign_a: dict[str, Any],
    campaign_b: dict[str, Any],
    comparison: dict[str, Any],
    winner: str,
) -> dict[str, Any]:
    base = summary_row(comparison["A"])
    return json_safe(
        {
            "title": title.strip(),
            "description": description.strip(),
            "segment_name": segment.get("segment") or segment.get("name"),
            "segment_display_name": segment.get("name"),
            "customer_count": int(base["고객수"]),
            "churn_rate_before": float(base["현재_평균이탈확률"]),
            "expected_churn_before": float(base["현재_예상이탈자"]),
            "recommended_scenario": winner,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "scenarios": [
                scenario_payload("A", campaign_a, comparison["A"]),
                scenario_payload("B", campaign_b, comparison["B"]),
            ],
        }
    )


def save_simulation_to_database(payload: dict[str, Any]) -> Any:
    """프로젝트 DB 저장 함수 연결 지점.

    실제 DB 모듈이 준비되면 이 함수 안에서 INSERT 트랜잭션을 실행합니다.
    현재는 로컬 파일이나 세션을 저장소처럼 사용하지 않습니다.
    """
    raise NotImplementedError(
        "DB 저장 모듈이 아직 연결되지 않았습니다. "
        "simulation과 simulation_scenario INSERT 함수를 이 위치에 연결해 주세요."
    )


def render_save_form(
    *,
    segment: dict[str, Any],
    campaign_a: dict[str, Any],
    campaign_b: dict[str, Any],
    comparison: dict[str, Any],
    winner: str,
) -> None:
    with st.container(key="kk-save"):
        st.markdown(
            compact(
                '<div class="kk kk-panel-head"><h2>시뮬레이션 저장</h2>'
                '<span>설명을 남기면 저장 목록에서 결과를 쉽게 구분할 수 있어요.</span></div>'
            ),
            unsafe_allow_html=True,
        )
        title = st.text_input(
            "시뮬레이션 제목",
            key="simulation_title",
            max_chars=120,
        )
        description = st.text_area(
            "설명",
            key="simulation_description",
            height=110,
            max_chars=1000,
            placeholder="이 고객 집단에 두 마케팅을 비교한 이유와 결과 해석을 입력하세요.",
        )

        _, back_col, save_col = st.columns([4, 1, 1.5])
        if back_col.button("대상 변경", use_container_width=True):
            st.switch_page("pages/2_matching.py")
        if save_col.button(
            "시뮬레이션 저장",
            type="primary",
            use_container_width=True,
        ):
            if not title.strip():
                st.error("시뮬레이션 제목을 입력해 주세요.")
                return

            payload = build_save_payload(
                title=title,
                description=description,
                segment=segment,
                campaign_a=campaign_a,
                campaign_b=campaign_b,
                comparison=comparison,
                winner=winner,
            )
            try:
                save_simulation_to_database(payload)
            except NotImplementedError as error:
                st.session_state["pending_simulation_payload"] = payload
                st.warning(str(error))
                with st.expander("DB에 전달될 저장 데이터 미리보기"):
                    st.json(payload)
            except Exception as error:
                st.error(f"시뮬레이션 저장 중 오류가 발생했습니다: {error}")
            else:
                st.success("시뮬레이션이 저장되었습니다.")


def experiments_page() -> None:
    st.markdown(compact(page_css()), unsafe_allow_html=True)
    st.markdown(compact(f'<div class="kk">{head_html()}</div>'), unsafe_allow_html=True)

    segment = selected_segment()
    with st.container(key="kk-body"):
        if not segment:
            st.warning("먼저 위험 고객 선택 화면에서 시뮬레이션 대상을 선택해 주세요.")
            if st.button("위험 고객 선택으로 이동", type="primary"):
                st.switch_page("pages/2_matching.py")
            st.stop()

        st.markdown(compact(target_html(segment)), unsafe_allow_html=True)

        segment_name = str(segment.get("segment") or segment.get("name"))
        try:
            render_whatif(segment, segment_name)
        except FileNotFoundError as error:
            st.error("시뮬레이션에 필요한 파일을 찾지 못했습니다.")
            st.code(str(error))

ui.render_header()
experiments_page()
