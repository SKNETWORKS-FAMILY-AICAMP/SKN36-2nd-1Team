"""KKeeper 홈 — 전체 회원 이탈 현황 대시보드.

배치 위치
---------
프로젝트/app/pages/1_marketing.py

상위 ``app`` 폴더의 ``ui.py``를 사용하고, 노트북에서 생성한 CSV는
프로젝트/data/processed 아래에서 읽습니다.
"""

from __future__ import annotations

from pathlib import Path
import sys

import altair as alt
import pandas as pd
import streamlit as st


# 프로젝트/app/pages/1_marketing.py 기준 경로
APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = APP_DIR.parent
DATA_DIR = PROJECT_ROOT / "data" / "processed"
sys.path.insert(0, str(APP_DIR))

import ui  # noqa: E402
from ui import compact  # noqa: E402


st.set_page_config(
    page_title="전체 회원 현황 · KKeeper",
    layout="wide",
    initial_sidebar_state="collapsed",
)
T = ui.init("input")

# 최종 LightGBM에서 확정한 위험 고객 판정 기준선
THRESHOLD = 0.2824

CUSTOMER_PATHS = [
    DATA_DIR / "kkbox_dashboard_customers.csv",
    DATA_DIR / "kkbox_scored.csv",
]
SEGMENT_SUMMARY_PATHS = [
    DATA_DIR / "dashboard_segment_summary.csv",
    DATA_DIR / "risk_segment_summary.csv",
]
RISK_SEGMENTS_PATH = DATA_DIR / "risk_segments.csv"

SEGMENT_ORDER = [
    "자동갱신 끔 · 활동량 저하형",
    "자동갱신 끔 · 결제·해지형",
    "자동갱신 끔 · 휴면형",
    "자동갱신 켬 · 결제·해지형",
    "자동갱신 켬 · 휴면형",
]

SEGMENT_DISPLAY = {
    "자동갱신 끔 · 활동량 저하형": "자동갱신 OFF · 저활동",
    "자동갱신 끔 · 결제·해지형": "자동갱신 OFF · 결제·해지",
    "자동갱신 끔 · 휴면형": "자동갱신 OFF · 휴면",
    "자동갱신 켬 · 결제·해지형": "자동갱신 ON · 해지 이력",
    "자동갱신 켬 · 휴면형": "자동갱신 ON · 장기 휴면",
}


