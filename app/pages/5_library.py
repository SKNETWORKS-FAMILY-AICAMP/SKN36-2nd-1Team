"""KKeeper ④ 라이브러리 — 실제 결과로 판정한 전략 모음 (주소: /library).

실험 관리에서 '판정 저장'한 실험이 전략 카드로 쌓여요.
판정(효과 있음 · 판단 보류 · 효과 없음)과 진행 중 여부로 걸러 볼 수 있고, PDF 보고서로 내려받을 수 있어요.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ui  # noqa: E402
from common import db  # noqa: E402
from common.constants import VERDICT_KIND, VERDICTS, seg_display  # noqa: E402
from common.experiment import WHATIF_LEVERS  # noqa: E402
from common.report import make_experiment_pdf, pdf_available  # noqa: E402

st.set_page_config(page_title="라이브러리 · KKeeper", layout="wide", initial_sidebar_state="collapsed")
T = ui.init("library")
ss = st.session_state
LEVER_LABELS = {k: v["label"] for k, v in WHATIF_LEVERS.items()}
FILTERS = ["전체", *VERDICTS, "진행 중"]


@st.cache_data(show_spinner=False)
def pdf_bytes(exp_id: int, updated_at: str) -> bytes:
    """실험이 바뀔 때만 PDF를 다시 만들어요 (updated_at이 캐시 기준)."""
    e = db.get_experiment(exp_id)
    return make_experiment_pdf(e, LEVER_LABELS, seg_display(e["segment"]))


def status_of(e: dict) -> str:
    return e["verdict"] if e["status"] == "완료" and e.get("verdict") else "진행 중"


def card_html(e: dict) -> str:
    s = status_of(e)
    if s == "진행 중":
        b = ui.badge("결과 입력 대기", "warn") if db.is_waiting(e) else ui.badge("진행 중", "accent")
    else:
        b = ui.badge(s, VERDICT_KIND[s])
    sim = ui.badge("시뮬레이션", "warn") if e.get("is_simulated") else ""
    head = (f'<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px">'
            f'<span style="font-size:18px; font-weight:700">{ui.esc(e["title"])}</span><span style="display:flex; gap:6px">{sim}{b}</span></div>'
            f'<div class="kk-cap" style="font-size:13px">적용 대상 · {seg_display(e["segment"])} · {ui.esc(e.get("strategy_kind") or "-")} '
            f'· {ui.esc(e.get("channel") or "-")}</div><div style="height:1px; background:{T["line"]}; margin:4px 0"></div>')
    if s == "진행 중":
        n_t, n_c = int(e.get("n_treat") or 0), int(e.get("n_ctrl") or 0)
        period = f'{e.get("start_date") or "-"} ~ {e.get("end_date") or "-"}'
        period_display = (f'<div><div class="kk-kpi-label">기간</div>'
                          f'<div class="kk-num-font" style="font-size:18px; font-weight:700; '
                          f'white-space:nowrap; margin-top:6px">{ui.esc(period)}</div></div>')
        body = (f'<div style="display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px">'
                f'{ui.kpi("실험군 / 대조군", f"{n_t:,} / {n_c:,}명")}{period_display}</div>')
    else:
        p_t = e["obs_x_treat"] / e["obs_n_treat"] if e.get("obs_n_treat") else 0
        p_c = e["obs_x_ctrl"] / e["obs_n_ctrl"] if e.get("obs_n_ctrl") else 0
        diff = p_c - p_t
        color = {"good": T["good_text"], "warn": T["text"], "bad": T["bad_text"]}[VERDICT_KIND[s]]
        rates = f"{p_t * 100:.1f}% <span class='kk-kpi-unit'>vs</span> {p_c * 100:.1f}%"
        pval = ui.pval(e.get("p_value"))
        body = (f'<div style="display:grid; grid-template-columns:1.2fr 1fr; gap:12px">'
                f'{ui.kpi("실측 이탈률 (실험군 vs 대조군)", rates)}'
                f'<div style="text-align:right">{ui.kpi("이탈 감소", f"{diff * 100:+.2f}%p", f"p = {pval}", color)}</div></div>')
    return f'<div class="kk kk-lib-card-content" style="display:flex; flex-direction:column; gap:8px">{head}{body}</div>'


@st.dialog("실험 상세", width="large")
def show_detail(e: dict) -> None:
    st.markdown(f"### {e['title']}")
    st.caption(f"실험 번호 #{e['id']} · 상태 {e['status']} · 저장 {e.get('created_at')}")
    cond = e.get("conditions") or {}
    goals = ", ".join(f"{LEVER_LABELS.get(k, k)} {v}%" for k, v in (e.get("levers") or {}).items() if v) or "-"
    rows = [
        ["전략", f'{ui.esc(e.get("strategy_kind") or "-")} · {ui.esc(e.get("strategy_goal") or "-")}'],
        ["설명", ui.esc(e.get("strategy_desc") or "-")],
        ["적용 조건", f'구독 기간 {cond.get("period", "전체")} · 마지막 접속 {cond.get("last", "전체")} · 요금제 {", ".join(cond.get("plans") or []) or "전체"}'],
        ["행동 목표(가정)", goals],
        ["대상 유형", seg_display(e["segment"])],
        ["가설 (모델)", f'대조군 {ui.pct(e.get("hyp_p_ctrl"), 2)} → 실험군 {ui.pct(e.get("hyp_p_treat"), 2)}'
                        + (f' · 그룹당 필요 {int(e["required_n"]):,}명' if e.get("required_n") else "")],
        ["설계", f'실험군 {int(e.get("n_treat") or 0):,}명 / 대조군 {int(e.get("n_ctrl") or 0):,}명 · {ui.esc(e.get("channel") or "-")} · '
                 f'{e.get("start_date") or "-"} ~ {e.get("end_date") or "-"}'],
        ["판단 기준", ui.esc(e.get("metric") or "-")],
    ]
    if e.get("verdict"):
        rows += [
            ["실측 결과", f'실험군 {e["obs_x_treat"]:,}/{e["obs_n_treat"]:,}명 · 대조군 {e["obs_x_ctrl"]:,}/{e["obs_n_ctrl"]:,}명'],
            ["차이 · 95% 신뢰구간", f'{e["ci_low"] * 100:+.2f} ~ {e["ci_high"] * 100:+.2f}%p · p = {ui.pval(e["p_value"])}'],
            ["판정", e["verdict"] + (" (시뮬레이션 · 실측 아님)" if e.get("is_simulated") else "")],
        ]
    if e.get("note"):
        rows.append(["메모", ui.esc(e["note"])])
    ui.html(f'<div class="kk">{ui.table(["항목", "내용"], rows)}</div>')


@st.dialog("실험 삭제")
def confirm_delete(e: dict) -> None:
    ui.html('<div class="kk kk-warnbox">실험과 배정 명단이 영구 삭제됩니다.</div>')
    sure = st.checkbox("삭제에 동의합니다.", key=f"lib-sure-{e['id']}")
    if st.button("삭제 확인", key=f"lib-del-{e['id']}", disabled=not sure,
                 type="primary", **ui.WIDE):
        db.delete_experiment(e["id"])
        st.toast("실험이 삭제되었습니다.")
        st.rerun()


ui.render_header()

# 라이브러리 전용 카드 스타일: 카드 크기는 유지하고 버튼의 시작 높이만 맞춤
st.markdown("""
<style>
.st-key-kk-lib-grid { padding-top: 24px !important; }
div[class*="st-key-kkbox-lib-"] {
    min-height: 280px !important;
    height: 280px !important;
    box-sizing: border-box !important;
}
/* 내용 길이와 관계없이 버튼이 바로 아래 같은 높이에서 시작 */
.kk-lib-card-content {
    height: 184px !important;
    min-height: 168px !important;
    max-height: 168px !important;
    flex: 0 0 168px !important;
    box-sizing: border-box;
    overflow: visible;
}
/* 새 전략 추가 카드는 기존 디자인과 높이를 유지 */

