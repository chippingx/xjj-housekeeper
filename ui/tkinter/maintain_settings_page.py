import json
import os
import sys
import time
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ui.tkinter.settings_sections import (
    build_basic_settings_section,
    build_query_settings_section,
    build_rename_rules_section,
    build_save_section,
    build_tags_section,
)
from ui.tkinter.settings_logic import create_settings_change_checker, create_save_settings_handler
from ui.tkinter.table_helpers import build_movie_info_table
from tools.data_backup.backup_manager import export_backup, import_backup, initialize_data, get_default_backup_paths
from tools.filename_formatter.formatter import load_rules_config
from tools.video_info_collector.sqlite_storage import SQLiteStorage


def _get_app_attr(name, default=None):
    module = sys.modules.get("ui.tkinter.app")
    if module and hasattr(module, name):
        return getattr(module, name)
    return default


def init_maintain_settings(app, parent):
    tk.Frame(parent, bg=app.colors["bg"], height=12).pack(fill=tk.X)

    canvas = tk.Canvas(parent, bg=app.colors["bg"], highlightthickness=0)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=app.colors["bg"])

    def _is_descendant(widget, ancestor):
        while widget is not None:
            if widget == ancestor:
                return True
            widget = widget.master
        return False

    def _on_mousewheel(event):
        current_canvas = getattr(app, "_settings_canvas", None)
        if current_canvas is None:
            return
        try:
            widget = app.root.winfo_containing(event.x_root, event.y_root)
        except KeyError:
            return
        if widget is None or not _is_descendant(widget, current_canvas):
            return
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

        current_canvas.yview_scroll(int(delta), "units")

    if not callable(getattr(app, "_settings_mousewheel_handler", None)):
        app._settings_mousewheel_handler = _on_mousewheel
    app.root.bind_all("<MouseWheel>", app._settings_mousewheel_handler)
    app.root.bind_all("<Button-4>", app._settings_mousewheel_handler)
    app.root.bind_all("<Button-5>", app._settings_mousewheel_handler)

    def update_scrollregion():
        app._settings_scroll_job = None
        if not getattr(app, "_settings_scroll_dirty", True):
            return
        start_time = time.perf_counter()
        bbox = canvas.bbox("all")
        if not bbox:
            bbox = (0, 0, 0, 0)
        canvas.configure(scrollregion=bbox)
        app._settings_scrollregion_cache = bbox
        app._settings_scroll_dirty = False
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        if app._debug_tab_perf:
            print(f"[perf] {datetime.now().isoformat(timespec='milliseconds')} update_scrollregion elapsed_ms={elapsed_ms:.2f}")
        app._perf_record("update_scrollregion", elapsed_ms)

    def mark_settings_scroll_dirty():
        app._settings_scroll_dirty = True
        notebook = getattr(app, "_maintain_notebook", None)
        settings_id = getattr(app, "_maintain_settings_tab_id", None)
        if notebook and settings_id and notebook.select() == settings_id:
            if app._settings_scroll_job is None:
                app._settings_scroll_job = app.root.after_idle(update_scrollregion)

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    app._settings_scroll_dirty = True
    app._settings_canvas = canvas
    app._settings_update_scroll = update_scrollregion

    form = tk.Frame(scrollable_frame, bg=app.colors["bg"])
    form.pack(fill=tk.X, pady=20)

    build_basic_settings_section(app, form)
    build_query_settings_section(app, form)

    app._settings_check_changes = lambda *args: None

    def trigger_settings_change(*args):
        return app._settings_check_changes(*args)

    build_tags_section(app, form, mark_settings_scroll_dirty, trigger_settings_change)
    build_rename_rules_section(app, form, mark_settings_scroll_dirty, trigger_settings_change)

    save_label = app.t("settings.save_button")
    build_save_section(app, form, save_label)

    check_changes = create_settings_change_checker(app, save_label)
    app._settings_check_changes = check_changes
    app.settings_title_var.trace("w", check_changes)
    app.settings_page_size_var.trace("w", check_changes)
    app.settings_language_var.trace("w", check_changes)
    app.rename_rule_pattern_var.trace("w", check_changes)
    app.rename_rule_replace_var.trace("w", check_changes)
    for var in app.column_vars.values():
        var.trace("w", check_changes)

    check_changes()
    app._settings_scroll_job = app.root.after(100, update_scrollregion)

    save_settings = create_save_settings_handler(app, check_changes)
    app.btn_save_settings.configure(command=save_settings)


