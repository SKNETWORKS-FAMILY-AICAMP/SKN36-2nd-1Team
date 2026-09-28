"""
KKeeper 공통 UI — 색상 테마, 전역 스타일, 상단 메뉴

app.py와 pages/ 폴더의 페이지들이 함께 씁니다.
각 페이지 맨 위에서 init("페이지 키")를 한 번 부르세요.
"""

import streamlit as st

# 메뉴 (키: 이름)
PAGES = {
    "home": "홈",
    "input": "마케팅 설계",
    "matching": "고객 매칭",
    "experiments": "실험 관리",
    "library": "라이브러리",
}
# pages/ 폴더에 따로 있는 페이지의 주소 (나머지는 app.py가 ?page= 로 보여줌)
PAGE_PATHS = {"home": "./", "input": "./marketing", "matching": "./matching",
              "experiments": "./experiments", "library": "./library"}

# ─────────────────────────────────────────────
# 색상 토큰 (시안 A 라이트 / 다크)
# ─────────────────────────────────────────────
THEMES = {
    "light": {
        "bg": "#FAF9FC", "surface": "#FFFFFF", "tint": "#F3EEFD", "tint_border": "#E2D8FA",
        "border": "#E6E2EE", "line": "#E9E6EF", "chip_border": "#DDD8E6",
        "text": "#1C1A22", "muted": "#6B6878", "subtle": "#7A7686", "num": "#9A95A8", "badge_text": "#55525F",
        "accent": "#6E4FCB", "accent_text": "#FFFFFF", "accent_soft": "#EFE9FC", "accent_soft2": "#E4D9FB",
        "nav_active": "#EEEAF7", "secondary_bg": "#F3EEFD", "secondary_text": "#4F35A8",
        "secondary_border": "#E2D8FA", "icon_box": "#FFFFFF",
        "avatar": [("#EFE9FC", "#9C7EDB"), ("#F8E9F1", "#CC9EB8"), ("#E6F3EC", "#93BBA3"), ("#E8ECF7", "#8A9BCC")],
        "hole": "#FAF9FC", "halo": ("#8B6AE0", 0.68, 0.56),
        "input_bg": "#FAF9FC", "tip_text": "#4F35A8", "placeholder": "#9A95A8",
    },
    "dark": {
        "bg": "#100F13", "surface": "#1B1A1F", "tint": "#1B1A1F", "tint_border": "#2F2D36",
        "border": "#2F2D36", "line": "#27262C", "chip_border": "#34323B",
        "text": "#EFEFEF", "muted": "#A6A6A6", "subtle": "#8A8A8A", "num": "#6E6E6E", "badge_text": "#C2C2C2",
        "accent": "#AA8FE5", "accent_text": "#1A1428", "accent_soft": "#261B3E", "accent_soft2": "#261B3E",
        "nav_active": "#28262E", "secondary_bg": "transparent", "secondary_text": "#EFEFEF",
        "secondary_border": "#45434D", "icon_box": "#261B3E",
        "avatar": [("#20192E", "#9C7EDB"), ("#2B1B27", "#CC9EB8"), ("#16251F", "#93BBA3"), ("#171D2E", "#8A9BCC")],
        "hole": "#100F13", "halo": ("#9C7EDB", 0.22, 0.72),
        "input_bg": "#141318", "tip_text": "#D6CCF2", "placeholder": "#6E6E76",
    },
}

# init()이 채우는 현재 상태
page = "home"
theme_name = "dark"
T = THEMES[theme_name]


