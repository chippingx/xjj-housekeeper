import sys
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from ui.services import update_video_tags
except Exception:
    def update_video_tags(video_id, tags):
        return False


def open_tags_manager(app, table: ttk.Treeview, item_id: str, video_id: int, current_tags_str: str) -> None:
    dialog = tk.Toplevel(app.root)
    dialog.withdraw()
    dialog.title(app.t("dialog.manage_tags_title"))
    dialog.geometry("400x500")

    dialog.update_idletasks()
    x = app.root.winfo_x() + (app.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = app.root.winfo_y() + (app.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    dialog.deiconify()

    dialog.transient(app.root)
    dialog.grab_set()
    dialog.focus_set()

    current_tags = set(t.strip() for t in current_tags_str.split(",") if t.strip())

    container = tk.Frame(dialog, bg=app.colors["white"], padx=15, pady=15)
    container.pack(fill=tk.BOTH, expand=True)

    add_frame = tk.Frame(container, bg=app.colors["white"])
    add_frame.pack(fill=tk.X, pady=(0, 10))

    tk.Label(add_frame, text=app.t("tags.add_label"), bg=app.colors["white"]).pack(side=tk.LEFT)
    new_tag_var = tk.StringVar()
    entry_container, entry = app.create_styled_entry(add_frame, textvariable=new_tag_var, font=app.fonts["base"])
    entry_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    list_frame = tk.Frame(container, bg=app.colors["white"], relief=tk.GROOVE, bd=1)
    list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    canvas = tk.Canvas(list_frame, bg=app.colors["white"], highlightthickness=0)
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=app.colors["white"])

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_mousewheel(event):
        if sys.platform == "darwin":
            delta = -1 * event.delta
        elif sys.platform.startswith("linux"):
            if event.num == 4:
                delta = -1
            elif event.num == 5:
                delta = 1
            else:
                delta = 0
        else:
            delta = -1 * (event.delta // 120)

        canvas.yview_scroll(int(delta), "units")

    bind_tags = ("<MouseWheel>", "<Button-4>", "<Button-5>")
    for tag in bind_tags:
        canvas.bind(tag, _on_mousewheel, add="+")
        scrollable_frame.bind(tag, _on_mousewheel, add="+")
        list_frame.bind(tag, _on_mousewheel, add="+")

    def _bind_mousewheel(_event=None):
        for tag in bind_tags:
            dialog.bind_all(tag, _on_mousewheel)

    def _unbind_mousewheel(_event=None):
        for tag in bind_tags:
            dialog.unbind_all(tag)

    list_frame.bind("<Enter>", _bind_mousewheel, add="+")
    list_frame.bind("<Leave>", _unbind_mousewheel, add="+")
    scrollable_frame.bind("<Enter>", _bind_mousewheel, add="+")
    scrollable_frame.bind("<Leave>", _unbind_mousewheel, add="+")

    check_vars = {}

    def refresh_list():
        for widget in scrollable_frame.winfo_children():
            widget.destroy()

        all_tags = sorted(list(set(app.settings.tags) | current_tags))

        for tag in all_tags:
            var = tk.BooleanVar(value=tag in current_tags)
            check_vars[tag] = var
            cb = tk.Checkbutton(scrollable_frame, text=tag, variable=var, bg=app.colors["white"], anchor="w")
            cb.pack(fill=tk.X, padx=5, pady=2)

    refresh_list()

    def add_new_tag():
        val = new_tag_var.get().strip()
        if not val:
            return

        current_tags.add(val)

        if val not in app.settings.tags:
            temp = list(app.settings.tags)
            temp.append(val)
            app.settings.tags = temp
            app.settings.save_settings()

            if hasattr(app, "_current_tags"):
                if val not in app._current_tags:
                    app._current_tags.append(val)
                    app._current_tags.sort()
            if hasattr(app, "tags_cb"):
                app.tags_cb["values"] = app._current_tags

        new_tag_var.set("")
        refresh_list()

    app.make_action_button(add_frame, text=app.t("button.add"), command=add_new_tag).pack(side=tk.LEFT)
    entry.bind("<Return>", lambda e: add_new_tag())

    btn_frame = tk.Frame(container, bg=app.colors["white"])
    btn_frame.pack(fill=tk.X, pady=(15, 0))

    def save():
        selected = [tag for tag, var in check_vars.items() if var.get()]

        success = update_video_tags(video_id, selected)
        if success:
            new_tags_str = ", ".join(sorted(selected))

            row = getattr(table, "_row_cache", {}).get(item_id)
            if row:
                row["tags"] = new_tags_str
                row["labels"] = new_tags_str

            values = list(table.item(item_id, "values") or [])
            cols = list(table["columns"])
            if "tags" in cols:
                idx = cols.index("tags")
                values[idx] = new_tags_str
                table.item(item_id, values=values)

            dialog.destroy()
        else:
            messagebox.showerror(app.t("message.title.error"), app.t("tags.save_failed"))

    app.make_action_button(btn_frame, text=app.t("button.save"), command=save).pack(side=tk.RIGHT)
    app.make_action_button(btn_frame, text=app.t("button.cancel"), command=dialog.destroy).pack(side=tk.RIGHT, padx=10)
