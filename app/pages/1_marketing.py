"""
KKeeper — 마케팅 설계 페이지 (pages/1_marketing.py · 주소: /marketing)

app.py 옆의 ui.py(공통 테마·스타일·상단 메뉴)를 함께 씁니다.
"""

import sys
from pathlib import Path

import streamlit as st

# ui.py는 app.py와 같은 폴더에 있어요 (pages 폴더 안이 아니에요)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ui  # noqa: E402
from ui import compact

st.set_page_config(page_title="마케팅 설계 · KKeeper", layout="wide", initial_sidebar_state="collapsed")
T = ui.init("input")
theme_name = ui.theme_name

KINDS = ["할인·프로모션", "콘텐츠 추천", "요금제 안내", "알림·리마인드", "혜택·리워드", "기타"]
GOALS = {
    "이탈 방지": "떠날 조짐이 보이는 고객 붙잡기",
    "재방문 유도": "뜸해진 고객 다시 부르기",
    "해지 철회": "해지 신청 고객 되돌리기",
    "업그레이드": "상위 요금제로 전환",
}
PERIODS = ["전체", "3개월 미만", "3~12개월", "1년 이상"]
LASTS = ["전체", "7일 이상 미접속", "14일 이상 미접속", "30일 이상 미접속"]
PLANS = ["개인", "학생", "가족", "[요금제 이름]"]          # 실제 요금제 이름으로 바꿔 주세요
CHANNELS = ["앱 푸시", "인앱 배너", "이메일", "문자"]
STEP_NAMES = ["마케팅 설계", "고객 매칭", "실험 관리", "라이브러리"]