def init_maintain_movie_info(app, parent):
    movie_service_cls = _get_app_attr("MovieDataCaptureService")
    if not movie_service_cls:
        tk.Label(parent, text=app.t("movie_info.unavailable"), bg=app.colors["bg"], fg="red").pack(pady=20)
        return

    tk.Frame(parent, bg=app.colors["bg"], height=12).pack(fill=tk.X)
    form = tk.Frame(parent, bg=app.colors["bg"])
    form.pack(fill=tk.X, pady=10)

    app.movie_info_placeholder = app.t("movie_info.placeholder")
    app.movie_info_keyword = tk.StringVar()
    entry_container, entry = app.create_styled_entry(form, textvariable=app.movie_info_keyword, width=40, fg="gray", font=app.fonts["base"])
    entry.insert(0, app.movie_info_placeholder)
    entry_container.pack(side=tk.LEFT, padx=8)
    app.attach_entry_context_menu(entry)

    def on_entry_focus_in(_event):
        if app.movie_info_keyword.get() == app.movie_info_placeholder:
            entry.delete(0, tk.END)
            entry.config(fg="black")

    def on_entry_focus_out(_event):
        if not app.movie_info_keyword.get().strip():
            entry.insert(0, app.movie_info_placeholder)
            entry.config(fg="gray")

    entry.bind("<FocusIn>", on_entry_focus_in)
    entry.bind("<FocusOut>", on_entry_focus_out)

    def do_search(silent=False):
        keyword = app.movie_info_keyword.get().strip()
        if not keyword or keyword == app.movie_info_placeholder:
            if not silent:
                messagebox_module = _get_app_attr("messagebox", messagebox)
                messagebox_module.showwarning(app.t("message.title.tip"), app.t("movie_info.input_required"))
            return

        def worker():
            svc = movie_service_cls()
            try:
                rows = svc.search_movie_info(keyword, "all")
                app.root.after(0, lambda: render_results(rows))
            except Exception as e:
                messagebox_module = _get_app_attr("messagebox", messagebox)
                app.root.after(0, lambda: messagebox_module.showerror(app.t("message.title.error"), str(e)))
            finally:
                svc.close()

        import threading
        threading.Thread(target=worker, daemon=False).start()

    app._movie_info_search_timer = None

    def on_key_release(_event):
        if app._movie_info_search_timer:
            app.root.after_cancel(app._movie_info_search_timer)
        app._movie_info_search_timer = app.root.after(600, lambda: do_search(silent=True))

    entry.bind("<KeyRelease>", on_key_release)
    entry.bind("<Return>", lambda _e: do_search(silent=False))

    app.make_action_button(form, text=app.t("movie_info.search_button"), command=lambda: do_search(silent=False)).pack(side=tk.LEFT, padx=4)

    right_actions = tk.Frame(form, bg=app.colors["bg"])
    right_actions.pack(side=tk.RIGHT, padx=8)

    def do_import():
        filedialog_module = _get_app_attr("filedialog", filedialog)
        file_path = filedialog_module.askopenfilename(
            title=app.t("movie_info.import_title"),
            filetypes=[(app.t("movie_info.filetype_label"), "*.txt *.csv"), (app.t("filetype.all"), "*.*")],
        )
        if not file_path:
            return
        dialog = tk.Toplevel(app.root)
        dialog.title(app.t("dialog.wait"))
        dialog.geometry("280x120")
        dialog.update_idletasks()
        x = app.root.winfo_x() + (app.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = app.root.winfo_y() + (app.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.transient(app.root)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        tk.Label(dialog, text=app.t("movie_info.importing"), font=("Helvetica", 12)).pack(pady=30)

        def worker():
            svc = movie_service_cls()
            result = None
            error = None
            try:
                result = svc.import_movie_info_file(file_path)
            except Exception as e:
                error = e
            finally:
                svc.close()

            def on_finish():
                dialog.destroy()
                messagebox_module = _get_app_attr("messagebox", messagebox)
                if error:
                    messagebox_module.showerror(app.t("movie_info.import_failed_title"), str(error))
                    return
                total = result.get("total", 0)
                imported = result.get("imported", 0)
                skipped = result.get("skipped", 0)
                invalid_date = result.get("invalid_date", 0)
                messagebox_module.showinfo(
                    app.t("movie_info.import_done_title"),
                    app.t("movie_info.import_done_summary", total=total, imported=imported, skipped=skipped, invalid_date=invalid_date),
                )
                keyword = app.movie_info_keyword.get().strip()
                if keyword and keyword != app.movie_info_placeholder:
                    do_search(silent=True)

            app.root.after(0, on_finish)

        import threading
        threading.Thread(target=worker, daemon=False).start()

    def do_export():
        filedialog_module = _get_app_attr("filedialog", filedialog)
        file_path = filedialog_module.asksaveasfilename(
            title=app.t("movie_info.export_title"),
            defaultextension=".csv",
            filetypes=[(app.t("filetype.csv"), "*.csv"), (app.t("filetype.all"), "*.*")],
            initialfile="movie_info_export.csv",
        )
        if not file_path:
            return
        dialog = tk.Toplevel(app.root)
        dialog.title(app.t("dialog.wait"))
        dialog.geometry("280x120")
        dialog.update_idletasks()
        x = app.root.winfo_x() + (app.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = app.root.winfo_y() + (app.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.transient(app.root)
        dialog.grab_set()
        dialog.protocol("WM_DELETE_WINDOW", lambda: None)
        tk.Label(dialog, text=app.t("movie_info.exporting"), font=("Helvetica", 12)).pack(pady=30)

        def worker():
            svc = movie_service_cls()
            result = None
            error = None
            try:
                result = svc.export_movie_info_file(file_path)
            except Exception as e:
                error = e
            finally:
                svc.close()

            def on_finish():
                dialog.destroy()
                messagebox_module = _get_app_attr("messagebox", messagebox)
                if error:
                    messagebox_module.showerror(app.t("movie_info.export_failed_title"), str(error))
                    return
                total = result.get("total", 0)
                messagebox_module.showinfo(app.t("movie_info.export_done_title"), app.t("movie_info.export_done_summary", total=total))

            app.root.after(0, on_finish)

        import threading
        threading.Thread(target=worker, daemon=False).start()

    app.make_action_button(right_actions, text=app.t("movie_info.import_button"), command=do_import).pack(side=tk.LEFT, padx=4)
    app.make_action_button(right_actions, text=app.t("movie_info.export_button"), command=do_export).pack(side=tk.LEFT, padx=4)

    _table, render_results = build_movie_info_table(app, parent)


def init_maintain_import(app, parent):
    tk.Frame(parent, bg=app.colors["bg"], height=12).pack(fill=tk.X)
    form = tk.Frame(parent, bg=app.colors["bg"])
    form.pack(fill=tk.X, pady=10)

    tk.Label(form, text=app.t("maintain.scan_path"), bg=app.colors["bg"], fg=app.colors["gray800"], font=app.fonts["base"]).pack(side=tk.LEFT)
    app.scan_dir_var = tk.StringVar()
    entry_container, entry = app.create_styled_entry(form, textvariable=app.scan_dir_var, width=50, font=app.fonts["base"])
    entry_container.pack(side=tk.LEFT, padx=8)
    app.attach_entry_context_menu(entry)

    def choose_dir():
        current = (app.scan_dir_var.get() or "").strip()
        os_module = _get_app_attr("os", os)
        initialdir = current if current and os_module.path.isdir(current) else app._last_scan_dir
        filedialog_module = _get_app_attr("filedialog", filedialog)
        d = filedialog_module.askdirectory(initialdir=initialdir)
        if d:
            app.scan_dir_var.set(d)
            app._last_scan_dir = d

    app.make_action_button(form, text=app.t("maintain.choose_dir"), command=choose_dir).pack(side=tk.LEFT, padx=8)

    status = tk.Label(parent, text="", bg=app.colors["bg"], fg=app.colors["gray700"])
    status.pack(fill=tk.X, pady=6)

    log_frame = tk.Frame(parent, bg=app.colors["bg"])
    log_frame.pack(fill=tk.BOTH, expand=True, pady=6)
    log_text = tk.Text(log_frame, height=10, bg=app.colors["white"], fg=app.colors["gray800"], wrap="none")
    vsb = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    log_text.configure(yscrollcommand=vsb.set)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    pb = ttk.Progressbar(parent, mode="determinate", length=360, style="Blue.Horizontal.TProgressbar")

    def append_log(line: str):
        log_text.insert(tk.END, line + "\n")
        try:
            max_lines = app._log_max_lines
            line_count = int(log_text.index("end-1c").split(".")[0])
            if line_count > max_lines:
                log_text.delete("1.0", f"{line_count - max_lines + 1}.0")
        except Exception:
            pass
        log_text.see(tk.END)

    def do_filename_adjustment():
        path = app.scan_dir_var.get().strip()
        if not path:
            messagebox_module = _get_app_attr("messagebox", messagebox)
            messagebox_module.showwarning(app.t("message.title.tip"), app.t("maintain.select_path_warning"))
            return

        log_text.delete("1.0", tk.END)
        status.configure(text=app.t("maintain.status.prepare_adjust", path=path))
        pb.pack(anchor="w", pady=4)
        pb.configure(value=0)

        def worker():
            def on_progress(current, total, message):
                progress = (current / total) * 100 if total > 0 else 0
                display_message = message
                if isinstance(message, dict):
                    key = message.get("key")
                    if key:
                        params = {k: v for k, v in message.items() if k != "key"}
                        display_message = app.t(key, **params)
                elif isinstance(message, str):
                    prefix = "Processing "
                    if message.startswith(prefix) and message.endswith("..."):
                        filename = message[len(prefix):-3]
                        display_message = app.t("maintain.status.processing", filename=filename)

                def update_ui():
                    pb.configure(value=progress)
                    append_log(display_message)
                    status.configure(text=app.t("maintain.status.adjusting", current=current, total=total))

                app.root.after(0, update_ui)
                time.sleep(0.1)

            try:
                rules_path = app._get_rename_rules_path()
                rules_path_str = str(rules_path) if rules_path.exists() else None
                run_filename_adjustment_fn = _get_app_attr("run_filename_adjustment")
                results = run_filename_adjustment_fn(
                    path,
                    flatten_output=True,
                    progress_callback=on_progress,
                    rules_path=rules_path_str,
                )
                _final_log_lines = results.get("log_lines", [])
            except Exception:
                _final_log_lines = None

            def finish():
                pb.pack_forget()
                status.configure(text=app.t("maintain.status.adjust_done"))

            app.root.after(0, finish)

        import threading
        threading.Thread(target=worker, daemon=False).start()

    def do_maintain():
        path = app.scan_dir_var.get().strip()
        if not path:
            messagebox_module = _get_app_attr("messagebox", messagebox)
            messagebox_module.showwarning(app.t("message.title.tip"), app.t("maintain.select_path_warning"))
            return

        log_text.delete("1.0", tk.END)
        status.configure(text=app.t("maintain.status.prepare_scan", path=path))
        pb.pack(anchor="w", pady=4)
        pb.configure(value=0)

        def worker():
            old_stdout = sys.stdout
            class Redirector:
                def __init__(self, callback):
                    self.callback = callback
                def write(self, s):
                    if s.strip():
                        self.callback(s)
                def flush(self):
                    pass

            def on_log(s):
                app.root.after(0, lambda: append_log(s.strip()))

            def on_progress(current, total, message):
                progress = (current / total) * 100 if total > 0 else 0
                def update_pb():
                    pb.configure(value=progress)
                app.root.after(0, update_pb)

            result = None
            error = None
            try:
                sys.stdout = Redirector(on_log)
                start_maintain_fn = _get_app_attr("start_maintain")
                result = start_maintain_fn(path, progress_callback=on_progress)
            except Exception as e:
                error = e
            finally:
                sys.stdout = old_stdout

            def finish():
                pb.pack_forget()
                messagebox_module = _get_app_attr("messagebox", messagebox)
                if error:
                    messagebox_module.showerror(app.t("message.title.system_error"), app.t("maintain.error.unhandled", error=error))
                    status.configure(text=app.t("maintain.status.system_error", error=error))
                    return

                if result and result.get("success"):
                    status.configure(text=app.t("maintain.status.completed", count=result.get("processed_count")))
                else:
                    msg = result.get("message") if result else app.t("maintain.error.unknown")
                    messagebox_module.showerror(app.t("message.title.failed"), msg)
                    status.configure(text=app.t("maintain.status.failed", message=msg))

            app.root.after(0, finish)

        import threading
        threading.Thread(target=worker, daemon=False).start()

    btn_row = tk.Frame(parent, bg=app.colors["bg"])
    btn_row.pack(anchor="w", pady=4)
    app.make_action_button(btn_row, text=app.t("maintain.filename_adjust"), command=do_filename_adjustment).pack(side=tk.LEFT, padx=6)
    app.make_action_button(btn_row, text=app.t("maintain.ingest"), command=do_maintain).pack(side=tk.LEFT, padx=6)


def init_maintain_data_backup(app, parent):
    tk.Frame(parent, bg=app.colors["bg"], height=12).pack(fill=tk.X)
    form = tk.Frame(parent, bg=app.colors["bg"])
    form.pack(fill=tk.BOTH, expand=True, pady=10)

    action_row = tk.Frame(form, bg=app.colors["bg"])
    action_row.pack(anchor="w", padx=20, pady=(0, 8))
    status = tk.Label(form, text=app.t("backup.status.ready"), bg=app.colors["bg"], fg=app.colors["gray700"])
    status.pack(fill=tk.X, padx=20, pady=(0, 6))

    log_frame = tk.Frame(form, bg=app.colors["bg"])
    log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 6))
    log_text = tk.Text(log_frame, height=10, bg=app.colors["white"], fg=app.colors["gray800"], wrap="none")
    log_vsb = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    log_text.configure(yscrollcommand=log_vsb.set)
    log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    log_vsb.pack(side=tk.RIGHT, fill=tk.Y)

    desc = tk.Label(
        form,
        text=app.t("backup.desc"),
        bg=app.colors["bg"],
        fg=app.colors["gray700"],
        wraplength=760,
        justify="left",
    )
    desc.pack(anchor="w", padx=20, pady=(0, 8))

    def append_log(line: str):
        log_text.insert(tk.END, line + "\n")
        log_text.see(tk.END)

    def schedule_log_lines(lines: list[str], delay_ms: int = 200, on_done=None):
        if not lines:
            if on_done:
                on_done()
            return

        def step(index=0):
            if index >= len(lines):
                if on_done:
                    on_done()
                return
            append_log(lines[index])
            app.root.after(delay_ms, lambda: step(index + 1))

        step()

    def _format_log_value(value):
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def _load_backup_payload(path: str):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            return {}

    def _build_backup_log_lines(payload: dict):
        data = payload.get("data", {}) or {}
        database_payload = data.get("database", {}) or {}
        settings_payload = data.get("settings", {}) or {}
        rename_payload = data.get("rename_rules", {}) or {}

        tables = [
            t.get("name") for t in (database_payload.get("tables", []) or []) if isinstance(t, dict) and t.get("name")
        ]
        rename_settings = rename_payload.get("settings", {}) or {}
        rename_rules = rename_payload.get("rename_rules", []) or []

        lines = []
        for name in tables:
            lines.append(app.t("backup.log.table", name=name))
        if settings_payload:
            lines.append(app.t("backup.log.settings_file"))
            for key in sorted(settings_payload.keys()):
                lines.append(app.t("backup.log.settings_key", item=key))
        if rename_payload:
            lines.append(app.t("backup.log.rules_file"))
            for key in sorted(rename_settings.keys()):
                lines.append(app.t("backup.log.rule_setting", item=key, value=_format_log_value(rename_settings.get(key))))
            for rule in rename_rules:
                if not isinstance(rule, dict):
                    continue
                pattern = rule.get("pattern", "")
                replace = rule.get("replace", "")
                if pattern or replace:
                    lines.append(app.t("backup.log.rule_item", pattern=pattern, replace=replace))

        config_files = (1 if settings_payload else 0) + (1 if rename_payload else 0)
        return lines, len(tables), config_files

    def _build_current_state_log_lines():
        tables = []
        try:
            db_path = get_default_backup_paths().get("db_path")
            if db_path:
                storage = SQLiteStorage(str(db_path))
                tables = list((storage.get_table_info() or {}).keys())
                storage.close()
        except Exception:
            tables = []

        settings_payload = {}
        try:
            settings_payload = dict(getattr(app, "_settings", None) or app.settings._settings or {})
        except Exception:
            settings_payload = {}

        rename_rules = []
        rename_settings = {}
        try:
            rules_path = app._get_rename_rules_path()
            rename_rules, rename_settings = load_rules_config(rules_path)
        except Exception:
            rename_rules, rename_settings = [], {}

        lines = []
        for name in sorted(tables):
            lines.append(app.t("backup.log.table", name=name))
        if settings_payload:
            lines.append(app.t("backup.log.settings_file"))
            for item in sorted(settings_payload.keys()):
                lines.append(app.t("backup.log.settings_key", item=item))
        if rename_settings or rename_rules:
            lines.append(app.t("backup.log.rules_file"))
            for item in sorted(rename_settings.keys()):
                lines.append(app.t("backup.log.rule_setting", item=item, value=_format_log_value(rename_settings.get(item))))
            for rule in rename_rules:
                if not isinstance(rule, dict):
                    continue
                pattern = rule.get("pattern", "")
                replace = rule.get("replace", "")
                if pattern or replace:
                    lines.append(app.t("backup.log.rule_item", pattern=pattern, replace=replace))

        config_files = (1 if settings_payload else 0) + (1 if rename_settings or rename_rules else 0)
        return lines, len(tables), config_files

    def set_busy(is_busy: bool):
        state = "disabled" if is_busy else "normal"
        export_btn.configure(state=state)
        import_btn.configure(state=state)
        init_btn.configure(state=state)

    def choose_export_path():
        filedialog_module = _get_app_attr("filedialog", filedialog)
        file_path = filedialog_module.asksaveasfilename(
            title=app.t("backup.export_title"),
            defaultextension=".json",
            filetypes=[(app.t("backup.filetype.json"), "*.json"), (app.t("filetype.all"), "*.*")],
            initialfile="data_backup.json",
        )
        return file_path or ""

    def choose_import_path():
        filedialog_module = _get_app_attr("filedialog", filedialog)
        file_path = filedialog_module.askopenfilename(
            title=app.t("backup.import_title"),
            filetypes=[(app.t("backup.filetype.json"), "*.json"), (app.t("filetype.all"), "*.*")],
        )
        return file_path or ""

    def do_export():
        file_path = choose_export_path()
        if not file_path:
            return
        log_text.delete("1.0", tk.END)
        status.configure(text=app.t("backup.status.exporting"))
        set_busy(True)

        def worker():
            error = None
            result = None
            try:
                app_version = None
                if isinstance(app.app_meta, dict):
                    app_version = app.app_meta.get("version")
                result = export_backup(file_path, app_version=app_version)
            except Exception as exc:
                error = exc

            def finish():
                set_busy(False)
                if error:
                    status.configure(text=app.t("backup.status.failed"))
                    messagebox_module = _get_app_attr("messagebox", messagebox)
                    messagebox_module.showerror(app.t("message.title.failed"), str(error))
                    return
                payload = _load_backup_payload(file_path)
                lines, table_count, config_files = _build_backup_log_lines(payload)
                lines = [app.t("backup.export_success", path=file_path), *lines]
                summary_text = app.t("backup.status.exported_summary", tables=table_count, configs=config_files)

                def after_logs():
                    status.configure(text=summary_text)

                schedule_log_lines(lines, on_done=after_logs)

            app.root.after(0, finish)

        import threading
        threading.Thread(target=worker, daemon=False).start()

    def do_import():
        file_path = choose_import_path()
        if not file_path:
            return
        messagebox_module = _get_app_attr("messagebox", messagebox)
        if not messagebox_module.askyesno(app.t("message.title.tip"), app.t("backup.import_confirm_init")):
            return
        log_text.delete("1.0", tk.END)
        status.configure(text=app.t("backup.status.importing"))
        set_busy(True)

        def worker():
            error = None
            result = None
            try:
                result = import_backup(file_path)
            except Exception as exc:
                error = exc

            def finish():
                set_busy(False)
                if error:
                    status.configure(text=app.t("backup.status.failed"))
                    messagebox_module.showerror(app.t("message.title.failed"), str(error))
                    return
                try:
                    import copy

                    app.settings._settings = copy.deepcopy(app.settings.DEFAULT_SETTINGS)
                    app.settings.load_settings()
                except Exception:
                    pass
                if hasattr(app, "_current_tags"):
                    app._current_tags = list(app.settings.tags)
                    app._current_tags.sort()
                    if hasattr(app, "tags_cb"):
                        app.tags_cb.configure(values=app._current_tags)
                        app.tags_cb.set("")
                    if hasattr(app, "tag_name_var"):
                        app.tag_name_var.set("")
                try:
                    rules_path = app._get_rename_rules_path()
                    app._rename_rules, app._rename_rules_settings = load_rules_config(rules_path)
                    app._rename_rules = [r for r in app._rename_rules if r.get("pattern")]
                    app._rename_rules_original = [dict(r) for r in app._rename_rules]
                    if hasattr(app, "rename_rules_cb"):
                        values = [r.get("pattern", "") for r in app._rename_rules if r.get("pattern")]
                        app.rename_rules_cb.configure(values=values)
                        app.rename_rules_cb.set("")
                    if hasattr(app, "rename_rule_pattern_var"):
                        app.rename_rule_pattern_var.set("")
                    if hasattr(app, "rename_rule_replace_var"):
                        app.rename_rule_replace_var.set("")
                except Exception:
                    pass
                payload = _load_backup_payload(file_path)
                lines, table_count, config_files = _build_backup_log_lines(payload)
                lines = [app.t("backup.import_success", path=file_path), *lines]
                summary_text = app.t("backup.status.imported_summary", tables=table_count, configs=config_files)

                def after_logs():
                    status.configure(text=summary_text)
                    messagebox_module.showinfo(app.t("message.title.tip"), app.t("backup.import_restart_tip"))

                schedule_log_lines(lines, on_done=after_logs)

            app.root.after(0, finish)

        import threading
        threading.Thread(target=worker, daemon=False).start()

    def do_initialize():
        messagebox_module = _get_app_attr("messagebox", messagebox)
        if not messagebox_module.askyesno(app.t("message.title.tip"), app.t("backup.init_confirm")):
            return
        log_text.delete("1.0", tk.END)
        status.configure(text=app.t("backup.status.initializing"))
        set_busy(True)

        def worker():
            error = None
            result = None
            try:
                try:
                    from ui import services as ui_services

                    svc = getattr(ui_services, "video_service", None)
                    if svc is not None and getattr(svc, "storage", None):
                        svc.storage.close()
                        svc.storage = None
                        svc.merge_manager = None
                except Exception:
                    pass
                result = initialize_data()
            except Exception as exc:
                error = exc

            def finish():
                set_busy(False)
                if error:
                    status.configure(text=app.t("backup.status.failed"))
                    messagebox_module.showerror(app.t("message.title.failed"), str(error))
                    return
                try:
                    import copy

                    app.settings._settings = copy.deepcopy(app.settings.DEFAULT_SETTINGS)
                    app.settings.load_settings()
                except Exception:
                    pass
                if hasattr(app, "_current_tags"):
                    app._current_tags = list(app.settings.tags)
                    app._current_tags.sort()
                    if hasattr(app, "tags_cb"):
                        app.tags_cb.configure(values=app._current_tags)
                        app.tags_cb.set("")
                    if hasattr(app, "tag_name_var"):
                        app.tag_name_var.set("")
                try:
                    rules_path = app._get_rename_rules_path()
                    app._rename_rules, app._rename_rules_settings = load_rules_config(rules_path)
                    app._rename_rules = [r for r in app._rename_rules if r.get("pattern")]
                    app._rename_rules_original = [dict(r) for r in app._rename_rules]
                    if hasattr(app, "rename_rules_cb"):
                        values = [r.get("pattern", "") for r in app._rename_rules if r.get("pattern")]
                        app.rename_rules_cb.configure(values=values)
                        app.rename_rules_cb.set("")
                    if hasattr(app, "rename_rule_pattern_var"):
                        app.rename_rule_pattern_var.set("")
                    if hasattr(app, "rename_rule_replace_var"):
                        app.rename_rule_replace_var.set("")
                except Exception:
                    pass
                lines, table_count, config_files = _build_current_state_log_lines()
                summary_text = app.t("backup.status.initialized_summary", tables=table_count, configs=config_files)

                def after_logs():
                    status.configure(text=summary_text)

                schedule_log_lines(lines, on_done=after_logs)

            app.root.after(0, finish)

        import threading
        threading.Thread(target=worker, daemon=False).start()

    export_btn = app.make_action_button(action_row, text=app.t("backup.export_button"), command=do_export)
    export_btn.pack(side=tk.LEFT, padx=(0, 10))
    import_btn = app.make_action_button(action_row, text=app.t("backup.import_button"), command=do_import)
    import_btn.pack(side=tk.LEFT, padx=(0, 10))
    init_btn = app.make_action_button(action_row, text=app.t("backup.init_button"), command=do_initialize)
    init_btn.pack(side=tk.LEFT)
