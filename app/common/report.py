"""실험 결과를 PDF 보고서로 만든다 (라이브러리 → PDF 다운로드)."""

from __future__ import annotations

from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
FONT_CANDIDATES = [
    APP_DIR / "assets" / "fonts" / "NanumGothic.ttf",
    Path("C:/Windows/Fonts/malgun.ttf"),
    Path("/Library/Fonts/AppleGothic.ttf"),
    Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
    Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
]


def font_path() -> Path | None:
    return next((p for p in FONT_CANDIDATES if p.exists()), None)


def pdf_available() -> tuple[bool, str]:
    try:
        import fpdf  # noqa: F401
    except ImportError:
        return False, "PDF 생성에 `pip install fpdf2`가 필요합니다."
    if font_path() is None:
        return False, "한글 폰트가 없습니다. app/assets/fonts/NanumGothic.ttf를 추가하십시오."
    return True, ""


def make_experiment_pdf(exp: dict, lever_labels: dict[str, str], segment_label: str) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("KR", "", str(font_path()))
    pdf.set_auto_page_break(auto=True, margin=15)

    def write(text, size=11, gap=7):
        pdf.set_font("KR", size=size)
        pdf.multi_cell(0, gap, str(text), new_x="LMARGIN", new_y="NEXT")

    def section(title):
        pdf.ln(4)
        write(title, size=13, gap=8)

    def p(x):
        return "-" if x is None else f"{float(x) * 100:.2f}%"

    write("KKeeper 실험 결과 보고서", size=10)
    write(exp["title"], size=16, gap=9)
    sim = " · 시뮬레이션 결과(실측 아님)" if exp.get("is_simulated") else ""
    write(f"판정: {exp.get('verdict') or '결과 입력 전'}{sim}  ·  실험 번호 #{exp['id']}  ·  상태 {exp['status']}", size=9)

    section("1. 마케팅 설계")
    write(f"전략 유형: {exp.get('strategy_kind') or '-'}  ·  목적: {exp.get('strategy_goal') or '-'}")
    cond = exp.get("conditions") or {}
    write(f"적용 조건: 구독 기간 {cond.get('period', '전체')}, 마지막 접속 {cond.get('last', '전체')}, "
          f"요금제 {', '.join(cond.get('plans') or []) or '전체'}")
    goals = [f"{lever_labels.get(k, k)} {v}%" for k, v in (exp.get("levers") or {}).items() if v]
    write(f"행동 목표(가정): {', '.join(goals) or '-'}")
    if exp.get("strategy_desc"):
        write(f"설명: {exp['strategy_desc']}")

    section("2. 대상과 가설")
    write(f"대상 유형: {segment_label}")
    write(f"가설: 대조군 예상 이탈률 {p(exp.get('hyp_p_ctrl'))} → 실험군 {p(exp.get('hyp_p_treat'))} (이탈 모델 예측)")
    if exp.get("required_n"):
        write(f"필요 인원: 그룹당 {int(exp['required_n']):,}명 (유의수준 5%, 검정력 80%)")

    section("3. 실험 설계")
    write(f"실험군 {int(exp.get('n_treat') or 0):,}명 / 대조군 {int(exp.get('n_ctrl') or 0):,}명 · 채널 {exp.get('channel') or '-'}")
    write(f"기간: {exp.get('start_date') or '-'} ~ {exp.get('end_date') or '-'} · 판단 기준: {exp.get('metric') or '-'}")

    section("4. 결과와 판정")
    if exp.get("verdict"):
        write(f"실험군 이탈률 {p(exp['obs_x_treat'] / exp['obs_n_treat'])} ({exp['obs_x_treat']:,}/{exp['obs_n_treat']:,}명)")
        write(f"대조군 이탈률 {p(exp['obs_x_ctrl'] / exp['obs_n_ctrl'])} ({exp['obs_x_ctrl']:,}/{exp['obs_n_ctrl']:,}명)")
        write(f"차이 {exp['ci_low'] * 100:+.2f}%p ~ {exp['ci_high'] * 100:+.2f}%p (95% 신뢰구간) · p = {'< 0.0001' if exp['p_value'] < 0.0001 else format(exp['p_value'], '.4f')}")
        write(f"판정: {exp['verdict']}")
    else:
        write("입력된 결과가 없습니다.")
    if exp.get("note"):
        write(f"메모: {exp['note']}")

    pdf.ln(6)
    write("※ 가설은 KKBox 데이터 기반 이탈 모델의 예측값이며, 판정은 실험군·대조군의 실제 결과를 기준으로 합니다.", size=8, gap=5)
    return bytes(pdf.output())
