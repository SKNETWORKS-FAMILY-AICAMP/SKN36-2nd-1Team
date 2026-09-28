"""
KKeeper — 실험 관리 페이지 (pages/3_experiments.py · 주소: /experiments)

고객 매칭(2_matching.py)에서 골라 온 고객 유형으로 A/B 실험을 만들고, 진행 상태별로
칸반 보드에서 관리해요. 실험이 끝나면 결과를 입력해서 효과를 검증하고, 검증 완료된
실험은 라이브러리(4_library.py)에 전략 카드로 자동으로 쌓여요.

지금은 아직 실제 접속·결제 데이터에 연결돼 있지 않아서:
  · "실험 대상"은 고객 매칭 단계에서 고른 유형(matched_segments)을 그대로 써요.
    (원래 기획엔 여기서 조건을 다시 걸러 대상 수를 조회하는 단계가 있었지만,
    그 역할은 이미 마케팅 설계 → 고객 매칭 단계가 하고 있어서 중복하지 않았어요.)
  · 결과 입력은 관리자가 실제 유지 고객 수를 직접 입력하면, 유지율·상승분·판정을
    자동으로 계산해요.
"""

import sys
import uuid
from html import escape
from pathlib import Path

import streamlit as st

# ui.py는 app.py와 같은 폴더에 있어요 (pages 폴더 안이 아니에요)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ui  # noqa: E402
import store  # noqa: E402 — 새로고침·재시작해도 실험이 안 사라지게 파일에 저장해요
from ui import compact

st.set_page_config(page_title="실험 관리 · KKeeper", layout="wide", initial_sidebar_state="collapsed")
T = ui.init("experiments")
theme_name = ui.theme_name

STEP_NAMES = ["마케팅 설계", "고객 매칭", "실험 관리", "라이브러리"]

# 판정 배지 등에 쓰는 색 — 다른 페이지의 색 토큰(ui.py THEMES)은 건드리지 않고
# 이 페이지에서만 쓰는 상태색을 따로 둬요.
STATUS_COLORS = {
    "light": {"good_bg": "#E6F6EC", "good_text": "#1F8B4C", "warn_bg": "#FDF3DF", "warn_text": "#9A6B0A",
              "bad_bg": "#FBEAEA", "bad_text": "#B23A32"},
    "dark": {"good_bg": "#1B2A20", "good_text": "#7EE2A8", "warn_bg": "#2A2418", "warn_text": "#E8C176",
             "bad_bg": "#2B1D1F", "bad_text": "#E8918C"},
}
S = STATUS_COLORS[theme_name]

STATUS_COLS = ["준비중", "진행중", "결과 입력 대기", "검증 완료"]
STATUS_KIND = {"준비중": "neutral", "진행중": "active", "결과 입력 대기": "warn", "검증 완료": "good"}
HAS_DIALOG = hasattr(st, "dialog")

TRASH_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13h10l1-13"/>'
    '<path d="M10 11v6"/><path d="M14 11v6"/></svg>'
)


def choose(label: str, options: list, key: str, default, label_visibility: str = "visible"):
    """알약 모양 선택. 오래된 Streamlit(1.40 미만)에서는 라디오로 대신 보여줘요."""
    if hasattr(st, "pills"):
        return st.pills(label, options, default=default, key=key, label_visibility=label_visibility)
    return st.radio(label, options, index=options.index(default), key=key, horizontal=True,
                     label_visibility=label_visibility)


def modal(title: str):
    """st.dialog가 있으면 그걸 쓰고, 없으면 같은 자리에서 펼쳐지는 expander로 대신해요."""
    if HAS_DIALOG:
        return st.dialog(title)

    def _decorator(fn):
        def _wrapped(*a, **kw):
            with st.expander(title, expanded=True):
                fn(*a, **kw)
        return _wrapped
    return _decorator


