from tkinter import messagebox

from tools.filename_formatter.formatter import save_rules_config
from ui.tkinter.table_helpers import refresh_query_page_columns


def create_settings_change_checker(app, save_label):
    def check_changes(*args):
        title_changed = app.settings_title_var.get().strip() != app.settings.app_title
        tags_changed = set(app._current_tags) != set(app.settings.tags)

        language_label_to_value = app.get_language_label_to_value()
        current_language = language_label_to_value.get(app.settings_language_var.get(), "zh_CN")
        language_changed = current_language != app.settings.language

        try:
            current_size = app.settings_page_size_var.get()
        except Exception:
            current_size = 0
        size_changed = current_size != app.settings.page_size

        current_cols = []
        for col, var in app.column_vars.items():
            if var.get():
                current_cols.append(col)
        if "video" not in current_cols:
            current_cols.insert(0, "video")

        default_order = getattr(app, "_settings_default_order", ["video", "actress", "tags", "file_path", "file_size", "duration", "resolution", "updated_time", "preference"])
        current_cols.sort(key=lambda x: default_order.index(x) if x in default_order else 999)
        cols_changed = current_cols != app.settings.visible_columns

        current_rules = [
            {"pattern": str(r.get("pattern", "")).strip(), "replace": "" if r.get("replace", "") is None else str(r.get("replace", ""))}
            for r in app._rename_rules
            if str(r.get("pattern", "")).strip()
        ]
        original_rules = [
            {"pattern": str(r.get("pattern", "")).strip(), "replace": "" if r.get("replace", "") is None else str(r.get("replace", ""))}
            for r in app._rename_rules_original
            if str(r.get("pattern", "")).strip()
        ]
        rules_changed = current_rules != original_rules

        button_color = app.colors["gray800"]
        if title_changed or tags_changed or size_changed or cols_changed or language_changed or rules_changed:
            app.btn_save_settings.configure(fg=button_color, text=f"{save_label}*")
        else:
            app.btn_save_settings.configure(fg=button_color, text=save_label)

    return check_changes


def create_save_settings_handler(app, check_changes):
    def save_settings():
        new_title = app.settings_title_var.get().strip()
        new_page_size = app.settings_page_size_var.get()
        language_label_to_value = app.get_language_label_to_value()
        new_language = language_label_to_value.get(app.settings_language_var.get(), "zh_CN")

        if not new_title:
            messagebox.showwarning(app.t("message.title.tip"), app.t("settings.title_required"))
            return

        try:
            if new_page_size < 1:
                messagebox.showwarning(app.t("message.title.tip"), app.t("settings.page_size_gt_zero"))
                return
        except Exception:
            messagebox.showwarning(app.t("message.title.tip"), app.t("settings.page_size_numeric"))
            return

        app.settings.app_title = new_title
        app.root.title(new_title)
        if hasattr(app, "brand_label"):
            app.brand_label.configure(text=new_title)

        app.settings.page_size = new_page_size

        previous_language = app.settings.language
        app.settings.language = new_language

        new_cols = []
        for col, var in app.column_vars.items():
            if var.get():
                new_cols.append(col)
        if "video" not in new_cols:
            new_cols.insert(0, "video")
        default_order = getattr(app, "_settings_default_order", ["video", "actress", "tags", "file_path", "file_size", "duration", "resolution", "updated_time", "preference"])
        new_cols.sort(key=lambda x: default_order.index(x) if x in default_order else 999)
        app.settings.visible_columns = new_cols

        app.settings.tags = app._current_tags
        app.settings.save_settings()

        rules_saved = save_rules_config(app._get_rename_rules_path(), app._rename_rules, app._rename_rules_settings)
        if rules_saved:
            app._rename_rules_original = [dict(r) for r in app._rename_rules]
        else:
            messagebox.showwarning(app.t("message.title.error"), app.t("settings.rename_rules_save_failed"))

        language_changed = previous_language != new_language
        if language_changed:
            app._apply_language(new_language)
            return

        check_changes()
        refresh_query_page_columns(app)

    return save_settings