/* 필터 오른쪽 컬럼의 체크박스를 아래 카드의 오른쪽 경계에 맞춤 */
div[data-testid="stColumn"]:has(.st-key-lib-hide-align) {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end !important;
}
div[data-testid="stColumn"]:has(.st-key-lib-hide-align) > div[data-testid="stVerticalBlock"] {
    width: 100% !important;
    align-items: flex-end !important;
}
.st-key-lib-hide-align {
    margin-left: auto !important;
    width: max-content !important;
    max-width: 100% !important;
    transform: translate(-6px, 10px) !important;
}
.st-key-lib-hide-align [data-testid="stCheckbox"] {
    width: max-content !important;
    max-width: 100% !important;
}
.st-key-lib-hide-align [data-testid="stCheckbox"] label {
    width: max-content !important;
    padding-right: 0 !important;
}

</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<style>
.st-key-lib-hide-align [data-testid="stCheckbox"] p {{
    color: {T['text']} !important;
    font-weight: 600 !important;
    opacity: 1 !important;
}}
.st-key-lib-hide-align [data-testid="stCheckbox"] label > span:first-child > div,
.st-key-lib-hide-align [data-testid="stCheckbox"] input[type="checkbox"] + div {{
    background-color: {T['accent_soft']} !important;
    border: 1px solid {T['accent']} !important;
}}
.st-key-lib-hide-align [data-testid="stCheckbox"] label:has(input:checked) > span:first-child > div,
.st-key-lib-hide-align [data-testid="stCheckbox"] input[type="checkbox"]:checked + div {{
    background-color: {T['accent']} !important;
    border: 1px solid {T['accent']} !important;
}}
.st-key-lib-hide-align [data-testid="stCheckbox"] label:has(input:checked) svg {{
    fill: {T['accent_text']} !important;
}}
</style>
""", unsafe_allow_html=True)

with st.container(key="kk-body"):
    st.markdown(ui.compact(ui.steps_html(4)), unsafe_allow_html=True)
    ui.html(ui.page_title("전략 라이브러리",
                          "실험군·대조군의 실제 결과로 판정한 전략 확인",
                          "4단계 · 라이브러리"))
    try:
        exps = db.list_experiments()
    except Exception as error:
        st.error(f"실험 저장소에 연결할 수 없습니다: {error}")
        st.stop()

    f1, f2 = st.columns([4, 1.3], vertical_alignment="center")
    with f1:
        counts = {f: sum(1 for e in exps if f == "전체" or status_of(e) == f) for f in FILTERS}
        chosen = ui.choose("판정 필터", FILTERS, "lib_filter", "전체", label_visibility="collapsed",
                           format_func=lambda f: f"{f} {counts[f]}") or "전체"
    with f2:
        with st.container(key="lib-hide-align"):
            hide_sim = st.checkbox(
                "시뮬레이션 결과 숨기기",
                key="lib_hide_sim"
            )

    shown = [e for e in exps if (chosen == "전체" or status_of(e) == chosen) and not (hide_sim and e.get("is_simulated"))]
    ok_pdf, pdf_msg = pdf_available()

    with st.container(key="kk-lib-grid"):
        cols = st.columns(2)
        for i, e in enumerate(shown):
            card_key = f"{e['id']}-{i}"
            with cols[i % 2], st.container(key=f"kkbox-lib-{card_key}"):
                ui.html(card_html(e))
                b1, b2, b3, b4 = st.columns(4)
                with b1:
                    if status_of(e) == "진행 중":
                        if st.button("결과 입력", key=f"input-{card_key}", type="primary", **ui.WIDE):
                            ss["open_exp"] = e["id"]
                            ss["exp_view"] = "results"
                            st.switch_page(ui.PAGE_FILES["experiments"])
                    else:
                        st.button("입력 완료", key=f"completed-{card_key}", disabled=True, **ui.WIDE)
                with b2:
                    if st.button("상세 보기", key=f"detail-{card_key}", **ui.WIDE):
                        show_detail(e)
                with b3:
                    if ok_pdf:
                        try:
                            data = pdf_bytes(e["id"], str(e.get("updated_at")))
                            st.download_button("PDF 보고서", data, f"kkeeper_exp{e['id']}.pdf", "application/pdf",
                                               key=f"pdf-{card_key}", **ui.WIDE)
                        except Exception as error:  # 폰트 문제 등
                            st.caption(f"PDF를 생성할 수 없습니다: {error}")
                    else:
                        st.button("PDF 보고서", key=f"pdf-{card_key}", disabled=True, help=pdf_msg, **ui.WIDE)
                with b4:
                    if st.button("삭제", key=f"delete-{card_key}", **ui.WIDE):
                        confirm_delete(e)

        with cols[len(shown) % 2], st.container(key="kkbox-lib-add"):
            ui.html(f'<div class="kk" style="text-align:center; padding:65px 0 6px"><div class="kk-card-title">+ 새 전략 검증하기</div>'
                    f'<div class="kk-card-note">마케팅 방안 입력 단계부터 다시 시작합니다.</div></div>')
            if st.button("마케팅 설계로 →", key="lib-new", **ui.WIDE):
                st.switch_page(ui.PAGE_FILES["marketing"])

    if not shown:
        st.caption("조건에 해당하는 전략이 없습니다. 실험 관리에서 결과와 판정을 저장하면 목록에 반영됩니다.")

    legacy = db.load_legacy_plans()
    if not legacy.empty:
        with st.expander(f"이전 버전에서 저장한 계획 {len(legacy)}건 (모델 예측만 포함, 실측 판정 없음)"):
            view = legacy[[c for c in ["id", "title", "segment_name", "marketing_name", "churn_rate_before", "churn_rate_after",
                                       "reduced_customers", "created_at"] if c in legacy.columns]]
            rows = [[ui.esc(str(v)) for v in r] for r in view.itertuples(index=False)]
            ui.html(f'<div class="kk">{ui.table(list(view.columns), rows)}</div>')
