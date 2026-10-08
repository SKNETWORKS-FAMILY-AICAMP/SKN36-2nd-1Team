"""
KKeeper — 고객 이탈 관리 워크스페이스

실행:  (프로젝트 폴더에서)  streamlit run app/app.py

화면 흐름
  홈 · 현황(대시보드)
  1 마케팅 설계 → 2 고객 매칭 → 3 실험 관리(A/B 테스트) → 4 라이브러리
  모델(참고)
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ui  # noqa: E402
from ui import compact, icon  # noqa: E402

st.set_page_config(page_title="KKeeper", layout="wide", initial_sidebar_state="collapsed")
T = ui.init("home")


def vinyl_svg() -> str:
    av = T["avatar"]
    rings = "".join(
        f'<circle cx="300" cy="260" r="{r}" fill="none" stroke="#FFFFFF" stroke-opacity="{o}"/>'
        for r, o in [(200, .09), (186, .09), (172, .13), (158, .09), (144, .09), (130, .13), (116, .09), (102, .09)]
    )

    def person(cx, cy, r, bg, fg, sw):
        return (f'<g><circle cx="{cx}" cy="{cy}" r="{r}" fill="{bg}" stroke="{fg}" stroke-width="{sw}"/>'
                f'<circle cx="{cx}" cy="{cy - r * 0.24:.1f}" r="{r * 0.24:.1f}" fill="{fg}"/>'
                f'<path d="M{cx - r * 0.44:.1f} {cy + r * 0.46:.1f}c{r * 0.08:.1f}-{r * 0.24:.1f} {r * 0.24:.1f}-{r * 0.34:.1f} {r * 0.44:.1f}-{r * 0.34:.1f}'
                f's{r * 0.36:.1f} {r * 0.1:.1f} {r * 0.44:.1f} {r * 0.34:.1f}" fill="{fg}"/></g>')

    return f"""
<svg class="kk-vinyl" viewBox="0 0 600 520" role="img" aria-label="유형별로 색이 다른 고객들이 궤도를 도는 레코드판 일러스트">
  <defs>
    <radialGradient id="kkBody" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#2C2A33"/><stop offset="1" stop-color="#16151A"/></radialGradient>
    <radialGradient id="kkHalo" cx="50%" cy="50%" r="50%"><stop offset="{T['halo'][2]}" stop-color="{T['halo'][0]}" stop-opacity="{T['halo'][1]}"/><stop offset="1" stop-color="{T['halo'][0]}" stop-opacity="0"/></radialGradient>
    <linearGradient id="kkSheen" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0"/><stop offset="0.5" stop-color="#FFFFFF" stop-opacity="0.14"/><stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>
  </defs>
  <ellipse cx="300" cy="260" rx="285" ry="118" fill="none" stroke="#CC9EB8" stroke-opacity="0.3" stroke-dasharray="2 7" transform="rotate(-18 300 260)"/>
  <circle cx="300" cy="260" r="262" fill="url(#kkHalo)"/>
  <g class="kk-spin">
    <circle cx="300" cy="260" r="215" fill="url(#kkBody)" stroke="#4A4A52" stroke-width="2"/>
    {rings}
    <path d="M300 260 L140 110 A215 215 0 0 1 220 62 Z" fill="url(#kkSheen)"/>
    <path d="M300 260 L460 410 A215 215 0 0 1 380 458 Z" fill="url(#kkSheen)"/>
    <circle cx="300" cy="260" r="80" fill="#9C7EDB"/>
    <circle cx="300" cy="260" r="80" fill="none" stroke="#100F13" stroke-opacity="0.15" stroke-width="6"/>
    <text x="300" y="238" text-anchor="middle" font-family="Rubik, sans-serif" font-weight="700" font-size="24" fill="#221C33">KKeeper</text>
    <text x="300" y="296" text-anchor="middle" font-family="Rubik, sans-serif" font-weight="600" font-size="8" letter-spacing="2" fill="#3A3150">KEEP EVERY LISTENER</text>
    <circle cx="300" cy="260" r="6" fill="{T['hole']}"/>
  </g>
  <ellipse cx="300" cy="260" rx="270" ry="150" fill="none" stroke="#8970CC" stroke-opacity="0.55" transform="rotate(14 300 260)"/>
  {person(72, 150, 26, av[0][0], av[0][1], 1.5)}
  {person(520, 118, 30, av[1][0], av[1][1], 1.8)}
  {person(112, 390, 28, av[2][0], av[2][1], 1.8)}
  {person(548, 330, 22, av[3][0], av[3][1], 1.5)}
  <circle cx="190" cy="78" r="4" fill="#9C7EDB"/><circle cx="420" cy="438" r="4" fill="#CC9EB8"/><circle cx="36" cy="270" r="3" fill="#93BBA3"/>
