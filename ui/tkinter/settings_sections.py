import tkinter as tk
from tkinter import ttk, messagebox

from tools.filename_formatter.formatter import load_rules_config


def build_tags_section(app, form, mark_settings_scroll_dirty, on_change):
    tk.Frame(form, height=1, bg=app.colors["gray200"]).pack(fill=tk.X, padx=20, pady=15)
    tk.Label(form, text=app.t("settings.tags_section"), bg=app.colors["bg"], fg=app.colors["gray800"], font=("Helvetica", 14, "bold")).pack(anchor="w", padx=20, pady=(0, 8))

    tags_frame = tk.Frame(form, bg=app.colors["bg"])
    tags_frame.pack(fill=tk.X, padx=20)

    tk.Label(tags_frame, text=app.t("settings.tags_select"), bg=app.colors["bg"]).grid(row=0, column=0, sticky="w", pady=5)
    app.tags_cb = ttk.Combobox(tags_frame, width=40, state="readonly")
    app.tags_cb.grid(row=0, column=1, sticky="w", padx=10, pady=5)

    tk.Label(tags_frame, text=app.t("settings.tags_name"), bg=app.colors["bg"]).grid(row=1, column=0, sticky="w", pady=5)
    app.tag_name_var = tk.StringVar()
    tag_entry_container, tag_entry = app.create_styled_entry(tags_frame, textvariable=app.tag_name_var, width=42, font=app.fonts["base"])
    tag_entry_container.grid(row=1, column=1, sticky="w", padx=10, pady=5)
    app.attach_entry_context_menu(tag_entry)

    btn_frame = tk.Frame(tags_frame, bg=app.colors["bg"])
    btn_frame.grid(row=2, column=1, sticky="w", padx=10, pady=10)

    app._current_tags = list(app.settings.tags)
    app._current_tags.sort()
    app.tags_cb.configure(postcommand=lambda: app.tags_cb.configure(values=app._current_tags))

    def refresh_tags_ui(select_val=None):
        app._current_tags.sort()
        if select_val:
            app.tags_cb.set(select_val)
            app.tag_name_var.set(select_val)
        else:
            app.tags_cb.set('')
            app.tag_name_var.set('')
        on_change()
        mark_settings_scroll_dirty()

    def on_tag_select(event):
        selected = app.tags_cb.get()
        if selected:
            app.tag_name_var.set(selected)

    app.tags_cb.bind("<<ComboboxSelected>>", on_tag_select)

    def add_tag():
        val = app.tag_name_var.get().strip()
        if not val:
            messagebox.showwarning(app.t("message.title.tip"), app.t("settings.tags_name_required"))
            return
        if val in app._current_tags:
            messagebox.showwarning(app.t("message.title.tip"), app.t("settings.tags_exists"))
            return
        app._current_tags.append(val)
        refresh_tags_ui(select_val=val)

    def update_tag():
        old_val = app.tags_cb.get()
        new_val = app.tag_name_var.get().strip()
        if not old_val:
            return
        if not new_val:
            messagebox.showwarning(app.t("message.title.tip"), app.t("settings.tags_name_required"))
            return
        if new_val != old_val and new_val in app._current_tags:
            messagebox.showwarning(app.t("message.title.tip"), app.t("settings.tags_target_exists"))
            return
        idx = app._current_tags.index(old_val)
        app._current_tags[idx] = new_val
        refresh_tags_ui(select_val=new_val)

    def delete_tag():
        val = app.tags_cb.get()
        if val and val in app._current_tags:
            app._current_tags.remove(val)
            refresh_tags_ui(select_val=None)

    app.make_action_button(btn_frame, text=app.t("settings.tags_add"), command=add_tag).pack(side=tk.LEFT, padx=(0, 5))
    app.make_action_button(btn_frame, text=app.t("settings.tags_update"), command=update_tag).pack(side=tk.LEFT, padx=5)
    app.make_action_button(btn_frame, text=app.t("settings.tags_delete"), command=delete_tag).pack(side=tk.LEFT, padx=5)


