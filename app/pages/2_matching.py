"""
KKeeper — 고객 매칭 페이지 (pages/2_matching.py · 주소: /matching)

마케팅 설계(1_marketing.py)에서 넘어온 전략을 바탕으로, 전략에 맞을 것으로 보이는
고객 유형(세그먼트) 후보를 보여주고, 실험에 쓸 유형을 고르게 해요.
시안(Claude Design 캔버스의 MatchingDark/Light.dc.html)과 동일한 구조로 맞췄어요:
카드 안 내용은 통째로 HTML로 그리고, 선택 여부만 카드 아래 별도 컨트롤로 받아요.
지금은 실제 데이터가 연결되어 있지 않아서, 전략 내용을 바탕으로 그럴듯한 예시 유형을
만들어 보여줘요. 데이터가 연결되면 pick_segments()만 실제 매칭 로직으로 바꾸면 돼요.
"""

import hashlib
import random
from html import escape
import sys
from pathlib import Path

import streamlit as st

# ui.py는 app.py와 같은 폴더에 있어요 (pages 폴더 안이 아니에요)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ui  # noqa: E402
from ui import compact

st.set_page_config(page_title="고객 매칭 · KKeeper", layout="wide", initial_sidebar_state="collapsed")
T = ui.init("matching")
theme_name = ui.theme_name

STEP_NAMES = ["마케팅 설계", "고객 매칭", "실험 관리", "라이브러리"]

# 예시 고객 유형 후보 (데이터 연결 전까지 쓰는 자리표시 값)
SEGMENT_POOL = [
    {"name": "장기 미접속 · 개인 요금제", "plan": "개인",
        "trait": "최근 30일 이상 접속 기록이 없고, 과거 평균 청취 시간은 상위권이었던 개인 요금제 이용자예요.",
        "risk": "높음", "tenure": "1년 이상", "last": "30일 이상 미접속"},
    {"name": "요금 부담 신호 · 학생 요금제", "plan": "학생",
        "trait": "학생 요금제 만료가 다가오고, 최근 결제 재시도 이력이 있는 이용자예요.",
        "risk": "중간", "tenure": "3~12개월", "last": "7일 이상 미접속"},
    {"name": "관심 이탈 · 가족 요금제 관리자", "plan": "가족",
        "trait": "가족 요금제 내 활성 인원이 줄고, 관리자 계정의 접속 빈도도 함께 낮아진 이용자예요.",
        "risk": "중간", "tenure": "1년 이상", "last": "14일 이상 미접속"},
    {"name": "신규 이탈 경고 · 가입 초기", "plan": "개인",
        "trait": "가입 3개월 미만이면서 추천 콘텐츠 클릭률이 평균보다 낮은 이용자예요.",
        "risk": "높음", "tenure": "3개월 미만", "last": "7일 이상 미접속"},
    {"name": "해지 철회 후보", "plan": "전체",
        "trait": "최근 해지를 신청해 유예 기간 중이며, 과거 재구독 이력이 있는 이용자예요.",
        "risk": "매우 높음", "tenure": "전체", "last": "전체"},
]


def pick_segments(strategy: dict, n: int = 3) -> list[dict]:
    """전략 내용을 바탕으로 후보 유형을 골라 예시 인원·적합도를 붙여요."""
    seed_src = f"{strategy.get('name','')}|{strategy.get('goal','')}|{strategy.get('kind','')}"
    rng = random.Random(int.from_bytes(hashlib.sha256(seed_src.encode()).digest()[:8], 'big'))
    goal = strategy.get("goal", "")
    pool = list(SEGMENT_POOL)
    if goal == "해지 철회":
        pool.sort(key=lambda s: 0 if "해지" in s["name"] else 1)
    elif goal == "업그레이드":
        pool.sort(key=lambda s: 0 if s["plan"] in ("학생", "가족") else 1)
    elif goal == "재방문 유도":
        pool.sort(key=lambda s: 0 if "미접속" in s["name"] or "관리자" in s["name"] else 1)
    else:
        pool.sort(key=lambda s: 0 if "장기" in s["name"] or "신규" in s["name"] else 1)
    chosen = pool[:n]
    out = []
    for i, s in enumerate(chosen):
        out.append({**s, "id": f"seg{i + 1}", "size": rng.randint(800, 6400),
                    "score": rng.randint(76, 97)})
    out.sort(key=lambda s: -s["score"])
    return out


