import sys
import tkinter as tk
from tkinter import ttk


def _get_service(name, default):
    module = sys.modules.get("ui.tkinter.app")
    if module and hasattr(module, name):
        return getattr(module, name)
    return default


def _default_search_videos_paged(keyword: str, preference: str = "all", page: int = 1, page_size: int = 100):
    return {"items": [], "total": 0, "page": page, "page_size": page_size}


def _default_random_videos(limit: int = 20, ensure_accessible: bool = True):
    return []


def _default_latest_videos_paged(*, days: int = 14, page: int = 1, page_size: int = 100, ensure_accessible: bool = True):
    return {"items": [], "total": 0, "page": page, "page_size": page_size}


def build_query_page(app, parent) -> tk.Frame:
    container = tk.Frame(parent, bg=app.colors["bg"])

    content = tk.Frame(container, bg=app.colors["bg"])
    content.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

    form = tk.Frame(content, bg=app.colors["bg"])
    form.pack(fill=tk.X)

    app.query_placeholder = app.t("query.placeholder")
    app.query_var = tk.StringVar(value=app.query_placeholder)
    entry_container, entry = app.create_styled_entry(form, textvariable=app.query_var, width=40, font=app.fonts["base"])
    entry_container.pack(side=tk.LEFT, padx=(0, 8))
    app.attach_entry_context_menu(entry)
    app.query_entry = entry

    preference_labels = app.get_preference_labels()
    preference_label_to_value = app.get_preference_label_to_value()
    app.preference_var = tk.StringVar(value=preference_labels["all"])
    pref_cb = ttk.Combobox(form, textvariable=app.preference_var, state="readonly", width=10, font=app.fonts["base"])
    pref_cb["values"] = (
        preference_labels["all"],
        preference_labels["like"],
        preference_labels["dislike"],
        preference_labels["deleted"],
        preference_labels["none"],
    )
    pref_cb.pack(side=tk.LEFT, padx=8, ipady=6)

    def _on_query_focus_in(_event):
        if app.query_var.get() == app.query_placeholder:
            app._ignore_query_trace = True
            try:
                app.query_var.set("")
            finally:
                app._ignore_query_trace = False

    def _on_query_focus_out(_event):
        if not app.query_var.get().strip():
            app._ignore_query_trace = True
            try:
                app.query_var.set(app.query_placeholder)
            finally:
                app._ignore_query_trace = False

    entry.bind("<FocusIn>", _on_query_focus_in)
    entry.bind("<FocusOut>", _on_query_focus_out)

    table_container = tk.Frame(content, bg=app.colors["bg"])
    table_container.pack(fill=tk.BOTH, expand=True, pady=20)

    columns = tuple(app.settings.visible_columns)
    table = ttk.Treeview(table_container, columns=columns, show="headings")
    left_cols = {"video", "actress", "tags", "file_path", "preference"}

    header_texts = app.get_column_labels()

    for col in columns:
        text = header_texts.get(col, col)
        table.heading(col, text=text, anchor="w" if col in left_cols else "e", command=lambda c=col: app.sort_table(table, c))
        if col == "file_path":
            width = 320
        elif col == "tags":
            width = 180
        elif col == "actress":
            width = 140
        elif col == "updated_time":
            width = 150
        elif col == "preference":
            width = 100
        else:
            width = 120
        table.column(col, width=width, anchor="w" if col in left_cols else "e")

    table._header_texts = header_texts
    table._context_role = "query"
    table.tag_configure("pref_like", background="#FEF3C7", foreground=app.colors["gray800"])
    table.tag_configure("pref_dislike", background="#FEE2E2", foreground=app.colors["gray800"])
    table.tag_configure("pref_deleted", background="#E5E7EB", foreground=app.colors["gray800"])

    vsb = ttk.Scrollbar(table_container, orient="vertical", command=table.yview)
    table.configure(yscrollcommand=vsb.set)
    table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    page_frame = tk.Frame(content, bg=app.colors["bg"])
    page_frame.pack(fill=tk.X, pady=(0, 0))
    app.page_frame = page_frame

    app.page_var = tk.IntVar(value=1)

    btn_prev = app.make_action_button(page_frame, text=app.t("pagination.prev"), padx=10)
    btn_prev.pack(side=tk.LEFT)

    page_label = tk.Label(page_frame, text=app.t("pagination.page_simple", page=1), bg=app.colors["bg"], fg=app.colors["gray700"], font=("Helvetica", 12))
    page_label.pack(side=tk.LEFT, padx=15)

    btn_next = app.make_action_button(page_frame, text=app.t("pagination.next"), padx=10)
    btn_next.pack(side=tk.LEFT)

    app.history_stack = []
    app.forward_stack = []
    app.current_search_state = {}

    def _save_history(new_state: dict):
        if app.current_search_state:
            if new_state != app.current_search_state:
                app.history_stack.append(app.current_search_state.copy())
                app.forward_stack.clear()
        app.current_search_state = new_state.copy()
        _update_nav_buttons()

    def _update_nav_buttons():
        btn_back.config(state=tk.NORMAL if app.history_stack else tk.DISABLED)
        btn_forward.config(state=tk.NORMAL if app.forward_stack else tk.DISABLED)

    def _restore_history(is_forward=False):
        if is_forward:
            if not app.forward_stack:
                return
            if app.current_search_state:
                app.history_stack.append(app.current_search_state.copy())
            target_state = app.forward_stack.pop()
        else:
            if not app.history_stack:
                return
            if app.current_search_state:
                app.forward_stack.append(app.current_search_state.copy())
            target_state = app.history_stack.pop()

        app.current_search_state = target_state.copy()
        _update_nav_buttons()

        mode = target_state.get("mode", "search")

        if mode == "random":
            app.page_frame.pack_forget()
        else:
            app.page_frame.pack(fill=tk.X, pady=(0, 0))

        if mode == "search":
            app.query_var.set(target_state.get("keyword", ""))
            app.preference_var.set(target_state.get("preference_label", preference_labels["all"]))
            app.page_var.set(target_state.get("page", 1))
            do_search_live(reset_page=False, save_history=False)
        elif mode == "latest":
            app.page_var.set(target_state.get("page", 1))
            do_latest_videos(reset_page=False, save_history=False)
        elif mode == "random":
            do_random_pick(save_history=False)

    def do_search_live(reset_page=False, save_history=True):
        if app._ignore_query_trace:
            return

        app.page_frame.pack(fill=tk.X, pady=(0, 0))

        keyword = app.query_var.get().strip()
        is_placeholder = keyword == app.query_placeholder

        pref_label = app.preference_var.get()
        preference = preference_label_to_value.get(pref_label, "all")

        if reset_page:
            app.page_var.set(1)

        page = app.page_var.get()
        page_size = app.settings.page_size

        if save_history:
            new_state = {
                "mode": "search",
                "keyword": keyword if not is_placeholder else "",
                "preference": preference,
                "preference_label": pref_label,
                "page": page,
            }
            _save_history(new_state)

        if (not keyword or is_placeholder) and preference == "all":
            app.render_table(table, [])
            page_label.config(text=app.t("pagination.page_simple", page=1))
            btn_prev.config(state=tk.DISABLED)
            btn_next.config(state=tk.DISABLED)
            return

        real_keyword = "" if is_placeholder else keyword

        try:
            search_videos_paged_fn = _get_service("search_videos_paged", _default_search_videos_paged)
            res = search_videos_paged_fn(real_keyword, preference, page, page_size)
            items = res.get("items", [])
            total = res.get("total", 0)

            app.render_table(table, items)

            total_pages = (total + page_size - 1) // page_size if total > 0 else 1
            page_label.config(text=app.t("pagination.page_full", page=page, total_pages=total_pages, total=total))

            btn_prev.config(state=tk.NORMAL if page > 1 else tk.DISABLED)
            btn_next.config(state=tk.NORMAL if page < total_pages else tk.DISABLED)

        except Exception as e:
            print(f"Search error: {e}")
            app.render_table(table, [])

    def do_search():
        do_search_live(reset_page=True)

    try:
        app.query_var.trace_add("write", lambda *_: do_search_live(reset_page=True))
    except Exception:
        entry.bind("<KeyRelease>", lambda _e: do_search_live(reset_page=True))

    entry.bind("<Return>", lambda _e: do_search())

    btn_back = app.make_action_button(form, text="<", command=lambda: _restore_history(is_forward=False), padx=10, state=tk.DISABLED)
    btn_back.pack(side=tk.LEFT, padx=(8, 4))

    btn_forward = app.make_action_button(form, text=">", command=lambda: _restore_history(is_forward=True), padx=10, state=tk.DISABLED)
    btn_forward.pack(side=tk.LEFT, padx=4)

    def on_pref_change(_event):
        do_search_live(reset_page=True)

    pref_cb.bind("<<ComboboxSelected>>", on_pref_change)

    def change_page(delta):
        current = app.page_var.get()
        new_page = current + delta
        if new_page < 1:
            return
        app.page_var.set(new_page)

        mode = app.current_search_state.get("mode", "search")
        if mode == "search":
            do_search_live(reset_page=False)
        elif mode == "latest":
            do_latest_videos(reset_page=False)

    btn_prev.config(command=lambda: change_page(-1))
    btn_next.config(command=lambda: change_page(1))

    def do_random_pick(save_history=True):
        app.page_frame.pack_forget()

        if save_history:
            _save_history({"mode": "random"})

        limit = app.settings.page_size
        try:
            random_videos_fn = _get_service("random_videos", _default_random_videos)
            results = random_videos_fn(limit=limit, ensure_accessible=True) or []
        except TypeError:
            random_videos_fn = _get_service("random_videos", _default_random_videos)
            results = random_videos_fn() or []
            if len(results) > limit:
                results = results[:limit]

        results = app.sort_results_by_file_size_desc(results)
        app.render_table(table, results)

    app.make_action_button(form, text=app.t("query.random_button"), command=do_random_pick).pack(side=tk.LEFT, padx=4)

    def do_latest_videos(reset_page=True, save_history=True):
        app.page_frame.pack(fill=tk.X, pady=(0, 0))

        if reset_page:
            app.page_var.set(1)
        page = app.page_var.get()
        page_size = app.settings.page_size

        if save_history:
            _save_history({"mode": "latest", "page": page})

        try:
            latest_videos_paged_fn = _get_service("latest_videos_paged", _default_latest_videos_paged)
            res = latest_videos_paged_fn(days=14, page=page, page_size=page_size, ensure_accessible=True)
            items = res.get("items", [])
            total = res.get("total", 0)

            app.render_table(table, items)

            total_pages = (total + page_size - 1) // page_size if total > 0 else 1
            page_label.config(text=app.t("pagination.page_full", page=page, total_pages=total_pages, total=total))

            btn_prev.config(state=tk.NORMAL if page > 1 else tk.DISABLED)
            btn_next.config(state=tk.NORMAL if page < total_pages else tk.DISABLED)

        except Exception as e:
            print(f"Latest videos error: {e}")
            app.render_table(table, [])

    app.make_action_button(form, text=app.t("query.latest_button"), command=do_latest_videos).pack(side=tk.LEFT, padx=4)

    table.bind("<Double-1>", lambda e: app.on_table_double_click(table, e))
    for sequence in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
        table.bind(sequence, lambda e: app.on_table_right_click(table, e))

    app.render_table(table, [])

    def refresh_data():
        mode = app.current_search_state.get("mode", "search")
        if mode in ("search", "latest"):
            if mode == "search":
                do_search_live(reset_page=False, save_history=False)
            else:
                do_latest_videos(reset_page=False, save_history=False)
        else:
            current_rows = []
            for item_id in table.get_children():
                row_data = getattr(table, "_row_cache", {}).get(item_id)
                if row_data:
                    current_rows.append(row_data)
            app.render_table(table, current_rows)

    container.refresh_data = refresh_data
    return container
