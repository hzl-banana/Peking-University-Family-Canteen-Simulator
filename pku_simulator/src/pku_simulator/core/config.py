"""运行配置和路径探测。

被 `qt_app.py`、`save_repo.py` 和打包产物间接依赖。这里统一判断开发态和
PyInstaller 打包态的资源目录/存档目录，UI 不需要自己猜路径。
"""

from pathlib import Path
import sys


def _detect_project_root() -> Path:
	"""返回资源所在根目录；打包态优先使用 PyInstaller 的临时资源目录。"""
	if getattr(sys, "frozen", False):
		meipass = getattr(sys, "_MEIPASS", None)
		if meipass:
			return Path(meipass)
		return Path(sys.executable).resolve().parent
	return Path(__file__).resolve().parents[3]


def _detect_save_dir(project_root: Path) -> Path:
	"""开发态写项目内 `save/`，打包态写用户目录，避免 App 内部不可写。"""
	if getattr(sys, "frozen", False):
		return Path.home() / ".pku_simulator" / "save"
	return project_root / "save"


PROJECT_ROOT = _detect_project_root()
SAVE_DIR = _detect_save_dir(PROJECT_ROOT)
SAVE_FILE = SAVE_DIR / "game_state.json"

CANVAS_WIDTH = 8640
CANVAS_HEIGHT = 5592
CANVAS_SIZE = (CANVAS_WIDTH, CANVAS_HEIGHT)
CANVAS_ASPECT_RATIO = CANVAS_WIDTH / CANVAS_HEIGHT

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = round(WINDOW_WIDTH / CANVAS_ASPECT_RATIO)
WINDOW_SIZE = (WINDOW_WIDTH, WINDOW_HEIGHT)
FPS = 60

APP_TITLE = "PKU Simulator - Scaffold"