def dashboard_css() -> str:
    """공통 UI의 색상 토큰을 그대로 사용하는 대시보드 전용 스타일."""
    return f"""
<style>
  .st-key-kk-dashboard {{ width:100%; max-width:1440px; margin:0 auto;
      padding:30px 48px 72px; box-sizing:border-box; }}
  .st-key-kk-dashboard > div[data-testid="stVerticalBlock"] {{ gap:14px !important; }}
  .st-key-kk-dashboard [data-testid="stHorizontalBlock"] {{ gap:16px !important;
      align-items:stretch !important; flex-wrap:wrap !important; }}
  .st-key-kk-dashboard [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{
      min-width:260px !important; }}

  .kk-dashboard-meta {{ display:flex; justify-content:flex-end; align-items:center; gap:8px;
      color:{T['muted']}; font-size:12px; flex-wrap:wrap; }}
  .kk-dashboard-meta span {{ padding:6px 10px; border:1px solid {T['border']};
      border-radius:999px; background:{T['surface']}; }}
  .kk-dashboard-intro {{ padding:10px 2px 12px; }}
  .kk-dashboard-intro h1 {{ margin:0; color:{T['text']}; font-size:27px;
      line-height:1.35; letter-spacing:-.025em; }}
  .kk-dashboard-intro p {{ margin:7px 0 0; color:{T['muted']}; font-size:14px; line-height:1.55; }}

  div[class*="st-key-kpi-"] {{ min-height:140px; padding:20px 22px !important;
      border:1px solid {T['border']} !important; border-radius:18px !important;
      background:{T['surface']} !important; box-shadow:none !important; box-sizing:border-box; }}
  .kk-kpi-label {{ color:{T['muted']}; font-size:13px; font-weight:600; line-height:1.45; }}
  .kk-kpi-value {{ margin-top:12px; color:{T['text']}; font-family:Rubik, sans-serif !important;
      font-size:30px; line-height:1.2; font-weight:700; letter-spacing:-.02em; overflow-wrap:anywhere; }}
  .kk-kpi-help {{ margin-top:8px; color:{T['subtle']}; font-size:12px; line-height:1.5; }}
  .kk-kpi-accent {{ color:{T['accent']}; }}

  .kk-section-title {{ min-height:77px; box-sizing:border-box; padding:28px 2px 14px;
      display:flex; justify-content:space-between; align-items:flex-end;
      gap:8px 18px; flex-wrap:wrap; }}
  .kk-section-title strong {{ color:{T['text']}; font-size:20px; line-height:1.35; font-weight:700; }}
  .kk-section-title span {{ color:{T['subtle']}; font-size:12px; line-height:1.5;
      text-align:right; max-width:55%; }}

  div[class*="st-key-chart-"] {{ padding:22px 24px 18px !important;
      border:1px solid {T['border']} !important; border-radius:18px !important;
      background:{T['surface']} !important; box-shadow:none !important;
      box-sizing:border-box; min-height:390px; }}
  div[class*="st-key-chart-"] > div[data-testid="stVerticalBlock"] {{ gap:8px !important; }}
  div[class*="st-key-chart-"] [data-testid="stVegaLiteChart"],
  div[class*="st-key-chart-"] .vega-embed,
  div[class*="st-key-chart-"] .vega-embed > div {{
      background:{T['surface']} !important; border-radius:12px !important; max-width:100%; }}
  div[class*="st-key-chart-"] [data-testid="stVegaLiteChart"] svg,
  div[class*="st-key-chart-"] [data-testid="stVegaLiteChart"] canvas {{
      background:transparent !important; }}
  .kk-chart-head {{ display:flex; justify-content:space-between; align-items:flex-start;
      gap:8px 16px; min-height:58px; padding-bottom:8px; box-sizing:border-box;
      flex-wrap:wrap; }}
  .kk-chart-title {{ color:{T['text']}; font-size:16px; line-height:1.4; font-weight:700; }}
  .kk-chart-note {{ margin-top:4px; color:{T['muted']}; font-size:12px; line-height:1.5; }}
  .kk-threshold {{ flex:0 0 auto; padding:5px 9px; border-radius:999px;
      background:{T['accent_soft']}; color:{T['accent']}; font-size:11px; font-weight:700; }}
  .kk-caption {{ color:{T['subtle']}; font-size:12px; line-height:1.55; padding-top:4px; }}
  .kk-legend {{ display:flex; justify-content:center; flex-wrap:wrap; gap:10px 18px;
      color:{T['muted']}; font-size:12px; line-height:1.5; padding:2px 0 8px; }}
  .kk-legend span {{ display:inline-flex; align-items:center; gap:7px; white-space:nowrap; }}
  .kk-legend i {{ display:inline-block; width:9px; height:9px; border-radius:50%; }}

  @media (max-width: 900px) {{
    .st-key-kk-dashboard {{ padding:24px 28px 56px; }}
    .kk-section-title {{ align-items:flex-start; }}
    .kk-section-title span {{ max-width:100%; text-align:left; }}
  }}
  @media (max-width: 640px) {{
    .st-key-kk-dashboard {{ padding:20px 16px 44px; }}
    .kk-dashboard-meta {{ justify-content:flex-start; }}
    .kk-section-title {{ min-height:0; padding-top:25px; }}
    div[class*="st-key-chart-"] {{ padding:20px 16px 16px !important; }}
  }}
</style>
"""


def _first_existing(paths: list[Path]) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def _as_binary(series: pd.Series) -> pd.Series:
    """CSV에서 bool·문자·정수로 섞일 수 있는 값을 0/1로 통일합니다."""
    if pd.api.types.is_bool_dtype(series):
        return series.astype(int)
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0).astype(int)
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.map(
        {
            "true": 1, "false": 0, "1": 1, "0": 0,
            "yes": 1, "no": 0, "위험": 1, "일반": 0,
        }
    ).fillna(0).astype(int)