def page_css() -> str:
    return f"""
<style>
  .st-key-kk-body {{ padding: 28px 64px 64px; }}
  .st-key-kk-body [data-testid="stVerticalBlock"] {{ gap: 16px !important; }}
  .st-key-kk-body [data-testid="stHorizontalBlock"] {{ gap: 20px !important; }}

  .st-key-kk-x-toolbar {{ margin: 20px 0 14px; }}
  .st-key-kk-x-toolbar button {{ padding-left: 20px !important; padding-right: 20px !important; }}

  .kk-x-col-head {{ display: flex; align-items: center; gap: 8px; padding: 0 2px 4px; }}
  .kk-x-col-head h3 {{ margin: 0; font-size: 15px; font-weight: 700; color: {T['text']}; }}
  .kk-x-col-count {{ font-family: Rubik, sans-serif; font-size: 12px; font-weight: 700; color: {T['subtle']};
                     background: {T['tint']}; border-radius: 999px; padding: 2px 9px; }}
  .kk-x-col-empty {{ font-size: 13px; color: {T['subtle']}; padding: 4px 2px 12px; }}

  div[class*="st-key-kkcard-exp"] {{ position: relative; background: {T['surface']}; border: 1px solid {T['border']} !important;
                                     border-radius: 16px !important; padding: 18px !important; margin-bottom: 0 !important; }}
  div[class*="st-key-kkcard-exp"] > div {{ border: none !important; }}
  /* Streamlit이 내부적으로 각 요소를 감싸는 div에도 position을 넣어서, 우리가 만든
     휴지통 아이콘/버튼이 "카드 전체" 기준이 아니라 그 안쪽 작은 박스 기준으로 움직이던
     문제가 있었어요. 카드 안 요소들의 position을 전부 리셋해서 확실히 카드 기준으로 붙게 해요. */
  div[class*="st-key-kkcard-exp"] * {{ position: static !important; }}
  .kk-x-badge-row {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
  div[class*="st-key-kkcard-exp"] .kk-x-card-del-icon {{ position: absolute !important; top: 16px; right: 5px; width: 34px; height: 34px;
      display: flex; align-items: center; justify-content: center; color: {T['subtle']}; pointer-events: none; }}
  .kk-x-card-title {{ margin: 0 0 3px !important; font-size: 16px; font-weight: 700; color: {T['text']}; line-height: 1.25; }}
  .kk p.kk-x-card-meta, div.kk .kk-x-card-meta {{ margin: 0 !important; font-size: 12px; color: {T['subtle']}; line-height: 1.35; }}
  .kk-x-card-lift {{ margin-top: 8px; font-family: Rubik, sans-serif; font-size: 20px; font-weight: 700; }}
  .kk-x-card-lift span {{ font-family: 'IBM Plex Sans KR', sans-serif; font-size: 12px; font-weight: 500; color: {T['subtle']}; margin-left: 6px; }}
  div[class*="st-key-kk-x-cta-gap"] {{ margin-top: 14px; }}
  div[class*="st-key-kk-x-field-"] {{ margin-bottom: 16px !important; }}
  div[class*="st-key-kkcard-exp"] div[class*="st-key-del_"] {{ position: absolute !important; top: 16px; right: 5px;
      width: 34px !important; height: 34px !important; z-index: 5; }}
  div[class*="st-key-kkcard-exp"] div[class*="st-key-del_"] button {{ width: 32px !important; height: 32px !important; min-height: 32px !important;
      padding: 0 !important; border: none !important; background: transparent !important;
      opacity: 0 !important; cursor: pointer !important; }}
  div[class*="st-key-kk-x-ratio-caption"] {{ margin: 10px 0 14px !important; }}
  div[class*="st-key-kk-x-ratio-caption"] [data-testid="stCaptionContainer"] p,
  div[class*="st-key-kk-x-ratio-caption"] small,
  div[class*="st-key-kk-x-ratio-caption"] p {{ font-size: 12px !important; line-height: 1.5 !important; }}

  .st-key-kk-body [data-testid="stBaseButton-primary"], .st-key-kk-body [data-testid="stBaseButton-secondary"] {{
      height: 44px !important; min-height: 44px !important; border-radius: 11px !important;
      font-family: 'IBM Plex Sans KR', sans-serif !important; }}
  .st-key-kk-body [data-testid="stBaseButton-primary"] {{ background: {T['accent']} !important; border: none !important;
      color: {T['accent_text']} !important; }}
  .st-key-kk-body [data-testid="stBaseButton-secondary"] {{ background: transparent !important;
      border: 1px solid {T['secondary_border']} !important; color: {T['text']} !important; }}
  .st-key-kk-body [data-testid="stBaseButton-primary"] p, .st-key-kk-body [data-testid="stBaseButton-secondary"] p {{
      font-size: 14px !important; font-weight: 700 !important; color: inherit !important; }}
  .st-key-kk-body button[data-variant="pills"],
  .st-key-kk-body [data-testid="stBaseButton-pills"], .st-key-kk-body [data-testid="stBaseButton-pillsActive"] {{
      min-height: 40px; padding: 0 16px !important; border-radius: 11px !important;
      font-family: 'IBM Plex Sans KR', sans-serif !important; font-size: 14px !important; }}
  .st-key-kk-body button[data-variant="pills"],
  .st-key-kk-body [data-testid="stBaseButton-pills"] {{
      background: transparent !important; border: 1px solid {T['chip_border']} !important; color: {T['badge_text']} !important; }}
  .st-key-kk-body button[data-variant="pills"][data-selected],
  .st-key-kk-body [data-testid="stBaseButton-pillsActive"] {{
      background: {T['accent_soft']} !important; border: 1px solid {T['accent']} !important; color: {T['accent']} !important; }}

  .kk-stepper {{ margin: 0; padding: 0; list-style: none; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }}
  .kk-stepper li.s {{ display: flex; align-items: center; gap: 10px; padding: 8px 16px 8px 8px; border-radius: 999px;
                     border: 1px solid {T['tint_border']}; font-size: 14px; color: {T['subtle']}; }}
  .kk-stepper li.s.on {{ border-color: transparent; background: {T['accent_soft']}; color: {T['accent']}; font-weight: 700; }}
  .kk-stepper li.s i {{ font-style: normal; width: 26px; height: 26px; border-radius: 999px; background: {T['surface']};
                       font-family: Rubik, sans-serif; font-size: 12px; display: flex; align-items: center; justify-content: center; }}
  .kk-stepper li.s.on i {{ background: {T['accent']}; color: {T['accent_text']}; }}
  .kk-stepper li.l {{ width: 12px; height: 1px; background: {T['chip_border']}; }}

  @media (max-width: 1100px) {{ .st-key-kk-body {{ padding: 24px 16px 48px; }} }}
</style>"""


