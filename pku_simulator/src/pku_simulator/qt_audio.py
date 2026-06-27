"""背景音乐控制。

主窗口继承此 mixin 后，通过 `_sync_background_music()` 根据当前页面/天数切换
BGM；音乐设置覆盖层通过 `_set_music_volume()` 调整音量。
"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from pku_simulator.core.config import PROJECT_ROOT
from pku_simulator.qt_defs import _clamped_ratio


class BackgroundMusicMixin:
    """BGM 路由接口；依赖 `MainWindow` 的 `_current_name`、`state` 和视图刷新。"""

    def _setup_background_music(self) -> None:
        """初始化播放器、音频输出和页面到 BGM 文件的映射。"""
        self._music_settings_visible = False
        self._music_volume = 0.48
        self._active_bgm_key = ""
        self._bgm_paths = {
            "start": PROJECT_ROOT / "bgm" / "bgm1.mp3",
            "shop": PROJECT_ROOT / "bgm" / "bgm2.mp3",
            "workbench_odd": PROJECT_ROOT / "bgm" / "bgm3.flac",
            "workbench_even": PROJECT_ROOT / "bgm" / "bgm4.mp3",
        }
        self._bgm_audio_output = QAudioOutput(self)
        self._bgm_audio_output.setVolume(self._music_volume)
        self._bgm_player = QMediaPlayer(self)
        self._bgm_player.setAudioOutput(self._bgm_audio_output)
        self._bgm_player.setLoops(QMediaPlayer.Loops.Infinite)

    def _current_bgm_key(self) -> str:
        """根据当前页面和天数返回 BGM key。"""
        if self._current_name == "start":
            return "start"
        if self._current_name == "shop":
            return "shop"
        if self._current_name == "workbench":
            return "workbench_odd" if self.state.day % 2 else "workbench_even"
        return ""

    def _sync_background_music(self) -> None:
        """切屏后调用；如果 key 未变则继续播放，否则换源。"""
        bgm_key = self._current_bgm_key()
        if bgm_key == self._active_bgm_key and self._bgm_player.source().isValid():
            if self._bgm_player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                self._bgm_player.play()
            return

        self._active_bgm_key = bgm_key
        bgm_path = self._bgm_paths.get(bgm_key)
        if bgm_path is None or not bgm_path.exists():
            self._bgm_player.stop()
            self._bgm_player.setSource(QUrl())
            return

        self._bgm_player.setSource(QUrl.fromLocalFile(str(bgm_path)))
        self._bgm_player.play()

    def _set_music_volume(self, volume: float) -> None:
        """音乐设置覆盖层的音量滑块/按钮会调用这里。"""
        self._music_volume = _clamped_ratio(volume)
        self._bgm_audio_output.setVolume(self._music_volume)
        self.game_scene_view.refresh_overlay()
