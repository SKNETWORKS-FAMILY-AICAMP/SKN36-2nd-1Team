"""
KKeeper 공통 UI — 색상 테마, 전역 스타일, 상단 메뉴, 화면 조각(HTML) 도우미

모든 페이지 맨 위에서
    T = ui.init("페이지 키")
    ui.render_header()
를 한 번씩 부르세요.

상단 메뉴는 st.page_link로 만들어서, 페이지를 옮겨도 세션(작성한 전략·매칭 결과 등)이
유지돼요. (예전처럼 <a href>로 옮기면 새로고침이 일어나 세션이 통째로 날아가요.)
단, 입력칸 값 자체는 Streamlit이 페이지를 떠날 때 지우므로, 마케팅 설계는 입력할 때마다
strategy_draft에 따로 저장해 두고 돌아오면 다시 채워요.
"""

from html import escape

import streamlit as st

# ─────────────────────────────────────────────
# 메뉴 (키, 이름, 파일)  · None은 구분선
# ─────────────────────────────────────────────
NAV = [
    ("home", "홈", "app.py"),
    ("dashboard", "현황", "pages/1_dashboard.py"),
    ("model", "모델", "pages/6_model.py"),
    None,
    ("marketing", "1\u00a0\u00a0\u00a0마케팅 설계", "pages/2_marketing.py"),
    ("matching", "2\u00a0\u00a0\u00a0고객 매칭", "pages/3_matching.py"),
    ("experiments", "3\u00a0\u00a0\u00a0실험 관리", "pages/4_experiments.py"),
    ("library", "4\u00a0\u00a0\u00a0라이브러리", "pages/5_library.py"),
]
PAGE_FILES = {item[0]: item[2] for item in NAV if item}

# ─────────────────────────────────────────────
# 색상 토큰 (라이트 / 다크)
# ─────────────────────────────────────────────
THEMES = {
    "light": {
        "bg": "#FAF9FC", "surface": "#FFFFFF", "tint": "#F3EEFD", "tint_border": "#E2D8FA",
        "border": "#E6E2EE", "line": "#E9E6EF", "chip_border": "#DDD8E6", "strong_border": "#CFC8DC",
        "text": "#1C1A22", "text2": "#3E3B47", "muted": "#5F5B6B", "subtle": "#6B6878", "num": "#9A95A8",
        "badge_text": "#55525F",
        "accent": "#6E4FCB", "accent_text": "#FFFFFF", "accent_soft": "#EFE9FC", "accent_soft2": "#E4D9FB",
        "accent_on_soft": "#4F35A8", "accent_line": "#B9A6EE",
        "nav_active": "#EEEAF7", "secondary_bg": "#F3EEFD", "secondary_text": "#4F35A8",
        "secondary_border": "#E2D8FA", "icon_box": "#FFFFFF", "input_bg": "#F6F4FA",
        "tip_text": "#4F35A8", "placeholder": "#9A95A8", "bar": "#DDD8E6",
        "good_bg": "#E6F6EC", "good_text": "#1F7A45", "warn_bg": "#FDF3DF", "warn_text": "#8A5F08",
        "warn_line": "#EBCF8F", "bad_bg": "#FBEAEA", "bad_text": "#B23A32",
        "seg": ["#9C7EDB", "#CC9EB8", "#93BBA3", "#8A9BCC"],
        "seg_bg": ["#EFE9FC", "#F8E9F1", "#E6F3EC", "#E8ECF7"],
        "avatar": [("#EFE9FC", "#9C7EDB"), ("#F8E9F1", "#CC9EB8"), ("#E6F3EC", "#93BBA3"), ("#E8ECF7", "#8A9BCC")],
        "hole": "#FAF9FC", "halo": ("#8B6AE0", 0.68, 0.56),
    },
    "dark": {
        "bg": "#100F13", "surface": "#242229", "tint": "#28252F", "tint_border": "#484352",
        "border": "#403C49", "line": "#37333F", "chip_border": "#504A5A", "strong_border": "#625B70",
        "text": "#F7F5F8", "text2": "#E0DCE4", "muted": "#C3BEC9", "subtle": "#AAA4B2", "num": "#918A9B",
        "badge_text": "#DDD8E2",
        "accent": "#B59AEC", "accent_text": "#1A1428", "accent_soft": "#332648", "accent_soft2": "#3A2B52",
        "accent_on_soft": "#E1D7F7", "accent_line": "#8063D1",
        "nav_active": "#302D38", "secondary_bg": "#24212B", "secondary_text": "#F4F1F6",
        "secondary_border": "#5B5567", "icon_box": "#302A42", "input_bg": "#211F26",
        "tip_text": "#E1D7F7", "placeholder": "#AAA3B3", "bar": "#4A4553",
        "good_bg": "#22392A", "good_text": "#8AE8B0", "warn_bg": "#3A311F", "warn_text": "#F1CC7F",
        "warn_line": "#8A6F2A", "bad_bg": "#3A2528", "bad_text": "#F19B95",
        "seg": ["#9C7EDB", "#CC9EB8", "#93BBA3", "#8A9BCC"],
        "seg_bg": ["#2B203E", "#3A2434", "#20372E", "#222A40"],
        "avatar": [("#2B203E", "#9C7EDB"), ("#3A2434", "#CC9EB8"), ("#20372E", "#93BBA3"), ("#222A40", "#8A9BCC")],
        "hole": "#100F13", "halo": ("#9C7EDB", 0.22, 0.72),
    },
}