def init(active_page: str, theme: str | None = None) -> dict:
    """현재 페이지와 테마를 정하고 색상 토큰을 돌려줘요.
    테마는 세션(같은 창 안)과 주소의 ?theme= 두 곳에 저장돼서, 모드를 바꿔도 입력 중인 내용이 유지돼요."""
    global page, theme_name, T
    page = active_page
    ss = st.session_state
    # 주소의 ?theme=이 명시돼 있으면(테마 버튼 클릭으로 새로고침된 경우) 그 값을 먼저 쓰고,
    # 없으면 세션에 저장된 값, 그것도 없으면 다크로 시작해요.
    th = theme or st.query_params.get("theme") or ss.get("kk_theme") or "dark"
    theme_name = th if th in THEMES else "dark"
    ss["kk_theme"] = theme_name
    T = THEMES[theme_name]
    return T


def link(to_page: str, theme: str | None = None) -> str:
    th = theme or theme_name
    path = PAGE_PATHS.get(to_page)
    return f"{path}?theme={th}" if path else f"./?page={to_page}&theme={th}"


def compact(html: str) -> str:
    # 마크다운이 들여쓰기·빈 줄을 코드 블록으로 읽지 않도록 한 덩어리로 정리
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


# ─────────────────────────────────────────────
# 아이콘 · 전역 스타일
# ─────────────────────────────────────────────
def icon(name: str, size: int = 20, stroke: str = "currentColor", width: float = 2) -> str:
    paths = {
        "pencil": '<path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/>',
        "grid": '<circle cx="7" cy="7" r="3"/><circle cx="17" cy="7" r="3"/><circle cx="7" cy="17" r="3"/><circle cx="17" cy="17" r="3" fill="currentColor"/>',
        "split": '<path d="M12 3v6"/><path d="M12 9l-6 6v6"/><path d="M12 9l6 6v6"/>',
        "books": '<path d="M5 4h4v16H5z"/><path d="M10 4h4v16h-4z"/><path d="M15.5 5.5l3.5-1 3 14.5-3.5 1z"/>',
        "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
        "search": '<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>',
        "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
        "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
        "moon": '<path d="M20 14.5A8 8 0 019.5 4a8 8 0 1010.5 10.5z"/>',
    }
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{stroke}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths[name]}</svg>')


# ─────────────────────────────────────────────
# 전역 스타일
# ─────────────────────────────────────────────
def global_css() -> str:
    return f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=Rubik:wght@600;700&display=swap">
