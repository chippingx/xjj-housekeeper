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

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tools.path_utils import get_config_path

try:
    from ui.services import search_videos, search_videos_paged, start_maintain, random_videos, latest_videos, latest_videos_paged, broken_videos, set_video_preference, update_video_tags, update_video_actress
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
    def update_video_tags(video_id: int, tags: list[str]):
        return False
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
        def app_title(self): return "小姐姐の管家"
        @app_title.setter
        def app_title(self, v): pass
        @property
        def language(self): return "zh_CN"
        @language.setter
        def language(self, v): pass
        def save_settings(self): pass


def run_filename_adjustment(
    base_path: str,
    include_subdirs: bool = True,
    flatten_output: bool = False,
    dry_run: bool = False,
    conflict_resolution: str = "rename",
    log_operations: bool = True,
    verify_size: bool = False,
    progress_callback=None,
):
    """调用 tools.filename_formatter 执行文件名调整并返回摘要与日志行。"""
    try:
        from tools.filename_formatter.formatter import FilenameFormatter
    except Exception as e:
        return {"summary": {"total": 0, "success": 0, "skipped": 0, "would_skip": 0, "preview": 0, "errors": 1}, "log_lines": [f"error: import failed - {e}"]}

    rules_env = os.getenv("RENAME_RULES_PATH")
    if rules_env:
        formatter = FilenameFormatter(default_rules_path=None)
    else:
        candidate_rules_path = PROJECT_ROOT / "output" / "video_info_collector" / "conf" / "rename_rules.yaml"
        formatter = FilenameFormatter(default_rules_path=str(candidate_rules_path) if candidate_rules_path.exists() else None)
    results = formatter.rename_in_directory(
        base_path,
        include_subdirs=include_subdirs,
        flatten_output=flatten_output,
        dry_run=dry_run,
        conflict_resolution=conflict_resolution,
        log_operations=log_operations,
        verify_size=verify_size,
        progress_callback=progress_callback,
    )

    summary = {
        "total": len(results),
        "success": sum(1 for r in results if str(r.status).startswith("success")),
        "skipped": sum(1 for r in results if str(r.status).startswith("skipped")),
        "would_skip": sum(1 for r in results if str(r.status).startswith("would skip")),
        "preview": sum(1 for r in results if str(r.status).startswith("preview")),
        "errors": sum(1 for r in results if str(r.status).startswith("error")),
    }
    log_lines = [f"{r.status}: {r.original} -> {r.new}" for r in results]
    return {"summary": summary, "log_lines": log_lines}