@st.cache_data(show_spinner=False)
def load_dashboard_data() -> tuple[pd.DataFrame, pd.DataFrame, Path]:
    """전체 고객 데이터와 5개 위험 고객 유형 요약을 읽습니다."""
    customer_path = _first_existing(CUSTOMER_PATHS)
    if customer_path is None:
        expected = " 또는 ".join(path.name for path in CUSTOMER_PATHS)
        raise FileNotFoundError(f"data/processed에 {expected} 파일이 필요합니다.")

    customers = pd.read_csv(customer_path, encoding="utf-8-sig", low_memory=False)
    required = {"msno", "churn_prob", "is_churn"}
    missing = required.difference(customers.columns)
    if missing:
        raise ValueError("전체 회원 CSV에 필요한 컬럼이 없습니다: " + ", ".join(sorted(missing)))

    customers["churn_prob"] = pd.to_numeric(customers["churn_prob"], errors="coerce").clip(0, 1)
    customers["is_churn"] = _as_binary(customers["is_churn"])
    if "risk" in customers.columns:
        customers["risk"] = _as_binary(customers["risk"])
    else:
        customers["risk"] = customers["churn_prob"].ge(THRESHOLD).astype(int)

    # 대시보드 고객 파일에 segment가 없다면 고객별 분류 CSV를 연결합니다.
    if "segment" not in customers.columns and RISK_SEGMENTS_PATH.exists():
        segment_users = pd.read_csv(
            RISK_SEGMENTS_PATH,
            encoding="utf-8-sig",
            usecols=lambda col: col in {"msno", "segment"},
        ).drop_duplicates("msno")
        customers = customers.merge(segment_users, on="msno", how="left")

    summary_path = _first_existing(SEGMENT_SUMMARY_PATHS)
    if summary_path is not None:
        segment_summary = pd.read_csv(summary_path, encoding="utf-8-sig")
    elif "segment" in customers.columns:
        valid = customers[customers["segment"].isin(SEGMENT_ORDER)]
        segment_summary = (
            valid.groupby("segment", as_index=False)
            .agg(인원=("msno", "size"), 평균_이탈확률=("churn_prob", "mean"))
        )
    else:
        segment_summary = pd.DataFrame()

    return customers, segment_summary, customer_path


def prepare_segment_summary(summary: pd.DataFrame) -> pd.DataFrame:
    """노트북별로 조금씩 다른 요약 컬럼명을 화면용으로 통일합니다."""
    if summary.empty or "segment" not in summary.columns:
        return pd.DataFrame()

    count_col = next(
        (col for col in ["인원", "고객수", "customer_count"] if col in summary.columns),
        None,
    )
    prob_col = next(
        (col for col in ["평균_이탈확률", "avg_churn_prob", "churn_prob"] if col in summary.columns),
        None,
    )
    if count_col is None or prob_col is None:
        return pd.DataFrame()

    result = summary[["segment", count_col, prob_col]].copy()
    result.columns = ["segment", "customer_count", "avg_churn_prob"]
    result = result[result["segment"].isin(SEGMENT_ORDER)]
    result["segment_name"] = result["segment"].map(SEGMENT_DISPLAY).fillna(result["segment"])
    result["customer_count"] = pd.to_numeric(result["customer_count"], errors="coerce").fillna(0)
    result["avg_churn_prob"] = pd.to_numeric(result["avg_churn_prob"], errors="coerce")
    result["count_label"] = result["customer_count"].map(lambda value: f"{int(value):,}명")
    result["prob_label"] = result["avg_churn_prob"].map(lambda value: f"{value:.1%}")
    result["sort"] = result["segment"].map({name: index for index, name in enumerate(SEGMENT_ORDER)})
    return result.sort_values("sort")


