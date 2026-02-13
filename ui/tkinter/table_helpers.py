from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk


def apply_query_table_columns(app, table, columns):
    header_texts = app.get_column_labels()
    left_cols = {"video", "actress", "tags", "file_path", "preference"}

    table._header_texts = header_texts
    table._context_role = "query"
    table.tag_configure("pref_like", background="#FEF3C7", foreground=app.colors["gray800"])
    table.tag_configure("pref_dislike", background="#FEE2E2", foreground=app.colors["gray800"])
    table.tag_configure("pref_deleted", background="#E5E7EB", foreground=app.colors["gray800"])

    for col in columns:
        text = header_texts.get(col, col)
        table.heading(col, text=text, anchor="w" if col in left_cols else "e", command=lambda c=col: app.sort_table(table, c))
        if col == "file_path":
            width = 280
        elif col == "tags":
            width = 160
        elif col == "actress":
            width = 120
        elif col == "updated_time":
            width = 140
        elif col == "preference":
            width = 80
        else:
            width = 120
        table.column(col, width=width, anchor="w" if col in left_cols else "e")


def _apply_query_table_columns(app, table, columns):
    apply_query_table_columns(app, table, columns)


def build_maintain_manage_table(app, parent):
    table_container = tk.Frame(parent, bg=app.colors["bg"])
    table_container.pack(fill=tk.BOTH, expand=True, pady=10)

    columns = ("video", "file_path", "file_size", "duration", "resolution", "updated_time")
    table = ttk.Treeview(table_container, columns=columns, show="headings")

    column_labels = app.get_column_labels()
    header_texts = {
        "video": column_labels["video"],
        "file_path": column_labels["file_path"],
        "file_size": column_labels["file_size"],
        "duration": column_labels["duration"],
        "resolution": column_labels["resolution"],
        "updated_time": column_labels["updated_time"],
    }

    for col in columns:
        table.heading(col, text=header_texts[col], anchor="w", command=lambda c=col: app.sort_table(table, c))
        if col == "file_path":
            width = 300
        elif col == "updated_time":
            width = 120
        elif col == "video":
            width = 150
        else:
            width = 100
        table.column(col, width=width, anchor="w")

    table._header_texts = header_texts
    table._context_role = "maintain"

    vsb = ttk.Scrollbar(table_container, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=vsb.set)
    table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    table.bind("<Double-1>", lambda e: app.on_table_double_click(table, e))
    for sequence in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
        table.bind(sequence, lambda e: app.on_table_right_click(table, e))

    return table


def build_movie_info_table(app, parent):
    table_container = tk.Frame(parent, bg=app.colors["bg"])
    table_container.pack(fill=tk.BOTH, expand=True, pady=10)

    columns = ("actress_name", "video_code", "title", "release_date")
    table = ttk.Treeview(table_container, columns=columns, show="headings")

    table.heading("actress_name", text=app.t("movie_info.table.actress_name"), anchor="w")
    table.heading("video_code", text=app.t("movie_info.table.video_code"), anchor="w")
    table.heading("title", text=app.t("movie_info.table.title"), anchor="w")
    table.heading("release_date", text=app.t("movie_info.table.release_date"), anchor="w")

    table.column("actress_name", width=150)
    table.column("video_code", width=150)
    table.column("title", width=300)
    table.column("release_date", width=120)

    vsb = ttk.Scrollbar(table_container, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=vsb.set)
    table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def render_results(rows):
        for item in table.get_children():
            table.delete(item)
        if not rows:
            return
        for row in rows:
            table.insert(
                "",
                tk.END,
                values=(
                    row.actress_name,
                    row.video_code,
                    row.title or "",
                    row.release_date or "",
                ),
            )

    return table, render_results


def render_table(app, table: ttk.Treeview, rows: list[dict]) -> None:
    for item in table.get_children():
        table.delete(item)
    if not rows:
        try:
            columns = list(table["columns"])
        except Exception:
            columns = ["video"]
        empty_values = [""] * len(columns)
        empty_values[0] = app.t("table.empty")
        table.insert("", tk.END, values=empty_values)
        table._row_cache = {}
        return

    row_cache = {}
    columns = list(table["columns"])
    preference_labels = app.get_preference_labels()

    for r in rows:
        row_data = dict(r)
        file_path = row_data.get("file_path") or row_data.get("path")
        if file_path is not None:
            row_data["file_path"] = str(file_path)

        video_label = row_data.get("video") or row_data.get("filename") or ""
        tags_label = row_data.get("tags") or row_data.get("labels") or ""
        pref_status = row_data.get("preference")

        values = []
        for col in columns:
            if col in ("video", "filename"):
                values.append(video_label)
            elif col == "actress":
                values.append(row_data.get("actress", ""))
            elif col in ("tags", "labels"):
                values.append(tags_label)
            elif col == "file_path":
                fp = row_data.get("file_path")
                values.append(str(Path(fp).parent) if fp else "")
            elif col == "file_size":
                values.append(row_data.get("file_size", ""))
            elif col == "duration":
                values.append(row_data.get("duration", ""))
            elif col == "resolution":
                values.append(row_data.get("resolution", ""))
            elif col == "updated_time":
                val = row_data.get("updated_time")
                if isinstance(val, (int, float)):
                    try:
                        val = datetime.fromtimestamp(val).strftime("%Y-%m-%d")
                    except Exception:
                        val = str(val)
                values.append(str(val) if val else "")
            elif col == "preference":
                values.append(
                    preference_labels["like"] if pref_status == "like"
                    else preference_labels["dislike"] if pref_status == "dislike"
                    else preference_labels["deleted"] if pref_status == "deleted"
                    else ""
                )
            else:
                values.append(str(row_data.get(col, "")))

        tags = ()
        if pref_status == "like":
            tags = ("pref_like",)
        elif pref_status == "dislike":
            tags = ("pref_dislike",)
        elif pref_status == "deleted":
            tags = ("pref_deleted",)

        item_id = table.insert("", tk.END, values=values, tags=tags)
        row_cache[item_id] = row_data

    table._row_cache = row_cache


def open_video_list_window(app, title: str, rows: list[dict]) -> None:
    win = tk.Toplevel(app.root)
    win.title(title)
    win.geometry("980x520")

    container = tk.Frame(win, bg=app.colors["white"])
    container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    table = ttk.Treeview(container, columns=("video", "file_size", "path"), show="headings")
    column_labels = app.get_column_labels()
    table.heading("video", text=column_labels["video"])
    table.heading("file_size", text=column_labels["file_size"])
    table.heading("path", text=column_labels["file_path"])
    table.column("video", width=200)
    table.column("file_size", width=100)
    table.column("path", width=400)
    table.pack(fill=tk.BOTH, expand=True)

    for r in rows:
        table.insert("", tk.END, values=(r.get("video"), r.get("file_size"), r.get("file_path")))

    table.bind("<Double-1>", lambda e: app.on_table_double_click(table, e))


def refresh_query_page_columns(app):
    if "query" not in app.pages:
        return

    def find_tree(widget):
        if isinstance(widget, ttk.Treeview):
            return widget
        for child in widget.winfo_children():
            res = find_tree(child)
            if res:
                return res
        return None

    table = find_tree(app.pages["query"])
    if not table:
        return

    columns = tuple(app.settings.visible_columns)
    try:
        table["columns"] = columns
        table["displaycolumns"] = columns
        _apply_query_table_columns(app, table, columns)
    except tk.TclError:
        app._rebuild_ui()
        return

    if hasattr(app.pages["query"], "refresh_data"):
        app.pages["query"].refresh_data()