def form_css() -> str:
    return f"""
<style>
  /* 본문 여백과 요소 간격 */
  .st-key-kk-body {{ padding: 28px 64px 64px; }}
  .st-key-kk-body [data-testid="stVerticalBlock"] {{ gap: 20px !important; }}
  .st-key-kk-body [data-testid="stHorizontalBlock"] {{ gap: 24px !important; }}

  /* 카드 */
  div[class*="st-key-kkcard"] {{ background: {T['surface']}; border: 1px solid {T['border']} !important;
                                 border-radius: 20px !important; padding: 30px 32px !important; }}
  div[class*="st-key-kkcard"] > div {{ border: none !important; }}

  /* 라벨 */
  .st-key-kk-body [data-testid="stWidgetLabel"] p {{ font-family: 'IBM Plex Sans KR', sans-serif !important;
      font-size: 15px !important; font-weight: 600 !important; color: {T['text']} !important; }}

  /* 라벨과 입력칸 사이 여백 */
  .st-key-kk-body [data-testid="stWidgetLabel"] {{ margin-bottom: 10px !important; }}

  /* 입력칸 · 선택칸 */
  .st-key-kk-body [data-testid="stTextInputRootElement"], .st-key-kk-body [data-testid="stTextAreaRootElement"],
  .st-key-kk-body [data-baseweb="input"], .st-key-kk-body [data-baseweb="textarea"],
  .st-key-kk-body [data-baseweb="select"] > div {{
      background: {T['input_bg']} !important; border: 1px solid {T['chip_border']} !important; border-radius: 12px !important; }}
  .st-key-kk-body [data-baseweb="base-input"] {{ background: transparent !important; }}
  .st-key-kk-body input, .st-key-kk-body textarea {{ background: transparent !important; }}
  .st-key-kk-body [data-testid="stTextInputRootElement"]:focus-within,
  .st-key-kk-body [data-testid="stTextAreaRootElement"]:focus-within {{ border-color: {T['accent']} !important; }}
  .st-key-kk-body input, .st-key-kk-body textarea, .st-key-kk-body [data-baseweb="select"] * {{
      color: {T['text']} !important; font-family: 'IBM Plex Sans KR', sans-serif !important; font-size: 16px !important; }}
  .st-key-kk-body input::placeholder, .st-key-kk-body textarea::placeholder {{ color: {T['placeholder']} !important; }}
  .st-key-kk-body [data-baseweb="input"]:focus-within, .st-key-kk-body [data-baseweb="textarea"]:focus-within {{
      border-color: {T['accent']} !important; }}
  .st-key-kk-body [data-testid="stTextInput"] input {{ height: 50px !important; padding: 0 16px !important; }}
  [data-baseweb="popover"] ul {{ background: {T['surface']} !important; }}
  [data-baseweb="popover"] li {{ color: {T['text']} !important; font-family: 'IBM Plex Sans KR', sans-serif !important; }}

  /* 드롭다운(팝오버) */
  .kk-dd-label {{ font-size: 15px; font-weight: 600; color: {T['text']}; margin-bottom: 4px; }}
  .st-key-kk-body [data-testid="stPopover"] button {{ min-height: 50px; padding: 0 16px !important; border-radius: 12px !important;
      background: {T['input_bg']} !important; border: 1px solid {T['chip_border']} !important; color: {T['text']} !important;
      justify-content: space-between !important; align-items: center !important; }}
  .st-key-kk-body [data-testid="stPopover"] button > div {{ width: 100% !important; display: flex !important;
      justify-content: space-between !important; align-items: center !important; }}
  .st-key-kk-body [data-testid="stPopover"] button [data-testid="stMarkdownContainer"] {{ text-align: left !important; }}
  .st-key-kk-body [data-testid="stPopover"] button:hover, .st-key-kk-body [data-testid="stPopover"] button:focus {{
      border-color: {T['accent']} !important; }}
  .st-key-kk-body [data-testid="stPopover"] button p {{ font-size: 16px !important; font-weight: 400 !important; color: {T['text']} !important; }}
  [data-testid="stPopoverBody"] {{ background: {T['surface']} !important; border: 1px solid {T['border']} !important; border-radius: 12px !important; }}
  [data-testid="stPopoverBody"] label p {{ font-family: 'IBM Plex Sans KR', sans-serif !important; font-size: 15px !important; color: {T['text']} !important; }}
  /* 알약 선택 버튼 (Streamlit 버전에 따라 이름이 달라서 두 방식으로 지정) */
  /* pill 버튼 그룹 간격 — 컨테이너 선택자가 버전마다 달라 버튼 자체에 margin으로 처리 */
  .st-key-kk-body [data-testid="stBaseButton-pills"],
  .st-key-kk-body [data-testid="stBaseButton-pillsActive"],
  .st-key-kk-body button[kind="pills"], .st-key-kk-body button[kind="pillsActive"],
  .st-key-kk-body button[data-variant="pills"] {{ margin: 2px 4px 2px 0 !important; }}
  .st-key-kk-body button[data-variant="pills"],
  .st-key-kk-body button[kind="pills"], .st-key-kk-body button[kind="pillsActive"],
  .st-key-kk-body [data-testid="stBaseButton-pills"], .st-key-kk-body [data-testid="stBaseButton-pillsActive"] {{
      min-height: 42px; padding: 0 18px !important; border-radius: 12px !important;
      font-family: 'IBM Plex Sans KR', sans-serif !important; font-size: 15px !important; }}
  .st-key-kk-body button[data-variant="pills"],
  .st-key-kk-body button[kind="pills"], .st-key-kk-body [data-testid="stBaseButton-pills"] {{
      background: transparent !important; border: 1px solid {T['chip_border']} !important; color: {T['badge_text']} !important; }}
  .st-key-kk-body button[data-variant="pills"][data-selected],
  .st-key-kk-body button[kind="pillsActive"], .st-key-kk-body [data-testid="stBaseButton-pillsActive"] {{
      background: {T['accent_soft']} !important; border: 1px solid {T['accent']} !important; color: {T['accent']} !important; }}
  .st-key-kk-body button[data-variant="pills"]:not([data-selected]):hover {{ background: {T['nav_active']} !important; }}
  .st-key-kk-body button[data-variant="pills"] *,
  .st-key-kk-body button[kind="pills"] *, .st-key-kk-body button[kind="pillsActive"] *,
  .st-key-kk-body [data-testid^="stBaseButton-pills"] * {{ font-size: 15px !important; color: inherit !important; }}
  .st-key-kk-body button[data-variant="pills"][data-selected] p,
  .st-key-kk-body button[kind="pillsActive"] p, .st-key-kk-body [data-testid="stBaseButton-pillsActive"] p {{ font-weight: 700 !important; }}

  /* 아래 버튼 */
  .st-key-kkcard-basic ~ div [data-testid="stButtonContainer"],
  .st-key-kk-body [data-testid="stButtonContainer"]:has([data-testid="stBaseButton-primary"]),
  .st-key-kk-body [data-testid="stButtonContainer"]:has([data-testid="stBaseButton-secondary"]) {{
      height: 56px !important; }}
  .st-key-kk-body [data-testid="stBaseButton-primary"], .st-key-kk-body [data-testid="stBaseButton-secondary"] {{
      height: 56px !important; min-height: 56px !important; border-radius: 14px !important;
      font-family: 'IBM Plex Sans KR', sans-serif !important; }}
  .st-key-kk-body [data-testid="stBaseButton-primary"] {{ background: {T['accent']} !important; border: none !important;
      color: {T['accent_text']} !important; }}
  .st-key-kk-body [data-testid="stBaseButton-secondary"] {{ background: transparent !important;
      border: 1px solid {T['secondary_border']} !important; color: {T['text']} !important; }}
  .st-key-kk-body [data-testid="stBaseButton-primary"] p, .st-key-kk-body [data-testid="stBaseButton-secondary"] p {{
      font-size: 17px !important; font-weight: 700 !important; color: inherit !important; }}

  /* 카드 제목 · 요약 · 안내 */
  .kk-card-h {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 4px; }}
  .kk-card-h b {{ font-family: Rubik, sans-serif !important; font-size: 14px; color: {T['accent']}; margin-right: 10px; }}
  .kk-card-h span.t {{ font-size: 20px; font-weight: 700; color: {T['text']}; }}
  .kk-card-h span.n {{ font-size: 13px; color: {T['subtle']}; }}
  /* 목적 라벨 옆 힌트 */
  .st-key-kk-body [data-testid="stWidgetLabel"] .kk-goal-hint {{
      font-size: 13px; font-weight: 400; color: {T['subtle']}; margin-left: 8px; }}
  .kk-goal-note {{ display: none; }}
  .kk-side {{ padding: 28px; border-radius: 20px; background: {T['surface']}; border: 1px solid {T['border']};
             display: flex; flex-direction: column; gap: 18px; }}
  .kk-side dl {{ margin: 0; display: flex; flex-direction: column; gap: 14px; }}
  .kk-side dl div {{ display: flex; justify-content: space-between; gap: 12px; font-size: 14px; }}
  .kk-side dt {{ color: {T['subtle']}; }}
  .kk-side dd {{ margin: 0; font-weight: 600; color: {T['text']}; text-align: right; }}
  .kk-tip {{ margin-top: 20px; padding: 24px 28px; border-radius: 20px; background: {T['accent_soft']};
            display: flex; flex-direction: column; gap: 10px; }}
  .kk-tip p {{ word-break: keep-all; overflow-wrap: break-word; }}
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


def input_head_html() -> str:
    steps = []
    for i, name in enumerate(STEP_NAMES):
        if i:
            steps.append('<li class="l" aria-hidden="true"></li>')
        on = " on" if i == 0 else ""
        steps.append(f'<li class="s{on}"><i>{i + 1:02d}</i>{name}</li>')
    return f"""