</svg>"""


STEPS = [
    ("01", "pencil", "마케팅 설계", "마케팅 방안과 대상 조건 입력", "marketing"),
    ("02", "grid", "고객 매칭", "전략이 잘 통할 고객 유형 추천", "matching"),
    ("03", "split", "실험 관리", "두 그룹으로 나눠 실제 효과 검증", "experiments"),
    ("04", "books", "라이브러리", "효과가 확인된 전략 저장과 재활용", "library"),
]


def home_css() -> str:
    return f"""
<style>
  /* 헤더 높이와 정렬은 ui.global_css()에서 모든 페이지에 공통 적용합니다. */

  /* 홈 화면은 참고 시안의 64px 여백과 500px 히어로 리듬을 따릅니다. */
  .st-key-kk-hero {{ min-height: 500px; padding: 0 64px; display: flex; align-items: center; }}
  .st-key-kk-hero > div, .st-key-kk-hero > div > [data-testid="stVerticalBlock"] {{ width: 100%; }}
  .st-key-kk-hero > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {{
      gap: 40px !important; align-items: center; }}
  .kk-hero-text {{ width: 660px; max-width: 100%; padding-bottom: 12px; display: flex; flex-direction: column; gap: 26px; }}
  .kk-hbadge {{ align-self: flex-start; display: flex; align-items: center; gap: 10px; padding: 8px 14px 8px 10px;
              border: 1px solid {T['chip_border']}; border-radius: 999px; font-size: 13px; font-weight: 500;
              color: {T['badge_text']}; letter-spacing: .02em; }}
  .kk .kk-h1, .kk .kk-h1 span {{ font-family: Rubik, sans-serif !important; font-weight: 700 !important; font-size: 132px !important;
      line-height: 0.95 !important; letter-spacing: -0.035em !important; color: {T['text']}; }}
  .kk .kk-sub {{ font-size: 24px !important; font-weight: 700 !important; line-height: 1.25 !important; letter-spacing: -0.02em; }} .st-key-kk-hero-btns {{ margin-top: 0 !important; padding-top: 34px !important; }}
  .kk-vinyl {{ display: block; width: 540px; max-width: 100%; margin: 32px auto 0; }}
  .kk-spin {{ transform-box: fill-box; transform-origin: center; animation: kkspin 28s linear infinite; }}
  @keyframes kkspin {{ to {{ transform: rotate(360deg); }} }}
  @media (prefers-reduced-motion: reduce) {{ .kk-spin {{ animation: none; }} }}

  .st-key-kk-hero-btns {{ margin-top: 12px; }}
  .st-key-kk-hero-btns [data-testid="stHorizontalBlock"] {{ gap: 12px !important; justify-content: flex-start; }}
  .st-key-kk-hero-btns [data-testid="stColumn"] {{ flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }}
  .st-key-kk-hero-btns a {{ height: 56px; padding: 0 28px !important; border-radius: 999px !important; }}
  .st-key-kk-hero-btns a p {{ font-size: 17px !important; font-weight: 700 !important; }}
  .st-key-kk-cta-main a {{ background: {T['accent']} !important; }}
  .st-key-kk-cta-main a p {{ color: {T['accent_text']} !important; }}
  .st-key-kk-cta-main button {{
      height: 56px !important; padding: 0 28px !important; border-radius: 999px !important;
      background: {T['accent']} !important; border: none !important;
  }}
  .st-key-kk-cta-main button p {{
      font-size: 17px !important; font-weight: 700 !important; color: {T['accent_text']} !important;
  }}
  .st-key-kk-cta-sub a {{ background: {T['secondary_bg']} !important; border: 1px solid {T['secondary_border']} !important; }}
  .st-key-kk-cta-sub a p {{ color: {T['secondary_text']} !important; }}

  .st-key-kk-home {{ padding: 0 64px 56px; }}
  .st-key-kk-home > div > [data-testid="stVerticalBlock"] {{ gap: 16px; }}
  .st-key-kk-steps-grid [data-testid="stHorizontalBlock"] {{ gap: 16px !important; }}
  .kk .kk-h2 {{ font-size: 20px !important; line-height: 1.3 !important; font-weight: 700 !important; letter-spacing: -0.01em; }}
  .st-key-kk-start-title {{ min-height: 26px; margin-bottom: 12px; }}
  div[class*="st-key-kk-step-"] {{ position: relative; min-height: 185px; }}
  div[class*="st-key-kk-step-"] > [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) {{
      position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important; z-index: 3; }}
  div[class*="st-key-kk-step-"] [data-testid="stPageLink"] {{ position: absolute; inset: 0; z-index: 3; }}
  div[class*="st-key-kk-step-"] [data-testid="stPageLink"] a {{
      position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important; opacity: 0; }}
  .kk-scard {{ height: 185px; padding: 22px 26px; border-radius: 20px; background: {T['tint']}; border: 1px solid {T['tint_border']};
             display: flex; flex-direction: column; justify-content: space-between; }}
  div[class*="st-key-kk-step-"]:hover .kk-scard {{ border-color: {T['accent']}; }}
  .kk-ibox {{ width: 52px; height: 52px; border-radius: 14px; background: {T['icon_box']}; color: {T['accent']};
             display: flex; align-items: center; justify-content: center; }}
  .kk-snum {{ font-family: Rubik, sans-serif !important; font-size: 16px; font-weight: 700; color: {T['num']}; }}
  .kk-stitle {{ display: flex; align-items: center; justify-content: space-between; font-size: 20px; font-weight: 700; }}
  .kk-sdesc {{ display: block; min-height: 45px; margin-top: 8px; font-size: 15px; line-height: 1.5; color: {T['muted']}; }}
  .st-key-kk-recent-title {{ min-height: 26px; margin-top: 20px; margin-bottom: 12px; }}
  .st-key-kk-recent-row {{ min-height: 104px; padding: 16px 24px 16px 20px; border-radius: 20px;
      background: {T['tint']}; border: 1px solid {T['tint_border']}; }}
  .st-key-kk-recent-row > div > [data-testid="stVerticalBlock"] {{ justify-content: center; }}
  .st-key-kk-recent-row [data-testid="stHorizontalBlock"] {{ gap: 22px !important; align-items: center; }}
  .st-key-kk-recent-row [data-testid="stColumn"]:last-child {{ flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }}
  .st-key-kk-recent-row [data-testid="stPageLink"] a {{ height: 48px; padding: 0 22px !important; border-radius: 999px !important;
      border: 1px solid {T['secondary_border']} !important; background: {T['surface']} !important; white-space: nowrap; }}
  .st-key-kk-recent-row [data-testid="stPageLink"] p {{ font-size: 15px !important; font-weight: 600 !important; color: {T['text']} !important; }}
  .kk-recent {{ min-height: 70px; display: flex; align-items: center; gap: 22px; flex-wrap: wrap; }}
  .kk-thumb {{ width: 64px; height: 64px; border-radius: 14px; background: {T['icon_box']}; display: flex; align-items: center; justify-content: center; }}

  @media (max-width: 1100px) {{
    .st-key-kk-hero {{ padding-top: 32px; padding-bottom: 32px; align-items: flex-start; }}
    .st-key-kk-hero > div > [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {{
        flex-direction: column; align-items: flex-start; gap: 8px !important; }}
    .st-key-kk-hero [data-testid="stColumn"] {{ width: 100% !important; flex: 1 1 100% !important; }}
    .kk-vinyl {{ width: min(540px, 78vw); margin-top: 8px; }}
    .st-key-kk-steps-grid [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; }}
    .st-key-kk-steps-grid [data-testid="stColumn"] {{ flex: 1 1 calc(50% - 8px) !important; width: calc(50% - 8px) !important; }}
    .kk-scard {{ height: auto; min-height: 175px; gap: 20px; }}
  }}
  @media (max-width: 640px) {{
    /* 홈의 공통 메뉴는 모바일에서도 한 줄을 유지하고 좌우로 넘겨 볼 수 있게 합니다. */
    .st-key-kk-head {{ padding: 14px 16px; overflow-x: auto; scrollbar-width: none; }}
    .st-key-kk-head::-webkit-scrollbar {{ display: none; }}
    .st-key-kk-head [data-testid="stHorizontalBlock"] {{
        flex-direction: row !important; flex-wrap: nowrap !important; width: max-content !important; min-width: max-content !important;
        min-height: 44px; gap: 4px !important; }}
    .st-key-kk-head [data-testid="stColumn"] {{ flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }}
    .st-key-kk-head [data-testid="stColumn"]:first-child {{ width: 158px !important; flex-basis: 158px !important; }}
    .st-key-kk-hero, .st-key-kk-home {{ padding-left: 16px; padding-right: 16px; }}
    .st-key-kk-home {{ padding-bottom: 40px; }}
    .kk .kk-h1, .kk .kk-h1 span {{ font-size: 72px !important; }}
    .kk .kk-sub {{ font-size: 24px !important; }}
    .st-key-kk-hero-btns [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; }}
    .st-key-kk-steps-grid [data-testid="stColumn"] {{ flex: 1 1 100% !important; width: 100% !important; }}
    .st-key-kk-recent-row {{ padding: 16px; }}
    .st-key-kk-recent-row [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; gap: 14px !important; }}
    .st-key-kk-recent-row [data-testid="stColumn"] {{ flex: 1 1 100% !important; width: 100% !important; }}
    .st-key-kk-recent-row [data-testid="stColumn"]:last-child {{ flex-basis: 100% !important; width: 100% !important; }}
    .st-key-kk-recent-row [data-testid="stPageLink"] a {{ width: 100%; }}
  }}