def probability_bins(customers: pd.DataFrame) -> pd.DataFrame:
    """실제 모델 임계값을 구간 경계에 넣어 회원 분포를 집계합니다."""
    edges = [0, .10, THRESHOLD, .50, .75, 1.0]
    names = ["0–10%", "10–28.24%", "28.24–50%", "50–75%", "75–100%"]
    work = customers[["churn_prob", "is_churn"]].dropna().copy()
    work["bin"] = pd.cut(work["churn_prob"], bins=edges, include_lowest=True,
                         right=False, labels=names)
    work.loc[work["churn_prob"].eq(1), "bin"] = names[-1]
    grouped = (
        work.groupby("bin", observed=False)
        .agg(customer_count=("churn_prob", "size"), actual_churn_rate=("is_churn", "mean"))
        .reset_index()
    )
    grouped["probability_range"] = grouped["bin"].astype(str)
    grouped["member_share"] = grouped["customer_count"] / max(len(work), 1)
    grouped["count_label"] = grouped["customer_count"].map(lambda value: f"{int(value):,}명")
    grouped["rate_label"] = grouped["actual_churn_rate"].map(lambda value: f"{value:.1%}")
    return grouped


def activity_summary(customers: pd.DataFrame) -> pd.DataFrame:
    """유지/이탈 회원의 이용 행동을 같은 단위(일) 지표로 비교합니다."""
    metrics = {
        "activity_days": "활동일",
        "days_since_last_log": "마지막 접속 후",
    }
    available = [column for column in metrics if column in customers.columns]
    if not available:
        return pd.DataFrame()

    work = customers[["is_churn", *available]].copy()
    for column in available:
        work[column] = pd.to_numeric(work[column], errors="coerce")

    grouped = work.groupby("is_churn")[available].mean().reset_index()
    grouped["status"] = grouped["is_churn"].map({0: "유지 회원", 1: "이탈 회원"})
    result = grouped.melt(
        id_vars=["is_churn", "status"],
        value_vars=available,
        var_name="metric",
        value_name="days",
    )
    result["metric_name"] = result["metric"].map(metrics)
    result["value_label"] = result["days"].map(lambda value: f"{value:,.1f}일")
    return result


def renewal_summary(customers: pd.DataFrame) -> pd.DataFrame:
    if "last_auto_renew" not in customers.columns:
        return pd.DataFrame()
    work = customers[["last_auto_renew", "is_churn"]].copy()
    work["last_auto_renew"] = pd.to_numeric(work["last_auto_renew"], errors="coerce")
    work = work[work["last_auto_renew"].isin([0, 1])]
    result = (
        work.groupby("last_auto_renew", as_index=False)
        .agg(customer_count=("is_churn", "size"), churn_rate=("is_churn", "mean"))
    )
    result["renewal"] = result["last_auto_renew"].map({0: "자동갱신 OFF", 1: "자동갱신 ON"})
    result["rate_label"] = result["churn_rate"].map(lambda value: f"{value:.1%}")
    result["count_label"] = result["customer_count"].map(lambda value: f"{int(value):,}명")
    return result


def style_chart(chart: alt.Chart) -> alt.Chart:
    return (
        chart.properties(background=T["surface"])
        .configure_view(
            fill=T["surface"],
            strokeOpacity=0,
        )
        .configure_axis(
            domainColor=T["border"],
            domainOpacity=0.8,
            gridColor=T["line"],
            gridOpacity=0.55,
            gridDash=[3, 4],
            labelColor=T["muted"],
            labelFont="IBM Plex Sans KR",
            labelFontSize=11,
            labelPadding=8,
            tickColor=T["border"],
            tickSize=4,
            titleColor=T["muted"],
            titleFont="IBM Plex Sans KR",
            titleFontSize=12,
            titleFontWeight=500,
            titlePadding=14,
        )
        .configure_legend(
            labelColor=T["muted"],
            labelFont="IBM Plex Sans KR",
            labelFontSize=11,
            labelLimit=150,
            symbolSize=110,
            title=None,
            orient="bottom",
            padding=8,
        )
        .configure_text(font="IBM Plex Sans KR", color=T["text"])
    )


def chart_header(title: str, note: str, badge: str | None = None) -> None:
    badge_html = f'<span class="kk-threshold">{badge}</span>' if badge else ""
    st.markdown(
        compact(
            f"""
            <div class="kk-chart-head">
              <div>
                <div class="kk-chart-title">{title}</div>
                <div class="kk-chart-note">{note}</div>
              </div>
              {badge_html}
            </div>
            """
        ),
        unsafe_allow_html=True,
    )