def build_rename_rules_section(app, form, mark_settings_scroll_dirty, on_change):
    tk.Frame(form, height=1, bg=app.colors["gray200"]).pack(fill=tk.X, padx=20, pady=15)
    tk.Label(form, text=app.t("settings.rename_rules_section"), bg=app.colors["bg"], fg=app.colors["gray800"], font=("Helvetica", 14, "bold")).pack(anchor="w", padx=20, pady=(0, 8))

    rules_frame = tk.Frame(form, bg=app.colors["bg"])
    rules_frame.pack(fill=tk.X, padx=20)

    rules_path = app._get_rename_rules_path()
    app._rename_rules, app._rename_rules_settings = load_rules_config(rules_path)
    normalized_rules = []
    for rule in app._rename_rules:
        if not isinstance(rule, dict):
            continue
        pattern = str(rule.get("pattern", "")).strip()
        if not pattern:
            continue
        replace = rule.get("replace", "")
        normalized_rules.append({"pattern": pattern, "replace": "" if replace is None else str(replace)})
    app._rename_rules = normalized_rules
    app._rename_rules_original = [dict(r) for r in app._rename_rules]

    tk.Label(rules_frame, text=app.t("settings.rename_rule_select"), bg=app.colors["bg"]).grid(row=0, column=0, sticky="w", pady=5)
    app.rename_rules_cb = ttk.Combobox(rules_frame, width=40, state="readonly")
    app.rename_rules_cb.grid(row=0, column=1, sticky="w", padx=10, pady=5)

    tk.Label(rules_frame, text=app.t("settings.rename_rule_pattern"), bg=app.colors["bg"]).grid(row=1, column=0, sticky="w", pady=5)
    app.rename_rule_pattern_var = tk.StringVar()
    pattern_entry_container, pattern_entry = app.create_styled_entry(rules_frame, textvariable=app.rename_rule_pattern_var, width=42, font=app.fonts["base"])
    pattern_entry_container.grid(row=1, column=1, sticky="w", padx=10, pady=5)
    app.attach_entry_context_menu(pattern_entry)

    tk.Label(rules_frame, text=app.t("settings.rename_rule_replace"), bg=app.colors["bg"]).grid(row=2, column=0, sticky="w", pady=5)
    app.rename_rule_replace_var = tk.StringVar()
    replace_entry_container, replace_entry = app.create_styled_entry(rules_frame, textvariable=app.rename_rule_replace_var, width=42, font=app.fonts["base"])
    replace_entry_container.grid(row=2, column=1, sticky="w", padx=10, pady=5)
    app.attach_entry_context_menu(replace_entry)

    rules_btn_frame = tk.Frame(rules_frame, bg=app.colors["bg"])
    rules_btn_frame.grid(row=3, column=1, sticky="w", padx=10, pady=10)

    def refresh_rules_ui(select_val=None):
        app._rename_rules = [r for r in app._rename_rules if r.get("pattern")]
        values = [r.get("pattern", "") for r in app._rename_rules if r.get("pattern")]
        app.rename_rules_cb.configure(values=values)
        if select_val:
            app.rename_rules_cb.set(select_val)
            app.rename_rule_pattern_var.set(select_val)
            replace_val = ""
            for r in app._rename_rules:
                if r.get("pattern") == select_val:
                    replace_val = r.get("replace", "")
                    break
            app.rename_rule_replace_var.set(replace_val)
        else:
            app.rename_rules_cb.set("")
            app.rename_rule_pattern_var.set("")
            app.rename_rule_replace_var.set("")
        on_change()
        mark_settings_scroll_dirty()

    def on_rule_select(event):
        selected = app.rename_rules_cb.get()
        if selected:
            app.rename_rule_pattern_var.set(selected)
            for r in app._rename_rules:
                if r.get("pattern") == selected:
                    app.rename_rule_replace_var.set(r.get("replace", ""))
                    break

    app.rename_rules_cb.bind("<<ComboboxSelected>>", on_rule_select)

    def add_rule():
        pattern = app.rename_rule_pattern_var.get().strip()
        replace = app.rename_rule_replace_var.get()
        if not pattern:
            messagebox.showwarning(app.t("message.title.tip"), app.t("settings.rename_rule_pattern_required"))
            return
        if any(r.get("pattern") == pattern for r in app._rename_rules):
            messagebox.showwarning(app.t("message.title.tip"), app.t("settings.rename_rule_exists"))
            return
        app._rename_rules.append({"pattern": pattern, "replace": "" if replace is None else replace})
        refresh_rules_ui(select_val=pattern)

    def update_rule():
        old_val = app.rename_rules_cb.get()
        if not old_val:
            return
        pattern = app.rename_rule_pattern_var.get().strip()
        replace = app.rename_rule_replace_var.get()
        if not pattern:
            messagebox.showwarning(app.t("message.title.tip"), app.t("settings.rename_rule_pattern_required"))
            return
        if pattern != old_val and any(r.get("pattern") == pattern for r in app._rename_rules):
            messagebox.showwarning(app.t("message.title.tip"), app.t("settings.rename_rule_target_exists"))
            return
        for idx, rule in enumerate(app._rename_rules):
            if rule.get("pattern") == old_val:
                app._rename_rules[idx] = {"pattern": pattern, "replace": "" if replace is None else replace}
                break
        refresh_rules_ui(select_val=pattern)

    def delete_rule():
        val = app.rename_rules_cb.get()
        if val:
            app._rename_rules = [r for r in app._rename_rules if r.get("pattern") != val]
            refresh_rules_ui(select_val=None)

    app.make_action_button(rules_btn_frame, text=app.t("settings.rename_rule_add"), command=add_rule).pack(side=tk.LEFT, padx=(0, 5))
    app.make_action_button(rules_btn_frame, text=app.t("settings.rename_rule_update"), command=update_rule).pack(side=tk.LEFT, padx=5)
    app.make_action_button(rules_btn_frame, text=app.t("settings.rename_rule_delete"), command=delete_rule).pack(side=tk.LEFT, padx=5)

    refresh_rules_ui()