<section class="kk-page" style="padding-bottom:0; flex-direction:row; align-items:flex-end; justify-content:space-between; flex-wrap:wrap; gap:24px">
  <div style="display:flex; flex-direction:column; gap:12px">
    <h1 class="kk-h2 kk-title" style="font-size:40px">마케팅 설계</h1>
    <p class="kk-desc" style="font-size:17px">전략의 목적과 적용 조건을 입력하면, 이 전략이 통할 고객 유형을 찾아드려요.</p>
  </div>
  <ol class="kk-stepper" aria-label="진행 단계">{''.join(steps)}</ol>
</section>"""


def card_title(num: str, title: str, note: str = "") -> str:
    note_html = f'<span class="n">{note}</span>' if note else ""
    return f'<div class="kk kk-card-h"><div><b>{num}</b><span class="t">{title}</span></div>{note_html}</div>'


def choose(label: str, options: list, key: str, default, multi: bool = False,
           label_visibility: str = "visible"):
    """알약 모양 선택. 오래된 Streamlit(1.40 미만)에서는 라디오·멀티셀렉트로 대신 보여줘요."""
    if hasattr(st, "pills"):
        return st.pills(label, options, selection_mode="multi" if multi else "single",
                        default=default, key=key, label_visibility=label_visibility)
    if multi:
        return st.multiselect(label, options, default=default, key=key,
                               label_visibility=label_visibility)
    return st.radio(label, options, index=options.index(default), key=key, horizontal=True,
                    label_visibility=label_visibility)


def dropdown(label: str, options: list, key: str, index: int = 0) -> str:
    """클릭해서 고르기만 하는 드롭다운 (글자 입력 불가). 버튼을 누르면 목록이 열려요."""
    ss = st.session_state
    if ss.get(key) not in options:
        ss[key] = options[index]
    st.markdown(f'<div class="kk kk-dd-label">{label}</div>', unsafe_allow_html=True)
    with st.popover(ss[key], use_container_width=True):
        st.radio(label, options, key=key, label_visibility="collapsed")
    return ss[key]


def summary_html(v: dict) -> str:
    def show(x):
        if not x:
            return "-"
        return ", ".join(x) if isinstance(x, (list, tuple)) else x
    rows = [("전략 이름", v["name"] or "-"), ("전략 유형", show(v["kind"])), ("목적", show(v["goal"])),
            ("구독 기간", show(v["period"])), ("마지막 접속", show(v["last"])),
            ("요금제", show(v["plans"])), ("전달 채널", show(v["channels"]))]
    dl = "".join(f"<div><dt>{a}</dt><dd>{b}</dd></div>" for a, b in rows)
    mini = ('<svg width="40" height="40" viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="20" fill="#1F1E24" stroke="#34323B"/>'
            '<circle cx="22" cy="22" r="14" fill="none" stroke="#FFFFFF" stroke-opacity="0.08"/><circle cx="22" cy="22" r="8" fill="#9C7EDB"/>'
            '<circle cx="22" cy="22" r="2" fill="#1F1E24"/></svg>')
    return f"""
