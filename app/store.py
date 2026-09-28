"""
KKeeper — 아주 단순한 로컬 저장소 (store.py)

실험 관리 · 라이브러리 데이터는 원래 session_state(서버 메모리)에만 있어서
새로고침하거나 서버를 재시작하면 그대로 사라졌어요. 지금은 아직 DB가 없는
시안 단계라, 같은 폴더의 kkeeper_data.json 파일에 그대로 읽고 써서
"새로고침해도 남아있는" 정도는 되게 해요.

실제 서비스로 갈 땐 이 파일을 DB 저장/조회로 바꿔치기하면 돼요 (다른 페이지 코드는
안 건드려도 되도록 load_into / save_from 두 함수로만 감싸 놨어요).
"""

import json
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "kkeeper_data.json"
KEYS = ("experiments", "strategy_library")


def load_into(session_state) -> None:
    """세션에 아직 값이 없는 키만, 파일에 저장돼 있던 내용으로 채워요.
    (이미 이번 세션에서 만든 값이 있으면 덮어쓰지 않아요.)"""
    if not DATA_FILE.exists():
        return
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    for key in KEYS:
        if key in data and key not in session_state:
            session_state[key] = data[key]


def save_from(session_state) -> None:
    """실험 목록과 라이브러리 목록을 지금 상태 그대로 파일에 저장해요."""
    data = {key: session_state.get(key, []) for key in KEYS}
    try:
        DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
