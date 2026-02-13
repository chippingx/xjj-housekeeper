import tkinter as tk

import pytest

from ui.tkinter.ui_helpers import (
    attach_entry_context_menu,
    create_styled_entry,
    get_system_video_players,
    make_action_button,
)


class DummyApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.colors = {
            "white": "#FFFFFF",
            "gray800": "#1F2937",
            "gray200": "#E5E7EB",
            "brand": "#2563EB",
            "accent": "#334155",
            "gray100": "#F5F7FA",
        }
        self.fonts = {"base": ("Helvetica", 11)}

    def t(self, key: str) -> str:
        if key == "context.cut":
            return "剪切"
        if key == "context.copy":
            return "复制"
        if key == "context.paste":
            return "粘贴"
        if key == "player.default":
            return "默认播放器"
        return key


def _make_root():
    try:
        return tk.Tk()
    except Exception as exc:
        pytest.skip(f"Tkinter 不可用，跳过测试：{exc}")


def test_create_styled_entry_returns_container_and_entry():
    root = _make_root()
    app = DummyApp(root)
    try:
        container, entry = create_styled_entry(app, root)
        assert isinstance(container, tk.Frame)
        assert isinstance(entry, tk.Entry)
        assert entry.master is container
        pack_info = entry.pack_info()
        assert int(pack_info.get("padx", 0)) == 8
        assert int(pack_info.get("pady", 0)) == 6
    finally:
        root.destroy()


def test_attach_entry_context_menu_sets_menu_and_labels():
    root = _make_root()
    app = DummyApp(root)
    try:
        entry = tk.Entry(root)
        attach_entry_context_menu(app, entry)
        assert hasattr(entry, "_context_menu")
        menu = getattr(entry, "_context_menu")
        labels = [
            menu.entrycget(i, "label")
            for i in range(menu.index("end") + 1)
        ]
        assert "剪切" in labels
        assert "复制" in labels
        assert "粘贴" in labels
    finally:
        root.destroy()


def test_make_action_button_primary_and_secondary_styles():
    root = _make_root()
    app = DummyApp(root)
    try:
        secondary = make_action_button(app, root, "次要")
        assert secondary.cget("bg") == app.colors["white"]
        assert secondary.cget("fg") == app.colors["gray800"]
        primary = make_action_button(app, root, "主要", bg=app.colors["brand"])
        assert primary.cget("bg") == app.colors["brand"]
        assert primary.cget("fg") == app.colors["white"]
        assert primary.cget("activebackground") == app.colors["accent"]
    finally:
        root.destroy()


def test_get_system_video_players_has_default():
    root = _make_root()
    app = DummyApp(root)
    try:
        players = get_system_video_players(app)
        assert "默认播放器" in players
        assert players["默认播放器"] is None
    finally:
        root.destroy()
