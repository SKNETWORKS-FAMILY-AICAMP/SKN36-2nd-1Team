"""마케팅 계획을 PDF로 만든다."""

from pathlib import Path

from fpdf import FPDF

APP_DIR = Path(__file__).resolve().parent.parent
FONT_CANDIDATES = [
    APP_DIR / "assets" / "fonts" / "NanumGothic.ttf",
    Path("C:/Windows/Fonts/malgun.ttf"),
]


def _font_path() -> Path:
    for path in FONT_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError("한글 폰트를 찾지 못했습니다. app/assets/fonts/NanumGothic.ttf를 넣어주세요.")


def make_plan_pdf(p: dict, goals: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("KR", "", str(_font_path()))
    pdf.set_auto_page_break(auto=True, margin=15)

    def write(text, size=11, gap=7):
        pdf.set_font("KR", size=size)
        pdf.multi_cell(0, gap, text, new_x="LMARGIN", new_y="NEXT")

    def section(title):
        pdf.ln(4)
        write(title, size=13, gap=8)

    before, after = p["churn_rate_before"] * 100, p["churn_rate_after"] * 100

    write("KKeeper 마케팅 계획서", size=10)
    write(str(p["title"]), size=16, gap=9)
    write(f"상태: {p['status']}  ·  계획 번호 #{p['id']}  ·  저장일 {p['created_at']}", size=9)

    section("대상과 전략")
    write(f"군집: {p['segment_name']} ({int(p['customer_count'] or 0):,}명)")
    write(f"핵심 목표: {p.get('cluster_goal') or '-'}")
    write(f"전략: {p['marketing_name']}")

    section("목표 설정")
    active = {k: v for k, v in goals.items() if v}
    write("\n".join(f"- {k}: {v}%" for k, v in active.items()) if active else "설정한 목표 없음")

    section("예상 결과 (모델 기반 What-if)")
    write(f"예상 이탈률: {before:.1f}% → {after:.1f}% ({after - before:+.2f}%p)")
    write(f"예상 이탈자: {p['expected_churn_before']:,.1f}명 → {p['expected_churn_after']:,.1f}명")
    write(f"예상 감소 인원: {p['reduced_customers']:,.1f}명")

    section("내용")
    write(p["description"] or "(작성한 내용 없음)")

    pdf.ln(6)
    write("※ 예상 결과는 KKBox 데이터로 학습한 이탈 모델의 예측이며, 실제 효과는 A/B 실험으로 확인해야 합니다.", size=8, gap=5)

    return bytes(pdf.output())