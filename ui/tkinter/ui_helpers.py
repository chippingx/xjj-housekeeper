import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from ui.tkinter.actress_dialogs import open_actress_manager
from ui.tkinter.delete_dialogs import confirm_and_delete
from ui.tkinter.tag_dialogs import open_tags_manager


def init_styles(app) -> None:
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass

    system = app.root.tk.call("tk", "windowingsystem")
    if system == "aqua":
        base_font = ("San Francisco", 13)
        bold_font = ("San Francisco", 13, "bold")
        title_font = ("San Francisco", 18, "bold")
        mono_font = ("Menlo", 12)
    elif system == "win32":
        base_font = ("Microsoft YaHei UI", 10)
        bold_font = ("Microsoft YaHei UI", 10, "bold")
        title_font = ("Microsoft YaHei UI", 14, "bold")
        mono_font = ("Consolas", 10)
    else:
        base_font = ("Helvetica", 11)
        bold_font = ("Helvetica", 11, "bold")
        title_font = ("Helvetica", 16, "bold")
        mono_font = ("Courier", 11)

    app.fonts = {
        "base": base_font,
        "bold": bold_font,
        "title": title_font,
        "mono": mono_font,
        "small": (base_font[0], base_font[1] - 2),
        "link": (base_font[0], base_font[1] - 1),
    }

    style.configure(
        "Treeview",
        background=app.colors["white"],
        fieldbackground=app.colors["white"],
        foreground=app.colors["gray800"],
        rowheight=44,
        font=app.fonts["base"],
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=app.colors["bg"],
        foreground=app.colors["gray700"],
        relief=tk.FLAT,
        font=app.fonts["bold"],
        padding=(16, 12),
    )
    style.map(
        "Treeview",
        background=[("selected", app.colors["selected_bg"])],
        foreground=[("selected", app.colors["selected_fg"])],
    )

    style.configure("Blue.Horizontal.TProgressbar", troughcolor=app.colors["gray100"], background=app.colors["brand"])
    style.configure("TNotebook", background=app.colors["bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        background=app.colors["gray200"],
        foreground=app.colors["gray700"],
        padding=(24, 12),
        font=app.fonts["base"],
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", app.colors["bg"])],
        foreground=[("selected", app.colors["gray800"])],
        padding=[("selected", (24, 12))],
    )

    style.configure(
        "TCombobox",
        background=app.colors["white"],
        fieldbackground=app.colors["white"],
        foreground=app.colors["gray800"],
        arrowcolor=app.colors["gray800"],
        padding=5,
        font=app.fonts["base"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", app.colors["white"])],
        selectbackground=[("readonly", app.colors["white"])],
        selectforeground=[("readonly", app.colors["gray800"])],
    )


def make_action_button(app, parent, text: str, command=None, **kwargs) -> tk.Button:
    padx = kwargs.pop("padx", 24)
    pady = kwargs.pop("pady", 10)

    bg = kwargs.pop("bg", app.colors["white"])
    fg = kwargs.pop("fg", app.colors["gray800"])
    activebg = kwargs.pop("activebackground", app.colors["gray100"])
    activefg = kwargs.pop("activeforeground", app.colors["gray800"])

    if bg == app.colors["brand"]:
        fg = app.colors["white"]
        activebg = app.colors["accent"]
        activefg = app.colors["white"]

    font = kwargs.pop("font", app.fonts["base"])

    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        font=font,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        activebackground=activebg,
        activeforeground=activefg,
        padx=padx,
        pady=pady,
        cursor="hand2",
        **kwargs,
    )
    return btn


def create_styled_entry(app, parent, **kwargs) -> tuple[tk.Frame, tk.Entry]:
    var = kwargs.pop("textvariable", None)
    width = kwargs.pop("width", None)
    font = kwargs.pop("font", app.fonts["base"])
    fg = kwargs.pop("fg", app.colors["gray800"])
    bg = kwargs.pop("bg", app.colors["white"])

    container = tk.Frame(
        parent,
        bg=bg,
        highlightthickness=1,
        highlightbackground=app.colors["gray200"],
        highlightcolor=app.colors["brand"],
        bd=0,
    )

    entry = tk.Entry(
        container,
        textvariable=var,
        width=width,
        font=font,
        fg=fg,
        bg=bg,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        insertbackground=app.colors["gray800"],
        **kwargs,
    )
    entry.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

    return container, entry


def attach_entry_context_menu(app, entry: tk.Entry) -> None:
    menu = tk.Menu(entry, tearoff=0)
    menu.add_command(label=app.t("context.cut"), command=lambda: entry.event_generate("<<Cut>>"))
    menu.add_command(label=app.t("context.copy"), command=lambda: entry.event_generate("<<Copy>>"))
    menu.add_command(label=app.t("context.paste"), command=lambda: entry.event_generate("<<Paste>>"))

    def show_menu(event: tk.Event):
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()

    for sequence in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
        entry.bind(sequence, show_menu, add="+")
    entry._context_menu = menu


def handle_table_double_click(app, table: ttk.Treeview, event: tk.Event):
    if getattr(app, "_processing_click", False):
        return "break"
    app._processing_click = True

    try:
        item = table.identify_row(event.y)
        if not item:
            return "break"

        col_name = None
        try:
            col_id = table.identify_column(event.x)
            col_idx = int(col_id.replace("#", "")) - 1
            col_name = table["columns"][col_idx]
        except Exception:
            pass

        row = getattr(table, "_row_cache", {}).get(item, {})
        file_path = row.get("file_path")
        if file_path:
            if Path(file_path).exists():
                if col_name == "file_path" or col_name == "path":
                    app.open_file_manager(file_path)
                else:
                    app.play_video(file_path)
            else:
                messagebox.showerror(app.t("message.title.file_missing"), app.t("message.file_missing", path=file_path))
    finally:
        app.root.after(500, lambda: setattr(app, "_processing_click", False))

    return "break"


def handle_table_right_click(app, table: ttk.Treeview, event: tk.Event):
    item = table.identify_row(event.y)
    if not item:
        return
    row = getattr(table, "_row_cache", {}).get(item, {})
    role = getattr(table, "_context_role", "query")
    file_path = row.get("file_path")
    if role == "query":
        if not file_path:
            return

    menu = tk.Menu(app.root, tearoff=0)
    setattr(table, "_context_menu", menu)
    video_label = row.get("video") or row.get("filename") or ""
    video_code = row.get("video_code") or ""
    video_id = row.get("id")

    if role.startswith("maintain"):
        if video_id:
            menu.add_command(label=app.t("context.delete_record"), command=lambda: confirm_and_delete(app, table, item, int(video_id), video_label))
        else:
            menu.add_command(label=app.t("context.delete_record"), state=tk.DISABLED)
    else:
        if video_code:
            actress_label = row.get("actress") or ""
            menu.add_command(label=app.t("context.edit_actress"), command=lambda: open_actress_manager(app, table, item, video_code, actress_label))
        else:
            menu.add_command(label=app.t("context.edit_actress"), state=tk.DISABLED)

        if video_id:
            tags_label = row.get("tags") or ""
            menu.add_command(label=app.t("context.edit_tags"), command=lambda: open_tags_manager(app, table, item, video_id, tags_label))
            menu.add_separator()

        menu.add_command(label=app.t("context.mark_like"), command=lambda: app.set_row_preference(table, item, video_label, "like"))
        menu.add_command(label=app.t("context.mark_dislike"), command=lambda: app.set_row_preference(table, item, video_label, "dislike"))
        menu.add_command(label=app.t("context.mark_deleted"), command=lambda: app.set_row_preference(table, item, video_label, "deleted"))
        menu.add_command(label=app.t("context.clear_preference"), command=lambda: app.set_row_preference(table, item, video_label, None))
        menu.add_separator()

        players = app.get_system_video_players()
        for name, path in players.items():
            menu.add_command(label=name, command=lambda p=path: app.play_video_with_player(Path(file_path), p))

    try:
        menu.tk_popup(event.x_root, event.y_root)
    except Exception:
        return


def open_file_manager(app, path: str):
    try:
        p = Path(path)
        target = p.parent if p.is_file() else p
        path_str = str(target)

        if sys.platform == "win32":
            os.startfile(path_str)
        elif sys.platform == "darwin":
            os.system(f"open '{path_str}'")
        else:
            os.system(f"xdg-open '{path_str}'")
    except Exception as e:
        messagebox.showerror(app.t("message.title.open_dir_failed"), str(e))


def play_video(app, video_path: str):
    try:
        if sys.platform == "win32":
            os.startfile(video_path)
        elif sys.platform == "darwin":
            os.system(f"open '{video_path}'")
        else:
            os.system(f"xdg-open '{video_path}'")
    except Exception as e:
        messagebox.showerror(app.t("message.title.play_failed"), str(e))


def play_video_with_player(app, video_path: Path, player_path: str):
    try:
        if not player_path:
            app.play_video(str(video_path))
        elif sys.platform == "darwin":
            os.system(f'open -a "{player_path}" "{video_path}"')
        else:
            os.system(f'"{player_path}" "{video_path}"')
    except Exception as e:
        messagebox.showerror(app.t("message.title.play_failed"), str(e))


def get_system_video_players(app):
    players = {app.t("player.default"): None}

    if sys.platform == "darwin":
        common_players = {
            "QuickTime Player": ["/System/Applications/QuickTime Player.app", "/Applications/QuickTime Player.app"],
            "VLC": ["/Applications/VLC.app", os.path.expanduser("~/Applications/VLC.app")],
            "IINA": ["/Applications/IINA.app", os.path.expanduser("~/Applications/IINA.app")],
            "Movist Pro": ["/Applications/Movist Pro.app"],
            "Elmedia Player": ["/Applications/Elmedia Player.app"],
            "OmniPlayer": ["/Applications/OmniPlayer.app", os.path.expanduser("~/Applications/OmniPlayer.app")],
            "暴风影音": ["/Applications/Baofeng.app", "/Applications/Storm.app", os.path.expanduser("~/Applications/Baofeng.app")],
        }

        for name, paths in common_players.items():
            for path in paths:
                if os.path.exists(path):
                    players[name] = path
                    break
    elif sys.platform == "win32":
        common_players = {
            "PotPlayer": [
                r"C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe",
                r"C:\Program Files (x86)\DAUM\PotPlayer\PotPlayerMini.exe",
            ],
            "VLC": [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            ],
            "MPV": [
                r"C:\Program Files\mpv\mpv.exe",
                r"C:\Program Files (x86)\mpv\mpv.exe",
            ],
            "KMPlayer": [
                r"C:\Program Files\KMPlayer\KMPlayer.exe",
                r"C:\Program Files (x86)\KMPlayer\KMPlayer.exe",
                r"C:\KMPlayer\KMPlayer.exe",
            ],
        }

        for name, paths in common_players.items():
            for path in paths:
                if os.path.exists(path):
                    players[name] = path
                    break

    return players