def build_basic_settings_section(app, form):
    tk.Label(form, text=app.t("settings.app_title"), bg=app.colors["bg"], fg=app.colors["gray800"], font=app.fonts["bold"]).pack(anchor="w", padx=20, pady=(0, 8))
    app.settings_title_var = tk.StringVar(value=app.settings.app_title)
    title_entry_container, title_entry = app.create_styled_entry(form, textvariable=app.settings_title_var, width=50, font=app.fonts["base"])
    title_entry_container.pack(anchor="w", padx=20, pady=(0, 15))
    app.attach_entry_context_menu(title_entry)

    tk.Label(form, text=app.t("settings.language"), bg=app.colors["bg"], fg=app.colors["gray800"], font=app.fonts["bold"]).pack(anchor="w", padx=20, pady=(0, 8))
    language_labels = app.get_language_labels()
    app.settings_language_var = tk.StringVar(value=language_labels.get(app.settings.language, language_labels["zh_CN"]))
    language_cb = ttk.Combobox(form, textvariable=app.settings_language_var, width=16, state="readonly", font=app.fonts["base"])
    language_cb["values"] = tuple(language_labels.values())
    language_cb.pack(anchor="w", padx=20, pady=(0, 15), ipady=6)


def build_query_settings_section(app, form):
    tk.Frame(form, height=1, bg=app.colors["gray200"]).pack(fill=tk.X, padx=20, pady=15)
    tk.Label(form, text=app.t("settings.query_section"), bg=app.colors["bg"], fg=app.colors["gray800"], font=app.fonts["bold"]).pack(anchor="w", padx=20, pady=(0, 8))

    size_frame = tk.Frame(form, bg=app.colors["bg"])
    size_frame.pack(anchor="w", padx=20)
    tk.Label(size_frame, text=app.t("settings.page_size"), bg=app.colors["bg"], font=app.fonts["base"]).pack(side=tk.LEFT)
    app.settings_page_size_var = tk.IntVar(value=app.settings.page_size)
    size_entry_container, size_entry = app.create_styled_entry(size_frame, textvariable=app.settings_page_size_var, width=10, font=app.fonts["base"])
    size_entry_container.pack(side=tk.LEFT, padx=10)
    app.attach_entry_context_menu(size_entry)

    tk.Label(form, text=app.t("settings.visible_columns"), bg=app.colors["bg"], font=app.fonts["base"]).pack(anchor="w", padx=20, pady=(15, 8))

    cols_frame = tk.Frame(form, bg=app.colors["bg"])
    cols_frame.pack(anchor="w", padx=20)

    column_labels = app.get_column_labels()
    available_columns = [
        ("video", column_labels["video"]),
        ("actress", column_labels["actress"]),
        ("tags", column_labels["tags"]),
        ("file_path", column_labels["file_path"]),
        ("file_size", column_labels["file_size"]),
        ("duration", column_labels["duration"]),
        ("resolution", column_labels["resolution"]),
        ("updated_time", column_labels["updated_time"]),
        ("preference", column_labels["preference"]),
    ]

    app.column_vars = {}
    current_cols = app.settings.visible_columns

    r, c = 0, 0
    for col_key, col_label in available_columns:
        var = tk.BooleanVar(value=col_key in current_cols)
        state = tk.DISABLED if col_key == "video" else tk.NORMAL
        if col_key == "video":
            var.set(True)
        cb = tk.Checkbutton(cols_frame, text=col_label, variable=var, bg=app.colors["bg"], state=state, font=("Helvetica", 11))
        cb.grid(row=r, column=c, sticky="w", padx=(0, 15), pady=5)
        app.column_vars[col_key] = var
        c += 1
        if c > 4:
            c = 0
            r += 1

    app._settings_default_order = ["video", "actress", "tags", "file_path", "file_size", "duration", "resolution", "updated_time", "preference"]


def build_save_section(app, form, save_label):
    tk.Frame(form, height=1, bg=app.colors["gray200"]).pack(fill=tk.X, padx=20, pady=20)
    footer_frame = tk.Frame(form, bg=app.colors["bg"])
    footer_frame.pack(fill=tk.X, padx=20)
    app.btn_save_settings = app.make_action_button(footer_frame, text=save_label, font=("Helvetica", 12), padx=20, pady=8)
    app.btn_save_settings.pack(side=tk.LEFT)
