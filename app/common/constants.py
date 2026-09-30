"""KKeeper 전 페이지가 함께 쓰는 상수.

- 위험 기준, 고객 유형 4가지(K-Means 결과) 이름과 설명
- 마케팅 설계 화면의 선택지
- 마케팅 설계 입력 → 이탈 모델이 읽는 행동 목표(레버) 기본값
"""

# 최종 LightGBM에서 확정한 위험 고객 판정 기준선
THRESHOLD = 0.2824

# ── 고객 유형 4가지 ─────────────────────────────
# 키는 risk_segments.csv / risk_segment_summary.csv의 segment 값 그대로예요.
# 순서가 화면 색상(s1~s4) 순서가 됩니다.
SEGMENTS = {
    "저활동·단기 구독형": {
        "id": "low-activity-short",
        "display": "저활동 · 단기 구독",
        "description": "단기 이용권을 쓰고 청취량이 적지만, 이탈 위험은 가장 낮은 집단",
    },
    "반복 거래·취소 위험형": {
        "id": "repeat-cancel",
        "display": "반복 거래 · 취소 위험",
        "description": "자동갱신 중에도 최근 거래에서 해지한, 해지 반복 위험 집단",
    },
    "장기 플랜·고결제 고위험형": {
        "id": "long-plan-high-pay",
        "display": "장기 플랜 · 고결제",
        "description": "고액 장기 결제에 청취도 활발하지만, 이탈 확률이 가장 높은 집단",
    },
    "장기 관계·고빈도 거래형": {
        "id": "long-tenure-frequent",
        "display": "장기 관계 · 고빈도 거래",
        "description": "오래·자주 이용했지만 해지 이력이 있는 집단",
    },
}
SEGMENT_ORDER = list(SEGMENTS)


def seg_display(name: str) -> str:
    return SEGMENTS.get(name, {}).get("display", name)


def seg_index(name: str) -> int:
    """색상 번호(1~4). 모르는 유형은 1번 색."""
    return SEGMENT_ORDER.index(name) + 1 if name in SEGMENTS else 1


# ── 마케팅 설계 선택지 ───────────────────────────
KINDS = ["할인·프로모션", "콘텐츠 추천", "요금제 안내", "알림·리마인드", "혜택·리워드", "기타"]
GOALS = {
    "이탈 방지": "떠날 조짐이 보이는 고객 붙잡기",
    "재방문 유도": "뜸해진 고객 다시 부르기",
    "해지 철회": "해지 신청 고객 되돌리기",
    "업그레이드": "상위 요금제로 전환",
}
PERIODS = ["전체", "3개월 미만", "3~12개월", "1년 이상"]
LASTS = ["전체", "7일 이상 미접속", "14일 이상 미접속", "30일 이상 미접속"]
PLANS = ["개인", "학생", "가족", "[요금제 이름]"]  # 실제 요금제 이름으로 바꿔 주세요
CHANNELS = ["앱 푸시", "인앱 배너", "이메일", "문자"]
STEP_NAMES = ["마케팅 설계", "고객 매칭", "실험 관리", "라이브러리"]

# ── 마케팅 설계 입력 → 행동 목표(레버) 기본값 ─────────
# 레버 이름은 common/experiment.py의 WHATIF_LEVERS와 같아요.
# 값은 "이 전략이 성공하면 이 정도 행동이 바뀐다"는 팀의 가정값이고,
# 마케팅 설계 화면의 '조정하기'에서 언제든 바꿀 수 있어요.
KIND_LEVERS = {
    "할인·프로모션": {"cancel_stop": 10, "auto_renew_on": 10},
    "콘텐츠 추천": {"song_variety": 10, "activity_up": 10},
    "요금제 안내": {"auto_renew_on": 20},
    "알림·리마인드": {"revisit": 20, "activity_up": 10},
    "혜택·리워드": {"activity_up": 10, "revisit": 20},
    "기타": {"activity_up": 10},
}
GOAL_LEVERS = {
    "이탈 방지": {},
    "재방문 유도": {"revisit": 20},
    "해지 철회": {"cancel_stop": 20},
    "업그레이드": {"auto_renew_on": 10},
}


def default_levers(kind: str, goal: str) -> dict:
    """전략 유형과 목적을 합쳐 행동 목표 기본값을 만든다 (같은 레버는 큰 값)."""
    levers = dict(KIND_LEVERS.get(kind, {}))
    for key, value in GOAL_LEVERS.get(goal, {}).items():
        levers[key] = max(levers.get(key, 0), value)
    return levers


# ── 실험 ────────────────────────────────────────
VERDICTS = ["효과 있음", "판단 보류", "효과 없음"]
VERDICT_KIND = {"효과 있음": "good", "판단 보류": "warn", "효과 없음": "bad"}
DEFAULT_METRIC = "캠페인 종료 후 30일 안에 이탈했는지"