def head_html() -> str:
    steps = []
    for i, name in enumerate(STEP_NAMES):
        if i:
            steps.append('<li class="l" aria-hidden="true"></li>')
        on = " on" if i == 2 else ""
        steps.append(f'<li class="s{on}"><i>{i + 1:02d}</i>{name}</li>')
    return f"""
<section class="kk-page" style="padding-bottom:0; flex-direction:row; align-items:flex-end; justify-content:space-between; flex-wrap:wrap; gap:24px">
  <div style="display:flex; flex-direction:column; gap:12px">
    <h1 class="kk-h2 kk-title" style="font-size:36px">실험 관리</h1>
    <p class="kk-desc" style="font-size:16px">만든 실험을 진행 상태별로 관리하고, 끝난 실험은 결과를 입력해 효과를 검증해요.</p>
  </div>
  <ol class="kk-stepper" aria-label="진행 단계">{''.join(steps)}</ol>
</section>"""


def status_badge(text: str, kind: str) -> str:
    colors = {
        "neutral": (T["surface"], T["subtle"], T["border"]),
        "active": (T["accent_soft"], T["accent"], "transparent"),
        "warn": (S["warn_bg"], S["warn_text"], "transparent"),
        "good": (S["good_bg"], S["good_text"], "transparent"),
    }
    bg, color, border = colors[kind]
    border_css = f"border:1px solid {border}" if border != "transparent" else "border:none"
    return (f'<span style="display:inline-flex; padding:5px 12px; border-radius:999px; background:{bg}; '
            f'color:{color}; font-size:12px; font-weight:700; {border_css}">{escape(text)}</span>')


def decide_verdict(lift: float, sample_n: int) -> tuple[str, str]:
    """유지율 상승분(%p)과 실험군 규모를 보고 판정을 내려요. 표본이 작거나 차이가
    미미하면 단정짓지 않고 '판단 보류'로 둬요."""
    if sample_n < 50 or abs(lift) < 2:
        return "판단 보류", "warn"
    if lift >= 2:
        return "효과 있음", "good"
    return "효과 없음", "bad"


def card_meta(exp: dict) -> str:
    if exp["status"] == "준비중":
        return f"{exp['duration']} 진행 예정 · 시작 대기 중"
    if exp["status"] == "진행중":
        return f"{exp['duration']} 진행 중 · 실험군 {exp['exp_n']:,}명 · 대조군 {exp['ctrl_n']:,}명"
    if exp["status"] == "결과 입력 대기":
        return "실험이 끝났어요 · 결과 입력이 필요해요"
    r = exp["result"]
    return f"실험군 유지율 {r['exp_rate']:.0f}% · 대조군 유지율 {r['ctrl_rate']:.0f}%"