<div class="kk kk-side">
  <div style="display:flex; align-items:center; gap:12px">{mini}<span style="font-size:18px; font-weight:700">입력 요약</span></div>
  <dl>{dl}</dl>
  <div style="height:1px; background:{T['border']}"></div>
  <div style="display:flex; flex-direction:column; gap:6px">
    <span style="font-size:13px; color:{T['subtle']}">조건에 맞는 구독자</span>
    <span style="font-family:Rubik, sans-serif; font-size:32px; font-weight:700; color:{T['accent']}">[N]명</span>
    <span style="font-size:13px; color:{T['subtle']}">데이터를 연결하면 예상 인원이 표시돼요</span>
  </div>
</div>
<div class="kk kk-tip">
  <span style="font-size:15px; font-weight:700; color:{T['accent']}">다음 단계</span>
  <span style="font-size:14px; line-height:1.7; color:{T['tip_text']}">입력한 전략을 바탕으로 이탈 위험도와 행동 특성이 맞는 고객 유형을 추천해 드려요.<br>추천된 유형으로 바로 실험을 만들 수 있어요.</span>
</div>"""


def input_page() -> None:
    st.markdown(compact(form_css()), unsafe_allow_html=True)
    st.markdown(compact(f'<div class="kk">{input_head_html()}</div>'), unsafe_allow_html=True)
    ss = st.session_state

    with st.container(key="kk-body"):
        left, right = st.columns([2.45, 1])
        with left:
            with st.container(key="kkcard-basic"):
                st.markdown(card_title("1", "기본 정보"), unsafe_allow_html=True)
                name = st.text_input("전략 이름", key="s_name",
                                     placeholder="예: 장기 미접속 구독자 맞춤 플레이리스트 추천")
                kind = choose("전략 유형", KINDS, "s_kind", "콘텐츠 추천")
                _cur_goal = st.session_state.get("s_goal", "이탈 방지")
                _goal_hint = GOALS.get(_cur_goal, "")
                st.markdown(
                    f'<div class="kk" style="display:flex;align-items:baseline;gap:8px;'
                    f'font-size:15px;font-weight:600;margin-bottom:-4px">'
                    f'목적'
                    f'<span style="font-size:13px;font-weight:400;color:{T["subtle"]}">'
                    f'· {_goal_hint}</span></div>',
                    unsafe_allow_html=True,
                )
                goal = choose("목적", list(GOALS), "s_goal", "이탈 방지",
                              label_visibility="collapsed")
                desc = st.text_area("전략 설명", key="s_desc", height=110,
                                    placeholder="어떤 고객에게, 무엇을, 어떻게 전달하는지 적어 주세요.")

            with st.container(key="kkcard-cond"):
                st.markdown(card_title("2", "적용 조건", "비워 두면 전체 구독자를 대상으로 매칭해요"),
                            unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    period = dropdown("구독 기간", PERIODS, "s_period")
                    plans = choose("요금제", PLANS, "s_plans", ["개인", "학생"], multi=True)
                with c2:
                    last = dropdown("마지막 접속", LASTS, "s_last", index=2)
                    channels = choose("전달 채널", CHANNELS, "s_channels", ["앱 푸시"], multi=True)

            msg = st.empty()
            _, b1, b2 = st.columns([1.5, 1, 1.5], gap="small")
            save = b1.button("임시 저장", key="s_save", use_container_width=True)
            go = b2.button("고객 매칭하기 →", key="s_go", type="primary", use_container_width=True)

        values = {"name": name.strip(), "kind": kind, "goal": goal, "desc": desc.strip(), "period": period,
                  "last": last, "plans": plans or [], "channels": channels or []}
        with right:
            st.markdown(compact(summary_html(values)), unsafe_allow_html=True)

    if save:
        ss["strategy_draft"] = values
        st.toast("임시 저장했어요.")
    if go:
        if not values["name"]:
            msg.error("전략 이름을 입력해 주세요.")
        elif not values["kind"] or not values["goal"]:
            msg.error("전략 유형과 목적을 골라 주세요.")
        else:
            ss["strategy"] = values
            st.switch_page("pages/2_matching.py")


# ─────────────────────────────────────────────




ui.render_header()
input_page()