</style>"""


def hero_text_html() -> str:
    return f"""
<div class="kk-hero-text">
  <div class="kk-hbadge"><span class="kk-dot" style="background:#9C7EDB"></span>음악 스트리밍 서비스 구독자 이탈 방지</div>
  <div style="display:flex; flex-direction:column; gap:26px">
    <h1 class="kk-h1"><span style="color:{T['accent']}">KK</span>eeper</h1>
    <p class="kk-sub">고객 이탈 관리 워크스페이스</p>
  </div>
</div>"""


def step_card(n, ic, title, desc) -> str:
    return f"""<div class="kk"><div class="kk-scard">
  <div style="display:flex; justify-content:space-between; align-items:flex-start">
    <div class="kk-ibox">{icon(ic, 24)}</div><span class="kk-snum">{n}</span></div>
  <div><div class="kk-stitle">{title}{icon('arrow', 20, T['subtle'])}</div><span class="kk-sdesc">{desc}</span></div>
</div></div>"""


def recent_html() -> tuple[str, str | None]:
    """최근 실험 한 건 (없으면 안내)."""
    mini = ('<svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="20" fill="#1F1E24" stroke="#34323B"/>'
            '<circle cx="22" cy="22" r="14" fill="none" stroke="#FFFFFF" stroke-opacity="0.08"/><circle cx="22" cy="22" r="8" fill="#9C7EDB"/>'
            '<circle cx="22" cy="22" r="2" fill="#1F1E24"/></svg>')
    try:
        from common import db
        from common.constants import seg_display
        exps = db.list_experiments()
    except Exception:
        exps = []
    if not exps:
        body = (f'<span style="font-size:19px; font-weight:700">등록된 실험 없음</span>'
                f'<span style="font-size:15px; color:{T["muted"]}">마케팅 방안 입력 후 효과가 높은 고객을 선별하여 A/B 테스트를 설계합니다.</span>')
        status, target = ui.badge("시작 전", "neutral"), "marketing"
    else:
        e = exps[0]
        if e["status"] == "완료":
            kind = {"효과 있음": "good", "판단 보류": "warn", "효과 없음": "bad"}.get(e.get("verdict"), "accent")
            status, target = ui.badge(e.get("verdict") or "완료", kind), "library"
        elif db.is_waiting(e):
            status, target = ui.badge("결과 입력 대기", "warn"), "experiments"
        else:
            status, target = ui.badge("진행 중", "accent"), "experiments"
        body = (f'<div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap"><span style="font-size:19px; font-weight:700">{ui.esc(e["title"])}</span>'
                f'{ui.badge("실험군 vs 대조군", "neutral")}</div>'
                f'<span style="font-size:15px; color:{T["muted"]}">{seg_display(e["segment"])} · 실험군 {int(e.get("n_treat") or 0):,}명 / 대조군 {int(e.get("n_ctrl") or 0):,}명</span>')
    return (f'<div class="kk"><div class="kk-recent"><div class="kk-thumb">{mini}</div>'
            f'<div style="flex:1 1 320px; display:flex; flex-direction:column; gap:6px">{body}</div>{status}</div></div>'), target


ui.render_header()
st.markdown(compact(home_css()), unsafe_allow_html=True)
with st.container(key="kk-hero"):
    left, right = st.columns([1.15, 1], vertical_alignment="center")
    with left:
        st.markdown(compact(f'<div class="kk">{hero_text_html()}</div>'), unsafe_allow_html=True)
        with st.container(key="kk-hero-btns"):
            c1, c2 = st.columns(2)
            with c1, st.container(key="kk-cta-main"):
                if st.button("마케팅 설계 시작하기  →", key="kk-new-marketing"):
                    # 새 마케팅 설계 시작: 이전 작성 중 상태와 매칭/실험 설계 상태 초기화
                    for key in [
                        "strategy",
                        "strategy_draft",
                        "match",
                        "design",
                        "s_name",
                        "s_kind",
                        "s_goal",
                        "s_desc",
                        "s_period",
                        "s_last",
                        "s_plans",
                        "s_channels",
                        "lever_base",
                    ]:
                        st.session_state.pop(key, None)

                    # 행동 목표 슬라이더 값 초기화
                    for key in list(st.session_state.keys()):
                        if key.startswith("lv_"):
                            st.session_state.pop(key, None)

                    st.switch_page(ui.PAGE_FILES["marketing"])
            with c2, st.container(key="kk-cta-sub"):
                st.page_link(ui.PAGE_FILES["dashboard"], label="오늘 현황 보기")
    right.markdown(compact(f'<div class="kk">{vinyl_svg()}</div>'), unsafe_allow_html=True)

with st.container(key="kk-home"):
    with st.container(key="kk-start-title"):
        st.markdown('<div class="kk"><h2 class="kk-h2">시작하기</h2></div>', unsafe_allow_html=True)
    with st.container(key="kk-steps-grid"):
        cols = st.columns(4)
        for col, (n, ic, title, desc, to) in zip(cols, STEPS):
            with col, st.container(key=f"kk-step-{to}"):
                st.markdown(compact(step_card(n, ic, title, desc)), unsafe_allow_html=True)
                st.page_link(ui.PAGE_FILES[to], label=title)

    with st.container(key="kk-recent-title"):
        st.markdown(
            '<div class="kk" style="padding-top:26px"><h2 class="kk-h2">최근 작업</h2></div>',
            unsafe_allow_html=True
        )
    recent, target = recent_html()
    with st.container(key="kk-recent-row"):
        left, right = st.columns([5, 1], vertical_alignment="center")
        left.markdown(compact(recent), unsafe_allow_html=True)
        with right:
            st.page_link(ui.PAGE_FILES[target], label="이어하기 →")
