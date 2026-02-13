import re
import tkinter as tk
from tkinter import messagebox, ttk


def open_actress_manager(app, table: ttk.Treeview, item_id: str, video_code: str, current_actress_str: str) -> None:
    if not video_code:
        messagebox.showerror(app.t("message.title.cannot_edit"), app.t("actress.missing_video_code"))
        return
    dialog = tk.Toplevel(app.root)
    dialog.withdraw()
    dialog.title(app.t("dialog.edit_actress_title"))
    dialog.geometry("360x160")

    dialog.update_idletasks()
    x = app.root.winfo_x() + (app.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = app.root.winfo_y() + (app.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    dialog.deiconify()

    dialog.transient(app.root)
    dialog.grab_set()
    dialog.focus_set()

    container = tk.Frame(dialog, bg=app.colors["white"], padx=15, pady=15)
    container.pack(fill=tk.BOTH, expand=True)

    tk.Label(container, text=app.t("actress.input_label"), bg=app.colors["white"]).pack(anchor="w")
    actress_var = tk.StringVar(value=current_actress_str or "")
    entry_container, entry = app.create_styled_entry(container, textvariable=actress_var, font=app.fonts["base"])
    entry_container.pack(fill=tk.X, pady=8)
    entry.focus_set()

    btn_frame = tk.Frame(container, bg=app.colors["white"])
    btn_frame.pack(fill=tk.X, pady=(6, 0))

    def _on_save():
        raw = actress_var.get().strip()
        names = [n.strip() for n in re.split(r"[，,;；/、]", raw) if n and n.strip()]
        ok = app.set_row_actress(table, item_id, video_code, names)
        if ok:
            dialog.destroy()
        else:
            messagebox.showerror(app.t("message.title.save_failed"), app.t("actress.update_failed"))

    btn_save = app.make_action_button(btn_frame, text=app.t("button.save"), padx=10, command=_on_save)
    btn_save.pack(side=tk.RIGHT, padx=5)

    btn_cancel = app.make_action_button(btn_frame, text=app.t("button.cancel"), padx=10, command=dialog.destroy)
    btn_cancel.pack(side=tk.RIGHT, padx=5)