def match_css() -> str:
    # 좌우 여백은 카드 하나하나가 margin:0 64px으로 직접 갖고, 감싸는 컨테이너에는
    # 위아래 간격(gap)만 준다. 컨테이너에 좌우 padding까지 같이 주면 두 배로 밀리므로 넣지 않는다.
    return f"""
<style>
    div[class*="st-key-kk-body"] {{ padding: 28px 0 64px !important; }}
    div[class*="st-key-kk-body"] > [data-testid="stVerticalBlock"] {{ gap: 0 !important; }}
    .kk-context {{ margin: 0 64px 20px; }}

    /* 전략 요약 띠 */
    .kk-recap {{ padding: 18px 24px; border-radius: 16px;
                background: {T['tint']}; border: 1px solid {T['tint_border']};
                display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }}
    .kk-recap b {{ font-size: 16px; font-weight: 700; color: {T['text']}; }}
    .kk-recap .kk-chip {{ padding: 6px 14px; border-radius: 10px; background: {T['surface']};
                        border: 1px solid {T['tint_border']}; font-size: 13px; font-weight: 600; color: {T['accent']}; }}

    /* 유형 카드 (내용은 통째로 HTML로 그림) */
    div[class*="st-key-kkseg-"] {{ margin: 0 64px 20px !important; padding: 26px 28px 40px !important;
                                    width: calc(100% - 128px) !important; box-sizing: border-box !important;
                                    border-radius: 20px !important; background: {T['surface']};
                                    border: 1px solid {T['border']} !important; position: relative !important;}}
    div[class*="st-key-kkseg-"] > div {{ border: none !important; }}
    div[class*="st-key-kkseg-"] [data-testid="stVerticalBlock"] {{ gap: 0 !important; }}
    div[class*="st-key-kkseg-"] [data-testid="stHorizontalBlock"] {{ align-items: start !important; }}
    .kk-seg-badges {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }}
    .kk-seg-score {{ display: inline-flex; align-items: baseline; gap: 4px; padding: 5px 12px; border-radius: 10px;
                    background: {T['accent_soft']}; color: {T['accent']}; font-weight: 700; font-size: 13px; }}
    .kk-seg-score b {{ font-family: Rubik, sans-serif; font-size: 16px; }}
    .kk-seg-risk {{ padding: 5px 12px; border-radius: 10px; border: 1px solid {T['chip_border']};
                    font-size: 13px; font-weight: 600; color: {T['badge_text']}; }}
    .kk-seg-risk.high {{ border-color: transparent; background: {T['accent_soft']}; color: {T['accent']}; }}
    .kk .kk-seg-name {{ font-size: 20px; font-weight: 700; line-height: 1.3; color: {T['text']}; margin: 0 0 10px !important; }}
    .kk .kk-seg-trait {{ font-size: 15px; line-height: 1.5; color: {T['muted']}; margin: 0 0 14px !important; }}
    .kk-seg-bar {{ height: 6px; border-radius: 999px; background: {T['tint_border']}; overflow: hidden; margin-bottom: 18px; }}
    .kk-seg-bar span {{ display: block; height: 100%; border-radius: 999px; background: {T['accent']}; }}
    .kk-meta {{ margin: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }}
    .kk-meta div {{ display: flex; flex-direction: column; gap: 4px; }}
    .kk-meta dt {{ margin: 0; font-size: 12px; color: {T['subtle']}; }}
    .kk-meta dd {{ margin: 0; font-size: 14px; font-weight: 600; color: {T['text']}; }}
    @media (max-width: 900px) {{ .kk-meta {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}

    /* 스위치는 카드 안의 오른쪽 열에 자연스럽게 배치 */
    div[class*="st-key-kk-toggle-"] [data-testid="stToggle"] label p {{
        display: block !important;
        color: {T['accent']} !important;
        font-size: 13px !important;
        font-weight: 700 !important;
    }}
    div[class*="st-key-kkseg-"] [data-testid="stToggle"] label {{ cursor: pointer; }}
    .kk .kk-demo-note {{ margin: 8px 2px 0 !important; font-size: 12px; line-height: 1.4; color: {T['subtle']}; }}

    /* 아래 이동 버튼 */
    div[class*="st-key-kk-actions"] {{ width: calc(100% - 128px) !important;
                                        box-sizing: border-box !important; margin: 8px 64px 0 !important; }}
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

    .kk-stepper {{ margin: 0; padding: 0; list-style: none; display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }}
    .kk-stepper li.s {{ display: flex; align-items: center; gap: 10px; padding: 8px 16px 8px 8px; border-radius: 999px;
                        border: 1px solid {T['tint_border']}; font-size: 14px; color: {T['subtle']}; }}
    .kk-stepper li.s.on {{ border-color: transparent; background: {T['accent_soft']}; color: {T['accent']}; font-weight: 700; }}
    .kk-stepper li.s i {{ font-style: normal; width: 26px; height: 26px; border-radius: 999px; background: {T['surface']};
                        font-family: Rubik, sans-serif; font-size: 12px; display: flex; align-items: center; justify-content: center; }}
    .kk-stepper li.s.on i {{ background: {T['accent']}; color: {T['accent_text']}; }}
    .kk-stepper li.l {{ width: 12px; height: 1px; background: {T['chip_border']}; }}

    @media (max-width: 1100px) {{
        div[class*="st-key-kk-body"] {{ padding: 24px 0 48px !important; }}
        .kk-context {{ margin: 0 16px 20px; }}
        div[class*="st-key-kkseg-"] {{ width: calc(100% - 32px) !important; margin: 0 16px 20px !important; }}
        div[class*="st-key-kk-actions"] {{ width: calc(100% - 32px) !important; margin: 8px 16px 0 !important; }}
    }}
</style>"""


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
        <h1 class="kk-h2 kk-title" style="font-size:40px">고객 매칭</h1>
        <p class="kk-desc" style="font-size:17px">전략에 맞을 것으로 보이는 고객 유형이에요. 실험에 쓸 유형을 골라 주세요.</p>
    </div>
    <ol class="kk-stepper" aria-label="진행 단계">{''.join(steps)}</ol>