# 버튼·차트를 칸 너비에 맞추는 인자. Streamlit 1.50부터 use_container_width 대신 width="stretch"를 써요.
def _version() -> tuple:
    try:
        return tuple(int(x) for x in st.__version__.split(".")[:2])
    except (AttributeError, ValueError):
        return (1, 50)


WIDE = {"width": "stretch"} if _version() >= (1, 50) else {"use_container_width": True}

# init()이 채우는 현재 상태
page = "home"
theme_name = "dark"
T = THEMES[theme_name]


def init(active_page: str) -> dict:
    """현재 페이지와 테마를 정하고 색상 토큰을 돌려줘요. 테마는 세션과 주소의 ?theme= 에 저장돼요."""
    global page, theme_name, T
    page = active_page
    ss = st.session_state
    th = ss.get("kk_theme") or st.query_params.get("theme") or "dark"
    theme_name = th if th in THEMES else "dark"
    ss["kk_theme"] = theme_name
    T = THEMES[theme_name]
    return T


def compact(html: str) -> str:
    """마크다운이 들여쓰기·빈 줄을 코드 블록으로 읽지 않도록 한 덩어리로 정리."""
    return "\n".join(line.strip() for line in html.splitlines() if line.strip())


def html(markup: str) -> None:
    st.markdown(compact(markup), unsafe_allow_html=True)


esc = escape


# ─────────────────────────────────────────────
# 숫자 표시
# ─────────────────────────────────────────────
def pval(p) -> str:
    try:
        p = float(p)
    except (TypeError, ValueError):
        return "-"
    return "< 0.0001" if p < 0.0001 else f"{p:.4f}"


def pct(x, digits: int = 1) -> str:
    try:
        return f"{float(x) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "-"


def num(x, digits: int = 0) -> str:
    try:
        return f"{float(x):,.{digits}f}"
    except (TypeError, ValueError):
        return "-"


# ─────────────────────────────────────────────
# 아이콘
# ─────────────────────────────────────────────
def icon(name: str, size: int = 20, stroke: str = "currentColor", width: float = 2) -> str:
    paths = {
        "pencil": '<path d="M4 20h4L19 9l-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/>',
        "grid": '<circle cx="7" cy="7" r="3"/><circle cx="17" cy="7" r="3"/><circle cx="7" cy="17" r="3"/><circle cx="17" cy="17" r="3" fill="currentColor"/>',
        "split": '<path d="M12 3v6"/><path d="M12 9l-6 6v6"/><path d="M12 9l6 6v6"/>',
        "books": '<path d="M5 4h4v16H5z"/><path d="M10 4h4v16h-4z"/><path d="M15.5 5.5l3.5-1 3 14.5-3.5 1z"/>',
        "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
        "check": '<path d="M5 12l5 5 9-10"/>',
        "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
    }
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{stroke}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{paths[name]}</svg>')


def logo_svg(size: int = 36) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 34 34" aria-hidden="true">'
            f'<circle cx="17" cy="17" r="15.5" fill="{T["surface"]}" stroke="{T["chip_border"]}"/>'
            f'<circle cx="17" cy="17" r="10" fill="none" stroke="{T["chip_border"]}"/>'
            f'<circle cx="17" cy="17" r="5.5" fill="#9C7EDB"/><circle cx="17" cy="17" r="1.6" fill="{T["bg"]}"/>'
            f'<circle cx="29" cy="8" r="3.2" fill="#CC9EB8"/></svg>')


# ─────────────────────────────────────────────
# 전역 스타일
# ─────────────────────────────────────────────
def global_css() -> str:
    return f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=Rubik:wght@600;700&display=swap">