def section_title(title: str, note: str) -> None:
    st.markdown(
        compact(
            f'<div class="kk-section-title"><strong>{title}</strong><span>{note}</span></div>'
        ),
        unsafe_allow_html=True,
    )


def render_kpi(key: str, label: str, value: str, help_text: str, accent: bool = False) -> None:
    value_class = "kk-kpi-value kk-kpi-accent" if accent else "kk-kpi-value"
    with st.container(key=f"kpi-{key}"):
        st.markdown(
            compact(
                f"""
                <div class="kk-kpi-label">{label}</div>
                <div class="{value_class}">{value}</div>
                <div class="kk-kpi-help">{help_text}</div>
                """
            ),
            unsafe_allow_html=True,
        )


ui.render_header()
st.markdown(compact(dashboard_css()), unsafe_allow_html=True)

try:
    customers, raw_segment_summary, loaded_path = load_dashboard_data()
except (FileNotFoundError, ValueError, pd.errors.ParserError) as error:
    with st.container(key="kk-dashboard"):
        st.error(str(error))
        st.code(
            "프로젝트/\n"
            "├─ app/\n"
            "│  ├─ app.py\n"
            "│  └─ ui.py\n"
            "└─ data/processed/\n"
            "   ├─ kkbox_dashboard_customers.csv  # 또는 kkbox_scored.csv\n"
            "   ├─ risk_segments.csv\n"
            "   └─ risk_segment_summary.csv"
        )
    st.stop()

segment_summary = prepare_segment_summary(raw_segment_summary)
prob_bins = probability_bins(customers)
activity = activity_summary(customers)
renewal = renewal_summary(customers)

total_count = len(customers)
churn_count = int(customers["is_churn"].sum())
churn_rate = churn_count / total_count if total_count else 0.0
risk_count = int(customers["risk"].sum())
risk_rate = risk_count / total_count if total_count else 0.0
risk_avg_prob = customers.loc[customers["risk"].eq(1), "churn_prob"].mean() if risk_count else 0.0
if total_count == 0:
    st.warning("분석할 회원이 없습니다.")
    st.stop()
classified_count = int(segment_summary["customer_count"].sum()) if not segment_summary.empty else 0
excluded_count = max(risk_count - classified_count, 0)