def result_form(exp: dict) -> None:
    ss = st.session_state
    with st.container(key=f"kk-x-field-intro-{exp['id']}"):
        st.markdown(
            f"실험 기간 {escape(exp['duration'])} · 대상 {exp['total_n']:,}명 "
            f"(실험군 {exp['exp_n']:,}명 · 대조군 {exp['ctrl_n']:,}명)"
        )
    with st.container(key=f"kk-x-field-exp-{exp['id']}"):
        exp_kept = st.number_input("실험군 유지 고객 수", min_value=0, max_value=exp["exp_n"],
                                    value=exp["exp_n"] // 2, key=f"rk_exp_{exp['id']}")
    with st.container(key=f"kk-x-field-ctrl-{exp['id']}"):
        ctrl_kept = st.number_input("대조군 유지 고객 수", min_value=0, max_value=exp["ctrl_n"],
                                     value=exp["ctrl_n"] // 2, key=f"rk_ctrl_{exp['id']}")
    with st.container(key=f"kk-x-cta-gap-rk-{exp['id']}"):
        if st.button("결과 계산하고 저장", key=f"rk_submit_{exp['id']}", type="primary", use_container_width=True):
            exp_rate = (exp_kept / exp["exp_n"] * 100) if exp["exp_n"] else 0.0
            ctrl_rate = (ctrl_kept / exp["ctrl_n"] * 100) if exp["ctrl_n"] else 0.0
            lift = exp_rate - ctrl_rate
            extra = max(0, round(exp["ctrl_n"] * lift / 100))
            verdict, kind = decide_verdict(lift, exp["exp_n"])
            exp["result"] = {"exp_kept": exp_kept, "ctrl_kept": ctrl_kept, "exp_rate": exp_rate,
                              "ctrl_rate": ctrl_rate, "lift": lift, "extra": extra, "verdict": verdict, "kind": kind}
            exp["status"] = "검증 완료"
            ss.setdefault("strategy_library", []).append({
                "exp_id": exp["id"], "name": exp["benefit"] if exp["benefit"] != "-" else exp["name"],
                "target": "·".join(s["name"] for s in exp["segments"]), "lift": lift, "n": exp["total_n"],
                "verdict": verdict, "kind": kind,
            })
            store.save_from(ss)
            st.rerun()


@modal("실험 결과 입력")
def _result_dialog() -> None:
    ss = st.session_state
    exp = next((e for e in ss.get("experiments", []) if e["id"] == ss.get("kk_result_target")), None)
    if not exp:
        return
    st.markdown(f"**{escape(exp['name'])}**")
    result_form(exp)


@modal("새 실험 만들기")
def _create_dialog() -> None:
    ss = st.session_state
    matched = ss.get("matched_segments")
    if not matched:
        st.warning("먼저 고객 매칭에서 실험에 쓸 유형을 선택해 주세요.")
        if st.button("고객 매칭으로 가기", key="ce_goto_matching"):
            st.switch_page("pages/2_matching.py")
        return

    strategy = ss.get("strategy") or {}
    default_name = (f"{strategy.get('name', '')} 실험".strip()) or "새 실험"
    with st.container(key="kk-x-field-name"):
        name = st.text_input("실험 이름", value=ss.get("ce_name", default_name), key="ce_name")
    with st.container(key="kk-x-field-hyp"):
        hypothesis = st.text_area(
            "실험 가설", key="ce_hyp", height=90,
            placeholder="예: 이용량이 줄어든 장기 유료 고객에게 이 혜택을 주면 유지율이 오를 것이다",
        )
    with st.container(key="kk-x-field-benefit"):
        benefit = st.text_input("적용 혜택", key="ce_benefit", placeholder="예: 30일 무료 이용권")
    with st.container(key="kk-x-field-duration"):
        duration = choose("실험 기간", ["1주", "2주", "4주", "직접 설정"], "ce_duration", "2주")

    total_n = sum(s["size"] for s in matched)
    with st.container(key="kk-x-field-matched"):
        st.markdown(f"**매칭된 고객 유형** · 총 약 {total_n:,}명")
        for s in matched:
            st.markdown(f"- {escape(s['name'])} · 약 {s['size']:,}명")

    with st.container(key="kk-x-field-ratio"):
        ratio_label = choose("배분 비율 (실험군 : 대조군)", ["50 : 50", "70 : 30", "30 : 70"], "ce_ratio", "50 : 50")
    ratio = int(ratio_label.split(":")[0].strip())
    exp_n = round(total_n * ratio / 100)
    ctrl_n = total_n - exp_n
    with st.container(key="kk-x-ratio-caption"):
        st.caption(f"실험군 약 {exp_n:,}명 · 대조군 약 {ctrl_n:,}명 — 두 그룹의 특성이 비슷하도록 무작위로 나눠요.")

    with st.container(key="kk-x-field-start"):
        start_now = choose("시작 방식", ["지금 시작", "예약(준비중으로 저장)"], "ce_start", "지금 시작")

    with st.container(key="kk-x-cta-gap-ce"):
        if st.button("실험 만들기", key="ce_submit", type="primary", use_container_width=True):
            if not name.strip():
                st.error("실험 이름을 입력해 주세요.")
                return
            exp = {
                "id": f"exp_{uuid.uuid4().hex[:8]}",
                "name": name.strip(), "hypothesis": hypothesis.strip(), "benefit": benefit.strip() or "-",
                "duration": duration, "segments": matched, "total_n": total_n,
                "ratio": ratio, "exp_n": exp_n, "ctrl_n": ctrl_n,
                "status": "진행중" if start_now == "지금 시작" else "준비중",
                "result": None,
            }
            ss.setdefault("experiments", []).append(exp)
            for k in ("ce_name", "ce_hyp", "ce_benefit"):
                ss.pop(k, None)
            store.save_from(ss)
            st.rerun()


def render_card(exp: dict) -> None:
    with st.container(key=f"kkcard-{exp['id']}"):
        st.markdown(compact(f"""<div class="kk">
            <div class="kk-x-badge-row">{status_badge(exp['status'], STATUS_KIND[exp['status']])}</div>
            <h3 class="kk-x-card-title">{escape(exp['name'])}</h3>
            <p class="kk-x-card-meta">{card_meta(exp)}</p>
        </div>
        <div class="kk kk-x-card-del-icon" aria-hidden="true">{TRASH_SVG}</div>"""), unsafe_allow_html=True)

        # 눈에는 안 보이지만 위 휴지통 아이콘 자리 위에 정확히 겹치는 진짜 버튼이에요
        # (ui.py 헤더의 테마 전환 버튼과 같은 방식 — 컨테이너로 감싸지 않고 버튼 자체에 key를 줘서
        # 레이아웃 흐름에 빈 칸을 남기지 않아요)
        if st.button("​", key=f"del_{exp['id']}", help="실험 삭제"):
            ss = st.session_state
            ss["experiments"] = [e for e in ss.get("experiments", []) if e["id"] != exp["id"]]
            ss["strategy_library"] = [it for it in ss.get("strategy_library", []) if it.get("exp_id") != exp["id"]]
            store.save_from(ss)
            st.rerun()

        if exp["status"] == "검증 완료" and exp["result"]:
            r = exp["result"]
            color = {"good": S["good_text"], "warn": S["warn_text"], "bad": S["bad_text"]}[r["kind"]]
            st.markdown(compact(
                f'<div class="kk-x-card-lift" style="color:{color}">{r["lift"]:+.0f}%p'
                f'<span>{escape(r["verdict"])}</span></div>'
            ), unsafe_allow_html=True)

        with st.container(key=f"kk-x-cta-gap-{exp['id']}"):
            if exp["status"] == "준비중":
                if st.button("지금 시작하기", key=f"start_{exp['id']}", use_container_width=True):
                    exp["status"] = "진행중"
                    store.save_from(st.session_state)
                    st.rerun()
            elif exp["status"] == "진행중":
                if st.button("실험 종료 · 결과 입력", key=f"finish_{exp['id']}", use_container_width=True):
                    exp["status"] = "결과 입력 대기"
                    store.save_from(st.session_state)
                    st.rerun()
            elif exp["status"] == "결과 입력 대기":
                if st.button("결과 입력하기", key=f"result_{exp['id']}", type="primary", use_container_width=True):
                    st.session_state["kk_result_target"] = exp["id"]
                    _result_dialog()
            else:
                if st.button("라이브러리에서 보기", key=f"lib_{exp['id']}", use_container_width=True):
                    st.switch_page("pages/4_library.py")


def experiments_page() -> None:
    ss = st.session_state
    store.load_into(ss)
    ss.setdefault("experiments", [])
    st.markdown(compact(page_css()), unsafe_allow_html=True)
    st.markdown(compact(f'<div class="kk">{head_html()}</div>'), unsafe_allow_html=True)

    with st.container(key="kk-body"):
        with st.container(key="kk-x-toolbar"):
            if st.button("+ 새 실험 만들기", key="ce_open", type="primary"):
                _create_dialog()

        cols = st.columns(4, gap="medium")
        for i, status in enumerate(STATUS_COLS):
            items = [e for e in ss["experiments"] if e["status"] == status]
            with cols[i]:
                st.markdown(compact(
                    f'<div class="kk kk-x-col-head"><h3>{status}</h3>'
                    f'<span class="kk-x-col-count">{len(items)}</span></div>'
                ), unsafe_allow_html=True)
                if not items:
                    st.markdown('<p class="kk kk-x-col-empty">아직 없어요</p>', unsafe_allow_html=True)
                for exp in items:
                    render_card(exp)


# ─────────────────────────────────────────────

ui.render_header()
experiments_page()
