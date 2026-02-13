import tkinter as tk
from tkinter import messagebox, ttk


def confirm_and_delete(app, table: ttk.Treeview, item_id: str, video_id: int, video_label: str) -> None:
    dialog = tk.Toplevel(app.root)
    dialog.withdraw()
    dialog.title(app.t("dialog.confirm_delete_title"))
    dialog.geometry("420x180")
    dialog.transient(app.root)
    dialog.grab_set()
    dialog.focus_set()

    dialog.update_idletasks()
    x = app.root.winfo_x() + (app.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = app.root.winfo_y() + (app.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    dialog.deiconify()

    container = tk.Frame(dialog, bg=app.colors["white"], padx=16, pady=16)
    container.pack(fill=tk.BOTH, expand=True)

    title = tk.Label(container, text=app.t("dialog.confirm_delete_heading"), bg=app.colors["white"], fg=app.colors["gray800"], font=("Helvetica", 16, "bold"))
    title.pack(anchor="w")

    msg = tk.Label(
        container,
        text=app.t("dialog.confirm_delete_message", video=video_label),
        bg=app.colors["white"], fg=app.colors["gray800"], justify="left", wraplength=380
    )
    msg.pack(anchor="w", pady=(8, 12))

    btns = tk.Frame(container, bg=app.colors["white"])
    btns.pack(fill=tk.X, pady=(6, 0))

    result = {"confirm": False}
    def do_cancel():
        result["confirm"] = False
        dialog.destroy()
    def do_delete():
        result["confirm"] = True
        dialog.destroy()

    cancel_btn = app.make_action_button(btns, text=app.t("button.cancel"), command=do_cancel, padx=20, pady=8)
    cancel_btn.pack(side=tk.RIGHT, padx=6)
    delete_btn = app.make_action_button(btns, text=app.t("button.delete"), command=do_delete, padx=20, pady=8)
    delete_btn.configure(bg=app.colors["brand"], fg="black", activebackground=app.colors["brand"])
    delete_btn.pack(side=tk.RIGHT, padx=6)

    dialog.wait_window(dialog)
    if not result["confirm"]:
        return

    try:
        from ui.services import VideoService
        svc = VideoService()
        ok = svc.delete_video(video_id)
    except Exception as e:
        messagebox.showerror(app.t("message.title.delete_failed"), str(e))
        return

    if ok:
        row_cache = getattr(table, "_row_cache", {})
        table.delete(item_id)
        row_cache.pop(item_id, None)
    else:
        messagebox.showwarning(app.t("message.title.not_deleted"), app.t("message.delete_not_success"))
