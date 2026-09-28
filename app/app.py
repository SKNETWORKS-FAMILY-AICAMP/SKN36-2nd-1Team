"""
KKeeper — 고객 이탈 관리 워크스페이스 (시안 A · 레코드판)

실행:  streamlit run app.py
구성:  app.py              홈 + 아직 준비 중인 페이지(고객 매칭·실험 관리·라이브러리)
       ui.py            공통 테마·스타일·상단 메뉴
       pages/1_marketing.py 마케팅 설계 (주소: /marketing)
화면:  오른쪽 위 해/달 버튼으로 라이트·다크 모드 전환 (기본: 다크)
"""

import sys
from pathlib import Path

import streamlit as st

# ui.py는 app.py와 같은 폴더에 있어요 (pages 폴더 안이 아니에요)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ui  # noqa: E402
from ui import PAGES, icon, link, compact

st.set_page_config(page_title="KKeeper", layout="wide", initial_sidebar_state="collapsed")

# 다른 페이지에서 넘어올 때(st.switch_page)는 주소 대신 세션에 담긴 값을 써요
ss = st.session_state
page = st.query_params.get("page") or ss.pop("goto", None) or "home"
if page not in PAGES or page in ("input", "matching", "experiments", "library"):
    page = "home"
T = ui.init(page, ss.pop("goto_theme", None))
theme_name = ui.theme_name


# ─────────────────────────────────────────────
# 홈
# ─────────────────────────────────────────────
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
    ("01", "pencil", "마케팅 설계", "전략의 목적과 적용 조건을 입력하세요.", "input"),
    ("02", "grid", "고객 매칭", "이탈 위험도와 행동 특성으로<br>전략에 맞는 유형을 추천합니다.", "matching"),
    ("03", "split", "실험 관리", "매칭된 고객을 두 그룹으로 나눠<br>전략을 적용합니다.", "experiments"),
    ("04", "books", "라이브러리", "두 그룹의 결과를 비교하고<br>검증된 전략을 저장합니다.", "library"),
]


def home_html() -> str:
    cards = "".join(
        f"""<a class="kk-card" href="{link(to)}" target="_self">
  <div class="kk-card-top"><div class="kk-ibox">{icon(ic, 24)}</div><span class="kk-num">{n}</span></div>
  <div><div class="kk-card-title">{title}{icon('arrow', 20, T['subtle'])}</div><span class="kk-card-desc">{desc}</span></div>
</a>"""
        for n, ic, title, desc, to in STEPS
    )
    mini_vinyl = (
        '<svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true"><circle cx="22" cy="22" r="20" fill="#1F1E24" stroke="#34323B"/>'
        '<circle cx="22" cy="22" r="14" fill="none" stroke="#FFFFFF" stroke-opacity="0.08"/><circle cx="22" cy="22" r="8" fill="#9C7EDB"/>'
        '<circle cx="22" cy="22" r="2" fill="#1F1E24"/></svg>'
    )
    return f"""
<section class="kk-hero">
  <div class="kk-hero-text">
    <div class="kk-badge"><span class="kk-dot"></span>음악 스트리밍 서비스 구독자 이탈 방지</div>
    <div style="display:flex; flex-direction:column; gap:44px">
      <h1 class="kk-h1"><span style="color:{T['accent']}">KK</span>eeper</h1>
      <p class="kk-sub">고객 이탈 관리 워크스페이스</p>
    </div>
    <p class="kk-desc">마케팅 설계부터 고객 매칭, 실험, 검증까지 한 곳에서.</p>
    <div class="kk-btns">
      <a class="kk-btn primary" href="{link('input')}" target="_self">마케팅 설계 시작하기 {icon('arrow', 18, 'currentColor', 2.2)}</a>
      <a class="kk-btn secondary" href="{link('library')}" target="_self">라이브러리 보기</a>
    </div>
  </div>
  {vinyl_svg()}
</section>

<section class="kk-section">
  <div class="kk-sec-head"><h2 class="kk-h2">시작하기</h2></div>
  <div class="kk-steps">{cards}</div>
</section>

<section class="kk-section" style="padding-bottom:56px">
  <h2 class="kk-h2">최근 작업</h2>
  <div class="kk-recent">
    <div class="kk-thumb">{mini_vinyl}</div>
    <div class="kk-recent-body">
      <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap">
        <span style="font-size:19px; font-weight:700">콘텐츠 추천 실험</span><span class="kk-tag">실험군 vs 대조군</span>
      </div>
      <span style="font-size:15px; color:{T['muted']}">매칭된 고객 유형을 대상으로 맞춤 콘텐츠 추천 효과를 비교합니다.</span>
    </div>
    <div class="kk-status"><span class="kk-dot"></span>진행 중</div>
    <a class="kk-ghost" href="{link('experiments')}" target="_self">이어하기 {icon('arrow', 16, 'currentColor', 2.2)}</a>
  </div>
</section>"""



# ─────────────────────────────────────────────
# 준비 중인 페이지
# ─────────────────────────────────────────────
PAGE_INTRO = {
    "experiments": "실험군·대조군 실험을 만들고 진행 상황을 보는 화면이 들어갈 자리예요.",
    "library": "검증된 전략을 모아 보는 화면이 들어갈 자리예요.",
}


def placeholder_html(key: str) -> str:
    title = PAGES.get(key)
    intro = PAGE_INTRO.get(key, "")
    return f"""
<section class="kk-page">
  <h1 class="kk-h2 kk-title">{title}</h1>
  <div class="kk-empty">{intro}<br>아직 준비 중인 화면이에요.</div>
</section>"""



ui.render_header()
body = home_html() if page == "home" else placeholder_html(page)
st.markdown(compact(f'<div class="kk">{body}</div>'), unsafe_allow_html=True)
