from __future__ import annotations

import sys
from pathlib import Path
import re
import os
import json
from datetime import datetime
import time

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PROJECT_ROOT = Path(sys._MEIPASS).resolve()
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

if __package__ is None or __package__ == "":
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.append(str(PROJECT_ROOT))

if "ui.tkinter.app" not in sys.modules:
    sys.modules["ui.tkinter.app"] = sys.modules[__name__]

import tkinter as tk
from tkinter import ttk, filedialog
from tools.path_utils import get_config_path
from tools.filename_formatter.formatter import run_filename_adjustment
from ui.tkinter.i18n import I18n
from ui.tkinter.query_page import build_query_page
from ui.tkinter.layout import add_sidebar_btn, build_layout, show_about
from ui.tkinter.maintain_settings_page import init_maintain_import, init_maintain_movie_info, init_maintain_settings
from ui.tkinter.maintain_buttons import build_maintain_manage_tools
from ui.tkinter.table_helpers import build_maintain_manage_table, render_table, open_video_list_window
from ui.tkinter.ui_helpers import (
    attach_entry_context_menu,
    create_styled_entry,
    get_system_video_players,
    handle_table_double_click,
    handle_table_right_click,
    init_styles,
    make_action_button,
    open_file_manager,
    play_video,
    play_video_with_player,
)

try:
    from ui.services import search_videos, search_videos_paged, start_maintain, random_videos, latest_videos, latest_videos_paged, broken_videos, set_video_preference, update_video_actress
except Exception as e:
    print(f"导入服务失败: {e}")
    # 提供降级占位，避免启动失败
    def search_videos(keyword: str):
        return []
    def search_videos_paged(keyword: str, preference: str = "all", page: int = 1, page_size: int = 100):
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    def latest_videos_paged(days: int = 14, page: int = 1, page_size: int = 100, ensure_accessible: bool = True):
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    def start_maintain(path: str, labels: str = None, logical_path: str = None):
        return {"success": False, "message": "服务不可用"}
    def random_videos(limit: int = 20, ensure_accessible: bool = True):
        return []
    def latest_videos(days: int = 14, limit: int = 20, ensure_accessible: bool = True):
        return []
    def broken_videos(ensure_accessible: bool = True):
        return []
    def set_video_preference(video_code: str, status: str | None):
        return None
    def update_video_actress(video_code: str, actress_names: list[str]):
        return False

try:
    from tools.movie_data_capture.service import MovieDataCaptureService
except ImportError:
    MovieDataCaptureService = None

try:
    from ui.app_settings import AppSettings
except ImportError:
    # Fallback if import fails, though it should work given the sys.path setup
    class AppSettings:
        def __init__(self): pass
        @property
        def app_title(self): return "倩影の居"
        @app_title.setter
        def app_title(self, v): pass
        @property
        def language(self): return "zh_CN"
        @language.setter
        def language(self, v): pass
        def save_settings(self): pass