</section>"""


def recap_html(sv: dict) -> str:
    def chip(text):
        return f'<span class="kk-chip">{escape(str(text))}</span>'
    parts = [chip(sv["kind"])] if sv.get("kind") else []
    if sv.get("goal"):
        parts.append(chip(sv["goal"]))
    if sv.get("plans"):
        parts.append(chip("요금제 " + "·".join(sv["plans"])))
    if sv.get("period") and sv["period"] != "전체":
        parts.append(chip(sv["period"]))
    if sv.get("last") and sv["last"] != "전체":
        parts.append(chip(sv["last"]))
    return f'<div class="kk kk-recap"><b>‘{escape(sv["name"])}’ 전략 기준</b>{"".join(parts)}</div>'


def segment_badges_html(seg: dict) -> str:
    risk_cls = "high" if seg["risk"] in ("높음", "매우 높음") else ""
    return f'''<div class="kk kk-seg-badges">
    <span class="kk-seg-score">적합도 <b>{seg['score']}</b>%</span>
    <span class="kk-seg-risk {risk_cls}">이탈 위험도 {escape(seg['risk'])}</span>
    </div>'''


def segment_html(seg: dict) -> str:
    meta = [("예상 인원", f"약 {seg['size']:,}명"), ("이탈 위험도", seg["risk"]),
            ("구독 기간", seg["tenure"]), ("마지막 접속", seg["last"])]
    meta_html = "".join(f"<div><dt>{escape(a)}</dt><dd>{escape(b)}</dd></div>" for a, b in meta)
    return f"""
<div class="kk">
    <h3 class="kk-seg-name">{escape(seg['name'])}</h3>
    <p class="kk-seg-trait">{escape(seg['trait'])}</p>
    <div class="kk-seg-bar"><span style="width:{seg['score']}%"></span></div>
    <dl class="kk-meta">{meta_html}</dl>
