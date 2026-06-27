"""存档仓库。

这是唯一直接读写 `SAVE_FILE` 的模块。业务层调用 `save_state()`，主窗口启动
时调用 `load_playable_state()` 自动处理破产旧档。
"""

from __future__ import annotations

import json
from datetime import datetime

from pku_simulator.core.config import SAVE_DIR, SAVE_FILE
from pku_simulator.core.models import GameState


def load_state() -> GameState:
    """读取当前存档；文件不存在或损坏时回落到新局。"""
    if not SAVE_FILE.exists():
        return GameState()

    try:
        raw = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
        return GameState.from_dict(raw)
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return GameState()


def load_playable_state() -> GameState:
    """启动时使用：若旧档已破产，先归档旧档再返回一局新状态。"""
    state = load_state()
    if not SAVE_FILE.exists() or not state.is_game_over():
        return state

    archived = _archive_save_file("bankrupt")
    new_state = GameState()
    save_state(new_state)
    if archived is not None:
        print(f"Archived bankrupt save to {archived}")
    return new_state


def save_state(state: GameState) -> None:
    """把 `GameState` 写入当前存档文件。"""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    SAVE_FILE.write_text(
        json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _archive_save_file(reason: str) -> str | None:
    """把当前存档改名为带 reason 和时间戳的历史文件。"""
    if not SAVE_FILE.exists():
        return None

    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"game_state_{reason}_{timestamp}"
    target = SAVE_DIR / f"{base_name}.json"
    suffix = 1
    while target.exists():
        target = SAVE_DIR / f"{base_name}_{suffix}.json"
        suffix += 1

    SAVE_FILE.rename(target)
    return str(target)