with st.container(key="kk-dashboard"):
    st.markdown(
        compact(
            f"""
            <div class="kk-dashboard-meta">
            
              
            </div>
            <div class="kk-dashboard-intro">
              <h1>전체 회원 대시보드</h1>
              
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    kpi_columns = st.columns(4)
    with kpi_columns[0]:
        render_kpi("members", "전체 회원", f"{total_count:,}명", "이탈 예측에 사용한 분석 표본")
    with kpi_columns[1]:
        render_kpi("churn", "실제 이탈률", f"{churn_rate:.2%}", f"이탈 회원 {churn_count:,}명")
    with kpi_columns[2]:
        render_kpi("retained", "유지 회원", f"{total_count - churn_count:,}명", "실제 이탈하지 않은 회원")
    with kpi_columns[3]:
        render_kpi("risk", "예측 위험 회원", f"{risk_count:,}명",
                   f"전체의 {risk_rate:.2%} · 기준 {THRESHOLD:.2%}", accent=True)

    section_title("전체 회원 이탈 현황", "전체 표본의 예측확률과 실제 이탈 결과")
    first_left, first_right = st.columns([1.65, 1])
    with first_left:
        with st.container(key="chart-probability"):
            chart_header(
                "예측 이탈확률 분포",
                "각 확률 구간에 속한 회원의 비율입니다. 세로축은 큰 쏠림을 읽기 쉽게 제곱근 눈금으로 표시합니다.",
                f"위험 기준 {THRESHOLD:.2%}",
            )
            range_order = prob_bins["probability_range"].tolist()
            base = alt.Chart(prob_bins).encode(
                x=alt.X(
                    "probability_range:N", sort=range_order, title=None,
                    axis=alt.Axis(labelAngle=0, labelLimit=80, labelOverlap=False),
                ),
                y=alt.Y(
                    "member_share:Q", title=None,
                    scale=alt.Scale(type="sqrt", domain=[0, 1]),
                    axis=alt.Axis(format=".0%", tickCount=4),
                ),
                tooltip=[
                    alt.Tooltip("probability_range:N", title="예측확률"),
                    alt.Tooltip("customer_count:Q", title="회원 수", format=","),
                    alt.Tooltip("member_share:Q", title="전체 비중", format=".1%"),
                    alt.Tooltip("actual_churn_rate:Q", title="실제 이탈률", format=".1%"),
                ],
            )
            distribution = (
                base.mark_area(color=T["accent"], opacity=.13, interpolate="monotone")
                + base.mark_line(color=T["accent"], strokeWidth=3, interpolate="monotone")
                + base.mark_circle(color=T["accent"], size=75)
            ).properties(height=238, padding={"left": 4, "right": 12, "top": 12, "bottom": 8})
            st.altair_chart(style_chart(distribution), width="stretch", theme=None)
            st.markdown(
                '<div class="kk-caption">마우스를 올리면 구간별 인원과 실제 이탈률을 볼 수 있습니다.</div>',
                unsafe_allow_html=True,
            )

    with first_right:
        with st.container(key="chart-churn"):
            chart_header("실제 이탈 구성", "분석 표본에서 관측된 유지·이탈 회원의 비중입니다.")
            churn_composition = pd.DataFrame([
                {"status": "유지", "count": total_count - churn_count, "order": 0},
                {"status": "이탈", "count": churn_count, "order": 1},
            ])
            churn_composition["share"] = churn_composition["count"] / total_count
            arcs = alt.Chart(churn_composition).mark_arc(
                innerRadius=67, outerRadius=99, stroke=T["surface"], strokeWidth=4
            ).encode(
                theta=alt.Theta("count:Q", stack=True),
                color=alt.Color(
                    "status:N",
                    scale=alt.Scale(domain=["유지", "이탈"],
                                    range=[T["accent_soft2"], T["accent"]]),
                    legend=None,
                ),
                order=alt.Order("order:Q"),
                tooltip=[
                    alt.Tooltip("status:N", title="상태"),
                    alt.Tooltip("count:Q", title="회원 수", format=","),
                    alt.Tooltip("share:Q", title="비율", format=".2%"),
                ],
            )
            center = alt.Chart(pd.DataFrame([{"rate": f"{churn_rate:.1%}"}])).mark_text(
                font="Rubik", fontSize=25, fontWeight=700, color=T["text"]
            ).encode(text="rate:N")
            st.altair_chart(
                style_chart((arcs + center).properties(height=238)),
                width="stretch", theme=None,
            )
            st.markdown(
                compact(
                    f"""
                    <div class="kk-legend">
                      <span><i style="background:{T['accent_soft2']}"></i>유지 {total_count - churn_count:,}명</span>
                      <span><i style="background:{T['accent']}"></i>이탈 {churn_count:,}명</span>
                    </div>
                    """
                ),
                unsafe_allow_html=True,
            )

    if not segment_summary.empty:
        section_title("위험 회원 유형", "위험 회원의 행동 특징에 따라 분류한 5개 집단")
        with st.container(key="chart-segments"):
            chart_header(
                "집단별 위험 회원 수",
                "집단의 규모를 비교합니다. 마우스를 올리면 평균 예측 이탈확률도 확인할 수 있습니다.",
                f"위험군 평균 {risk_avg_prob:.1%}",
            )
            segment_order = segment_summary["segment_name"].tolist()
            bars = alt.Chart(segment_summary).mark_bar(
                cornerRadiusEnd=6, size=23, color=T["accent"]
            ).encode(
                y=alt.Y(
                    "segment_name:N", sort=segment_order, title=None,
                    axis=alt.Axis(labelLimit=200, labelPadding=12, labelFontSize=11),
                ),
                x=alt.X("customer_count:Q", title=None, axis=None,
                        scale=alt.Scale(domain=[0, max(segment_summary["customer_count"].max() * 1.18, 1)])),
                tooltip=[
                    alt.Tooltip("segment_name:N", title="위험 유형"),
                    alt.Tooltip("customer_count:Q", title="회원 수", format=","),
                    alt.Tooltip("avg_churn_prob:Q", title="평균 이탈확률", format=".1%"),
                ],
            )
            count_labels = bars.mark_text(
                align="left", baseline="middle", dx=8,
                color=T["text"], font="IBM Plex Sans KR", fontSize=11, fontWeight=700,
            ).encode(text="count_label:N")
            st.altair_chart(
                style_chart((bars + count_labels).properties(
                    height=270, padding={"left": 2, "right": 64, "top": 8, "bottom": 8}
                )),
                width="stretch", theme=None,
            )
            caption = f"5개 집단 분류 완료 {classified_count:,}명"
            if excluded_count:
                caption += f" · 분류에서 제외된 위험 회원 {excluded_count:,}명"
            st.markdown(f'<div class="kk-caption">{caption}</div>', unsafe_allow_html=True)

    if not activity.empty or not renewal.empty:
        section_title("이용·결제 행동", "이탈 여부에 따라 행동 지표가 어떻게 다른지 비교합니다")
        behavior_left, behavior_right = st.columns([1.15, 1])
        with behavior_left:
            with st.container(key="chart-activity"):
                chart_header("청취 활동 비교", "유지 회원과 이탈 회원의 지표별 평균 일수입니다.")
                if activity.empty:
                    st.info("activity_days 또는 days_since_last_log 컬럼이 없습니다.")
                else:
                    dots = alt.Chart(activity).mark_circle(size=200, opacity=.95).encode(
                        x=alt.X("days:Q", title="평균 일수",
                                scale=alt.Scale(zero=True),
                                axis=alt.Axis(tickCount=5, format=".0f")),
                        y=alt.Y("metric_name:N", title=None,
                                sort=["활동일", "마지막 접속 후"],
                                axis=alt.Axis(labelLimit=130, labelPadding=10)),
                        yOffset=alt.YOffset("status:N", sort=["유지 회원", "이탈 회원"]),
                        color=alt.Color(
                            "status:N", sort=["유지 회원", "이탈 회원"],
                            scale=alt.Scale(domain=["유지 회원", "이탈 회원"],
                                            range=[T["accent"], "#B982A7" if ui.theme_name == "light" else "#DBA3C4"]),
                            legend=alt.Legend(orient="bottom", direction="horizontal"),
                        ),
                        tooltip=[
                            alt.Tooltip("status:N", title="회원 상태"),
                            alt.Tooltip("metric_name:N", title="지표"),
                            alt.Tooltip("days:Q", title="평균 일수", format=",.1f"),
                        ],
                    ).properties(height=230, padding={"left": 4, "right": 10, "top": 10, "bottom": 8})
                    st.altair_chart(style_chart(dots), width="stretch", theme=None)

        with behavior_right:
            with st.container(key="chart-renewal"):
                chart_header("자동갱신별 실제 이탈률", "마지막 거래의 자동갱신 설정에 따른 관측값입니다.")
                if renewal.empty:
                    st.info("last_auto_renew 컬럼이 없습니다.")
                else:
                    renewal_base = alt.Chart(renewal).encode(
                        x=alt.X("churn_rate:Q", title="실제 이탈률",
                                scale=alt.Scale(domain=[0, min(1, max(.5, renewal["churn_rate"].max() * 1.2))]),
                                axis=alt.Axis(format=".0%", tickCount=5)),
                        y=alt.Y("renewal:N", title=None,
                                sort=["자동갱신 OFF", "자동갱신 ON"],
                                axis=alt.Axis(labelLimit=110, labelPadding=8)),
                        tooltip=[
                            alt.Tooltip("renewal:N", title="자동갱신"),
                            alt.Tooltip("customer_count:Q", title="회원 수", format=","),
                            alt.Tooltip("churn_rate:Q", title="실제 이탈률", format=".2%"),
                        ],
                    )
                    stems = renewal_base.mark_bar(size=3, color=T["tint_border"])
                    points = renewal_base.mark_circle(size=230, color=T["accent"])
                    st.altair_chart(
                        style_chart((stems + points).properties(
                            height=230, padding={"left": 4, "right": 12, "top": 10, "bottom": 8}
                        )),
                        width="stretch", theme=None,
                    )