</div>"""


def empty_state_html() -> str:
    return '<div class="kk-empty">아직 설계된 전략이 없어요. 먼저 마케팅 설계에서 전략을 만들어 주세요.</div>'


def matching_page() -> None:
    ss = st.session_state
    st.markdown(compact(match_css()), unsafe_allow_html=True)
    st.markdown(compact(f'<div class="kk">{head_html()}</div>'), unsafe_allow_html=True)

    strategy = ss.get("strategy")
    with st.container(key="kk-body"):
        if not strategy:
            strategy = {"name": "장기 미접속", "kind": "콘텐츠 추천", "goal": "이탈 방지",
                        "plans": ["개인", "학생"], "period": "전체", "last": "14일 이상 미접속"}
            preview = True
        else:
            preview = False

        note = ("화면 예시 · 적합도, 예상 인원, 위험도는 실제 데이터와 모델에 연결되기 전까지 예시 값입니다." if preview
                else "현재 고객 유형과 수치는 시연용 예시입니다. 실제 모델 및 고객 데이터 연결 후 교체해야 합니다.")
        st.markdown(compact(f'<div class="kk kk-context">{recap_html(strategy)}<p class="kk-demo-note">{note}</p></div>'),
                    unsafe_allow_html=True)

        if preview:
            segments = [
                {**SEGMENT_POOL[0], "id": "preview1", "score": 92, "size": 2061},
                {**SEGMENT_POOL[3], "id": "preview2", "score": 87, "size": 802},
                {**SEGMENT_POOL[1], "id": "preview3", "score": 83, "size": 1954},
            ]
            ss.setdefault("sel_preview1", True)
        else:
            # 전략이 바뀌면(=마케팅 설계를 새로 하고 왔으면) 예전에 눌러놨던 선택 토글 값이
            # 남아있지 않도록 같이 초기화해요. 세그먼트 id가 seg1/seg2/seg3처럼 고정이라
            # 그냥 두면 이전 전략에서 켜뒀던 토글이 새 전략에도 그대로 켜진 채로 보여요.
            sig = (strategy.get("name"), strategy.get("goal"), strategy.get("kind"))
            if ss.get("kk_matching_sig") != sig:
                ss["kk_matching_sig"] = sig
                for old_seg in ss.get("matching_candidates", []):
                    ss.pop(f"sel_{old_seg['id']}", None)
                ss["matching_candidates"] = pick_segments(strategy)
            segments = ss["matching_candidates"]

        selected_ids = []
        for seg in segments:
            with st.container(key=f"kkseg-{seg['id']}"):
                badges_col, toggle_col = st.columns([10, 2], vertical_alignment="top")
                with badges_col:
                    st.markdown(compact(segment_badges_html(seg)), unsafe_allow_html=True)
                with toggle_col:
                    with st.container(key=f"kk-toggle-{seg['id']}", horizontal=True, horizontal_alignment="right"):
                        on = st.toggle("선택", key=f"sel_{seg['id']}")
                st.markdown(compact(segment_html(seg)), unsafe_allow_html=True)
            if on:
                selected_ids.append(seg["id"])

        with st.container(key="kk-actions"):
            msg = st.empty()
            _, b1, b2 = st.columns([4.3, 0.8, 1.4], gap="small")
            back = b1.button("이전 단계로", key="m_back", use_container_width=True)
            go = b2.button("선택한 유형으로 실험 만들기 →", key="m_go", type="primary", use_container_width=True)

    if back:
        st.switch_page("pages/1_marketing.py")
    if go:
        if preview:
            msg.error("먼저 마케팅 설계에서 전략을 저장해 주세요. 현재 표시된 고객 유형은 시안 예시입니다.")
        elif not selected_ids:
            msg.error("실험에 쓸 고객 유형을 하나 이상 선택해 주세요.")
        else:
            ss["matched_segments"] = [s for s in segments if s["id"] in selected_ids]
            st.switch_page("pages/3_experiments.py")


# ─────────────────────────────────────────────

ui.render_header()
matching_page()