class I18n:
    def __init__(self, i18n_dir: Path, language: str, fallback: str = "zh_CN"):
        self.i18n_dir = i18n_dir
        self.language = language or fallback
        self.fallback = fallback
        self._translations: dict[str, dict] = {}
        self._load_language(self.language)
        if self.fallback != self.language:
            self._load_language(self.fallback)

    def _load_language(self, lang: str):
        if lang in self._translations:
            return
        path = self.i18n_dir / f"{lang}.json"
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._translations[lang] = json.load(f) or {}
        except Exception:
            self._translations[lang] = {}

    def t(self, key: str, default: str | None = None, **kwargs):
        data = self._translations.get(self.language, {})
        fallback = self._translations.get(self.fallback, {})
        if key in data:
            value = data[key]
        elif key in fallback:
            value = fallback[key]
        else:
            value = default if default is not None else key
        try:
            return str(value).format(**kwargs)
        except Exception:
            return str(value)


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
            # 更新品牌色：从 #2563EB (Bright Blue) 改为 #0F172A (Dark Slate/Black) 或 #1E293B (Deep Navy)
            # 这里选择 Deep Navy 风格，显得更专业沉稳，配合白色文字
            "brand": "#1E293B",  # 类似 GitHub Dark 或 VS Code 侧边栏的深色
            "accent": "#334155",  # 辅助色
            "selected_bg": "#E2E8F0",  # 列表选中背景：淡蓝灰
            "selected_fg": "#1E293B",  # 列表选中文字：使用品牌色
            "selected_border": "#CBD5E1",
            # 侧边栏样式调整
            "sidebar_bg": "#F8F9FA",      # 极浅灰背景
            "sidebar_fg": "#4B5563",      # 深灰文字
            "sidebar_hover": "#E5E7EB",   # 悬停稍深灰
            "sidebar_active": "#E2E8F0",  # 选中背景：淡蓝灰
            "sidebar_active_fg": "#1E293B", # 选中文字：使用品牌色
        }

        self._last_scan_dir: str | None = None
        self._log_max_lines = 2000
        self._ignore_query_trace = False
        self._settings_scroll_dirty = False
        self._settings_scroll_job = None
        self._settings_scrollregion_cache = None
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
            "zh_CN": self.t("language.zh_CN"),
            "zh_TW": self.t("language.zh_TW"),
            "en_US": self.t("language.en_US"),
            "ja_JP": self.t("language.ja_JP"),
            "ko_KR": self.t("language.ko_KR"),
            "th_TH": self.t("language.th_TH")
        }
        self._language_label_to_value = {v: k for k, v in self._language_labels.items()}
        self._maintain_tab_labels = {
            "import": self.t("maintain.tab.import"),
            "manage": self.t("maintain.tab.manage"),
            "movie_info": self.t("maintain.tab.movie_info"),
            "settings": self.t("maintain.tab.settings")
        }

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

    def _init_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
            
        # 字体配置（跨平台优化）
        system = self.root.tk.call("tk", "windowingsystem")
        if system == "aqua":  # macOS
            base_font = ("San Francisco", 13)
            bold_font = ("San Francisco", 13, "bold")
            title_font = ("San Francisco", 18, "bold")
            mono_font = ("Menlo", 12)
        elif system == "win32":  # Windows
            base_font = ("Microsoft YaHei UI", 10)
            bold_font = ("Microsoft YaHei UI", 10, "bold")
            title_font = ("Microsoft YaHei UI", 14, "bold")
            mono_font = ("Consolas", 10)
        else:  # Linux/Other
            base_font = ("Helvetica", 11)
            bold_font = ("Helvetica", 11, "bold")
            title_font = ("Helvetica", 16, "bold")
            mono_font = ("Courier", 11)
            
        self.fonts = {
            "base": base_font,
            "bold": bold_font,
            "title": title_font,
            "mono": mono_font,
            "small": (base_font[0], base_font[1] - 2),
            "link": (base_font[0], base_font[1] - 1)
        }

        # 表格样式
        style.configure(
            "Treeview",
            background=self.colors["white"],
            fieldbackground=self.colors["white"],
            foreground=self.colors["gray800"],
            rowheight=44,  # 进一步增加行高，提升呼吸感
            font=self.fonts["base"],
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background=self.colors["bg"],  # 浅灰背景
            foreground=self.colors["gray700"],
            relief=tk.FLAT,
            font=self.fonts["bold"],
            padding=(16, 12)  # 增加水平内边距
        )
        # 选中态样式：不再使用深色背景+白字，而是使用浅色背景+深色文字+左侧指示条（模拟）
        # 这里仅能配置背景和文字颜色
        style.map("Treeview", 
            background=[("selected", self.colors["selected_bg"])], 
            foreground=[("selected", self.colors["selected_fg"])]
        )

        style.configure("Blue.Horizontal.TProgressbar", troughcolor=self.colors["gray100"], background=self.colors["brand"])
        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=self.colors["gray200"],
            foreground=self.colors["gray700"],
            padding=(24, 12),  # 增加 Tab 间距
            font=self.fonts["base"],
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.colors["bg"])],
            foreground=[("selected", self.colors["brand"])],  # 选中文字使用品牌色
            padding=[("selected", (24, 12))],
        )

        # Combobox style
        style.configure(
            "TCombobox",
            background=self.colors["white"],
            fieldbackground=self.colors["white"],
            foreground=self.colors["gray800"],
            arrowcolor=self.colors["brand"],
            padding=5,
            font=self.fonts["base"]
        )
        # On some themes/OS, fieldbackground must be set via map or different option
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.colors["white"])],
            selectbackground=[("readonly", self.colors["white"])],
            selectforeground=[("readonly", self.colors["gray800"])]
        )

    def _make_action_button(self, parent, text: str, command=None, **kwargs) -> tk.Button:
        padx = kwargs.pop("padx", 24)
        pady = kwargs.pop("pady", 10)
        
        # 默认样式配置（次级按钮）
        bg = kwargs.pop("bg", self.colors["white"])
        fg = kwargs.pop("fg", self.colors["gray800"])
        activebg = kwargs.pop("activebackground", self.colors["gray100"])
        activefg = kwargs.pop("activeforeground", self.colors["gray800"])
        
        # 检查是否为主按钮（通过 bg 参数判断是否使用品牌色）
        is_primary = bg == self.colors["brand"]
        if is_primary:
            fg = self.colors["white"]
            activebg = self.colors["accent"]
            activefg = self.colors["white"]
            
        font = kwargs.pop("font", self.fonts["base"])
        
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
            **kwargs
        )
        return btn

    def _style_entry(self, entry: tk.Entry):
        """统一输入框样式"""
        entry.configure(
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["gray200"],
            highlightcolor=self.colors["brand"],
            bg=self.colors["white"],
            fg=self.colors["gray800"],
            insertbackground=self.colors["gray800"]  # 光标颜色
        )
        # Tkinter Entry doesn't support internal padding directly.
        # We can't change it to ttk.Entry easily without refactoring everything.
        # However, we can use a border trick or accept that ipady helps.
        # For left padding, unfortunately tk.Entry is limited.
        # But user insists on padding.
        # Let's try to add a small borderwidth with flat relief? No, that doesn't help text pos.
        # Actually, we can use a wrapper frame if we want perfect padding, but that's invasive.
        # Let's try to use `ttk.Entry` style if possible? No, the code passes `entry` around.
        # Wait, there is a trick: font with leading space? No.
        # Actually, for `tk.Entry`, `bd` and `relief` are the only layout params.
        # If we really need padding, we should wrap it.
        # But given the user request, let's try to switch to ttk.Entry where possible
        # or just add a margin via pack/grid? No, that's external.
        
        # NOTE: Since switching to ttk.Entry or wrapping is too risky for this stage,
        # we will continue using tk.Entry but maybe increase the borderwidth slightly 
        # with matching background to simulate padding? 
        # No, tk.Entry border is outside.
        
        # Real solution: Convert to ttk.Entry where this is called, 
        # or use a Frame wrapper.
        # Let's try to use a Frame wrapper in _create_styled_entry helper instead.
        pass

    def _create_styled_entry(self, parent, **kwargs) -> tuple[tk.Frame, tk.Entry]:
        """创建一个带内边距的输入框（通过Frame包裹实现）"""
        # Extract pack/grid args if any? No, caller handles geometry.
        # We return (container, entry)
        
        # Extract entry specific args
        var = kwargs.pop("textvariable", None)
        width = kwargs.pop("width", None)
        font = kwargs.pop("font", self.fonts["base"])
        fg = kwargs.pop("fg", self.colors["gray800"])
        bg = kwargs.pop("bg", self.colors["white"])
        
        # Container (acts as border)
        container = tk.Frame(
            parent, 
            bg=bg, 
            highlightthickness=1, 
            highlightbackground=self.colors["gray200"], 
            highlightcolor=self.colors["brand"],
            bd=0
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
            insertbackground=self.colors["gray800"],
            **kwargs
        )
        entry.pack(fill=tk.BOTH, expand=True, padx=8, pady=6) # Simulated padding
        
        return container, entry

    def _build_layout(self) -> None:
        # 使用 Grid 布局：左侧边栏，右侧主内容
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # 1. 侧边导航栏 (Sidebar)
        self.sidebar = tk.Frame(self.root, bg=self.colors["sidebar_bg"], width=250)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False) # 固定宽度

        # 侧边栏标题
        self.brand_label = tk.Label(
            self.sidebar,
            text=self.settings.app_title,
            bg=self.colors["sidebar_bg"],
            fg=self.colors["brand"],
            font=self.fonts["title"],  # 使用系统字体
            padx=28, pady=36  # 进一步增加留白
        )
        self.brand_label.pack(anchor="w")

        # 导航按钮容器
        self.nav_btns = {}
        self._add_sidebar_btn("query", self.t("sidebar.query"), lambda: self.show_page("query"))
        self._add_sidebar_btn("maintain", self.t("sidebar.maintain"), lambda: self.show_page("maintain"))

        # 侧边栏底部：版本号链接
        version_text = self.app_meta.get("version", "V1.0")
        
        # 底部容器，增加视觉分割
        bottom_frame = tk.Frame(self.sidebar, bg=self.colors["sidebar_bg"], padx=28, pady=28)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.about_link = tk.Label(
            bottom_frame,
            text=version_text,
            bg=self.colors["sidebar_bg"],
            fg=self.colors["gray700"],
            font=self.fonts["link"],  # 使用稍大一点的字体
            cursor="hand2"
        )
        self.about_link.pack(anchor="w")
        self.about_link.bind("<Button-1>", lambda e: self._show_about())

        # 2. 主内容区域 (Main)
        # 主区域背景保持浅灰，内容区通过卡片承载
        self.main_area = tk.Frame(self.root, bg=self.colors["bg"])
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(1, weight=1) # Row 1 是页面内容
        self.main_area.grid_columnconfigure(0, weight=1)

        # Header 区域 (Row 0)
        self.header = tk.Frame(self.main_area, bg=self.colors["bg"], height=64)  # 增加高度
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.pack_propagate(False)

        # 侧边栏切换按钮
        self.sidebar_visible = True
        self.toggle_btn = tk.Button(
            self.header,
            text="☰",
            font=self.fonts["title"],  # 使用图标字体大小
            bg=self.colors["bg"],
            fg=self.colors["gray700"],
            bd=0,
            relief=tk.FLAT,
            activebackground=self.colors["gray100"],
            command=self._toggle_sidebar,
            cursor="hand2"
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=24, pady=12)


    def _toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar.grid_remove()
            self.sidebar_visible = False
        else:
            self.sidebar.grid()
            self.sidebar_visible = True

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
        import webbrowser
        
        dialog = tk.Toplevel(self.root)
        dialog.title(self.t("about.title"))
        dialog.geometry("400x260")
        dialog.resizable(False, False)
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_set()
        
        container = tk.Frame(dialog, bg=self.colors["white"], padx=20, pady=20)
        container.pack(fill=tk.BOTH, expand=True)
        
        # App Title
        tk.Label(
            container, 
            text=self.settings.app_title or self.t("app.title"), 
            bg=self.colors["white"], 
            fg=self.colors["brand"], 
            font=("Helvetica", 20, "bold")
        ).pack(pady=(10, 5))
        
        # Version
        version = self.app_meta.get("version", "V1.0")
        tk.Label(
            container, 
            text=f"Version {version}", 
            bg=self.colors["white"], 
            fg=self.colors["gray700"], 
            font=("Helvetica", 12)
        ).pack(pady=(0, 20))
        
        # Project Link
        link_url = self.app_meta.get("developer_url") or self.app_meta.get("homepage") or ""
        if link_url:
            link_text = "GitHub Repository"
            if "github.com" in link_url:
                try:
                    # try to extract user/repo
                    parts = link_url.rstrip("/").split("/")
                    if len(parts) >= 2:
                        link_text = f"GitHub: {parts[-2]}/{parts[-1]}"
                except:
                    pass
            
            link_label = tk.Label(
                container, 
                text=link_text, 
                bg=self.colors["white"], 
                fg=self.colors["brand"], 
                font=("Helvetica", 11, "underline"), 
                cursor="hand2"
            )
            link_label.pack(pady=5)
            link_label.bind("<Button-1>", lambda e: webbrowser.open(link_url))
            
        # License
        license_name = self.app_meta.get("license", "MIT")
        tk.Label(
            container, 
            text=f"License: {license_name}", 
            bg=self.colors["white"], 
            fg=self.colors["gray700"], 
            font=("Helvetica", 10)
        ).pack(pady=(5, 0))
        
        # Copyright
        tk.Label(
            container,
            text="Copyright © 2025 XJJ Housekeeper Contributors",
            bg=self.colors["white"],
            fg=self.colors["gray700"],
            font=("Helvetica", 10)
        ).pack(side=tk.BOTTOM, pady=10)

    def _add_sidebar_btn(self, key: str, text: str, command):
        # 现代扁平化按钮样式
        btn = tk.Button(
            self.sidebar,
            text=text,
            bg=self.colors["sidebar_bg"],
            fg=self.colors["sidebar_fg"],
            font=self.fonts["base"],
            bd=0,
            relief=tk.FLAT,
            activebackground=self.colors["sidebar_hover"],
            activeforeground=self.colors["brand"],
            anchor="w",
            padx=24,  # 增加内边距
            pady=14,
            command=command,
            cursor="hand2"
        )
        btn.pack(fill=tk.X, pady=2)
        self.nav_btns[key] = btn

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
        menu = tk.Menu(entry, tearoff=0)
        menu.add_command(label=self.t("context.cut"), command=lambda: entry.event_generate("<<Cut>>"))
        menu.add_command(label=self.t("context.copy"), command=lambda: entry.event_generate("<<Copy>>"))
        menu.add_command(label=self.t("context.paste"), command=lambda: entry.event_generate("<<Paste>>"))

        def show_menu(event: tk.Event):
            menu.tk_popup(event.x_root, event.y_root)
            menu.grab_release()

        for sequence in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
            entry.bind(sequence, show_menu, add="+")
        entry._context_menu = menu

    # ================= 页面构建：查询 =================
    def _create_query_page(self, parent) -> tk.Frame:
        container = tk.Frame(parent, bg=self.colors["bg"])
        
        # 内容边距
        content = tk.Frame(container, bg=self.colors["bg"])
        content.pack(fill=tk.BOTH, expand=True, padx=24, pady=24)

        # 搜索表单
        form = tk.Frame(content, bg=self.colors["bg"])
        form.pack(fill=tk.X)

        self.query_placeholder = self.t("query.placeholder")
        self.query_var = tk.StringVar(value=self.query_placeholder)
        entry_container, entry = self._create_styled_entry(form, textvariable=self.query_var, width=40, font=self.fonts["base"])
        entry_container.pack(side=tk.LEFT, padx=(0, 8))
        self._attach_entry_context_menu(entry)
        self.query_entry = entry

        # 偏好筛选
        self.preference_var = tk.StringVar(value=self._preference_labels["all"])
        pref_cb = ttk.Combobox(form, textvariable=self.preference_var, state="readonly", width=10, font=self.fonts["base"])
        pref_cb['values'] = (
            self._preference_labels["all"],
            self._preference_labels["like"],
            self._preference_labels["dislike"],
            self._preference_labels["deleted"],
            self._preference_labels["none"]
        )
        pref_cb.pack(side=tk.LEFT, padx=8, ipady=6)  # 对应增加高度

        def _on_query_focus_in(_event):
            if self.query_var.get() == self.query_placeholder:
                self._ignore_query_trace = True
                try:
                    self.query_var.set("")
                finally:
                    self._ignore_query_trace = False

        def _on_query_focus_out(_event):
            if not self.query_var.get().strip():
                self._ignore_query_trace = True
                try:
                    self.query_var.set(self.query_placeholder)
                finally:
                    self._ignore_query_trace = False

        entry.bind("<FocusIn>", _on_query_focus_in)
        entry.bind("<FocusOut>", _on_query_focus_out)

        # 结果表格
        table_container = tk.Frame(content, bg=self.colors["bg"])
        table_container.pack(fill=tk.BOTH, expand=True, pady=20)  # 增加垂直间距
        
        # Load columns from settings
        columns = tuple(self.settings.visible_columns)
        table = ttk.Treeview(table_container, columns=columns, show="headings")
        left_cols = {"video", "actress", "tags", "file_path", "preference"}
        
        header_texts = dict(self._column_labels)
        
        for col in columns:
            text = header_texts.get(col, col)
            table.heading(col, text=text, anchor="w" if col in left_cols else "e", command=lambda c=col: self._sort_table(table, c))
            if col == "file_path": width = 320  # 加宽路径列
            elif col == "tags": width = 180
            elif col == "actress": width = 140
            elif col == "updated_time": width = 150
            elif col == "preference": width = 100
            else: width = 120
            table.column(col, width=width, anchor="w" if col in left_cols else "e")
        
        table._header_texts = header_texts
        table._context_role = "query"
        # 更新标签颜色以适配新背景
        table.tag_configure("pref_like", background="#FEF3C7", foreground=self.colors["gray800"])
        table.tag_configure("pref_dislike", background="#FEE2E2", foreground=self.colors["gray800"])
        table.tag_configure("pref_deleted", background="#E5E7EB", foreground=self.colors["gray800"])
        
        # 滚动条
        vsb = ttk.Scrollbar(table_container, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=vsb.set)
        table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 分页控件
        page_frame = tk.Frame(content, bg=self.colors["bg"])
        page_frame.pack(fill=tk.X, pady=(0, 0))
        self.page_frame = page_frame # Store ref for visibility toggling
        
        self.page_var = tk.IntVar(value=1)
        
        # 左侧分页按钮
        btn_prev = self._make_action_button(page_frame, text=self.t("pagination.prev"), padx=10)
        btn_prev.pack(side=tk.LEFT)
        
        page_label = tk.Label(page_frame, text=self.t("pagination.page_simple", page=1), bg=self.colors["bg"], fg=self.colors["gray700"], font=("Helvetica", 12))
        page_label.pack(side=tk.LEFT, padx=15)
        
        btn_next = self._make_action_button(page_frame, text=self.t("pagination.next"), padx=10)
        btn_next.pack(side=tk.LEFT)

        # 搜索逻辑
        self.history_stack = []
        self.forward_stack = []
        self.current_search_state = {}

        def _save_history(new_state: dict):
            # 只有当新状态与当前状态不同时才保存
            if self.current_search_state:
                # 简单比较 mode, keyword, preference, page
                if new_state != self.current_search_state:
                    self.history_stack.append(self.current_search_state.copy())
                    # 新的操作清空前进栈
                    self.forward_stack.clear()
            self.current_search_state = new_state.copy()
            _update_nav_buttons()

        def _update_nav_buttons():
            btn_back.config(state=tk.NORMAL if self.history_stack else tk.DISABLED)
            btn_forward.config(state=tk.NORMAL if self.forward_stack else tk.DISABLED)

        def _restore_history(is_forward=False):
            if is_forward:
                if not self.forward_stack: return
                # 把当前状态压入后退栈
                if self.current_search_state:
                    self.history_stack.append(self.current_search_state.copy())
                # 从前进栈弹出目标状态
                target_state = self.forward_stack.pop()
            else:
                if not self.history_stack: return
                # 把当前状态压入前进栈
                if self.current_search_state:
                    self.forward_stack.append(self.current_search_state.copy())
                # 从后退栈弹出目标状态
                target_state = self.history_stack.pop()
            
            self.current_search_state = target_state.copy()
            _update_nav_buttons()
            
            # 恢复状态并执行搜索
            mode = target_state.get("mode", "search")
            
            # 恢复分页组件可见性
            if mode == "random":
                self.page_frame.pack_forget()
            else:
                self.page_frame.pack(fill=tk.X, pady=(0, 0))

            if mode == "search":
                self.query_var.set(target_state.get("keyword", ""))
                self.preference_var.set(target_state.get("preference_label", self._preference_labels["all"]))
                self.page_var.set(target_state.get("page", 1))
                do_search_live(reset_page=False, save_history=False)
            elif mode == "latest":
                self.page_var.set(target_state.get("page", 1))
                do_latest_videos(reset_page=False, save_history=False)
            elif mode == "random":
                do_random_pick(save_history=False)

        def do_search_live(reset_page=False, save_history=True):
            if self._ignore_query_trace:
                return
            
            # Ensure page frame is visible
            self.page_frame.pack(fill=tk.X, pady=(0, 0))
            
            keyword = self.query_var.get().strip()
            is_placeholder = (keyword == self.query_placeholder)
            
            # 获取偏好
            pref_label = self.preference_var.get()
            preference = self._preference_label_to_value.get(pref_label, "all")
            
            if reset_page:
                self.page_var.set(1)
            
            page = self.page_var.get()
            page_size = self.settings.page_size

            # 保存历史
            if save_history:
                new_state = {
                    "mode": "search",
                    "keyword": keyword if not is_placeholder else "",
                    "preference": preference,
                    "preference_label": pref_label,
                    "page": page
                }
                _save_history(new_state)
            
            # 如果是 placeholder 且没有偏好筛选，则视为无搜索
            if (not keyword or is_placeholder) and preference == "all":
                self._render_table(table, [])
                page_label.config(text=self.t("pagination.page_simple", page=1))
                btn_prev.config(state=tk.DISABLED)
                btn_next.config(state=tk.DISABLED)
                return

            real_keyword = "" if is_placeholder else keyword
            
            try:
                res = search_videos_paged(real_keyword, preference, page, page_size)
                items = res.get("items", [])
                total = res.get("total", 0)
                
                # 更新表格
                self._render_table(table, items)
                
                # 更新分页 UI
                total_pages = (total + page_size - 1) // page_size if total > 0 else 1
                page_label.config(text=self.t("pagination.page_full", page=page, total_pages=total_pages, total=total))
                
                btn_prev.config(state=tk.NORMAL if page > 1 else tk.DISABLED)
                btn_next.config(state=tk.NORMAL if page < total_pages else tk.DISABLED)
                
            except Exception as e:
                print(f"Search error: {e}")
                self._render_table(table, [])

        def do_search():
            do_search_live(reset_page=True)

        try:
            self.query_var.trace_add('write', lambda *_: do_search_live(reset_page=True))
        except Exception:
            entry.bind("<KeyRelease>", lambda e: do_search_live(reset_page=True))

        entry.bind("<Return>", lambda e: do_search())
        
        btn_back = self._make_action_button(form, text="<", command=lambda: _restore_history(is_forward=False), padx=10, state=tk.DISABLED)
        btn_back.pack(side=tk.LEFT, padx=(8, 4))
        
        btn_forward = self._make_action_button(form, text=">", command=lambda: _restore_history(is_forward=True), padx=10, state=tk.DISABLED)
        btn_forward.pack(side=tk.LEFT, padx=4)
        
        # Remove search button as requested
        # tk.Button(form, text="搜索", command=do_search, bg=self.colors["white"], fg="black", padx=20, pady=5, relief=tk.FLAT).pack(side=tk.LEFT, padx=4)

        # 绑定偏好变更
        def on_pref_change(event):
            do_search_live(reset_page=True)
        pref_cb.bind("<<ComboboxSelected>>", on_pref_change)
        
        # 绑定分页按钮
        def change_page(delta):
            current = self.page_var.get()
            new_page = current + delta
            if new_page < 1: return
            self.page_var.set(new_page)
            
            mode = self.current_search_state.get("mode", "search")
            if mode == "search":
                do_search_live(reset_page=False)
            elif mode == "latest":
                do_latest_videos(reset_page=False)
            
        btn_prev.config(command=lambda: change_page(-1))
        btn_next.config(command=lambda: change_page(1))

        def do_random_pick(save_history=True):
            # 隐藏分页组件
            self.page_frame.pack_forget()
            
            if save_history:
                _save_history({"mode": "random"})
            
            limit = self.settings.page_size
            try:
                results = random_videos(limit=limit, ensure_accessible=True) or []
            except TypeError:
                # Fallback if limit param not supported by old mock/impl
                results = random_videos() or []
                if len(results) > limit:
                    results = results[:limit]
            
            results = self._sort_results_by_file_size_desc(results)
            self._render_table(table, results)

        self._make_action_button(form, text=self.t("query.random_button"), command=do_random_pick).pack(side=tk.LEFT, padx=4)

        def do_latest_videos(reset_page=True, save_history=True):
            # 恢复分页组件
            self.page_frame.pack(fill=tk.X, pady=(0, 0))
            
            if reset_page:
                self.page_var.set(1)
            page = self.page_var.get()
            page_size = self.settings.page_size
            
            if save_history:
                _save_history({"mode": "latest", "page": page})

            try:
                # 使用分页接口
                res = latest_videos_paged(days=14, page=page, page_size=page_size, ensure_accessible=True)
                items = res.get("items", [])
                total = res.get("total", 0)
                
                # self._sort_results_by_file_size_desc(results) # Latest usually sorted by time, no need to resort by size
                self._render_table(table, items)
                
                # 更新分页 UI
                total_pages = (total + page_size - 1) // page_size if total > 0 else 1
                page_label.config(text=self.t("pagination.page_full", page=page, total_pages=total_pages, total=total))
                
                btn_prev.config(state=tk.NORMAL if page > 1 else tk.DISABLED)
                btn_next.config(state=tk.NORMAL if page < total_pages else tk.DISABLED)
                
            except Exception as e:
                print(f"Latest videos error: {e}")
                self._render_table(table, [])

        self._make_action_button(form, text=self.t("query.latest_button"), command=do_latest_videos).pack(side=tk.LEFT, padx=4)

        table.bind("<Double-1>", lambda e: self._on_table_double_click(table, e))
        # 兼容 macOS 和 Windows 的右键绑定
        for sequence in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
            table.bind(sequence, lambda e: self._on_table_right_click(table, e))

        self._render_table(table, [])
        
        def refresh_data():
            mode = self.current_search_state.get("mode", "search")
            if mode in ("search", "latest"):
                # Re-fetch (handles page size change too)
                if mode == "search": 
                    do_search_live(reset_page=False, save_history=False)
                else: 
                    do_latest_videos(reset_page=False, save_history=False)
            else:
                # Random mode or initial state: Re-render with new columns using cached data
                current_rows = []
                for item_id in table.get_children():
                    row_data = getattr(table, "_row_cache", {}).get(item_id)
                    if row_data:
                        current_rows.append(row_data)
                self._render_table(table, current_rows)

        container.refresh_data = refresh_data
        return container

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
        if not MovieDataCaptureService:
            tk.Label(parent, text=self.t("movie_info.unavailable"), bg=self.colors["bg"], fg="red").pack(pady=20)
            return

        tk.Frame(parent, bg=self.colors["bg"], height=12).pack(fill=tk.X)
        form = tk.Frame(parent, bg=self.colors["bg"])
        form.pack(fill=tk.X, pady=10)

        # Search input
        self.movie_info_placeholder = self.t("movie_info.placeholder")
        self.movie_info_keyword = tk.StringVar()
        entry_container, entry = self._create_styled_entry(form, textvariable=self.movie_info_keyword, width=40, fg="gray", font=self.fonts["base"])
        entry.insert(0, self.movie_info_placeholder)
        entry_container.pack(side=tk.LEFT, padx=8)
        self._attach_entry_context_menu(entry)

        def on_entry_focus_in(event):
            if self.movie_info_keyword.get() == self.movie_info_placeholder:
                entry.delete(0, tk.END)
                entry.config(fg="black")
        
        def on_entry_focus_out(event):
            if not self.movie_info_keyword.get().strip():
                entry.insert(0, self.movie_info_placeholder)
                entry.config(fg="gray")

        entry.bind("<FocusIn>", on_entry_focus_in)
        entry.bind("<FocusOut>", on_entry_focus_out)

        # Search buttons
        def do_search(silent=False):
            keyword = self.movie_info_keyword.get().strip()
            if not keyword or keyword == self.movie_info_placeholder:
                if not silent:
                    messagebox.showwarning(self.t("message.title.tip"), self.t("movie_info.input_required"))
                return

            # Run in thread to avoid blocking UI
            import threading
            def worker():
                svc = MovieDataCaptureService()
                try:
                    rows = svc.search_movie_info(keyword, "all")
                    # Update UI in main thread
                    self.root.after(0, lambda: render_results(rows))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror(self.t("message.title.error"), str(e)))
                finally:
                    svc.close()
            
            threading.Thread(target=worker, daemon=True).start()

        # Bind auto-search
        self._movie_info_search_timer = None
        def on_key_release(event):
            # Skip special keys if needed, but simple debounce handles it
            if self._movie_info_search_timer:
                self.root.after_cancel(self._movie_info_search_timer)
            self._movie_info_search_timer = self.root.after(600, lambda: do_search(silent=True))
        
        entry.bind("<KeyRelease>", on_key_release)
        entry.bind("<Return>", lambda e: do_search(silent=False))

        self._make_action_button(form, text=self.t("movie_info.search_button"), command=lambda: do_search(silent=False)).pack(side=tk.LEFT, padx=4)
        
        right_actions = tk.Frame(form, bg=self.colors["bg"])
        right_actions.pack(side=tk.RIGHT, padx=8)

        def do_import():
            file_path = filedialog.askopenfilename(
                title=self.t("movie_info.import_title"),
                filetypes=[(self.t("movie_info.filetype_label"), "*.txt *.csv"), (self.t("filetype.all"), "*.*")]
            )
            if not file_path:
                return
            dialog = tk.Toplevel(self.root)
            dialog.title(self.t("dialog.wait"))
            dialog.geometry("280x120")
            dialog.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.protocol("WM_DELETE_WINDOW", lambda: None)
            tk.Label(dialog, text=self.t("movie_info.importing"), font=("Helvetica", 12)).pack(pady=30)

            import threading
            def worker():
                svc = MovieDataCaptureService()
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
                    if error:
                        messagebox.showerror(self.t("movie_info.import_failed_title"), str(error))
                        return
                    total = result.get("total", 0)
                    imported = result.get("imported", 0)
                    skipped = result.get("skipped", 0)
                    invalid_date = result.get("invalid_date", 0)
                    messagebox.showinfo(
                        self.t("movie_info.import_done_title"),
                        self.t("movie_info.import_done_summary", total=total, imported=imported, skipped=skipped, invalid_date=invalid_date),
                    )
                    keyword = self.movie_info_keyword.get().strip()
                    if keyword and keyword != self.movie_info_placeholder:
                        do_search(silent=True)
                
                self.root.after(0, on_finish)

            threading.Thread(target=worker, daemon=True).start()

        def do_export():
            file_path = filedialog.asksaveasfilename(
                title=self.t("movie_info.export_title"),
                defaultextension=".csv",
                filetypes=[(self.t("filetype.csv"), "*.csv"), (self.t("filetype.all"), "*.*")],
                initialfile="movie_info_export.csv",
            )
            if not file_path:
                return
            dialog = tk.Toplevel(self.root)
            dialog.title(self.t("dialog.wait"))
            dialog.geometry("280x120")
            dialog.update_idletasks()
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")
            dialog.transient(self.root)
            dialog.grab_set()
            dialog.protocol("WM_DELETE_WINDOW", lambda: None)
            tk.Label(dialog, text=self.t("movie_info.exporting"), font=("Helvetica", 12)).pack(pady=30)

            import threading
            def worker():
                svc = MovieDataCaptureService()
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
                    if error:
                        messagebox.showerror(self.t("movie_info.export_failed_title"), str(error))
                        return
                    total = result.get("total", 0)
                    messagebox.showinfo(self.t("movie_info.export_done_title"), self.t("movie_info.export_done_summary", total=total))
                
                self.root.after(0, on_finish)

            threading.Thread(target=worker, daemon=True).start()

        self._make_action_button(right_actions, text=self.t("movie_info.import_button"), command=do_import).pack(side=tk.LEFT, padx=4)
        self._make_action_button(right_actions, text=self.t("movie_info.export_button"), command=do_export).pack(side=tk.LEFT, padx=4)

        # Results table
        table_container = tk.Frame(parent, bg=self.colors["bg"])
        table_container.pack(fill=tk.BOTH, expand=True, pady=10)

        columns = ("actress_name", "video_code", "title", "release_date")
        table = ttk.Treeview(table_container, columns=columns, show="headings")
        
        table.heading("actress_name", text=self.t("movie_info.table.actress_name"), anchor="w")
        table.heading("video_code", text=self.t("movie_info.table.video_code"), anchor="w")
        table.heading("title", text=self.t("movie_info.table.title"), anchor="w")
        table.heading("release_date", text=self.t("movie_info.table.release_date"), anchor="w")

        table.column("actress_name", width=150)
        table.column("video_code", width=150)
        table.column("title", width=300)
        table.column("release_date", width=120)

        vsb = ttk.Scrollbar(table_container, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=vsb.set)
        table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        def render_results(rows):
            # Clear existing
            for item in table.get_children():
                table.delete(item)
            
            if not rows:
                return

            for row in rows:
                # row is MovieInfoRow
                table.insert("", tk.END, values=(
                    row.actress_name,
                    row.video_code,
                    row.title or "",
                    row.release_date or ""
                ))

    def _init_maintain_import(self, parent):
        tk.Frame(parent, bg=self.colors["bg"], height=12).pack(fill=tk.X)
        form = tk.Frame(parent, bg=self.colors["bg"])
        form.pack(fill=tk.X, pady=10)

        tk.Label(form, text=self.t("maintain.scan_path"), bg=self.colors["bg"], fg=self.colors["gray800"], font=self.fonts["base"]).pack(side=tk.LEFT)
        self.scan_dir_var = tk.StringVar()
        entry_container, entry = self._create_styled_entry(form, textvariable=self.scan_dir_var, width=50, font=self.fonts["base"])
        entry_container.pack(side=tk.LEFT, padx=8)
        self._attach_entry_context_menu(entry)

        def choose_dir():
            current = (self.scan_dir_var.get() or "").strip()
            initialdir = current if current and os.path.isdir(current) else self._last_scan_dir
            d = filedialog.askdirectory(initialdir=initialdir)
            if d:
                self.scan_dir_var.set(d)
                self._last_scan_dir = d

        self._make_action_button(form, text=self.t("maintain.choose_dir"), command=choose_dir).pack(side=tk.LEFT, padx=8)

        status = tk.Label(parent, text="", bg=self.colors["bg"], fg=self.colors["gray700"])
        status.pack(fill=tk.X, pady=6)

        log_frame = tk.Frame(parent, bg=self.colors["bg"])
        log_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        log_text = tk.Text(log_frame, height=10, bg=self.colors["white"], fg=self.colors["gray800"], wrap="none")
        vsb = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
        log_text.configure(yscrollcommand=vsb.set)
        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        pb = ttk.Progressbar(parent, mode="determinate", length=360, style="Blue.Horizontal.TProgressbar")
        
        def append_log(line: str):
            log_text.insert(tk.END, line + "\n")
            try:
                max_lines = self._log_max_lines
                line_count = int(log_text.index("end-1c").split(".")[0])
                if line_count > max_lines:
                    log_text.delete("1.0", f"{line_count - max_lines + 1}.0")
            except Exception:
                pass
            log_text.see(tk.END)

        # 文件名调整逻辑
        def do_filename_adjustment():
            import threading
            path = self.scan_dir_var.get().strip()
            if not path:
                messagebox.showwarning(self.t("message.title.tip"), self.t("maintain.select_path_warning"))
                return
            
            log_text.delete("1.0", tk.END)
            status.configure(text=self.t("maintain.status.prepare_adjust", path=path))
            pb.pack(anchor="w", pady=4)
            pb.configure(value=0)

            def worker():
                def on_progress(current, total, message):
                    progress = (current / total) * 100 if total > 0 else 0
                    
                    def update_ui():
                        pb.configure(value=progress)
                        append_log(message)
                        status.configure(text=self.t("maintain.status.adjusting", current=current, total=total))
                    
                    self.root.after(0, update_ui)
                    time.sleep(0.1)  # 模拟逐行打印效果

                try:
                    # 注意：这里直接使用回调进行日志输出，不再依赖返回的log_lines进行一次性输出
                    # 但 run_filename_adjustment 仍会返回完整结果
                    results = run_filename_adjustment(path, flatten_output=True, progress_callback=on_progress)
                    final_log_lines = results.get("log_lines", [])
                except Exception as e:
                    final_log_lines = [f"Error: {e}"]
                
                def finish():
                    pb.pack_forget()
                    # 不再重复追加所有日志，因为回调里已经打印了
                    # for line in final_log_lines:
                    #     append_log(line)
                    status.configure(text=self.t("maintain.status.adjust_done"))
                
                self.root.after(0, finish)
            threading.Thread(target=worker, daemon=True).start()

        # 维护逻辑
        def do_maintain():
            import threading
            path = self.scan_dir_var.get().strip()
            if not path:
                messagebox.showwarning(self.t("message.title.tip"), self.t("maintain.select_path_warning"))
                return

            log_text.delete("1.0", tk.END)
            status.configure(text=self.t("maintain.status.prepare_scan", path=path))
            pb.pack(anchor="w", pady=4)
            pb.configure(value=0)

            def worker():
                # 捕获 stdout
                old_stdout = sys.stdout
                class Redirector:
                    def __init__(self, callback): self.callback = callback
                    def write(self, s): 
                        if s.strip(): self.callback(s)
                    def flush(self): pass
                
                def on_log(s):
                    self.root.after(0, lambda: append_log(s.strip()))

                def on_progress(current, total, message):
                    progress = (current / total) * 100 if total > 0 else 0
                    def update_pb():
                        pb.configure(value=progress)
                        # status.configure(text=message) # 可能会与log刷屏冲突，暂时只更新进度条
                    self.root.after(0, update_pb)

                result = None
                error = None
                try:
                    sys.stdout = Redirector(on_log)
                    result = start_maintain(path, progress_callback=on_progress)
                except Exception as e:
                    error = e
                finally:
                    sys.stdout = old_stdout
                
                def finish():
                    pb.pack_forget()
                    if error:
                        messagebox.showerror(self.t("message.title.system_error"), self.t("maintain.error.unhandled", error=error))
                        status.configure(text=self.t("maintain.status.system_error", error=error))
                        return

                    if result and result.get("success"):
                        status.configure(text=self.t("maintain.status.completed", count=result.get("processed_count")))
                    else:
                        msg = result.get("message") if result else self.t("maintain.error.unknown")
                        messagebox.showerror(self.t("message.title.failed"), msg)
                        status.configure(text=self.t("maintain.status.failed", message=msg))

                self.root.after(0, finish)

            threading.Thread(target=worker, daemon=True).start()

        btn_row = tk.Frame(parent, bg=self.colors["bg"])
        btn_row.pack(anchor="w", pady=4)
        self._make_action_button(btn_row, text=self.t("maintain.filename_adjust"), command=do_filename_adjustment).pack(side=tk.LEFT, padx=6)
        self._make_action_button(btn_row, text=self.t("maintain.ingest"), command=do_maintain).pack(side=tk.LEFT, padx=6)

    def _init_maintain_settings(self, parent):
        tk.Frame(parent, bg=self.colors["bg"], height=12).pack(fill=tk.X)
        
        # 使用 Canvas 实现滚动
        canvas = tk.Canvas(parent, bg=self.colors["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors["bg"])

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            # Windows/macOS/Linux differences
            if sys.platform == "darwin":
                delta = -1 * event.delta
            elif sys.platform.startswith("linux"):
                if event.num == 4: delta = -1
                elif event.num == 5: delta = 1
                else: delta = 0
            else: # Windows
                delta = -1 * (event.delta // 120)
            
            canvas.yview_scroll(int(delta), "units")

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        # Bind enter/leave events to the scrollable area
        scrollable_frame.bind("<Enter>", _bind_mousewheel)
        scrollable_frame.bind("<Leave>", _unbind_mousewheel)
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        def update_scrollregion():
            self._settings_scroll_job = None
            if not getattr(self, "_settings_scroll_dirty", True):
                return
            start_time = time.perf_counter()
            bbox = canvas.bbox("all")
            if not bbox:
                bbox = (0, 0, 0, 0)
            canvas.configure(scrollregion=bbox)
            self._settings_scrollregion_cache = bbox
            self._settings_scroll_dirty = False
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            if self._debug_tab_perf:
                print(f"[perf] {datetime.now().isoformat(timespec='milliseconds')} update_scrollregion elapsed_ms={elapsed_ms:.2f}")
            self._perf_record("update_scrollregion", elapsed_ms)

        def mark_settings_scroll_dirty():
            self._settings_scroll_dirty = True
            notebook = getattr(self, "_maintain_notebook", None)
            settings_id = getattr(self, "_maintain_settings_tab_id", None)
            if notebook and settings_id and notebook.select() == settings_id:
                if self._settings_scroll_job is None:
                    self._settings_scroll_job = self.root.after_idle(update_scrollregion)

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._settings_scroll_dirty = True
        self._settings_canvas = canvas
        self._settings_update_scroll = update_scrollregion

        form = tk.Frame(scrollable_frame, bg=self.colors["bg"])
        form.pack(fill=tk.X, pady=20)
        
        # Title Setting
        # 加大字体
        tk.Label(form, text=self.t("settings.app_title"), bg=self.colors["bg"], fg=self.colors["gray800"], font=self.fonts["bold"]).pack(anchor="w", padx=20, pady=(0, 8))
        
        self.settings_title_var = tk.StringVar(value=self.settings.app_title)
        title_entry_container, title_entry = self._create_styled_entry(form, textvariable=self.settings_title_var, width=50, font=self.fonts["base"])
        title_entry_container.pack(anchor="w", padx=20, pady=(0, 15))
        self._attach_entry_context_menu(title_entry)

        tk.Label(form, text=self.t("settings.language"), bg=self.colors["bg"], fg=self.colors["gray800"], font=self.fonts["bold"]).pack(anchor="w", padx=20, pady=(0, 8))
        self.settings_language_var = tk.StringVar(value=self._language_labels.get(self.settings.language, self._language_labels["zh_CN"]))
        language_cb = ttk.Combobox(form, textvariable=self.settings_language_var, width=16, state="readonly", font=self.fonts["base"])
        language_cb["values"] = tuple(self._language_labels.values())
        language_cb.pack(anchor="w", padx=20, pady=(0, 15), ipady=6)
        
        # Page Size Setting
        tk.Frame(form, height=1, bg=self.colors["gray200"]).pack(fill=tk.X, padx=20, pady=15)
        tk.Label(form, text=self.t("settings.query_section"), bg=self.colors["bg"], fg=self.colors["gray800"], font=self.fonts["bold"]).pack(anchor="w", padx=20, pady=(0, 8))
        
        size_frame = tk.Frame(form, bg=self.colors["bg"])
        size_frame.pack(anchor="w", padx=20)
        tk.Label(size_frame, text=self.t("settings.page_size"), bg=self.colors["bg"], font=self.fonts["base"]).pack(side=tk.LEFT)
        self.settings_page_size_var = tk.IntVar(value=self.settings.page_size)
        size_entry_container, size_entry = self._create_styled_entry(size_frame, textvariable=self.settings_page_size_var, width=10, font=self.fonts["base"])
        size_entry_container.pack(side=tk.LEFT, padx=10)
        self._attach_entry_context_menu(size_entry)
        
        # Column Visibility Setting
        tk.Label(form, text=self.t("settings.visible_columns"), bg=self.colors["bg"], font=self.fonts["base"]).pack(anchor="w", padx=20, pady=(15, 8))
        
        cols_frame = tk.Frame(form, bg=self.colors["bg"])
        cols_frame.pack(anchor="w", padx=20)
        
        # Full list of available columns (key, label)
        available_columns = [
            ("video", self._column_labels["video"]),
            ("actress", self._column_labels["actress"]),
            ("tags", self._column_labels["tags"]),
            ("file_path", self._column_labels["file_path"]),
            ("file_size", self._column_labels["file_size"]),
            ("duration", self._column_labels["duration"]),
            ("resolution", self._column_labels["resolution"]),
            ("updated_time", self._column_labels["updated_time"]),
            ("preference", self._column_labels["preference"])
        ]
        
        self.column_vars = {}
        current_cols = self.settings.visible_columns
        
        # Grid layout for checkboxes
        r, c = 0, 0
        for col_key, col_label in available_columns:
            var = tk.BooleanVar(value=col_key in current_cols)
            # Video column is mandatory
            state = tk.DISABLED if col_key == "video" else tk.NORMAL
            if col_key == "video": var.set(True)
            
            cb = tk.Checkbutton(cols_frame, text=col_label, variable=var, bg=self.colors["bg"], state=state, font=("Helvetica", 11))
            cb.grid(row=r, column=c, sticky="w", padx=(0, 15), pady=5)
            self.column_vars[col_key] = var
            
            c += 1
            if c > 4: # 5 columns per row
                c = 0
                r += 1
        
        # Tags Management Section
        tk.Frame(form, height=1, bg=self.colors["gray200"]).pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(form, text=self.t("settings.tags_section"), bg=self.colors["bg"], fg=self.colors["gray800"], font=("Helvetica", 14, "bold")).pack(anchor="w", padx=20, pady=(0, 8))
        
        tags_frame = tk.Frame(form, bg=self.colors["bg"])
        tags_frame.pack(fill=tk.X, padx=20)
        
        # Tags List (Combobox as requested)
        tk.Label(tags_frame, text=self.t("settings.tags_select"), bg=self.colors["bg"]).grid(row=0, column=0, sticky="w", pady=5)
        self.tags_cb = ttk.Combobox(tags_frame, width=40, state="readonly")
        self.tags_cb.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        # Tag Name Entry
        tk.Label(tags_frame, text=self.t("settings.tags_name"), bg=self.colors["bg"]).grid(row=1, column=0, sticky="w", pady=5)
        self.tag_name_var = tk.StringVar()
        tag_entry_container, tag_entry = self._create_styled_entry(tags_frame, textvariable=self.tag_name_var, width=42, font=self.fonts["base"])
        tag_entry_container.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        self._attach_entry_context_menu(tag_entry)
        
        # Tag Buttons
        btn_frame = tk.Frame(tags_frame, bg=self.colors["bg"])
        btn_frame.grid(row=2, column=1, sticky="w", padx=10, pady=10)
        
        # Internal state for tags
        self._current_tags = list(self.settings.tags) # Copy
        self._current_tags.sort()
        self.tags_cb.configure(postcommand=lambda: self.tags_cb.configure(values=self._current_tags))
        
        def refresh_tags_ui(select_val=None):
            self._current_tags.sort()
            if select_val:
                self.tags_cb.set(select_val)
                # Keep the input value as requested
                self.tag_name_var.set(select_val)
            else:
                self.tags_cb.set('')
                self.tag_name_var.set('')
            check_changes()
            mark_settings_scroll_dirty()
            
        def on_tag_select(event):
            selected = self.tags_cb.get()
            if selected:
                self.tag_name_var.set(selected)
                
        self.tags_cb.bind("<<ComboboxSelected>>", on_tag_select)
        
        def add_tag():
            val = self.tag_name_var.get().strip()
            if not val:
                messagebox.showwarning(self.t("message.title.tip"), self.t("settings.tags_name_required"))
                return
            if val in self._current_tags:
                messagebox.showwarning(self.t("message.title.tip"), self.t("settings.tags_exists"))
                return
            self._current_tags.append(val)
            refresh_tags_ui(select_val=val)
            
        def update_tag():
            old_val = self.tags_cb.get()
            new_val = self.tag_name_var.get().strip()
            if not old_val:
                return
            if not new_val:
                messagebox.showwarning(self.t("message.title.tip"), self.t("settings.tags_name_required"))
                return
            if new_val != old_val and new_val in self._current_tags:
                messagebox.showwarning(self.t("message.title.tip"), self.t("settings.tags_target_exists"))
                return
                
            idx = self._current_tags.index(old_val)
            self._current_tags[idx] = new_val
            refresh_tags_ui(select_val=new_val)
            
        def delete_tag():
            val = self.tags_cb.get()
            if val and val in self._current_tags:
                self._current_tags.remove(val)
                refresh_tags_ui(select_val=None)

        self._make_action_button(btn_frame, text=self.t("settings.tags_add"), command=add_tag).pack(side=tk.LEFT, padx=(0, 5))
        self._make_action_button(btn_frame, text=self.t("settings.tags_update"), command=update_tag).pack(side=tk.LEFT, padx=5)
        self._make_action_button(btn_frame, text=self.t("settings.tags_delete"), command=delete_tag).pack(side=tk.LEFT, padx=5)

        # Save Settings Logic
        tk.Frame(form, height=1, bg=self.colors["gray200"]).pack(fill=tk.X, padx=20, pady=20)
        
        save_label = self.t("settings.save_button")
        footer_frame = tk.Frame(form, bg=self.colors["bg"])
        footer_frame.pack(fill=tk.X, padx=20)
        self.btn_save_settings = self._make_action_button(footer_frame, text=save_label, font=("Helvetica", 12), padx=20, pady=8)
        self.btn_save_settings.pack(side=tk.LEFT)
        
        def check_changes(*args):
            # Title
            title_changed = self.settings_title_var.get().strip() != self.settings.app_title
            
            # Tags
            tags_changed = set(self._current_tags) != set(self.settings.tags)

            # Language
            current_language = self._language_label_to_value.get(self.settings_language_var.get(), "zh_CN")
            language_changed = current_language != self.settings.language
            
            # Page Size
            try:
                current_size = self.settings_page_size_var.get()
            except:
                current_size = 0
            size_changed = current_size != self.settings.page_size
            
            # Columns
            current_cols = []
            for col, var in self.column_vars.items():
                if var.get():
                    current_cols.append(col)
            if "video" not in current_cols:
                current_cols.insert(0, "video")
            
            default_order = ["video", "actress", "tags", "file_path", "file_size", "duration", "resolution", "updated_time", "preference"]
            current_cols.sort(key=lambda x: default_order.index(x) if x in default_order else 999)
            
            cols_changed = current_cols != self.settings.visible_columns
            
            if title_changed or tags_changed or size_changed or cols_changed or language_changed:
                self.btn_save_settings.configure(fg="blue", text=f"{save_label}*")
            else:
                self.btn_save_settings.configure(fg="black", text=save_label)
        
        self.settings_title_var.trace("w", check_changes)
        self.settings_page_size_var.trace("w", check_changes)
        self.settings_language_var.trace("w", check_changes)
        for var in self.column_vars.values():
            var.trace("w", check_changes)
            
        # Check initial state
        check_changes()
        # Initial scroll region update
        self._settings_scroll_job = self.root.after(100, update_scrollregion)
        
        def save_settings():
            new_title = self.settings_title_var.get().strip()
            new_page_size = self.settings_page_size_var.get()
            new_language = self._language_label_to_value.get(self.settings_language_var.get(), "zh_CN")
            
            if not new_title:
                messagebox.showwarning(self.t("message.title.tip"), self.t("settings.title_required"))
                return
                
            try:
                if new_page_size < 1:
                    messagebox.showwarning(self.t("message.title.tip"), self.t("settings.page_size_gt_zero"))
                    return
            except Exception:
                messagebox.showwarning(self.t("message.title.tip"), self.t("settings.page_size_numeric"))
                return
            
            # Save Title
            self.settings.app_title = new_title
            self.root.title(new_title)
            if hasattr(self, 'brand_label'):
                self.brand_label.configure(text=new_title)
                
            # Save Page Size
            self.settings.page_size = new_page_size

            previous_language = self.settings.language
            self.settings.language = new_language
            
            # Save Visible Columns
            new_cols = []
            for col, var in self.column_vars.items():
                if var.get():
                    new_cols.append(col)
            
            # Ensure video is first and present
            if "video" not in new_cols:
                new_cols.insert(0, "video")
            
            # Sort based on default order
            default_order = ["video", "actress", "tags", "file_path", "file_size", "duration", "resolution", "updated_time", "preference"]
            new_cols.sort(key=lambda x: default_order.index(x) if x in default_order else 999)
            
            self.settings.visible_columns = new_cols
                
            # Save Tags
            self.settings.tags = self._current_tags
            
            self.settings.save_settings()
            
            language_changed = previous_language != new_language
            if language_changed:
                self._apply_language(new_language)
                return

            check_changes()

            if hasattr(self, "_refresh_query_page_columns"):
                self._refresh_query_page_columns()
            
        self.btn_save_settings.configure(command=save_settings)

    def _refresh_query_page_columns(self):
        # Helper to update query page treeview columns dynamically
        if "query" not in self.pages: return
        
        # Find treeview in query page
        def find_tree(widget):
            if isinstance(widget, ttk.Treeview): return widget
            for child in widget.winfo_children():
                res = find_tree(child)
                if res: return res
            return None
            
        table = find_tree(self.pages["query"])
        if not table: return
        
        columns = tuple(self.settings.visible_columns)
        table["columns"] = columns
        table["displaycolumns"] = columns # Ensure visibility
        
        header_texts = dict(self._column_labels)
        
        left_cols = {"video", "actress", "tags", "file_path", "preference"}
        
        for col in columns:
            text = header_texts.get(col, col)
            table.heading(col, text=text, anchor="w" if col in left_cols else "e", command=lambda c=col: self._sort_table(table, c))
            
            if col == "file_path": width = 280
            elif col == "tags": width = 160
            elif col == "actress": width = 120
            elif col == "updated_time": width = 140
            elif col == "preference": width = 80
            else: width = 120
            table.column(col, width=width, anchor="w" if col in left_cols else "e")

        if hasattr(self.pages["query"], "refresh_data"):
            self.pages["query"].refresh_data()

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

        # 结果表格容器
        table_container = tk.Frame(parent, bg=self.colors["bg"])
        table_container.pack(fill=tk.BOTH, expand=True, pady=10)

        columns = ("video", "file_path", "file_size", "duration", "resolution", "updated_time")
        table = ttk.Treeview(table_container, columns=columns, show="headings")
        
        header_texts = {
            "video": self._column_labels["video"],
            "file_path": self._column_labels["file_path"],
            "file_size": self._column_labels["file_size"],
            "duration": self._column_labels["duration"],
            "resolution": self._column_labels["resolution"],
            "updated_time": self._column_labels["updated_time"]
        }
        
        for col in columns:
            table.heading(col, text=header_texts[col], anchor="w", command=lambda c=col: self._sort_table(table, c))
            if col == "file_path": width = 300
            elif col == "updated_time": width = 120
            elif col == "video": width = 150
            else: width = 100
            table.column(col, width=width, anchor="w")

        # 保存列名映射供排序使用
        table._header_texts = header_texts
        table._context_role = "maintain"

        vsb = ttk.Scrollbar(table_container, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=vsb.set)
        table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        table.bind("<Double-1>", lambda e: self._on_table_double_click(table, e))
        # 兼容 macOS 和 Windows 的右键绑定
        for sequence in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
            table.bind(sequence, lambda e: self._on_table_right_click(table, e))

        # 损坏视频按钮
        btn_broken = self._make_action_button(tools_row, text=self.t("maintain.broken_button"))
        
        def show_broken_videos():
            import threading, queue
            q = queue.Queue()
            orig = btn_broken.cget("text")
            btn_broken.configure(state=tk.DISABLED, text=self.t("button.loading"))
            
            # 清空表格
            self._render_table(table, [])
            
            def worker():
                try:
                    from ui.services import VideoService
                    local_service = VideoService()
                    res = local_service.broken_videos(ensure_accessible=True) or []
                except Exception:
                    res = []
                q.put(res)
            
            def check():
                try:
                    res = q.get_nowait()
                    btn_broken.configure(state=tk.NORMAL, text=orig)
                    # 按视频升序排序
                    res.sort(key=lambda x: x.get('video') or x.get('filename') or '')
                    table._context_role = "maintain"
                    self._render_table(table, res)
                except queue.Empty:
                    self.root.after(100, check)
            
            threading.Thread(target=worker, daemon=True).start()
            check()

        btn_broken.configure(command=show_broken_videos)
        btn_broken.pack(side=tk.LEFT, padx=6)

        # 重复视频按钮
        btn_dup = self._make_action_button(tools_row, text=self.t("maintain.duplicate_button"))
        
        def show_duplicate_videos():
            import threading, queue
            q = queue.Queue()
            orig = btn_dup.cget("text")
            btn_dup.configure(state=tk.DISABLED, text=self.t("button.loading"))
            
            # 清空表格
            self._render_table(table, [])

            def worker():
                try:
                    from ui.services import VideoService
                    local_service = VideoService()
                    res = local_service.duplicate_videos(ensure_accessible=True) or []
                except Exception:
                    res = []
                q.put(res)
            
            def check():
                try:
                    res = q.get_nowait()
                    btn_dup.configure(state=tk.NORMAL, text=orig)
                    # 按视频升序排序
                    res.sort(key=lambda x: x.get('video') or x.get('filename') or '')
                    table._context_role = "maintain"
                    self._render_table(table, res)
                except queue.Empty:
                    self.root.after(100, check)

            threading.Thread(target=worker, daemon=True).start()
            check()

        btn_dup.configure(command=show_duplicate_videos)
        btn_dup.pack(side=tk.LEFT, padx=6)


    # ================= 通用辅助 =================
    def _render_table(self, table: ttk.Treeview, rows: list[dict]) -> None:
        for item in table.get_children():
            table.delete(item)
        if not rows:
            try:
                columns = list(table["columns"])
            except Exception:
                columns = ["video"]
            empty_values = [""] * len(columns)
            empty_values[0] = self.t("table.empty")
            table.insert("", tk.END, values=empty_values)
            table._row_cache = {}
            return

        row_cache = {}
        columns = list(table["columns"])
        
        for r in rows:
            video_label = r.get("video") or r.get("filename") or ""
            tags_label = r.get("tags") or r.get("labels") or ""
            pref_status = r.get("preference")
            
            values = []
            for col in columns:
                if col in ("video", "filename"): values.append(video_label)
                elif col == "actress": values.append(r.get("actress", ""))
                elif col in ("tags", "labels"): values.append(tags_label)
                elif col == "file_path":
                    fp = r.get("file_path")
                    # For query page we want full path? No, logic above says parent dir? 
                    # Actually logic above (line 966) shows parent dir.
                    # But if query page, maybe we want full path or relative?
                    # The original code: values.append(str(Path(fp).parent) if fp else "")
                    # Wait, let's keep original behavior.
                    values.append(str(Path(fp).parent) if fp else "")
                elif col == "file_size": values.append(r.get("file_size", ""))
                elif col == "duration": values.append(r.get("duration", ""))
                elif col == "resolution": values.append(r.get("resolution", ""))
                elif col == "updated_time":
                    val = r.get("updated_time")
                    if isinstance(val, (int, float)):
                        try:
                            val = datetime.fromtimestamp(val).strftime("%Y-%m-%d")
                        except Exception:
                            val = str(val)
                    values.append(str(val) if val else "")
                elif col == "preference":
                    values.append(self._preference_labels["like"] if pref_status == "like" else self._preference_labels["dislike"] if pref_status == "dislike" else self._preference_labels["deleted"] if pref_status == "deleted" else "")
                else: values.append(str(r.get(col, "")))
            
            tags = ()
            if pref_status == "like": tags = ("pref_like",)
            elif pref_status == "dislike": tags = ("pref_dislike",)
            elif pref_status == "deleted": tags = ("pref_deleted",)
            
            item_id = table.insert("", tk.END, values=values, tags=tags)
            row_cache[item_id] = r
            
        table._row_cache = row_cache

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

    def _on_table_double_click(self, table: ttk.Treeview, event: tk.Event):
        # 防抖动：避免快速双击触发两次
        if getattr(self, "_processing_click", False):
            return "break"
        self._processing_click = True
        
        try:
            item = table.identify_row(event.y)
            if not item: return
            
            # Identify column
            col_name = None
            try:
                col_id = table.identify_column(event.x)
                col_idx = int(col_id.replace("#", "")) - 1
                col_name = table["columns"][col_idx]
            except: pass

            row = getattr(table, "_row_cache", {}).get(item, {})
            file_path = row.get("file_path")
            if file_path:
                if Path(file_path).exists():
                    if col_name == "file_path" or col_name == "path":
                        self._open_file_manager(file_path)
                    else:
                        self._play_video(file_path)
                else:
                    messagebox.showerror(self.t("message.title.file_missing"), self.t("message.file_missing", path=file_path))
        finally:
            # 500ms 后重置点击状态
            self.root.after(500, lambda: setattr(self, "_processing_click", False))
        
        return "break"

    def _open_file_manager(self, path: str):
        try:
            p = Path(path)
            target = p.parent if p.is_file() else p
            path_str = str(target)
            
            if sys.platform == "win32": os.startfile(path_str)
            elif sys.platform == "darwin": os.system(f"open '{path_str}'")
            else: os.system(f"xdg-open '{path_str}'")
        except Exception as e:
            messagebox.showerror(self.t("message.title.open_dir_failed"), str(e))

    def _on_table_right_click(self, table: ttk.Treeview, event: tk.Event):
        item = table.identify_row(event.y)
        if not item: return
        row = getattr(table, "_row_cache", {}).get(item, {})
        role = getattr(table, "_context_role", "query")
        file_path = row.get("file_path")
        if role == "query":
            if not file_path: return
        
        menu = tk.Menu(self.root, tearoff=0)
        setattr(table, "_context_menu", menu)
        video_label = row.get("video") or row.get("filename") or ""
        video_code = row.get("video_code") or ""
        video_id = row.get("id")
        
        if role.startswith("maintain"):
            if video_id:
                menu.add_command(label=self.t("context.delete_record"), command=lambda: self._confirm_and_delete(table, item, int(video_id), video_label))
            else:
                menu.add_command(label=self.t("context.delete_record"), state=tk.DISABLED)
        else:
            if video_code:
                actress_label = row.get("actress") or ""
                menu.add_command(label=self.t("context.edit_actress"), command=lambda: self._open_actress_manager(table, item, video_code, actress_label))
            else:
                menu.add_command(label=self.t("context.edit_actress"), state=tk.DISABLED)
            
            if video_id:
                tags_label = row.get("tags") or ""
                menu.add_command(label=self.t("context.edit_tags"), command=lambda: self._open_tags_manager(table, item, video_id, tags_label))
                menu.add_separator()
            
            menu.add_command(label=self.t("context.mark_like"), command=lambda: self._set_row_preference(table, item, video_label, "like"))
            menu.add_command(label=self.t("context.mark_dislike"), command=lambda: self._set_row_preference(table, item, video_label, "dislike"))
            menu.add_command(label=self.t("context.mark_deleted"), command=lambda: self._set_row_preference(table, item, video_label, "deleted"))
            menu.add_command(label=self.t("context.clear_preference"), command=lambda: self._set_row_preference(table, item, video_label, None))
            menu.add_separator()
            
            players = self._get_system_video_players()
            for name, path in players.items():
                menu.add_command(label=name, command=lambda p=path: self._play_video_with_player(Path(file_path), p))
            
        try:
            menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            return

    def _confirm_and_delete(self, table: ttk.Treeview, item_id: str, video_id: int, video_label: str) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.withdraw()
        dialog.title(self.t("dialog.confirm_delete_title"))
        dialog.geometry("420x180")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_set()
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.deiconify()
        
        container = tk.Frame(dialog, bg=self.colors["white"], padx=16, pady=16)
        container.pack(fill=tk.BOTH, expand=True)
        
        title = tk.Label(container, text=self.t("dialog.confirm_delete_heading"), bg=self.colors["white"], fg=self.colors["brand"], font=("Helvetica", 16, "bold"))
        title.pack(anchor="w")
        
        msg = tk.Label(
            container,
            text=self.t("dialog.confirm_delete_message", video=video_label),
            bg=self.colors["white"], fg=self.colors["gray800"], justify="left", wraplength=380
        )
        msg.pack(anchor="w", pady=(8, 12))
        
        btns = tk.Frame(container, bg=self.colors["white"])
        btns.pack(fill=tk.X, pady=(6, 0))
        
        result = {"confirm": False}
        def do_cancel():
            result["confirm"] = False
            dialog.destroy()
        def do_delete():
            result["confirm"] = True
            dialog.destroy()
        
        cancel_btn = self._make_action_button(btns, text=self.t("button.cancel"), command=do_cancel, padx=20, pady=8)
        cancel_btn.pack(side=tk.RIGHT, padx=6)
        delete_btn = self._make_action_button(btns, text=self.t("button.delete"), command=do_delete, padx=20, pady=8)
        delete_btn.configure(bg=self.colors["brand"], fg="black", activebackground=self.colors["brand"])
        delete_btn.pack(side=tk.RIGHT, padx=6)
        
        dialog.wait_window(dialog)
        if not result["confirm"]:
            return
        
        try:
            from ui.services import VideoService
            svc = VideoService()
            ok = svc.delete_video(video_id)
        except Exception as e:
            messagebox.showerror(self.t("message.title.delete_failed"), str(e))
            return
        
        if ok:
            row_cache = getattr(table, "_row_cache", {})
            table.delete(item_id)
            row_cache.pop(item_id, None)
        else:
            messagebox.showwarning(self.t("message.title.not_deleted"), self.t("message.delete_not_success"))

    def _open_tags_manager(self, table: ttk.Treeview, item_id: str, video_id: int, current_tags_str: str) -> None:
        """打开标签管理对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.withdraw()  # 先隐藏，避免闪烁
        dialog.title(self.t("dialog.manage_tags_title"))
        dialog.geometry("400x500")
        
        # Center dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.deiconify()  # 位置确定后再显示
        
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_set()
        
        # Parse current tags
        current_tags = set(t.strip() for t in current_tags_str.split(",") if t.strip())
        
        # Container
        container = tk.Frame(dialog, bg=self.colors["white"], padx=15, pady=15)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Add New Tag Section
        add_frame = tk.Frame(container, bg=self.colors["white"])
        add_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(add_frame, text=self.t("tags.add_label"), bg=self.colors["white"]).pack(side=tk.LEFT)
        new_tag_var = tk.StringVar()
        entry_container, entry = self._create_styled_entry(add_frame, textvariable=new_tag_var, font=self.fonts["base"])
        entry_container.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Tags List (Checkboxes)
        list_frame = tk.Frame(container, bg=self.colors["white"], relief=tk.GROOVE, bd=1)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        canvas = tk.Canvas(list_frame, bg=self.colors["white"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors["white"])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            # Windows/macOS/Linux differences
            if sys.platform == "darwin":
                delta = -1 * event.delta
            elif sys.platform.startswith("linux"):
                if event.num == 4: delta = -1
                elif event.num == 5: delta = 1
                else: delta = 0
            else: # Windows
                delta = -1 * (event.delta // 120)
            
            canvas.yview_scroll(int(delta), "units")

        # Bind wheel events to canvas and frame
        bind_tags = ("<MouseWheel>", "<Button-4>", "<Button-5>")
        for tag in bind_tags:
            canvas.bind(tag, _on_mousewheel)
            scrollable_frame.bind(tag, _on_mousewheel)
        
        # Variables to track check states
        check_vars = {}
        
        def refresh_list():
            # Clear existing
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
            
            # Merge settings tags and current video tags (in case video has tags not in settings)
            all_tags = sorted(list(set(self.settings.tags) | current_tags))
            
            for tag in all_tags:
                var = tk.BooleanVar(value=tag in current_tags)
                check_vars[tag] = var
                cb = tk.Checkbutton(scrollable_frame, text=tag, variable=var, bg=self.colors["white"], anchor="w")
                cb.pack(fill=tk.X, padx=5, pady=2)
        
        refresh_list()
        
        def add_new_tag():
            val = new_tag_var.get().strip()
            if not val: return
            
            # Add to local set and refresh
            current_tags.add(val)
            
            # Add to global settings if not exists
            if val not in self.settings.tags:
                 temp = list(self.settings.tags)
                 temp.append(val)
                 self.settings.tags = temp
                 self.settings.save_settings()
                 
                 # Sync with Settings page UI if initialized
                 if hasattr(self, '_current_tags'):
                     if val not in self._current_tags:
                         self._current_tags.append(val)
                         self._current_tags.sort()
                 if hasattr(self, 'tags_cb'):
                     self.tags_cb['values'] = self._current_tags
            
            new_tag_var.set("")
            refresh_list()
            
        self._make_action_button(add_frame, text=self.t("button.add"), command=add_new_tag).pack(side=tk.LEFT)
        entry.bind("<Return>", lambda e: add_new_tag())
        
        # Buttons
        btn_frame = tk.Frame(container, bg=self.colors["white"])
        btn_frame.pack(fill=tk.X, pady=(15, 0))
        
        def save():
            selected = [tag for tag, var in check_vars.items() if var.get()]
            
            # Call service
            success = update_video_tags(video_id, selected)
            if success:
                # Update UI
                new_tags_str = ", ".join(sorted(selected))
                
                # Update row cache
                row = getattr(table, "_row_cache", {}).get(item_id)
                if row:
                    row["tags"] = new_tags_str
                    # Update tags or labels key depending on what's used
                    row["labels"] = new_tags_str 
                
                # Update treeview
                values = list(table.item(item_id, "values") or [])
                cols = list(table["columns"])
                if "tags" in cols:
                    idx = cols.index("tags")
                    values[idx] = new_tags_str
                    table.item(item_id, values=values)
                
                dialog.destroy()
            else:
                messagebox.showerror(self.t("message.title.error"), self.t("tags.save_failed"))
        
        # Changed button text color to black as requested
        self._make_action_button(btn_frame, text=self.t("button.save"), command=save).pack(side=tk.RIGHT)
        self._make_action_button(btn_frame, text=self.t("button.cancel"), command=dialog.destroy).pack(side=tk.RIGHT, padx=10)

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

    def _open_actress_manager(self, table: ttk.Treeview, item_id: str, video_code: str, current_actress_str: str) -> None:
        if not video_code:
            messagebox.showerror(self.t("message.title.cannot_edit"), self.t("actress.missing_video_code"))
            return
        dialog = tk.Toplevel(self.root)
        dialog.withdraw()
        dialog.title(self.t("dialog.edit_actress_title"))
        dialog.geometry("360x160")
        
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.deiconify()
        
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.focus_set()
        
        container = tk.Frame(dialog, bg=self.colors["white"], padx=15, pady=15)
        container.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(container, text=self.t("actress.input_label"), bg=self.colors["white"]).pack(anchor="w")
        actress_var = tk.StringVar(value=current_actress_str or "")
        entry_container, entry = self._create_styled_entry(container, textvariable=actress_var, font=self.fonts["base"])
        entry_container.pack(fill=tk.X, pady=8)
        entry.focus_set()
        
        btn_frame = tk.Frame(container, bg=self.colors["white"])
        btn_frame.pack(fill=tk.X, pady=(6, 0))
        
        def _on_save():
            raw = actress_var.get().strip()
            names = [n.strip() for n in re.split(r"[，,;；/、]", raw) if n and n.strip()]
            ok = self._set_row_actress(table, item_id, video_code, names)
            if ok:
                dialog.destroy()
            else:
                messagebox.showerror(self.t("message.title.save_failed"), self.t("actress.update_failed"))
        
        btn_save = self._make_action_button(btn_frame, text=self.t("button.save"), padx=10, command=_on_save)
        btn_save.pack(side=tk.RIGHT, padx=5)
        
        btn_cancel = self._make_action_button(btn_frame, text=self.t("button.cancel"), padx=10, command=dialog.destroy)
        btn_cancel.pack(side=tk.RIGHT, padx=5)

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

    def _show_video_list_window(self, title: str, rows: list[dict]) -> None:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("980x520")
        
        container = tk.Frame(win, bg=self.colors["white"])
        container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        
        table = ttk.Treeview(container, columns=("video", "file_size", "path"), show="headings")
        table.heading("video", text=self._column_labels["video"])
        table.heading("file_size", text=self._column_labels["file_size"])
        table.heading("path", text=self._column_labels["file_path"])
        table.column("video", width=200)
        table.column("file_size", width=100)
        table.column("path", width=400)
        table.pack(fill=tk.BOTH, expand=True)
        
        for r in rows:
            table.insert("", tk.END, values=(r.get("video"), r.get("file_size"), r.get("file_path")))
            
        table.bind("<Double-1>", lambda e: self._on_table_double_click(table, e))

    def _play_video(self, video_path: str):
        try:
            if sys.platform == "win32": os.startfile(video_path)
            elif sys.platform == "darwin": os.system(f"open '{video_path}'")
            else: os.system(f"xdg-open '{video_path}'")
        except Exception as e:
            messagebox.showerror(self.t("message.title.play_failed"), str(e))

    def _play_video_with_player(self, video_path: Path, player_path: str):
        try:
            if not player_path: self._play_video(str(video_path))
            elif sys.platform == "darwin": os.system(f'open -a "{player_path}" "{video_path}"')
            else: os.system(f'"{player_path}" "{video_path}"')
        except Exception as e:
            messagebox.showerror(self.t("message.title.play_failed"), str(e))

    def _get_system_video_players(self):
        players = {self.t("player.default"): None}
        
        if sys.platform == "darwin":
            # macOS 常见播放器路径检测
            common_players = {
                "QuickTime Player": ["/System/Applications/QuickTime Player.app", "/Applications/QuickTime Player.app"],
                "VLC": ["/Applications/VLC.app", os.path.expanduser("~/Applications/VLC.app")],
                "IINA": ["/Applications/IINA.app", os.path.expanduser("~/Applications/IINA.app")],
                "Movist Pro": ["/Applications/Movist Pro.app"],
                "Elmedia Player": ["/Applications/Elmedia Player.app"],
                "OmniPlayer": ["/Applications/OmniPlayer.app", os.path.expanduser("~/Applications/OmniPlayer.app")],
                "暴风影音": ["/Applications/Baofeng.app", "/Applications/Storm.app", os.path.expanduser("~/Applications/Baofeng.app")]
            }
            
            for name, paths in common_players.items():
                for path in paths:
                    if os.path.exists(path):
                        players[name] = path
                        break
                        
        elif sys.platform == "win32":
            # Windows 常见播放器路径检测
            # 注意：Windows 路径可能因安装位置不同而变化，这里检测默认安装路径
            common_players = {
                "PotPlayer": [
                    r"C:\Program Files\DAUM\PotPlayer\PotPlayerMini64.exe",
                    r"C:\Program Files (x86)\DAUM\PotPlayer\PotPlayerMini.exe"
                ],
                "VLC": [
                    r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                    r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
                ],
                "MPV": [
                    r"C:\Program Files\mpv\mpv.exe",
                    r"C:\Program Files (x86)\mpv\mpv.exe"
                ],
                "KMPlayer": [
                    r"C:\Program Files\KMPlayer\KMPlayer.exe",
                    r"C:\Program Files (x86)\KMPlayer\KMPlayer.exe",
                    r"C:\KMPlayer\KMPlayer.exe"
                ]
            }
            
            for name, paths in common_players.items():
                for path in paths:
                    if os.path.exists(path):
                        players[name] = path
                        break
                        
        return players

    def run(self) -> None:
        self.root.mainloop()

if __name__ == "__main__":
    XJJDesktopApp().run()
