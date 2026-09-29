"""
KKeeper — 위험 고객 집단 선택 페이지 (pages/2_matching.py · 주소: /matching)

미리 생성한 위험 고객 4개 집단을 불러와 보여줍니다.
사용자는 고객 집단 카드를 선택 영역으로 드래그하고, 선택한 집단의
실제 요약 지표와 이탈확률 상위 고객을 확인한 뒤 다음 단계로 이동합니다.

"""

from html import escape
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

try:
    from streamlit_sortables import sort_items
except ImportError:  # 패키지 설치 전에도 페이지가 완전히 멈추지 않도록 선택형 UI 제공
    sort_items = None

# 실제 구조: 프로젝트/app/pages/2_matching.py, 프로젝트/app/ui.py, 프로젝트/data/processed
APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = APP_DIR.parent
sys.path.insert(0, str(APP_DIR))
import ui  # noqa: E402
from ui import compact  # noqa: E402

st.set_page_config(page_title="고객 매칭 · KKeeper", layout="wide", initial_sidebar_state="collapsed")
T = ui.init("matching")

STEP_NAMES = ["마케팅 설계", "고객 매칭", "실험 관리", "라이브러리"]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
SUMMARY_PATH = DATA_DIR / "risk_segment_summary.csv"
SEGMENTS_PATH = DATA_DIR / "risk_segments.csv"

# CSV의 분석용 이름은 그대로 두고, 화면에서는 짧고 읽기 쉬운 이름을 사용합니다.
SEGMENT_UI = {
    "저활동·단기 구독형": {
        "id": "low-activity-short",
        "display": "저활동 · 단기 구독",
        "description": "30일 단기 이용권 중심이고 청취 활동이 가장 적은 집단입니다. 위험 고객 중 상대적 위험은 가장 낮습니다.",
    },
    "반복 거래·취소 위험형": {
        "id": "repeat-cancel",
        "display": "반복 거래 · 취소 위험",
        "description": "자동갱신을 쓰면서도 마지막 거래에서 해지한 고객이 대부분인, 해지를 반복하는 집단입니다.",
    },
    "장기 플랜·고결제 고위험형": {
        "id": "long-plan-high-pay",
        "display": "장기 플랜 · 고결제",
        "description": "긴 이용권을 높은 금액으로 결제하고 활발히 듣지만, 이탈 확률이 가장 높은 집단입니다.",
    },
    "장기 관계·고빈도 거래형": {
        "id": "long-tenure-frequent",
        "display": "장기 관계 · 고빈도 거래",
        "description": "오래 이용하며 거래와 결제가 잦지만 해지 경험이 있는 집단입니다.",
    },
}