<style>
  header[data-testid="stHeader"], footer, #MainMenu, [data-testid="stToolbar"],
  [data-testid="stDecoration"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
  .stApp {{ background: {T['bg']}; }}
  .block-container {{ max-width: 1440px; padding: 0 !important; }}
  [data-testid="stVerticalBlock"] {{ gap: 0; }}
  html, body, .stApp, label, input, textarea, button {{
      font-family: 'IBM Plex Sans KR', sans-serif !important; color: {T['text']}; }}
  .stMarkdown, .stMarkdown p {{ font-family: 'IBM Plex Sans KR', sans-serif !important; }}
  /* Streamlit이 마크다운 블록 아래에 붙이는 음수 여백 때문에 요소가 겹치지 않게 */
  .stMarkdown, [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] > *,
  [data-testid="stMarkdownContainer"] > *:last-child {{ margin-bottom: 0 !important; }}
  .kk, .kk * {{ box-sizing: border-box; }}
  .kk h1, .kk h2, .kk h3, .kk p {{ margin: 0 !important; padding: 0 !important; }}
  .kk [data-testid="stHeaderActionElements"], .kk .kk-anchor {{ display: none !important; }}
  .kk a {{ color: inherit; text-decoration: none; }}
  .kk-num-font, .kk .kk-num-font {{ font-family: Rubik, 'IBM Plex Sans KR', sans-serif !important; }}

  /* ── 상단 메뉴 ── */
  /* 홈과 모든 하위 페이지가 동일한 88px 헤더 및 구분선 기준을 사용 */
  .st-key-kk-head {{
      height: 88px !important; min-height: 88px !important;
      padding: 0 48px !important; position: relative; border-bottom: none;
  }}
  .st-key-kk-head::after {{
      content: ""; position: absolute; left: 48px; right: 48px; bottom: 0;
      height: 1px; background: {T['line']};
  }}
  .st-key-kk-head > div > [data-testid="stVerticalBlock"],
  .st-key-kk-head [data-testid="stHorizontalBlock"] {{
      min-height: 88px !important; align-items: center !important;
  }}
  .st-key-kk-head [data-testid="stHorizontalBlock"] {{ gap: 4px !important; }}
  .st-key-kk-head [data-testid="stColumn"] {{ display: flex; align-items: center; }}
  .st-key-kk-head [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child {{
      position: relative; top: -8px;
  }}
  .st-key-kk-head [data-testid="stColumn"] > div {{ width: 100%; }}
  .st-key-kk-head [data-testid="stPageLink"] a {{
      min-height: 44px; display: flex; align-items: center;
  }}
  .kk-logo {{ display: flex; align-items: center; gap: 12px; font-family: Rubik, sans-serif !important;
             height: 44px; line-height: 1; font-weight: 700; font-size: 26px; letter-spacing: -0.02em; color: {T['text']}; }}
  .kk-logo svg {{ display: block; flex: 0 0 auto; }}
  .kk-logo span {{ font-family: Rubik, sans-serif !important; }}
  /* 로고를 덮는 투명한 페이지 링크: 기존 페이지 전환과 세션 상태 유지 */
  .st-key-kk-logo-link {{ position: relative; min-height: 44px; cursor: pointer; }}
  .st-key-kk-logo-link [data-testid="stVerticalBlock"] {{ position: relative; min-height: 44px; }}
  .st-key-kk-logo-link [data-testid="stElementContainer"]:has(.kk-logo) {{ pointer-events: none; }}
  .st-key-kk-logo-link [data-testid="stElementContainer"]:has([data-testid="stPageLink"]) {{
      position: absolute !important; inset: 0 !important; z-index: 10;
      width: 100% !important; height: 44px !important;
  }}
  .st-key-kk-logo-link [data-testid="stPageLink"],
  .st-key-kk-logo-link [data-testid="stPageLink"] a {{
      width: 100% !important; height: 44px !important; min-height: 44px !important;
  }}
  .st-key-kk-logo-link [data-testid="stPageLink"] a {{ opacity: 0 !important; cursor: pointer !important; }}
  .st-key-kk-head [data-testid="stPageLink"] a, .st-key-kk-head a[data-testid="stPageLink-NavLink"] {{
      justify-content: center; padding: 8px 12px !important; border-radius: 999px !important; background: transparent !important; }}
  .st-key-kk-head [data-testid="stPageLink"] a p, .st-key-kk-head a[data-testid="stPageLink-NavLink"] p,
  .st-key-kk-head [data-testid="stPageLink"] a span {{ font-size: 14px !important; font-weight: 500 !important;
      color: {T['muted']} !important; white-space: nowrap; }}
  .st-key-kk-head [data-testid="stPageLink"] a:hover {{ background: {T['nav_active']} !important; }}
  .st-key-kk-head .st-key-kk-nav-{page} [data-testid="stPageLink"] a,
  .st-key-kk-head a[aria-current="page"] {{
      background: {T['accent_soft']} !important;
      box-shadow: inset 0 0 0 1px {T['accent_line']} !important;
  }}
  .st-key-kk-head .st-key-kk-nav-{page} [data-testid="stPageLink"] a p,
  .st-key-kk-head .st-key-kk-nav-{page} [data-testid="stPageLink"] a span,
  .st-key-kk-head a[aria-current="page"] p,
  .st-key-kk-head a[aria-current="page"] span {{
      color: {T['accent_on_soft']} !important;
      font-weight: 700 !important;
  }}
  .st-key-kk-theme button {{ width: 44px; height: 44px; min-height: 44px; padding: 0 !important; border-radius: 12px !important;
      border: 1px solid {T['chip_border']} !important; background: {T['surface']} !important; color: {T['text']} !important;
      display: flex !important; align-items: center !important; justify-content: center !important; gap: 0 !important; }}
  .st-key-kk-theme button [data-testid="stMarkdownContainer"] {{ display: none !important; }}
  .st-key-kk-theme button span, .st-key-kk-theme button [data-testid="stIconMaterial"] {{ margin: 0 !important; }}
  .kk-nav-sep {{ width: 1px; height: 18px; background: {T['chip_border']}; margin: auto; transform: translate(-14px, 0px); }}

  /* ── 본문 ── */
  .st-key-kk-body {{ padding: 24px 48px 56px; }}
  .st-key-kk-body > div > [data-testid="stVerticalBlock"], .st-key-kk-body [data-testid="stVerticalBlock"] {{ gap: 16px; }}
  .st-key-kk-body [data-testid="stHorizontalBlock"] {{ gap: 16px !important; }}
  .kk-eyebrow {{ font-size: 12px; font-weight: 700; color: {T['subtle']}; letter-spacing: .05em; }}
  .kk .kk-title, h1.kk-title {{ font-size: 30px !important; font-weight: 700 !important; letter-spacing: -0.02em;
      line-height: 1.3 !important; color: {T['text']} !important; }}
  .kk .kk-lead, p.kk-lead {{ margin-top: 8px !important; padding-bottom: 16px !important;font-size: 14px !important; line-height: 1.6 !important; color: {T['muted']} !important; }}
  .kk h1, .kk h2, .kk h3 {{ font-family: 'IBM Plex Sans KR', sans-serif !important; }}
  .kk-card {{ padding: 22px 24px; border: 1px solid {T['border']}; border-radius: 18px; background: {T['surface']}; }}
  .kk-card-title {{ font-size: 16px; font-weight: 700; color: {T['text']}; }}
  .kk-card-note {{ font-size: 12px; color: {T['muted']}; margin-top: 4px; line-height: 1.5; }}
  .kk-cap {{ font-size: 12px; color: {T['subtle']}; line-height: 1.55; }}
  .kk-secnum {{ font-family: Rubik, sans-serif !important; font-weight: 700; color: {T['num']}; margin-right: 10px; }}
  .kk-sechead {{ display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }}
  .kk-sectitle {{ font-size: 17px; font-weight: 700; }}
  .kk-kpi-label {{ font-size: 12px; font-weight: 600; color: {T['muted']}; }}
  .kk-kpi-val {{ font-family: Rubik, 'IBM Plex Sans KR', sans-serif !important; font-size: 26px; font-weight: 700; margin-top: 6px; }}
  .kk-kpi-unit {{ font-size: 14px; font-weight: 500; color: {T['muted']}; font-family: 'IBM Plex Sans KR', sans-serif !important; }}
  .kk-kpi-help {{ font-size: 12px; color: {T['subtle']}; margin-top: 6px; }}
  .kk-strip {{ display: flex; align-items: stretch; border: 1px solid {T['border']}; border-radius: 18px; background: {T['surface']}; overflow: hidden; }}
  .kk-strip > div {{ flex: 1; padding: 16px 22px; }}
  .kk-strip > span {{ width: 1px; background: {T['line']}; }}
  .kk-badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; font-size: 12px;
              font-weight: 700; white-space: nowrap; }}
  .kk-badge.accent {{ background: {T['accent_soft']}; color: {T['accent_on_soft']}; }}
  .kk-badge.good {{ background: {T['good_bg']}; color: {T['good_text']}; }}
  .kk-badge.warn {{ background: {T['warn_bg']}; color: {T['warn_text']}; }}
  .kk-badge.bad {{ background: {T['bad_bg']}; color: {T['bad_text']}; }}
  .kk-badge.neutral {{ border: 1px solid {T['chip_border']}; color: {T['badge_text']}; }}
  .kk-track {{ height: 8px; border-radius: 999px; background: {T['line']}; display: flex; overflow: hidden; }}
  .kk-track > span {{ border-radius: 999px; display: block; }}
  .kk-dot {{ width: 8px; height: 8px; border-radius: 999px; display: inline-block; flex-shrink: 0; }}
  .kk-tip {{ padding: 14px 16px; border-radius: 12px; background: {T['accent_soft']}; color: {T['accent_on_soft']};
            font-size: 13px; line-height: 1.6; }}
    .kk-warnbox {{ padding: 14px 16px; border-radius: 12px; background: {T['warn_bg']} !important; color: {T['warn_text']} !important; border: 1px solid {T['warn_line']}; font-size: 13px; line-height: 1.6;}}
    .kk-warnbox, .kk-warnbox * {{ color: {T['warn_text']} !important; }}
  .kk-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  .kk-table th {{ text-align: left; font-size: 12px; font-weight: 500; color: {T['subtle']}; padding: 8px 10px;
                 border-bottom: 1px solid {T['line']}; }}
  .kk-table td {{ padding: 10px 10px; border-bottom: 1px solid {T['line']}; color: {T['text']}; }}
  .kk-table tr:last-child td {{ border-bottom: none; }}
  .kk-table .r {{ text-align: right; }}
  .kk-table .num {{ font-family: Rubik, 'IBM Plex Sans KR', sans-serif !important; }}

  /* 작업 단계 · 진행 중인 작업 */
  .kk-steps {{ display: flex; align-items: center; gap: 12px; padding-bottom: 16px; }}
  .kk-step {{ display: flex; align-items: center; gap: 10px; font-size: 14px; color: {T['subtle']}; white-space: nowrap; }}
  .kk-step i {{ font-style: normal; width: 28px; height: 28px; border-radius: 999px; border: 1px solid {T['chip_border']};
               font-family: Rubik, sans-serif; font-weight: 700; font-size: 13px; display: flex; align-items: center; justify-content: center; }}
  .kk-step.on, .kk-step[aria-current="step"] {{ color: {T['accent_on_soft']} !important; font-weight: 700 !important; }}
  .kk-step.on i, .kk-step[aria-current="step"] i {{
      background: {T['accent']} !important; border-color: {T['accent']} !important; color: {T['accent_text']} !important; }}
  .kk-step.done {{ color: {T['muted']} !important; }}
  .kk-step.done i {{
      background: {T['accent_soft']} !important; border-color: {T['accent_line']} !important; color: {T['accent_on_soft']} !important; }}
  .kk-step-line {{ flex-grow: 1; height: 1px; background: {T['border']}; }}
  .kk-step-line.done {{ background: {T['accent_line']}; }}
  .kk-context-wrap {{ display: flow-root !important; padding: 1px 0 !important; }}
  .kk-context-wrap .kk-context {{ margin: 20px 0 28px !important; }}
  .kk-context {{ margin-top: 0; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 12px 18px;
                border: 1px solid {T['border']}; border-radius: 14px; background: {T['surface']}; }}
  .kk-chip {{ padding: 6px 12px; border-radius: 999px; font-size: 13px; }}
  .kk-chip.on {{ background: {T['accent_soft']}; color: {T['accent_on_soft']}; }}
  .kk-chip.off {{ border: 1px dashed {T['chip_border']}; color: {T['subtle']}; }}

  /* ── Streamlit 입력 요소 ──
     Streamlit 버전마다 안쪽 구조가 달라서, 위젯 틀 안의 모든 요소(라벨 제외)에 색을 입혀요. */
  [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label {{ font-size: 13px !important; font-weight: 600 !important;
      color: {T['text2']} !important; }}
  :is([data-testid="stTextInput"], [data-testid="stTextArea"], [data-testid="stSelectbox"], [data-testid="stMultiSelect"],
      [data-testid="stNumberInput"], [data-testid="stDateInput"])
      *:not([data-testid="stWidgetLabel"]):not([data-testid="stWidgetLabel"] *):not(svg):not(svg *) {{
      background-color: {T['input_bg']} !important; color: {T['text']} !important; }}
  :is([data-testid="stTextInput"], [data-testid="stTextArea"], [data-testid="stSelectbox"], [data-testid="stMultiSelect"],
      [data-testid="stNumberInput"], [data-testid="stDateInput"]) [data-baseweb] {{
      border-color: {T['chip_border']} !important; border-radius: 12px !important; overflow: hidden; }}
  :is([data-testid="stTextInput"], [data-testid="stTextArea"], [data-testid="stSelectbox"], [data-testid="stNumberInput"],
      [data-testid="stDateInput"]) svg {{ fill: {T['muted']}; color: {T['muted']}; }}
  input::placeholder, textarea::placeholder {{ color: {T['placeholder']} !important; opacity: 1; }}
  [data-testid="stPopoverBody"], [data-testid="stPopoverBody"] > div {{
      background-color: {T['surface']} !important; color: {T['text']} !important; }}
  [data-testid="stPopoverBody"] :is(h1, h2, h3, p, label, span) {{
      color: {T['text']} !important; }}
  [data-testid="stPopoverBody"] [data-testid="stCheckbox"] p {{
      color: {T['text2']} !important; }}
  [role="listbox"], [role="listbox"] * {{
      background-color: {T['surface']} !important; color: {T['text']} !important; }}
  [role="listbox"] [role="option"]:hover, [role="listbox"] [aria-selected="true"] {{ background-color: {T['nav_active']} !important; }}
  [data-testid="stFileUploaderDropzone"], [data-testid="stFileUploaderDropzone"] * {{ background-color: {T['input_bg']} !important; color: {T['text2']} !important; }}
  /* Streamlit 1.62 st.dialog 모달 */
  [data-testid="stDialog"] section[role="dialog"] {{
      background-color: {T['surface']} !important; color: {T['text']} !important;
      padding: 24px !important; }}
  /* 삭제 확인 모달: 제목과 본문 사이의 과도한 여백 제거 */
  [data-testid="stDialog"] [slot="title"] {{
      margin: 0 0 12px !important; padding: 0 !important; }}
  [data-testid="stDialog"] [data-testid="stVerticalBlock"] {{
      gap: 12px !important; }}
  [data-testid="stDialog"] [data-testid="stAlert"] {{
      margin: 0 !important; padding: 12px 16px !important; }}
  [data-testid="stDialog"] [data-testid="stCheckbox"] {{
      margin: 0 !important; }}
  [data-testid="stDialog"] [data-testid="stButton"] {{
      margin: 0 !important; }}
  [data-testid="stDialog"] [slot="title"],
  [data-testid="stDialog"] [slot="title"] *,
  [data-testid="stDialog"] :is(p, label, span) {{
      color: {T['text']} !important; }}
  [data-testid="stDialog"] [data-testid="stCheckbox"] p {{
      color: {T['text2']} !important; }}
  [data-testid="stDialog"] button[aria-label="Close"] {{
      color: {T['text']} !important; background: transparent !important; }}
  [data-testid="stDialog"] button[aria-label="Close"] svg {{
      color: {T['text']} !important; fill: none !important; }}
  /* 알약 선택(st.pills) — 버전에 따라 이름이 달라서 여러 방식으로 지정 */
  [data-testid="stButtonGroup"] button, button[kind="pills"], button[kind="pillsActive"],
  button[data-testid="stBaseButton-pills"], button[data-testid="stBaseButton-pillsActive"] {{
      border-radius: 999px !important; min-height: 38px; padding: 0 14px !important; margin: 2px 4px 2px 0 !important;
      background: {T['input_bg']} !important; border: 1px solid {T['chip_border']} !important; box-shadow: none !important; }}
  [data-testid="stButtonGroup"] button *, button[kind="pills"] *, button[data-testid="stBaseButton-pills"] * {{
      color: {T['text2']} !important; background: transparent !important; }}
  [data-testid="stButtonGroup"] button:hover {{ border-color: {T['accent']} !important; }}
  [data-testid="stButtonGroup"] button:is([aria-checked="true"], [aria-pressed="true"], [kind$="Active"], [data-testid$="Active"]),
  button[kind="pillsActive"], button[data-testid="stBaseButton-pillsActive"] {{
      background: {T['accent_soft']} !important; border: 1px solid {T['accent']} !important; }}
  [data-testid="stButtonGroup"] button:is([aria-checked="true"], [aria-pressed="true"], [kind$="Active"], [data-testid$="Active"]) *,
  button[kind="pillsActive"] *, button[data-testid="stBaseButton-pillsActive"] * {{
      color: {T['accent_on_soft']} !important; font-weight: 700 !important; }}
  [data-testid="stBaseButton-primary"] {{ background: {T['accent']} !important; border: none !important; border-radius: 999px !important;
      min-height: 46px; padding: 0 22px !important; }}
  [data-testid="stBaseButton-primary"] p {{ color: {T['accent_text']} !important; font-weight: 700 !important; font-size: 15px !important; }}
  [data-testid="stBaseButton-secondary"] {{ background: transparent !important; border: 1px solid {T['strong_border']} !important;
      border-radius: 999px !important; min-height: 44px; }}
  [data-testid="stBaseButton-secondary"] p {{ color: {T['text']} !important; font-weight: 600 !important; }}
  [data-testid="stBaseButton-secondary"]:hover {{ border-color: {T['accent']} !important; }}
  [data-testid="stDownloadButton"] button {{ border-radius: 999px !important; }}
  [data-testid="stExpander"] details {{ border: 1px solid {T['border']} !important; border-radius: 14px !important;
      background: {T['surface']} !important; overflow: hidden; }}
  [data-testid="stExpander"] summary {{ background: {T['surface']} !important; color: {T['text']} !important; }}
  [data-testid="stExpander"] summary:hover {{ background: {T['nav_active']} !important; }}
  [data-testid="stExpander"] summary p, [data-testid="stExpander"] summary span {{
      font-weight: 600 !important; color: {T['text']} !important; }}
  [data-testid="stExpander"] summary svg {{ fill: {T['text']} !important; color: {T['text']} !important; }}
  [data-testid="stSlider"] [role="slider"] {{ background: {T['accent']} !important; }}
  [data-testid="stAlert"] {{ border-radius: 12px !important; }}
  .stCheckbox p, [data-testid="stToggle"] p, [data-testid="stRadio"] p {{ color: {T['text2']} !important; }}
  div[data-testid="stVegaLiteChart"], .vega-embed {{ background: transparent !important; }}

  /* 카드처럼 보이는 Streamlit 컨테이너: key를 kkbox- 로 시작하게 지으면 돼요 */
  div[class*="st-key-kkbox-"] {{ padding: 22px 24px !important; border: 1px solid {T['border']} !important;
      border-radius: 18px !important; background: {T['surface']} !important; }}
  div[class*="st-key-kkbox-"] [data-testid="stVerticalBlock"] {{ gap: 14px; }}
  div[class*="st-key-kkfoot"] {{ padding: 14px 20px !important; border: 1px solid {T['border']} !important;
      border-radius: 18px !important; background: {T['surface']} !important; margin-top: 8px; }}

  @media (max-width: 1100px) {{
    .st-key-kk-head, .st-key-kk-body {{ padding-left: 16px; padding-right: 16px; }}
    .kk-steps .kk-step span {{ display: none; }}
  }}  
    /* KKeeper 로고 세로 위치 조정 */
    .st-key-kk-head .st-key-kk-logo-link {{
        transform: translateY(10px) !important;
    }}

    /* 고객 매칭 분석 카드 높이 통일 */
    .st-key-kkbox-why,
    .st-key-kkbox-top {{
        min-height: 480px !important;
        height: 540px !important;
        box-sizing: border-box !important;
    }}
    /* 실험 선택 박스 배경색 */
    .st-key-exp_pick [data-baseweb="select"],
    .st-key-exp_pick [data-baseweb="select"] > div,
    .st-key-exp_pick [data-baseweb="select"] > div * {{
        background-color: #302D38 !important;
        color: #EFEFEF !important;
    }}

    .st-key-exp_pick [data-baseweb="select"] > div {{
        border: 1px solid #504A5D !important;
        border-radius: 12px !important;
    }}

    .st-key-exp_pick [data-baseweb="select"] svg {{
        background: transparent !important;
        fill: #B8B2C4 !important;
    }}
</style>
"""


# ─────────────────────────────────────────────
# 상단 메뉴
# ─────────────────────────────────────────────
def _toggle_theme() -> None:
    new = "light" if st.session_state.get("kk_theme", "dark") == "dark" else "dark"
    st.session_state["kk_theme"] = new
    st.query_params["theme"] = new


def render_header() -> None:
    st.markdown(compact(global_css()), unsafe_allow_html=True)
    widths = [2.1] + [(0.12 if item is None else (1.05 if item[1][0].isdigit() else 0.62)) for item in NAV] + [0.5]
    with st.container(key="kk-head"):
        cols = st.columns(widths, vertical_alignment="center")
        with cols[0]:
            with st.container(key="kk-logo-link"):
                st.markdown(
                    compact(f'<div class="kk"><div class="kk-logo">{logo_svg()}'
                            f'<span><span style="color:{T["accent"]}">KK</span>eeper</span></div></div>'),
                    unsafe_allow_html=True,
                )
                st.page_link(PAGE_FILES["home"], label="KKeeper 홈으로 이동")
        for col, item in zip(cols[1:-1], NAV):
            with col:
                if item is None:
                    st.markdown('<div class="kk-nav-sep"></div>', unsafe_allow_html=True)
                    continue
                key, label, path = item
                with st.container(key=f"kk-nav-{key}"):
                    st.page_link(path, label=label)
        with cols[-1]:
            dark = theme_name == "dark"
            st.button("​", key="kk-theme", on_click=_toggle_theme,
                      icon=":material/light_mode:" if dark else ":material/dark_mode:",
                      help="라이트 모드로 전환" if dark else "다크 모드로 전환")


# ─────────────────────────────────────────────
# 화면 조각
# ─────────────────────────────────────────────
def page_title(title: str, lead: str = "", eyebrow: str = "") -> str:
    eb = f'<div class="kk-eyebrow" style="margin-bottom:8px">{eyebrow}</div>' if eyebrow else ""
    ld = f'<p class="kk-lead">{lead}</p>' if lead else ""
    return f'<div class="kk">{eb}<h1 class="kk-title">{title}</h1>{ld}</div>'


def steps_html(active: int) -> str:
    """1~4단계 진행 표시. active보다 앞 단계는 완료 표시."""
    from common.constants import STEP_NAMES

    parts = []
    for i, name in enumerate(STEP_NAMES, start=1):
        if i > 1:
            parts.append(f'<span class="kk-step-line{" done" if i <= active else ""}"></span>')
        if i < active:
            parts.append(f'<span class="kk-step done"><i>{icon("check", 14, "currentColor", 3)}</i><span>{name}</span></span>')
        elif i == active:
            parts.append(f'<span class="kk-step on" aria-current="step"><i>{i}</i><span>{name}</span></span>')
        else:
            parts.append(f'<span class="kk-step"><i>{i}</i><span>{name}</span></span>')
    return f'<nav class="kk kk-steps" aria-label="작업 단계">{"".join(parts)}</nav>'


def context_html(strategy: dict | None, target: str | None, experiment: str | None) -> str:
    """진행 중인 작업: 전략 › 대상 › 실험."""
    def chip(label, value, fallback):
        if value:
            return f'<span class="kk-chip on">{label} · {esc(value)}</span>'
        return f'<span class="kk-chip off">{label} · {fallback}</span>'

    s_value = None
    if strategy:
        s_value = f"{strategy.get('name') or '이름 없음'} · {strategy.get('kind', '')}"
    arrow = f'<span style="color:{T["num"]}">›</span>'
    # 위(단계 표시)·아래(페이지 제목)와 띄우는 여백.
    # Streamlit이 바깥 margin을 지우므로 안쪽 상자에 margin을 주고, 바깥 상자는 flow-root로 그 여백을 안에 가둬요.
    return (f'<div class="kk" style="padding:8px 0 16px"><div class="kk-context">'
            f'<span class="kk-eyebrow" style="margin-right:6px">진행 중인 작업</span>'
            f'{chip("전략", s_value, "작성 중")}{arrow}{chip("대상", target, "매칭 전")}{arrow}'
            f'{chip("실험", experiment, "설계 전")}</div></div>')


def badge(text: str, kind: str = "accent") -> str:
    return f'<span class="kk-badge {kind}">{esc(str(text))}</span>'


def track(share: float, color: str | None = None, height: int = 8) -> str:
    w = max(0.0, min(1.0, float(share or 0))) * 100
    return (f'<span class="kk-track" style="height:{height}px; flex:1 1 auto; min-width:60px"><span style="width:{w:.1f}%; '
            f'background:{color or T["accent"]}"></span></span>')


def kpi(label: str, value: str, help_text: str = "", color: str | None = None) -> str:
    style = f' style="color:{color}"' if color else ""
    hp = f'<div class="kk-kpi-help">{help_text}</div>' if help_text else ""
    return f'<div><div class="kk-kpi-label">{label}</div><div class="kk-kpi-val"{style}>{value}</div>{hp}</div>'


def table(headers: list[str], rows: list[list[str]], right: set[int] | None = None) -> str:
    right = right or set()
    th = "".join(f'<th class="{"r" if i in right else ""}">{h}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td class="{"r num" if i in right else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>"
        for r in rows
    )
    return f'<table class="kk-table"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'


def seg_color(name: str) -> str:
    from common.constants import seg_index

    return T["seg"][seg_index(name) - 1]


def show_missing_files(error: Exception) -> None:
    """데이터·모델 파일이 없을 때 공통 안내."""
    st.error("필수 데이터 파일이 없습니다. 아래 경로를 확인하십시오.")
    st.code(str(error))
    st.caption("샘플 데이터 확인: 프로젝트 폴더에서 `python tools/make_sample_data.py`를 실행하십시오.")


def altair_theme(chart):
    """Altair 차트를 현재 테마 색으로 맞춰요."""
    return (
        chart.properties(background="transparent")
        .configure_view(strokeOpacity=0)
        .configure_axis(domainColor=T["border"], gridColor=T["line"], gridDash=[3, 4], labelColor=T["muted"],
                        labelFont="IBM Plex Sans KR", labelFontSize=11, tickColor=T["border"], titleColor=T["muted"],
                        titleFont="IBM Plex Sans KR", titleFontSize=12, titleFontWeight=500)
        .configure_legend(labelColor=T["muted"], labelFont="IBM Plex Sans KR", title=None, orient="bottom")
        .configure_text(font="IBM Plex Sans KR", color=T["text"])
    )


def choose(label: str, options: list, key: str, default=None, multi: bool = False, label_visibility: str = "visible",
           format_func=str):
    """알약 모양 선택. 오래된 Streamlit(1.40 미만)에서는 라디오·멀티셀렉트로 대신 보여줘요.
    기본값은 위젯 인자 대신 session_state에 넣어요 (버전에 따라 첫 클릭이 사라지는 문제 방지)."""
    ss = st.session_state
    if key not in ss:
        ss[key] = default
    kwargs = {"key": key, "label_visibility": label_visibility, "format_func": format_func}
    if hasattr(st, "pills"):
        return st.pills(label, options, selection_mode="multi" if multi else "single", **kwargs)
    if multi:
        return st.multiselect(label, options, **kwargs)
    if ss.get(key) not in options:
        ss[key] = options[0]
    return st.radio(label, options, horizontal=True, **kwargs)