class XJJDesktopApp:
    def __init__(self) -> None:
        self.settings = AppSettings()
        self.app_meta = self._load_app_meta()
        self.i18n = I18n(PROJECT_ROOT / "i18n", self.settings.language)
        self._init_i18n_labels()
        self.root = tk.Tk()
        self.root.title(self.settings.app_title or self.t("app.title"))
        self.root.geometry("1280x800")
        self.root.configure(bg="#F7F9FC")

        # 颜色与样式常量
        self.colors = {
            "bg": "#F7F9FC",
            "white": "#FFFFFF",
            "gray100": "#F5F7FA",
            "gray200": "#E5E7EB",
            "gray700": "#374151",
            "gray800": "#1F2937",
            "brand": "#2563EB",
            "accent": "#334155",
            "selected_bg": "#2563EB",
            "selected_fg": "#FFFFFF",
            "selected_border": "#CBD5E1",
            "sidebar_bg": "#F8F9FA",
            "sidebar_fg": "#4B5563",
            "sidebar_hover": "#E5E7EB",
            "sidebar_active": "#E2E8F0",
            "sidebar_active_fg": "#1F2937",
        }

        self._last_scan_dir: str | None = None
        self._log_max_lines = 2000
        self._ignore_query_trace = False
        self._settings_scroll_dirty = False
        self._settings_scroll_job = None
        self._settings_scrollregion_cache = None
        self._settings_mousewheel_handler = None
        self._settings_canvas = None
        self._settings_update_scroll = None
        self._settings_check_changes = None
        self._movie_info_search_timer = None
        self._maintain_notebook = None
        self._maintain_settings_tab_id = None
        self._maintain_tab_loading_overlays = {}
        self._maintain_tab_loading_jobs = {}
        self._debug_tab_perf = os.environ.get("XJJ_DEBUG_TAB_PERF") == "1"
        self._debug_tab_switch = os.environ.get("XJJ_DEBUG_TAB_SWITCH") == "1"
        self._perf_enabled = os.environ.get("XJJ_PERF_TRACE") == "1"
        self._perf_auto_click = os.environ.get("XJJ_PERF_CLICK") == "1"
        self._perf_autorun = os.environ.get("XJJ_PERF_AUTORUN") == "1"
        self._perf_auto_quit = os.environ.get("XJJ_PERF_AUTO_QUIT") == "1"
        self._perf_switch_rounds = int(os.environ.get("XJJ_PERF_SWITCH_ROUNDS", "3"))
        self._perf_switch_delay_ms = int(os.environ.get("XJJ_PERF_SWITCH_DELAY_MS", "900"))
        self._perf_auto_quit_ms = int(os.environ.get("XJJ_PERF_AUTO_QUIT_MS", "0"))
        self._perf_records = {}
        self._perf_sequence = []
        self._trace_tab_render = os.environ.get("XJJ_TRACE_TAB_RENDER") == "1"
        self._trace_tab_map = os.environ.get("XJJ_TRACE_TAB_MAP") == "1"
        self._trace_records = {}
        self._tab_switch_started = None
        self._tab_switch_text = None
        self._tab_render_token = 0
        self._tab_render_complete = True
        self._auto_switch_active = False
        self._auto_switch_waiting = False
        self._tab_render_state = {}
        self._tab_expose_token = 0
        self._tab_expose_logged = False
        self._maintain_tab_probes = {}
        self._tab_render_watchdog_job = None
        self._tab_render_stall_ms = int(os.environ.get("XJJ_TRACE_RENDER_STALL_MS", "2000"))

        self._init_styles()
        self._build_layout()
        
        # 页面容器
        self.pages = {}
        self._init_pages()

        # 默认显示查询页
        self.current_page = "query"
        self._update_sidebar_selection()
        self.show_page("query")
        if self._perf_auto_click and self._perf_autorun:
            self.show_page("maintain")
            self.root.after(
                800,
                lambda: self._simulate_tab_clicks(
                    self._maintain_notebook,
                    rounds=self._perf_switch_rounds,
                    delay_ms=self._perf_switch_delay_ms,
                ),
            )

    def _init_i18n_labels(self) -> None:
        self.t = self.i18n.t
        self._column_labels = {
            "video": self.t("table.header.video"),
            "actress": self.t("table.header.actress"),
            "tags": self.t("table.header.tags"),
            "file_path": self.t("table.header.file_path"),
            "file_size": self.t("table.header.file_size"),
            "duration": self.t("table.header.duration"),
            "resolution": self.t("table.header.resolution"),
            "updated_time": self.t("table.header.updated_time"),
            "preference": self.t("table.header.preference")
        }
        self._preference_labels = {
            "all": self.t("preference.all"),
            "like": self.t("preference.like"),
            "dislike": self.t("preference.dislike"),
            "deleted": self.t("preference.deleted"),
            "none": self.t("preference.none")
        }
        self._preference_label_to_value = {v: k for k, v in self._preference_labels.items()}
        self._language_labels = {
            "zh_CN": "简体中文",
            "zh_TW": "繁體中文",
            "en_US": "English",
            "ja_JP": "日本語",
            "ko_KR": "한국어",
            "th_TH": "ไทย"
        }
        self._language_label_to_value = {v: k for k, v in self._language_labels.items()}
        self._maintain_tab_labels = {
            "import": self.t("maintain.tab.import"),
            "manage": self.t("maintain.tab.manage"),
            "movie_info": self.t("maintain.tab.movie_info"),
            "settings": self.t("maintain.tab.settings")
        }

    def get_column_labels(self) -> dict[str, str]:
        return dict(self._column_labels)

    def get_preference_labels(self) -> dict[str, str]:
        return dict(self._preference_labels)

    def get_preference_label_to_value(self) -> dict[str, str]:
        return dict(self._preference_label_to_value)

    def get_language_labels(self) -> dict[str, str]:
        return dict(self._language_labels)

    def get_language_label_to_value(self) -> dict[str, str]:
        return dict(self._language_label_to_value)

    def _load_app_meta(self) -> dict:
        defaults = {
            "version": "V1.0",
            "developer_url": "https://github.com/chippingx/xjj-housekeeper",
            "homepage": "https://github.com/chippingx/xjj-housekeeper",
            "license": "MIT"
        }
        try:
            meta_path = get_config_path("config/app_meta.json", calling_file=__file__)
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    defaults.update({k: v for k, v in data.items() if v})
        except Exception:
            pass
        return defaults

    def _get_rename_rules_path(self) -> Path:
        return get_config_path("output/video_info_collector/conf/rename_rules.yaml", calling_file=__file__)

    def _init_styles(self) -> None:
        init_styles(self)

    def _make_action_button(self, parent, text: str, command=None, **kwargs) -> tk.Button:
        return make_action_button(self, parent, text, command, **kwargs)

    def make_action_button(self, parent, text: str, command=None, **kwargs) -> tk.Button:
        return make_action_button(self, parent, text, command, **kwargs)

    def _create_styled_entry(self, parent, **kwargs) -> tuple[tk.Frame, tk.Entry]:
        return create_styled_entry(self, parent, **kwargs)

    def create_styled_entry(self, parent, **kwargs) -> tuple[tk.Frame, tk.Entry]:
        return create_styled_entry(self, parent, **kwargs)

    def _build_layout(self) -> None:
        build_layout(self)


    def _toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar.grid_remove()
            self.sidebar_visible = False
        else:
            self.sidebar.grid()
            self.sidebar_visible = True

    def toggle_sidebar(self):
        self._toggle_sidebar()

    def _get_about_content(self) -> str:
        app_name = self.settings.app_title or self.t("app.title")
        version = self.app_meta.get("version", "V1.0")
        developer = self.app_meta.get("developer_url", "")
        homepage = self.app_meta.get("homepage", "")
        license_name = self.app_meta.get("license", "")
        return self.t(
            "about.content",
            app_name=app_name,
            version=version,
            developer=developer,
            homepage=homepage,
            license=license_name
        )

    def _show_about(self):
        show_about(self)

    def _add_sidebar_btn(self, key: str, text: str, command):
        add_sidebar_btn(self, key, text, command)

    def _update_sidebar_selection(self) -> None:
        for key, btn in self.nav_btns.items():
            if key == self.current_page:
                btn.configure(
                    bg=self.colors["sidebar_active"],
                    fg=self.colors["sidebar_active_fg"],
                    font=self.fonts["bold"]
                )
            else:
                btn.configure(
                    bg=self.colors["sidebar_bg"],
                    fg=self.colors["sidebar_fg"],
                    font=self.fonts["base"]
                )

    def _init_pages(self) -> None:
        # 预先创建所有页面，使用 grid 堆叠在 main_area
        self.pages["query"] = self._create_query_page(self.main_area)
        self.pages["maintain"] = self._create_maintain_page(self.main_area)
        
        for page in self.pages.values():
            page.grid(row=1, column=0, sticky="nsew")

    def show_page(self, name: str) -> None:
        self.current_page = name
        self._update_sidebar_selection()
        
        if name in self.pages:
            self.pages[name].tkraise()
            
            # 页面特有逻辑
            if name == "query":
                # 尝试聚焦搜索框
                try:
                    self.query_entry.focus_set()
                except Exception:
                    pass

    def _attach_entry_context_menu(self, entry: tk.Entry) -> None:
        attach_entry_context_menu(self, entry)

    def attach_entry_context_menu(self, entry: tk.Entry) -> None:
        attach_entry_context_menu(self, entry)

    def _create_query_page(self, parent) -> tk.Frame:
        return build_query_page(self, parent)

    # ================= 页面构建：维护 =================
    def _create_maintain_page(self, parent) -> tk.Frame:
        container = tk.Frame(parent, bg=self.colors["bg"])

        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True, padx=24, pady=(24, 24))

        tab_frames = {
            "import": tk.Frame(notebook, bg=self.colors["bg"]),
            "manage": tk.Frame(notebook, bg=self.colors["bg"]),
            "movie_info": tk.Frame(notebook, bg=self.colors["bg"]),
            "settings": tk.Frame(notebook, bg=self.colors["bg"]),
        }

        tab_import_label = self._maintain_tab_labels["import"]
        tab_manage_label = self._maintain_tab_labels["manage"]
        tab_movie_info_label = self._maintain_tab_labels["movie_info"]
        tab_settings_label = self._maintain_tab_labels["settings"]

        notebook.add(tab_frames["import"], text=tab_import_label)
        notebook.add(tab_frames["manage"], text=tab_manage_label)
        notebook.add(tab_frames["movie_info"], text=tab_movie_info_label)
        notebook.add(tab_frames["settings"], text=tab_settings_label)

        self._maintain_notebook = notebook
        self._maintain_settings_tab_id = str(tab_frames["settings"])
        self._maintain_tab_frames = {
            tab_import_label: tab_frames["import"],
            tab_manage_label: tab_frames["manage"],
            tab_movie_info_label: tab_frames["movie_info"],
            tab_settings_label: tab_frames["settings"],
        }
        self._maintain_tab_probes = {}
        for tab_text, frame in self._maintain_tab_frames.items():
            probe = tk.Frame(frame, bg=self.colors["bg"], width=2, height=2)
            probe.place(x=1, y=1, width=2, height=2)
            self._maintain_tab_probes[tab_text] = probe
        self._maintain_tab_loading_overlays = {}
        for tab_text, frame in self._maintain_tab_frames.items():
            overlay = tk.Frame(frame, bg=self.colors["bg"])
            label = tk.Label(overlay, text=self.t("maintain.loading"), bg=self.colors["bg"], fg=self.colors["gray700"], font=("Helvetica", 14))
            label.place(relx=0.5, rely=0.5, anchor="center")
            overlay.place_forget()
            self._maintain_tab_loading_overlays[tab_text] = overlay
        self._maintain_tab_loading_jobs = {}

        def time_init(tab_name: str, fn, frame):
            start_time = time.perf_counter()
            fn(frame)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._trace_record("tab_init", elapsed_ms, f"tab={tab_name}")

        time_init(tab_import_label, self._init_maintain_import, tab_frames["import"])
        time_init(tab_manage_label, self._init_maintain_manage, tab_frames["manage"])
        time_init(tab_movie_info_label, self._init_maintain_movie_info, tab_frames["movie_info"])
        time_init(tab_settings_label, self._init_maintain_settings, tab_frames["settings"])

        def on_tab_changed(_event):
            start_time = time.perf_counter()
            selected = notebook.select()
            if not selected:
                return
            tab_text = notebook.tab(selected, "text")
            self._tab_switch_started = start_time
            self._tab_switch_text = tab_text
            self._tab_render_token += 1
            current_token = self._tab_render_token
            self._tab_render_complete = False
            self._tab_render_state[current_token] = {"stable": 0, "last": (0, 0), "visible_logged": False}
            self._tab_expose_token = current_token
            self._tab_expose_logged = False
            if self._tab_render_watchdog_job is not None:
                self._safe_after_cancel(self._tab_render_watchdog_job)
                self._tab_render_watchdog_job = None
            if self._debug_tab_perf:
                print(f"[perf] {datetime.now().isoformat(timespec='milliseconds')} on_tab_changed enter tab={tab_text}")
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if self._debug_tab_perf:
                print(f"[perf] {datetime.now().isoformat(timespec='milliseconds')} on_tab_changed exit tab={tab_text} elapsed_ms={elapsed_ms:.2f}")
            self._perf_record("on_tab_changed", elapsed_ms, f"tab={tab_text}")
            self._trace_record("tab_changed_handler", elapsed_ms, f"tab={tab_text}")
            self.root.after_idle(lambda t=tab_text: self._force_tab_redraw(t))
            self._show_tab_loading(tab_text)
            self._schedule_tab_loading_hide(tab_text)
            if tab_text == tab_settings_label:
                update = getattr(self, "_settings_update_scroll", None)
                if update is not None:
                    self._settings_scroll_dirty = True
                    if self._settings_scroll_job is not None:
                        self._safe_after_cancel(self._settings_scroll_job)
                        self._settings_scroll_job = None
                    self._settings_scroll_job = self.root.after_idle(update)
            if self._trace_tab_render:
                self.root.after_idle(lambda t=tab_text, s=start_time: self._trace_record_since("tab_idle", s, f"tab={t}"))
                self.root.after_idle(lambda t=tab_text, s=start_time, token=current_token: self._start_tab_render_watch(t, s, token))
                self.root.after_idle(lambda t=tab_text: self._force_tab_redraw(t))
                if self._tab_render_stall_ms > 0:
                    self._tab_render_watchdog_job = self.root.after(
                        self._tab_render_stall_ms,
                        lambda t=tab_text, s=start_time, token=current_token: self._tab_render_watchdog(t, s, token),
                    )

        notebook.bind("<<NotebookTabChanged>>", on_tab_changed)
        if self._trace_tab_map:
            frame_map = {
                tab_frames["import"]: tab_import_label,
                tab_frames["manage"]: tab_manage_label,
                tab_frames["movie_info"]: tab_movie_info_label,
                tab_frames["settings"]: tab_settings_label,
            }
            expose_widgets = dict(frame_map)
            settings_canvas = getattr(self, "_settings_canvas", None)
            if settings_canvas is not None:
                expose_widgets[settings_canvas] = tab_settings_label
            for tab_text, probe in self._maintain_tab_probes.items():
                expose_widgets[probe] = tab_text

            def on_map(event):
                tab_text = frame_map.get(event.widget)
                started = self._tab_switch_started
                if tab_text and started:
                    self._trace_record_since("tab_map", started, f"tab={tab_text}")

            def on_expose(event):
                if not self._trace_tab_render:
                    return
                if self._tab_expose_logged:
                    return
                started = self._tab_switch_started
                tab_text = expose_widgets.get(event.widget)
                if not started or not tab_text:
                    return
                if self._tab_expose_token != self._tab_render_token:
                    return
                self._tab_expose_logged = True
                self._trace_record_since("tab_expose", started, f"tab={tab_text}")

            for frame in frame_map:
                frame.bind("<Map>", on_map)
            for widget in expose_widgets:
                widget.bind("<Expose>", on_expose)
                widget.bind("<Visibility>", on_expose)
                widget.bind("<Motion>", lambda e: self._trace_tab_motion())

        if self._debug_tab_switch:
            self.root.after(1000, lambda: self._simulate_tab_switches(notebook))

        return container

    def _simulate_tab_switches(self, notebook: ttk.Notebook, rounds: int = 4, delay_ms: int = 600) -> None:
        tabs = list(notebook.tabs())
        if not tabs:
            return
        total = rounds * len(tabs)
        index = 0

        def step():
            nonlocal total, index
            if total <= 0:
                return
            tab_id = tabs[index % len(tabs)]
            start_time = time.perf_counter()
            notebook.select(tab_id)
            def on_idle():
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                if self._debug_tab_perf:
                    text = notebook.tab(tab_id, "text")
                    print(f"[perf] {datetime.now().isoformat(timespec='milliseconds')} switch_complete tab={text} elapsed_ms={elapsed_ms:.2f}")
            self.root.after_idle(on_idle)
            index += 1
            total -= 1
            self.root.after(delay_ms, step)

        step()

    def _simulate_tab_clicks(self, notebook: ttk.Notebook | None, rounds: int = 3, delay_ms: int = 900) -> None:
        if notebook is None:
            return
        tabs = list(notebook.tabs())
        if not tabs:
            return
        total = rounds * len(tabs)
        index = 0

        def finish():
            self._dump_perf_summary()
            self._dump_trace_summary()
            if self._perf_auto_quit and self._perf_auto_quit_ms > 0:
                self.root.after(self._perf_auto_quit_ms, self.root.quit)

        def step():
            nonlocal total, index
            if total <= 0:
                finish()
                return
            if self._auto_switch_waiting:
                self.root.after(50, step)
                return
            tab_id = tabs[index % len(tabs)]
            tab_text = notebook.tab(tab_id, "text")
            start_time = time.perf_counter()
            notebook.select(tab_id)

            def on_idle():
                self._perf_record_since("tab_switch_complete", start_time, f"tab={tab_text}")
                self._trace_record_since("tab_click_complete", start_time, f"tab={tab_text}")

            self.root.after_idle(on_idle)
            index += 1
            total -= 1
            self._auto_switch_waiting = True
            self._wait_tab_render_then_next(delay_ms, step)

        self._auto_switch_active = True
        step()

    def _perf_record(self, name: str, elapsed_ms: float, extra: str | None = None) -> None:
        if not self._perf_enabled:
            return
        self._perf_records.setdefault(name, []).append(elapsed_ms)
        if extra:
            self._perf_sequence.append((name, elapsed_ms, extra))
            print(f"[perf] {datetime.now().isoformat(timespec='milliseconds')} {name} elapsed_ms={elapsed_ms:.2f} {extra}")
        else:
            self._perf_sequence.append((name, elapsed_ms, ""))
            print(f"[perf] {datetime.now().isoformat(timespec='milliseconds')} {name} elapsed_ms={elapsed_ms:.2f}")

    def _perf_record_since(self, name: str, start_time: float, extra: str | None = None) -> None:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._perf_record(name, elapsed_ms, extra)

    def _dump_perf_summary(self) -> None:
        if not self._perf_enabled or not self._perf_records:
            return
        print("[perf] summary_begin")
        for name, items in sorted(self._perf_records.items()):
            if not items:
                continue
            count = len(items)
            avg = sum(items) / count
            max_ms = max(items)
            min_ms = min(items)
            print(f"[perf] summary {name} count={count} avg_ms={avg:.2f} max_ms={max_ms:.2f} min_ms={min_ms:.2f}")
        print("[perf] summary_end")

    def _trace_record(self, name: str, elapsed_ms: float, extra: str | None = None) -> None:
        if not self._trace_tab_render:
            return
        self._trace_records.setdefault(name, []).append(elapsed_ms)
        if extra:
            print(f"[trace] {datetime.now().isoformat(timespec='milliseconds')} {name} elapsed_ms={elapsed_ms:.2f} {extra}", flush=True)
        else:
            print(f"[trace] {datetime.now().isoformat(timespec='milliseconds')} {name} elapsed_ms={elapsed_ms:.2f}", flush=True)

    def _trace_record_since(self, name: str, start_time: float, extra: str | None = None) -> None:
        if not self._trace_tab_render:
            return
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._trace_record(name, elapsed_ms, extra)

    def _trace_tab_layout(self, tab_text: str, start_time: float, token: int) -> None:
        if not self._trace_tab_render:
            return
        if token != self._tab_render_token:
            return
        start_time = time.perf_counter()
        self.root.update_idletasks()
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._trace_record("update_idletasks", elapsed_ms, f"tab={tab_text}")
        if tab_text == self._maintain_tab_labels["settings"]:
            canvas = getattr(self, "_settings_canvas", None)
            if canvas is not None:
                start_bbox = time.perf_counter()
                bbox = canvas.bbox("all")
                elapsed_bbox = (time.perf_counter() - start_bbox) * 1000
                self._trace_record("settings_bbox", elapsed_bbox, f"tab={tab_text} bbox={bbox}")
        if token == self._tab_render_token:
            self._tab_render_complete = True
            self._auto_switch_waiting = False
            if self._auto_switch_active:
                self._trace_record_since("tab_render_complete", start_time, f"tab={tab_text}")

    def _dump_trace_summary(self) -> None:
        if not self._trace_tab_render or not self._trace_records:
            return
        print("[trace] summary_begin")
        for name, items in sorted(self._trace_records.items()):
            if not items:
                continue
            count = len(items)
            avg = sum(items) / count
            max_ms = max(items)
            min_ms = min(items)
            print(f"[trace] summary {name} count={count} avg_ms={avg:.2f} max_ms={max_ms:.2f} min_ms={min_ms:.2f}")
        print("[trace] summary_end")

    def _wait_tab_render_then_next(self, delay_ms: int, callback) -> None:
        if self._tab_render_complete:
            self.root.after(delay_ms, callback)
            return
        self.root.after(50, lambda: self._wait_tab_render_then_next(delay_ms, callback))

    def _start_tab_render_watch(self, tab_text: str, start_time: float, token: int) -> None:
        if not self._trace_tab_render:
            return
        if token != self._tab_render_token:
            return
        state = self._tab_render_state.get(token, {"stable": 0, "last": (0, 0), "visible_logged": False})
        frame = self._get_tab_frame(tab_text)
        probe = self._get_tab_probe_widget(tab_text, frame)
        if probe is None:
            self._tab_render_complete = True
            self._auto_switch_waiting = False
            self._trace_record_since("tab_render_ready", start_time, f"tab={tab_text} probe=none")
            return
        mapped = bool(probe.winfo_ismapped())
        size = (probe.winfo_width(), probe.winfo_height())
        viewable = False
        if mapped and size[0] > 1 and size[1] > 1:
            try:
                cx = probe.winfo_rootx() + max(1, size[0] // 2)
                cy = probe.winfo_rooty() + max(1, size[1] // 2)
                widget = self.root.winfo_containing(cx, cy)
                viewable = widget is not None and self._is_widget_descendant(frame, widget)
            except Exception:
                viewable = False
        if viewable and not state.get("visible_logged"):
            state["visible_logged"] = True
            self._trace_record_since("tab_render_visible", start_time, f"tab={tab_text} size={size}")
        if mapped and size[0] > 1 and size[1] > 1:
            if size == state["last"]:
                state["stable"] += 1
            else:
                state["stable"] = 0
                state["last"] = size
        else:
            state["stable"] = 0
            state["last"] = size
        self._tab_render_state[token] = state
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        if state["stable"] >= 2 and viewable:
            self._tab_render_complete = True
            self._auto_switch_waiting = False
            self._trace_record("tab_render_ready", elapsed_ms, f"tab={tab_text} size={size}")
            if tab_text == self._maintain_tab_labels["settings"]:
                canvas = getattr(self, "_settings_canvas", None)
                if canvas is not None:
                    bbox = canvas.bbox("all")
                    self._trace_record("settings_bbox", 0.0, f"tab={tab_text} bbox={bbox}")
                update = getattr(self, "_settings_update_scroll", None)
                if update is not None and getattr(self, "_settings_scroll_dirty", False):
                    update()
            self._hide_tab_loading(tab_text)
            return
        if elapsed_ms > 15000:
            self._tab_render_complete = True
            self._auto_switch_waiting = False
            self._trace_record("tab_render_timeout", elapsed_ms, f"tab={tab_text} size={size} mapped={mapped}")
            self._hide_tab_loading(tab_text)
            return
        self.root.after(50, lambda t=tab_text, s=start_time, tok=token: self._start_tab_render_watch(t, s, tok))

    def _get_tab_frame(self, tab_text: str):
        frames = getattr(self, "_maintain_tab_frames", None)
        if not frames:
            return None
        return frames.get(tab_text)

    def _get_tab_probe_widget(self, tab_text: str, frame):
        probes = getattr(self, "_maintain_tab_probes", None)
        if probes and tab_text in probes:
            return probes[tab_text]
        return frame

    def _is_widget_descendant(self, parent, widget) -> bool:
        if parent is None or widget is None:
            return False
        try:
            current = widget
            while current is not None:
                if str(current) == str(parent):
                    return True
                parent_name = current.winfo_parent()
                if not parent_name:
                    return False
                current = current.nametowidget(parent_name)
        except Exception:
            return False
        return False

    def _safe_after_cancel(self, job_id) -> None:
        try:
            self.root.after_cancel(job_id)
        except Exception:
            return

    def _show_tab_loading(self, tab_text: str) -> None:
        overlays = getattr(self, "_maintain_tab_loading_overlays", None)
        if not overlays:
            return
        overlay = overlays.get(tab_text)
        if overlay is None:
            return
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        overlay.lift()

    def _schedule_tab_loading_hide(self, tab_text: str) -> None:
        jobs = getattr(self, "_maintain_tab_loading_jobs", None)
        if jobs is None:
            return
        existing = jobs.get(tab_text)
        if existing is not None:
            self._safe_after_cancel(existing)
        def finalize():
            frame = self._get_tab_frame(tab_text)
            if frame is not None:
                try:
                    frame.update_idletasks()
                except Exception:
                    pass
            self._hide_tab_loading(tab_text)
            jobs.pop(tab_text, None)
        jobs[tab_text] = self.root.after(200, finalize)

    def _hide_tab_loading(self, tab_text: str) -> None:
        overlays = getattr(self, "_maintain_tab_loading_overlays", None)
        if not overlays:
            return
        overlay = overlays.get(tab_text)
        if overlay is None:
            return
        overlay.place_forget()

    def _force_tab_redraw(self, tab_text: str) -> None:
        frame = self._get_tab_frame(tab_text)
        if frame is None:
            return
        start_time = time.perf_counter()
        try:
            frame.update_idletasks()
        except Exception:
            return
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        if self._trace_tab_render:
            self._trace_record("tab_force_redraw", elapsed_ms, f"tab={tab_text}")

    def _tab_render_watchdog(self, tab_text: str, start_time: float, token: int) -> None:
        if token != self._tab_render_token:
            return
        if self._tab_render_complete:
            return
        state = self._tab_render_state.get(token, {"stable": 0, "last": (0, 0), "visible_logged": False})
        probe = self._get_tab_probe_widget(tab_text, self._get_tab_frame(tab_text))
        mapped = bool(probe.winfo_ismapped()) if probe is not None else False
        size = (probe.winfo_width(), probe.winfo_height()) if probe is not None else (0, 0)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        if not state.get("visible_logged"):
            self._trace_record("tab_render_stall", elapsed_ms, f"tab={tab_text} size={size} mapped={mapped}")
            self._force_tab_redraw(tab_text)
        if elapsed_ms <= 15000 and not self._tab_render_complete:
            self._tab_render_watchdog_job = self.root.after(
                self._tab_render_stall_ms,
                lambda t=tab_text, s=start_time, tok=token: self._tab_render_watchdog(t, s, tok),
            )

    def _trace_tab_motion(self) -> None:
        if not self._trace_tab_render:
            return
        if self._tab_render_complete:
            return
        started = self._tab_switch_started
        tab_text = self._tab_switch_text
        if started and tab_text:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._trace_record("tab_motion_nudge", elapsed_ms, f"tab={tab_text}")
            self._force_tab_redraw(tab_text)

    def _init_maintain_movie_info(self, parent):
        init_maintain_movie_info(self, parent)

    def _init_maintain_import(self, parent):
        init_maintain_import(self, parent)

    def _init_maintain_settings(self, parent):
        init_maintain_settings(self, parent)

    def _rebuild_ui(self) -> None:
        current_page = getattr(self, "current_page", "query")
        for child in self.root.winfo_children():
            child.destroy()
        self._init_styles()
        self._build_layout()
        self.pages = {}
        self._init_pages()
        if current_page not in self.pages:
            current_page = "query"
        self.current_page = current_page
        self.root.title(self.settings.app_title or self.t("app.title"))
        self._update_sidebar_selection()
        self.show_page(self.current_page)

    def _apply_language(self, language: str) -> None:
        target = language or self.i18n.fallback
        self.i18n.language = target
        self.i18n._load_language(target)
        if self.i18n.fallback != target:
            self.i18n._load_language(self.i18n.fallback)
        self._init_i18n_labels()
        self._rebuild_ui()

    def _init_maintain_manage(self, parent):
        tk.Frame(parent, bg=self.colors["bg"], height=12).pack(fill=tk.X)
        tools_section = tk.Frame(parent, bg=self.colors["bg"])
        tools_section.pack(fill=tk.X, pady=10)
        
        tools_row = tk.Frame(tools_section, bg=self.colors["bg"])
        tools_row.pack(anchor="w", pady=4)

        table = build_maintain_manage_table(self, parent)

        build_maintain_manage_tools(self, tools_row, table)


    # ================= 通用辅助 =================
    def _render_table(self, table: ttk.Treeview, rows: list[dict]) -> None:
        render_table(self, table, rows)

    def render_table(self, table: ttk.Treeview, rows: list[dict]) -> None:
        render_table(self, table, rows)

    def _parse_file_size_for_sorting(self, value) -> float:
        if not isinstance(value, str): return 0.0
        text = value.strip().upper()
        if text.endswith("GB") or text.endswith("G"): return float(text[:-2].strip() if text.endswith("GB") else text[:-1].strip()) * 1024
        if text.endswith("MB") or text.endswith("M"): return float(text[:-2].strip() if text.endswith("MB") else text[:-1].strip())
        try: return float(text)
        except: return 0.0

    def _parse_duration_for_sorting(self, value) -> int:
        if not isinstance(value, str):
            return 0
        text = value.strip()
        if not text:
            return 0
        m = re.fullmatch(r"(\d+):(\d{1,2}):(\d{1,2})", text)
        if m:
            h, mm, ss = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return h * 3600 + mm * 60 + ss
        m = re.fullmatch(r"(\d{1,2}):(\d{1,2})", text)
        if m:
            mm, ss = (int(m.group(1)), int(m.group(2)))
            return mm * 60 + ss
        try:
            return int(float(text))
        except Exception:
            return 0

    def _parse_resolution_for_sorting(self, value) -> tuple[int, int]:
        if not isinstance(value, str):
            return (0, 0)
        text = value.strip().lower().replace("×", "x")
        m = re.search(r"(\d+)\s*x\s*(\d+)", text)
        if not m:
            return (0, 0)
        try:
            return (int(m.group(1)), int(m.group(2)))
        except Exception:
            return (0, 0)

    def _sort_results_by_file_size_desc(self, rows: list[dict]) -> list[dict]:
        try:
            return sorted(rows, key=lambda r: self._parse_file_size_for_sorting(r.get("file_size")), reverse=True)
        except Exception:
            return rows

    def sort_results_by_file_size_desc(self, rows: list[dict]) -> list[dict]:
        return self._sort_results_by_file_size_desc(rows)

    def _sort_table(self, table: ttk.Treeview, column_key: str) -> None:
        try: columns = list(table["columns"])
        except: return
        if column_key not in columns: return

        sort_state = getattr(table, "_sort_state", {"column": None, "ascending": True})
        ascending = not sort_state.get("ascending", True) if sort_state.get("column") == column_key else True
        
        items = list(table.get_children())
        
        def key_for(item_id):
            values = table.item(item_id, "values")
            idx = columns.index(column_key)
            val = values[idx]
            if column_key == "file_size": return self._parse_file_size_for_sorting(val)
            if column_key == "duration": return self._parse_duration_for_sorting(val)
            if column_key == "resolution": return self._parse_resolution_for_sorting(val)
            return val

        sorted_items = sorted(items, key=key_for, reverse=not ascending)
        for index, item_id in enumerate(sorted_items):
            table.move(item_id, "", index)
        
        table._sort_state = {"column": column_key, "ascending": ascending}
        
        header_texts = getattr(table, "_header_texts", {})
        for col in columns:
            base = header_texts.get(col, col)
            label = f"{base} {'↑' if ascending else '↓'}" if col == column_key else base
            table.heading(col, text=label)

    def sort_table(self, table: ttk.Treeview, column_key: str) -> None:
        self._sort_table(table, column_key)

    def _on_table_double_click(self, table: ttk.Treeview, event: tk.Event):
        return handle_table_double_click(self, table, event)

    def on_table_double_click(self, table: ttk.Treeview, event: tk.Event):
        return handle_table_double_click(self, table, event)

    def _open_file_manager(self, path: str):
        open_file_manager(self, path)

    def open_file_manager(self, path: str):
        self._open_file_manager(path)

    def _on_table_right_click(self, table: ttk.Treeview, event: tk.Event):
        handle_table_right_click(self, table, event)

    def on_table_right_click(self, table: ttk.Treeview, event: tk.Event):
        handle_table_right_click(self, table, event)

    def _set_row_preference(self, table: ttk.Treeview, item_id: str, video_code: str, status: str | None) -> None:
        try: set_video_preference(video_code, status)
        except: return
        
        row = getattr(table, "_row_cache", {}).get(item_id)
        if row: row["preference"] = status
        
        values = list(table.item(item_id, "values") or [])
        cols = list(table["columns"])
        if "preference" in cols:
            idx = cols.index("preference")
            display = self._preference_labels["like"] if status == "like" else self._preference_labels["dislike"] if status == "dislike" else self._preference_labels["deleted"] if status == "deleted" else ""
            values[idx] = display
            table.item(item_id, values=values)
            
        if status == "like": table.item(item_id, tags=("pref_like",))
        elif status == "dislike": table.item(item_id, tags=("pref_dislike",))
        elif status == "deleted": table.item(item_id, tags=("pref_deleted",))
        else: table.item(item_id, tags=())

    def set_row_preference(self, table: ttk.Treeview, item_id: str, video_code: str, status: str | None) -> None:
        self._set_row_preference(table, item_id, video_code, status)

    def _set_row_actress(self, table: ttk.Treeview, item_id: str, video_code: str, actress_names: list[str]) -> bool:
        try:
            if not update_video_actress(video_code, actress_names):
                return False
        except Exception:
            return False
        
        new_actress_str = ", ".join(actress_names)
        row = getattr(table, "_row_cache", {}).get(item_id)
        if row:
            row["actress"] = new_actress_str
            row["video_code"] = video_code
        
        values = list(table.item(item_id, "values") or [])
        cols = list(table["columns"])
        if "actress" in cols:
            idx = cols.index("actress")
            values[idx] = new_actress_str
            table.item(item_id, values=values)
        return True

    def set_row_actress(self, table: ttk.Treeview, item_id: str, video_code: str, actress_names: list[str]) -> bool:
        return self._set_row_actress(table, item_id, video_code, actress_names)

    def _show_video_list_window(self, title: str, rows: list[dict]) -> None:
        open_video_list_window(self, title, rows)

    def show_video_list_window(self, title: str, rows: list[dict]) -> None:
        self._show_video_list_window(title, rows)

    def _play_video(self, video_path: str):
        play_video(self, video_path)

    def play_video(self, video_path: str):
        self._play_video(video_path)

    def _play_video_with_player(self, video_path: Path, player_path: str):
        play_video_with_player(self, video_path, player_path)

    def play_video_with_player(self, video_path: Path, player_path: str):
        self._play_video_with_player(video_path, player_path)

    def _get_system_video_players(self):
        return get_system_video_players(self)

    def get_system_video_players(self):
        return self._get_system_video_players()

    def run(self) -> None:
        self.root.mainloop()

if __name__ == "__main__":
    XJJDesktopApp().run()