<style>
  /* Streamlit 기본 UI 숨기기 */
  header[data-testid="stHeader"], footer, #MainMenu, [data-testid="stToolbar"],
  [data-testid="stDecoration"], [data-testid="stSidebar"] {{ display: none !important; }}
  .stApp {{ background: {T['bg']}; }}
  .block-container {{ max-width: 1440px; padding: 0 !important; }}
  [data-testid="stVerticalBlock"] {{ gap: 0 !important; }}
  html, body, .stApp, .stMarkdown, .stMarkdown p {{ font-family: 'IBM Plex Sans KR', sans-serif; color: {T['text']}; }}

  .kk a {{ color: {T['text']}; text-decoration: none; }}
  .kk a:hover {{ color: {T['accent']}; }}
  .kk * {{ box-sizing: border-box; }}
  .kk p, .kk h1, .kk h2 {{ margin: 0; padding: 0; }}

  /* 헤더 */
  .kk-header {{ height: 88px; padding: 0 64px; display: flex; align-items: center; justify-content: space-between;
               border-bottom: 1px solid {T['line']}; }}
  .kk-logo {{ display: flex; align-items: center; gap: 14px; font-family: Rubik, sans-serif; font-weight: 700;
             font-size: 30px; letter-spacing: -0.02em; }}
  .kk-nav {{ display: flex; gap: 18px; align-items: center; }}
  .kk-nav a {{ padding: 10px 18px; border-radius: 999px; font-size: 15px; font-weight: 500; color: {T['muted']}; }}
  .kk-nav a.on {{ background: {T['nav_active']}; font-weight: 600; color: {T['text']}; }}
  .kk-tools {{ display: flex; gap: 10px; align-items: center; }}
  .kk-round {{ width: 44px; height: 44px; border-radius: 12px; border: 1px solid {T['chip_border']};
              background: {T['surface']}; color: {T['text']} !important; display: flex; align-items: center; justify-content: center; }}
  .kk-round:hover {{ border-color: {T['accent']}; }}

  /* 눈에 안 보이는 진짜 버튼을 헤더의 첫 번째 kk-round(모드 전환 아이콘) 위에 정확히 겹쳐서
     클릭만 받게 해요. 안 보이는 버튼이라 Streamlit이 안에 어떤 태그를 만들든 상관없어요. */
  [data-testid="stMainBlockContainer"], .block-container {{ position: relative !important; }}
  .st-key-kk-theme {{ position: absolute !important; top: 22px; right: 172px; width: 44px !important;
      height: 44px !important; z-index: 25; }}
  .st-key-kk-theme button {{ width: 44px !important; height: 44px !important; min-height: 44px !important;
      padding: 0 !important; border: none !important; background: transparent !important;
      opacity: 0 !important; cursor: pointer !important; }}
  @media (max-width: 640px) {{ .st-key-kk-theme {{ top: 14px; right: 178px; }} }}

  /* 히어로 */
  .kk-hero {{ min-height: 500px; padding: 0 64px; display: flex; align-items: center; justify-content: space-between; gap: 40px; }}
  .kk-hero-text {{ width: 660px; max-width: 100%; display: flex; flex-direction: column; gap: 26px; }}
  .kk-badge {{ align-self: flex-start; display: flex; align-items: center; gap: 10px; padding: 8px 14px 8px 10px;
              border: 1px solid {T['chip_border']}; border-radius: 999px; font-size: 13px; font-weight: 500;
              color: {T['badge_text']}; letter-spacing: 0.02em; }}
  .kk-dot {{ width: 8px; height: 8px; border-radius: 999px; background: #9C7EDB; display: inline-block; }}
  .kk-h1 {{ font-family: Rubik, sans-serif !important; font-weight: 700; font-size: 132px; line-height: 0.95;
           letter-spacing: -0.035em; color: {T['text']}; }}
  .kk-sub {{ font-size: 32px; font-weight: 700; letter-spacing: -0.02em; line-height: 1.25; }}
  .kk-desc {{ font-size: 14px; line-height: 1.6; color: {T['muted']} !important; }}
  .kk-btns {{ display: flex; gap: 12px; flex-wrap: wrap; }}
  .kk-btn {{ height: 56px; padding: 0 28px; border-radius: 999px; font-size: 17px; font-weight: 700;
            display: inline-flex; align-items: center; gap: 10px; }}
  .kk .kk-btn.primary {{ background: {T['accent']}; color: {T['accent_text']}; }}
  .kk .kk-btn.secondary {{ background: {T['secondary_bg']}; border: 1px solid {T['secondary_border']};
                          color: {T['secondary_text']}; font-weight: 600; }}
  .kk .kk-btn:hover {{ filter: brightness(1.05); }}
  .kk-vinyl {{ width: 540px; max-width: 100%; flex-shrink: 1; margin-top: 32px; }}
  .kk-spin {{ transform-box: fill-box; transform-origin: center; animation: kkspin 28s linear infinite; }}
  @keyframes kkspin {{ to {{ transform: rotate(360deg); }} }}
  @media (prefers-reduced-motion: reduce) {{ .kk-spin {{ animation: none; }} }}

  /* 섹션 */
  .kk-section {{ padding: 0 64px; display: flex; flex-direction: column; gap: 20px; }}
  .kk-section + .kk-section {{ padding-top: 36px; }}
  .kk-sec-head {{ display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; }}
  .kk-h2 {{ font-size: 24px; font-weight: 700; letter-spacing: -0.01em; }}
  .kk-cap {{ font-size: 14px; color: {T['subtle']}; }}
  .kk-steps {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }}
  .kk-card {{ height: 216px; padding: 26px; border-radius: 20px; background: {T['tint']};
             border: 1px solid {T['tint_border']}; display: flex; flex-direction: column; justify-content: space-between; }}
  .kk-card:hover {{ border-color: {T['accent']}; }}
  .kk-card-top {{ display: flex; justify-content: space-between; align-items: flex-start; }}
  .kk-ibox {{ width: 52px; height: 52px; border-radius: 14px; background: {T['icon_box']}; color: {T['accent']};
             display: flex; align-items: center; justify-content: center; }}
  .kk-num {{ font-family: Rubik, sans-serif; font-size: 16px; font-weight: 700; color: {T['num']}; }}
  .kk-card-title {{ display: flex; align-items: center; justify-content: space-between; font-size: 20px; font-weight: 700;
                   color: {T['text']}; }}
  .kk-card-desc {{ display: block; min-height: 45px; margin-top: 8px; font-size: 15px; line-height: 1.5; color: {T['muted']}; }}

  .kk-recent {{ min-height: 104px; padding: 16px 24px 16px 20px; border-radius: 20px; background: {T['tint']};
               border: 1px solid {T['tint_border']}; display: flex; align-items: center; gap: 22px; flex-wrap: wrap; }}
  .kk-thumb {{ width: 64px; height: 64px; border-radius: 14px; background: {T['icon_box']}; display: flex;
              align-items: center; justify-content: center; flex-shrink: 0; }}
  .kk-recent-body {{ flex: 1 1 320px; display: flex; flex-direction: column; gap: 6px; }}
  .kk-tag {{ padding: 3px 10px; border-radius: 6px; border: 1px solid {T['tint_border']}; font-size: 12px;
            font-weight: 600; color: {T['accent']}; }}
  .kk-status {{ display: flex; align-items: center; gap: 8px; padding: 8px 14px; border-radius: 999px;
               background: {T['accent_soft2']}; font-size: 14px; font-weight: 600; color: {T['accent']}; }}
  .kk .kk-ghost {{ height: 48px; padding: 0 22px; border-radius: 999px; border: 1px solid {T['secondary_border']};
                  background: {T['surface']}; font-size: 15px; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; }}

  /* 준비 중 페이지 */
  .kk-page {{ padding: 56px 64px; display: flex; flex-direction: column; gap: 18px; }}
  .kk-empty {{ margin-top: 12px; padding: 56px; border-radius: 20px; border: 1px dashed {T['tint_border']};
              background: {T['tint']}; color: {T['muted']}; font-size: 16px; line-height: 1.7; }}

  /* Streamlit 기본 글자 스타일(h1·h2·p 크기, 여백, 글씨체) 덮어쓰기 */
  .kk h1, .kk h2, .kk p, .kk span, .kk a, .kk div {{ font-family: 'IBM Plex Sans KR', sans-serif !important; }}
  .kk h1, .kk h2, .kk p {{ margin: 0 !important; padding: 0 !important; scroll-margin: 0 !important; }}
  .kk h1 .kk-anchor, .kk [data-testid="stHeaderActionElements"] {{ display: none !important; }}
  .kk .kk-h1, .kk .kk-h1 span {{ font-family: Rubik, sans-serif !important; font-weight: 700 !important;
                                font-size: 132px !important; line-height: 0.95 !important; letter-spacing: -0.035em !important; }}
  .kk .kk-sub {{ font-size: 32px !important; font-weight: 700 !important; line-height: 1.25 !important;
                letter-spacing: -0.02em !important; color: {T['text']} !important; }}
  .kk .kk-desc {{ font-size: 14px !important; line-height: 1.6 !important; font-weight: 400 !important; }}
  .kk .kk-h2 {{ font-size: 24px !important; font-weight: 700 !important; line-height: 1.3 !important;
               letter-spacing: -0.01em !important; color: {T['text']} !important; }}
  .kk .kk-logo, .kk .kk-logo span, .kk .kk-num {{ font-family: Rubik, sans-serif !important; }}
  .kk .kk-title {{ font-size: 36px !important; }}

  /* 좁은 화면 */
  @media (max-width: 1100px) {{
    .kk-steps {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .kk-hero {{ flex-direction: column; align-items: flex-start; padding-top: 32px; padding-bottom: 32px; }}
    .kk-header {{ height: auto; padding-top: 14px; padding-bottom: 10px; flex-wrap: wrap; row-gap: 10px; }}
    .kk-nav {{ order: 3; width: 100%; overflow-x: auto; white-space: nowrap; }}
    .kk-card {{ height: auto; min-height: 200px; gap: 24px; }}
  }}
  @media (max-width: 640px) {{
    .kk-header, .kk-hero, .kk-section, .kk-page {{ padding-left: 16px; padding-right: 16px; }}
    .kk-steps {{ grid-template-columns: 1fr; }}
    .kk .kk-h1, .kk .kk-h1 span {{ font-size: 72px !important; }}
    .kk .kk-sub {{ font-size: 24px !important; }}
  }}
</style>
"""




# ─────────────────────────────────────────────
# 상단 메뉴
# ─────────────────────────────────────────────
def header_html() -> str:
    nav = "".join(
        (f'<a href="{link(k)}" target="_self" class="on" aria-current="page">{v}</a>' if k == page
         else f'<a href="{link(k)}" target="_self">{v}</a>')
        for k, v in PAGES.items()
    )
    logo_svg = (
        f'<svg width="42" height="42" viewBox="0 0 34 34" aria-hidden="true">'
        f'<circle cx="17" cy="17" r="15.5" fill="{T["surface"]}" stroke="{T["chip_border"]}"/>'
        f'<circle cx="17" cy="17" r="10" fill="none" stroke="{T["chip_border"]}"/>'
        f'<circle cx="17" cy="17" r="5.5" fill="#9C7EDB"/><circle cx="17" cy="17" r="1.6" fill="{T["bg"]}"/>'
        f'<circle cx="29" cy="8" r="3.2" fill="#CC9EB8"/></svg>'
    )
    return f"""
<header class="kk-header">
  <a href="{link('home')}" target="_self" class="kk-logo" aria-label="KKeeper 홈">{logo_svg}
    <span><span style="color:{T['accent']}">KK</span>eeper</span></a>
  <nav class="kk-nav" aria-label="주 메뉴">{nav}</nav>
  <div class="kk-tools">
    <span class="kk-round" aria-hidden="true">{icon('sun' if theme_name == 'dark' else 'moon', 18)}</span>
    <a href="#" class="kk-round" aria-label="검색">{icon('search', 18)}</a>
    <a href="#" class="kk-round" aria-label="내 계정">{icon('user', 18)}</a>
  </div>
</header>"""



def _toggle_theme() -> None:
    # 페이지를 새로 불러오지 않고(같은 세션 안에서) 테마만 바꿔요 → 입력 중이던 값이 안 날아가요
    new = "light" if st.session_state.get("kk_theme", "dark") == "dark" else "dark"
    st.session_state["kk_theme"] = new
    st.query_params["theme"] = new


def render_header() -> None:
    st.markdown(compact(global_css()), unsafe_allow_html=True)
    st.markdown(compact(f'<div class="kk">{header_html()}</div>'), unsafe_allow_html=True)
    label = "라이트 모드로 전환" if theme_name == "dark" else "다크 모드로 전환"
    # 눈에는 안 보이지만 헤더의 아이콘 자리(맨 처음 kk-round) 위에 정확히 겹치는 진짜 버튼.
    # 클릭을 이 버튼이 받고, 화면에 보이는 아이콘은 위 header_html()의 <span>이 담당해요.
    st.button("​", key="kk-theme", on_click=_toggle_theme, help=label)