@st.cache_data(show_spinner=False)
def load_segment_data(summary_path: str, segments_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """노트북이 저장한 집단 요약과 고객별 분류 결과를 읽고 화면용 값을 붙입니다."""
    summary = pd.read_csv(summary_path, encoding="utf-8-sig")
    customers = pd.read_csv(segments_path, encoding="utf-8-sig")

    required_summary = {
        "segment", "인원", "평균_이탈확률", "평균_활동일", "마지막접속후_평균일수",
        "평균_해지횟수", "평균_결제금액",
    }
    required_customers = {"msno", "segment", "churn_prob"}
    missing_summary = required_summary.difference(summary.columns)
    missing_customers = required_customers.difference(customers.columns)
    if missing_summary or missing_customers:
        missing = sorted(missing_summary | missing_customers)
        raise ValueError("필요한 CSV 컬럼이 없습니다: " + ", ".join(missing))

    expected = (
        customers.groupby("segment", as_index=False)["churn_prob"]
        .sum()
        .rename(columns={"churn_prob": "예상_이탈자"})
    )
    summary = summary.merge(expected, on="segment", how="left")
    summary["예상_이탈자"] = summary["예상_이탈자"].fillna(0)
    summary["display_name"] = summary["segment"].map(
        lambda name: SEGMENT_UI.get(name, {}).get("display", name)
    )
    summary["description"] = summary["segment"].map(
        lambda name: SEGMENT_UI.get(name, {}).get("description", "위험 고객 분석으로 분류된 집단입니다.")
    )
    summary["segment_id"] = summary["segment"].map(
        lambda name: SEGMENT_UI.get(name, {}).get("id", name)
    )

    order = {name: i for i, name in enumerate(SEGMENT_UI)}
    summary["_order"] = summary["segment"].map(order).fillna(len(order))
    summary = summary.sort_values("_order").drop(columns="_order").reset_index(drop=True)
    return summary, customers


def match_css() -> str:
    return f"""
<style>
    div[class*="st-key-kk-body"] {{ padding: 28px 0 64px !important; }}
    div[class*="st-key-kk-body"] > [data-testid="stVerticalBlock"] {{ gap: 0 !important; }}
    .kk-context {{ margin: 0 64px 18px; }}

    .kk-recap {{ padding: 24px 26px; border-radius: 18px; background: {T['tint']};
                border: 1px solid {T['tint_border']}; }}
    .kk-recap-head {{ display: flex; align-items: baseline; justify-content: space-between;
                      gap: 16px; flex-wrap: wrap; margin-bottom: 18px; }}
    .kk-recap-head b {{ font-size: 22px; font-weight: 700; color: {T['text']}; }}
    .kk-recap-head span {{ font-size: 13px; color: {T['muted']}; }}
    .kk-recap-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
    .kk-recap-metric {{ min-height: 80px; padding: 14px 16px; border-radius: 13px;
                        background: {T['surface']}; border: 1px solid {T['tint_border']};
                        display: flex; flex-direction: column; justify-content: space-between; gap: 8px; }}
    .kk-recap-metric span {{ font-size: 12px; color: {T['subtle']}; }}
    .kk-recap-metric strong {{ font-family: Rubik, 'IBM Plex Sans KR', sans-serif;
                               font-size: 21px; color: {T['accent']}; }}
    .kk .kk-guide {{ margin: 10px 2px 0 !important; font-size: 13px; line-height: 1.5; color: {T['subtle']}; }}

    div[class*="st-key-kk-drag-area"] {{ margin: 0 64px 18px !important; }}
    div[class*="st-key-kk-drag-area"] iframe {{ border-radius: 18px !important; }}

    .kk-selected-detail {{ margin: 0 64px 20px; padding: 26px 28px; border-radius: 20px;
                          background: {T['surface']}; border: 1px solid {T['accent']}; }}
    .kk-detail-badges {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }}
    .kk-detail-badge {{ padding: 5px 12px; border-radius: 10px; background: {T['accent_soft']};
                       color: {T['accent']}; font-size: 13px; font-weight: 700; }}
    .kk-detail-badge.neutral {{ background: transparent; border: 1px solid {T['chip_border']};
                               color: {T['badge_text']}; }}
    .kk .kk-detail-title {{ font-size: 22px; font-weight: 700; line-height: 1.35;
                           color: {T['text']}; margin: 0 0 9px !important; }}
    .kk .kk-detail-description {{ font-size: 15px; line-height: 1.55; color: {T['muted']};
                                 margin: 0 0 16px !important; }}
    .kk-risk-label {{ display: flex; justify-content: space-between; gap: 12px; margin-bottom: 7px;
                     font-size: 12px; color: {T['subtle']}; }}
    .kk-risk-label b {{ color: {T['accent']}; font-size: 13px; }}
    .kk-risk-bar {{ height: 7px; border-radius: 999px; background: {T['tint_border']};
                    overflow: hidden; margin-bottom: 20px; }}
    .kk-risk-bar span {{ display: block; height: 100%; border-radius: 999px; background: {T['accent']}; }}
    .kk-detail-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
    .kk-detail-metric {{ min-height: 78px; padding: 13px 15px; border-radius: 13px;
                         background: {T['tint']}; border: 1px solid {T['tint_border']};
                         display: flex; flex-direction: column; justify-content: space-between; gap: 8px; }}
    .kk-detail-metric span {{ font-size: 12px; color: {T['subtle']}; }}
    .kk-detail-metric b {{ font-family: Rubik, 'IBM Plex Sans KR', sans-serif; font-size: 17px;
                          font-weight: 700; color: {T['text']}; }}
    .kk-reason {{ margin-top: 14px; padding: 13px 15px; border-radius: 12px;
                  background: {T['accent_soft']}; color: {T['tip_text']}; font-size: 13px; line-height: 1.55; }}
    .kk-empty-selection {{ margin: 0 64px 20px; min-height: 132px; padding: 28px 24px;
                           border-radius: 20px; border: 1px dashed {T['tint_border']};
                           background: {T['tint']}; display: flex; flex-direction: column;
                           align-items: center; justify-content: center; text-align: center; gap: 8px; }}
    .kk-empty-selection b {{ font-size: 17px; color: {T['text']}; }}
    .kk-empty-selection span {{ font-size: 14px; line-height: 1.5; color: {T['muted']}; }}

    div[class*="st-key-kk-customer-table"] {{ width: calc(100% - 128px) !important;
                                               margin: 0 64px 18px !important; }}
    div[class*="st-key-kk-customer-table"] details {{ border: 1px solid {T['border']};
                                                       border-radius: 14px; background: {T['surface']}; }}
    div[class*="st-key-kk-customer-table"] summary {{ color: {T['text']}; font-weight: 600; }}

    div[class*="st-key-kk-actions"] {{ width: calc(100% - 128px) !important;
                                        box-sizing: border-box !important; margin: 8px 64px 0 !important; }}
    .st-key-kk-body [data-testid="stButtonContainer"]:has([data-testid="stBaseButton-primary"]),
    .st-key-kk-body [data-testid="stButtonContainer"]:has([data-testid="stBaseButton-secondary"]) {{ height: 56px !important; }}
    .st-key-kk-body [data-testid="stBaseButton-primary"],
    .st-key-kk-body [data-testid="stBaseButton-secondary"] {{ height: 56px !important; min-height: 56px !important;
        border-radius: 14px !important; font-family: 'IBM Plex Sans KR', sans-serif !important; }}
    .st-key-kk-body [data-testid="stBaseButton-primary"] {{ background: {T['accent']} !important;
        border: none !important; color: {T['accent_text']} !important; }}
    .st-key-kk-body [data-testid="stBaseButton-secondary"] {{ background: transparent !important;
        border: 1px solid {T['secondary_border']} !important; color: {T['text']} !important; }}
    .st-key-kk-body [data-testid="stBaseButton-primary"] p,
    .st-key-kk-body [data-testid="stBaseButton-secondary"] p {{ font-size: 17px !important;
        font-weight: 700 !important; color: inherit !important; }}

    .kk-stepper {{ margin: 0; padding: 0; list-style: none; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }}
    .kk-stepper li.s {{ display: flex; align-items: center; gap: 10px; padding: 8px 16px 8px 8px;
                        border-radius: 999px; border: 1px solid {T['tint_border']};
                        font-size: 14px; color: {T['subtle']}; }}
    .kk-stepper li.s.on {{ border-color: transparent; background: {T['accent_soft']};
                           color: {T['accent']}; font-weight: 700; }}
    .kk-stepper li.s i {{ font-style: normal; width: 26px; height: 26px; border-radius: 999px;
                         background: {T['surface']}; font-family: Rubik, sans-serif; font-size: 12px;
                         display: flex; align-items: center; justify-content: center; }}
    .kk-stepper li.s.on i {{ background: {T['accent']}; color: {T['accent_text']}; }}
    .kk-stepper li.l {{ width: 12px; height: 1px; background: {T['chip_border']}; }}

    @media (max-width: 900px) {{
        .kk-recap-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        .kk-detail-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 1100px) {{
        div[class*="st-key-kk-body"] {{ padding: 24px 0 48px !important; }}
        .kk-context, .kk-selected-detail, .kk-empty-selection {{ margin-left: 16px; margin-right: 16px; }}
        div[class*="st-key-kk-drag-area"] {{ margin-left: 16px !important; margin-right: 16px !important; }}
        div[class*="st-key-kk-customer-table"], div[class*="st-key-kk-actions"] {{
            width: calc(100% - 32px) !important; margin-left: 16px !important; margin-right: 16px !important; }}
    }}
    @media (max-width: 580px) {{
        .kk-recap-grid {{ grid-template-columns: 1fr; }}
        .kk-detail-grid {{ grid-template-columns: 1fr; }}
    }}
</style>"""


def sortable_css() -> str:
    """streamlit-sortables iframe 내부에 적용되는 현재 테마용 스타일입니다."""
    return f"""
    .sortable-component {{
        display: flex;
        flex-direction: column;
        align-items: stretch;
        gap: 16px;
        padding: 0;
        background: transparent;
        color: {T['text']};
        font-family: 'IBM Plex Sans KR', sans-serif;
    }}
    .sortable-container {{
        width: 100%;
        min-width: 0;
        min-height: 0;
        padding: 18px;
        border-radius: 18px;
        border: 1px solid {T['border']};
        background: {T['surface']};
    }}
    .sortable-container-header {{
        margin: 0 0 14px;
        padding: 0 2px 12px;
        border-bottom: 1px solid {T['line']};
        color: {T['text']};
        font-size: 18px;
        font-weight: 700;
    }}
    .sortable-container-body {{
        min-height: 0;
        padding: 2px;
        border-radius: 12px;
        background: transparent;
    }}
    .sortable-container:first-child .sortable-container-body {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
    }}
    .sortable-container:last-child {{
        min-height: 142px;
        border-style: dashed;
        border-color: {T['accent']};
        background: {T['accent_soft']};
    }}
    .sortable-container:last-child .sortable-container-body {{
        min-height: 78px;
    }}
    .sortable-container:last-child .sortable-container-body:not(:has(.sortable-item))::before {{
        content: "위 고객 카드 중 하나를 이곳으로 드래그하세요";
        min-height: 76px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0 18px;
        color: {T['muted']};
        font-size: 14px;
        font-weight: 500;
        text-align: center;
        pointer-events: none;
    }}
    .sortable-item, .sortable-item:hover {{
        width: 100%;
        min-height: 132px;
        margin: 0;
        padding: 17px 18px;
        border-radius: 14px;
        border: 1px solid {T['tint_border']};
        background: {T['tint']};
        color: {T['text']};
        font-size: 13px;
        font-weight: 600;
        line-height: 1.58;
        white-space: pre-line;
        box-shadow: none;
        cursor: grab;
    }}
    .sortable-container:last-child .sortable-item {{ min-height: 104px; }}
    .sortable-item:hover {{ border-color: {T['accent']}; }}
    @media (max-width: 720px) {{
        .sortable-container:first-child .sortable-container-body {{ grid-template-columns: 1fr; }}
        .sortable-item {{ min-height: 116px; }}
    }}
    """


def head_html() -> str:
    steps = []
    for i, name in enumerate(STEP_NAMES):
        if i:
            steps.append('<li class="l" aria-hidden="true"></li>')
        on = " on" if i == 1 else ""
        steps.append(f'<li class="s{on}"><i>{i + 1:02d}</i>{name}</li>')
    return f"""
<section class="kk-page" style="padding-bottom:0; flex-direction:row; align-items:flex-end; justify-content:space-between; flex-wrap:wrap; gap:24px">
    <div style="display:flex; flex-direction:column; gap:12px">
        <h1 class="kk-h2 kk-title" style="font-size:40px">위험 고객 선택</h1>
        <p class="kk-desc" style="font-size:17px">고객 집단을 선택 영역으로 옮기면 실제 분석 결과를 확인할 수 있어요.</p>
    </div>
    <ol class="kk-stepper" aria-label="진행 단계">{''.join(steps)}</ol>
</section>"""


def recap_html(summary: pd.DataFrame, customers: pd.DataFrame) -> str:
    risky = len(customers)
    classified = int(customers["segment"].isin(SEGMENT_UI).sum())
    threshold = 28.24
    return f"""
<div class="kk kk-recap">
    <div class="kk-recap-head">
        <b>위험 고객 분류 결과</b>
        <span>이탈 위험 고객을 거래·결제·이용 행동 기준으로 군집화(K-Means)했습니다.</span>
    </div>
    <div class="kk-recap-grid">
        <div class="kk-recap-metric"><span>전체 위험 고객</span><strong>{risky:,}명</strong></div>
        <div class="kk-recap-metric"><span>{len(summary)}개 군집 분류 완료</span><strong>{classified:,}명</strong></div>
        <div class="kk-recap-metric"><span>위험 판단 기준</span><strong>{threshold:.2f}% 이상</strong></div>
        <div class="kk-recap-metric"><span>위험 고객 군집</span><strong>{len(summary)}개</strong></div>
    </div>
</div>
<p class="kk kk-guide">아래 고객 카드 중 한 개를 실험 대상 영역으로 드래그하세요. 선택하면 그 아래에 집단 상세정보가 표시됩니다.</p>"""


def drag_label(row: pd.Series) -> str:
    return (
        f"{row['display_name']}\n"
        f"{row['description']}\n"
        f"고객 {int(row['인원']):,}명 · 평균 이탈확률 {float(row['평균_이탈확률']) * 100:.1f}%\n"
        f"평균 활동일 {float(row['평균_활동일']):.1f}일 · 마지막 접속 {float(row['마지막접속후_평균일수']):.1f}일 전"
    )


def selection_detail_html(row: pd.Series) -> str:
    probability = float(row["평균_이탈확률"])
    metrics = [
        ("고객 수", f"{int(row['인원']):,}명"),
        ("현재 예상 이탈자", f"약 {round(float(row['예상_이탈자'])):,}명"),
        ("평균 활동일", f"{float(row['평균_활동일']):.1f}일"),
        ("마지막 접속", f"{float(row['마지막접속후_평균일수']):.1f}일 전"),
        ("평균 해지 횟수", f"{float(row['평균_해지횟수']):.2f}회"),
        ("평균 결제금액", f"{float(row['평균_결제금액']):,.1f}"),
    ]
    metric_html = "".join(
        f'<div class="kk-detail-metric"><span>{escape(label)}</span><b>{escape(value)}</b></div>'
        for label, value in metrics
    )
    return f"""
<section class="kk kk-selected-detail">
    <div class="kk-detail-badges">
        <span class="kk-detail-badge">평균 이탈확률 {probability * 100:.1f}%</span>
        <span class="kk-detail-badge neutral">행동 특성 군집 (K-Means)</span>
    </div>
    <h2 class="kk-detail-title">{escape(str(row['display_name']))}</h2>
    <p class="kk-detail-description">{escape(str(row['description']))}</p>
    <div class="kk-risk-label"><span>집단 평균 이탈확률</span><b>{probability * 100:.1f}%</b></div>
    <div class="kk-risk-bar" role="progressbar" aria-label="평균 이탈확률"
         aria-valuenow="{probability * 100:.1f}" aria-valuemin="0" aria-valuemax="100">
        <span style="width:{min(max(probability * 100, 0), 100):.1f}%"></span>
    </div>
    <div class="kk-detail-grid">{metric_html}</div>
    <div class="kk-reason"><b>분류 기준</b> · 이탈 위험 고객의 거래·구독, 결제, 서비스 이용 행동 17개 지표를 표준화한 뒤 K-Means로 4개 군집으로 나눴습니다.</div>
</section>"""


def empty_selection_html() -> str:
    return """
<div class="kk kk-empty-selection">
    <b>아직 선택한 고객 집단이 없어요.</b>
    <span>위험 고객 집단에서 카드 하나를 끌어 이곳으로 옮기면<br>고객 수, 이탈확률, 활동과 해지 특성이 표시됩니다.</span>
</div>"""


def selected_record(row: pd.Series) -> dict:
    """다음 페이지와 기존 실험 페이지에서 함께 사용할 세션 저장 형식입니다."""
    return {
        "id": str(row["segment_id"]),
        "segment": str(row["segment"]),
        "name": str(row["display_name"]),
        "trait": str(row["description"]),
        "size": int(row["인원"]),
        "score": round(float(row["평균_이탈확률"]) * 100),
        "churn_prob": float(row["평균_이탈확률"]),
        "expected_churn": float(row["예상_이탈자"]),
        "activity_days": float(row["평균_활동일"]),
        "days_since_last_log": float(row["마지막접속후_평균일수"]),
        "cancel_count": float(row["평균_해지횟수"]),
        "avg_payment": float(row["평균_결제금액"]),
        # 기존 실험 화면에서 참조할 수 있는 호환용 필드
        "risk": f"{float(row['평균_이탈확률']) * 100:.1f}%",
        "last": f"{float(row['마지막접속후_평균일수']):.1f}일 전",
        "tenure": "집단 상세 참조",
    }


def matching_page() -> None:
    ss = st.session_state
    st.markdown(compact(match_css()), unsafe_allow_html=True)
    st.markdown(compact(f'<div class="kk">{head_html()}</div>'), unsafe_allow_html=True)

    with st.container(key="kk-body"):
        try:
            summary, customers = load_segment_data(str(SUMMARY_PATH), str(SEGMENTS_PATH))
        except FileNotFoundError:
            st.error(
                "위험 고객 분류 파일을 찾지 못했습니다. 먼저 실험 노트북을 실행해 "
                "data/processed/risk_segments.csv와 risk_segment_summary.csv를 생성해 주세요."
            )
            st.stop()
        except ValueError as error:
            st.error(str(error))
            st.stop()

        st.markdown(
            compact(f'<div class="kk kk-context">{recap_html(summary, customers)}</div>'),
            unsafe_allow_html=True,
        )

        label_to_segment = {drag_label(row): row["segment"] for _, row in summary.iterrows()}
        labels = list(label_to_segment)

        if sort_items is None:
            st.warning("드래그 기능을 사용하려면 프로젝트 환경에 streamlit-sortables를 설치해 주세요.")
            selected_label = st.selectbox(
                "위험 고객 집단",
                options=[""] + labels,
                format_func=lambda value: value.splitlines()[0] if value else "고객 집단을 선택하세요",
            )
            selected_labels = [selected_label] if selected_label else []
        else:
            with st.container(key="kk-drag-area"):
                result = sort_items(
                    [
                        {"header": "위험 고객 집단 · 카드를 선택해 드래그하세요", "items": labels},
                        {"header": "실험 대상 고객 집단", "items": []},
                    ],
                    multi_containers=True,
                    direction="vertical",
                    custom_style=sortable_css(),
                )
            selected_labels = result[1]["items"] if result and len(result) > 1 else []

        valid_selection = len(selected_labels) == 1
        selected_row = None
        if len(selected_labels) > 1:
            st.error("고객 집단은 한 번에 하나만 선택할 수 있어요. 선택 영역에 한 집단만 남겨 주세요.")
        elif valid_selection:
            selected_segment = label_to_segment.get(selected_labels[0])
            matched = summary.loc[summary["segment"] == selected_segment]
            if not matched.empty:
                selected_row = matched.iloc[0]
                st.markdown(compact(selection_detail_html(selected_row)), unsafe_allow_html=True)

                segment_customers = (
                    customers.loc[customers["segment"] == selected_segment, ["msno", "churn_prob"]]
                    .sort_values("churn_prob", ascending=False)
                    .head(5)
                    .copy()
                )
                segment_customers["고객 ID"] = segment_customers["msno"].map(
                    lambda value: f"{str(value)[:7]}…{str(value)[-4:]}"
                )
                segment_customers["이탈확률"] = segment_customers["churn_prob"].map(
                    lambda value: f"{float(value) * 100:.1f}%"
                )
                with st.container(key="kk-customer-table"):
                    with st.expander("이탈확률이 높은 고객 5명 보기"):
                        st.dataframe(
                            segment_customers[["고객 ID", "이탈확률"]],
                            use_container_width=True,
                            hide_index=True,
                        )
        with st.container(key="kk-actions"):
            _, back_col, next_col = st.columns([4.3, 0.8, 1.5], gap="small")
            back = back_col.button("이전 단계로", key="m_back", use_container_width=True)
            go = next_col.button(
                "선택한 집단으로 실험 만들기 →",
                key="m_go",
                type="primary",
                use_container_width=True,
                disabled=not (valid_selection and selected_row is not None),
            )

    if back:
        st.switch_page("pages/1_marketing.py")
    if go and selected_row is not None:
        record = selected_record(selected_row)
        ss["matched_segment"] = record
        ss["matched_segments"] = [record]
        st.switch_page("pages/3_experiments.py")


ui.render_header()
matching_page()
