from __future__ import annotations

import sys
from pathlib import Path
import re
import os
from datetime import datetime
import time

# 兼容直接运行：确保项目根目录在 sys.path 中
if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from ui.services import search_videos, start_maintain, random_videos, latest_videos, broken_videos, set_video_preference
except Exception as e:
    print(f"导入服务失败: {e}")
    # 提供降级占位，避免启动失败
    def search_videos(keyword: str):
        return []
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

try:
    from tools.movie_data_capture.service import MovieDataCaptureService
except ImportError:
    MovieDataCaptureService = None


APP_TITLE = "XJJ Housekeeper"


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

    formatter = FilenameFormatter()
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


class XJJDesktopApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("1000x640")
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
            "accent": "#60A5FA",
            "selected_bg": "#EEF2FF",
            "selected_border": "#C7D2FE",
            # 侧边栏样式调整：改为浅色清爽风格
            "sidebar_bg": "#FFFFFF",      # 纯白背景
            "sidebar_fg": "#4B5563",      # 深灰文字
            "sidebar_hover": "#F3F4F6",   # 悬停浅灰
            "sidebar_active": "#EFF6FF",  # 选中浅蓝背景
            "sidebar_active_fg": "#2563EB", # 选中品牌蓝文字
        }

        self._last_scan_dir: str | None = None
        self._log_max_lines = 2000
        self._ignore_query_trace = False

        self._init_styles()
        self._build_layout()
        
        # 页面容器
        self.pages = {}
        self._init_pages()

        # 默认显示查询页
        self.current_page = "query"
        self._update_sidebar_selection()
        self.show_page("query")

    def _init_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        # 表格样式
        style.configure(
            "Treeview",
            background=self.colors["white"],
            fieldbackground=self.colors["white"],
            foreground=self.colors["gray800"],
            rowheight=28,
        )
        style.configure(
            "Treeview.Heading",
            background=self.colors["gray100"],
            foreground=self.colors["gray800"],
            relief=tk.FLAT,
        )
        style.map("Treeview", background=[("selected", self.colors["brand"])], foreground=[("selected", self.colors["white"])])

        style.configure("Blue.Horizontal.TProgressbar", troughcolor=self.colors["gray100"], background=self.colors["brand"])

    def _build_layout(self) -> None:
        # 使用 Grid 布局：左侧边栏，右侧主内容
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # 1. 侧边导航栏 (Sidebar)
        self.sidebar = tk.Frame(self.root, bg=self.colors["sidebar_bg"], width=200)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False) # 固定宽度

        # 侧边栏标题
        brand = tk.Label(
            self.sidebar,
            text=APP_TITLE,
            bg=self.colors["sidebar_bg"],
            fg=self.colors["brand"],  # 标题改为品牌色
            font=("Helvetica", 14, "bold"),
            padx=20, pady=20
        )
        brand.pack(anchor="w")

        # 导航按钮容器
        self.nav_btns = {}
        self._add_sidebar_btn("query", "查 询", lambda: self.show_page("query"))
        self._add_sidebar_btn("maintain", "维 护", lambda: self.show_page("maintain"))

        # 2. 主内容区域 (Main)
        self.main_area = tk.Frame(self.root, bg=self.colors["bg"])
        self.main_area.grid(row=0, column=1, sticky="nsew")
        self.main_area.grid_rowconfigure(1, weight=1) # Row 1 是页面内容
        self.main_area.grid_columnconfigure(0, weight=1)

        # Header 区域 (Row 0)
        self.header = tk.Frame(self.main_area, bg=self.colors["bg"], height=50)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.pack_propagate(False)

        # 侧边栏切换按钮
        self.sidebar_visible = True
        self.toggle_btn = tk.Button(
            self.header,
            text="☰",
            font=("Helvetica", 16),
            bg=self.colors["bg"],
            fg=self.colors["gray700"],
            bd=0,
            relief=tk.FLAT,
            activebackground=self.colors["gray100"],
            command=self._toggle_sidebar,
            cursor="hand2"
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=10, pady=5)

    def _toggle_sidebar(self):
        if self.sidebar_visible:
            self.sidebar.grid_remove()
            self.sidebar_visible = False
        else:
            self.sidebar.grid()
            self.sidebar_visible = True

    def _add_sidebar_btn(self, key: str, text: str, command):
        btn = tk.Button(
            self.sidebar,
            text=text,
            bg=self.colors["sidebar_bg"],
            fg=self.colors["sidebar_fg"],
            font=("Helvetica", 12),
            bd=0,
            relief=tk.FLAT,
            activebackground=self.colors["sidebar_hover"],
            activeforeground=self.colors["brand"],
            anchor="w",
            padx=20,
            pady=10,
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
                    font=("Helvetica", 12, "bold")
                )
            else:
                btn.configure(
                    bg=self.colors["sidebar_bg"],
                    fg=self.colors["sidebar_fg"],
                    font=("Helvetica", 12, "normal")
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
        menu.add_command(label="剪切", command=lambda: entry.event_generate("<<Cut>>"))
        menu.add_command(label="复制", command=lambda: entry.event_generate("<<Copy>>"))
        menu.add_command(label="粘贴", command=lambda: entry.event_generate("<<Paste>>"))

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
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 搜索表单
        form = tk.Frame(content, bg=self.colors["bg"])
        form.pack(fill=tk.X)

        self.query_placeholder = "视频号/标签"
        self.query_var = tk.StringVar(value=self.query_placeholder)
        entry = tk.Entry(form, textvariable=self.query_var, width=40)
        entry.pack(side=tk.LEFT, padx=(0, 8))
        self._attach_entry_context_menu(entry)
        self.query_entry = entry

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
        table_container.pack(fill=tk.BOTH, expand=True, pady=12)
        
        columns = ("video", "tags", "file_path", "file_size", "duration", "resolution", "updated_time", "preference")
        table = ttk.Treeview(table_container, columns=columns, show="headings")
        left_cols = {"video", "tags", "file_path", "preference"}
        
        header_texts = {}
        for col, text in zip(columns, ("视频", "标签", "路径", "大小", "时长", "分辨率", "更新时间", "偏好")):
            header_texts[col] = text
            table.heading(col, text=text, anchor="w" if col in left_cols else "e", command=lambda c=col: self._sort_table(table, c))
            if col == "file_path": width = 280
            elif col == "tags": width = 160
            elif col == "updated_time": width = 140
            elif col == "preference": width = 80
            else: width = 120
            table.column(col, width=width, anchor="w" if col in left_cols else "e")
        
        table._header_texts = header_texts
        table.tag_configure("pref_like", background="#FEF3C7")
        table.tag_configure("pref_dislike", background="#FEE2E2")
        
        # 滚动条
        vsb = ttk.Scrollbar(table_container, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=vsb.set)
        table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 搜索逻辑
        def do_search_live():
            if self._ignore_query_trace:
                return
            keyword = self.query_var.get().strip()
            if not keyword or keyword == self.query_placeholder:
                self._render_table(table, [])
                return
            results = search_videos(keyword) or []
            results = self._sort_results_by_file_size_desc(results)
            self._render_table(table, results)

        def do_search():
            do_search_live()

        try:
            self.query_var.trace_add('write', lambda *_: do_search_live())
        except Exception:
            entry.bind("<KeyRelease>", lambda e: do_search_live())

        entry.bind("<Return>", lambda e: do_search())
        tk.Button(form, text="搜索", command=do_search, bg=self.colors["white"], relief=tk.GROOVE).pack(side=tk.LEFT, padx=8)

        def do_random_pick():
            try:
                results = random_videos(limit=20, ensure_accessible=True) or []
            except TypeError:
                results = random_videos() or []
            results = self._sort_results_by_file_size_desc(results)
            self._render_table(table, results)

        tk.Button(form, text="随机挑选", command=do_random_pick, bg=self.colors["white"], relief=tk.GROOVE).pack(side=tk.LEFT, padx=4)

        def do_latest_videos():
            try:
                results = latest_videos(days=14, limit=20, ensure_accessible=True) or []
            except TypeError:
                results = latest_videos() or []
            results = self._sort_results_by_file_size_desc(results)
            self._render_table(table, results)

        tk.Button(form, text="最新视频", command=do_latest_videos, bg=self.colors["white"], relief=tk.GROOVE).pack(side=tk.LEFT, padx=4)

        table.bind("<Double-1>", lambda e: self._on_table_double_click(table, e))
        # 兼容 macOS 和 Windows 的右键绑定
        for sequence in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
            table.bind(sequence, lambda e: self._on_table_right_click(table, e))

        self._render_table(table, [])
        return container

    # ================= 页面构建：维护 =================
    def _create_maintain_page(self, parent) -> tk.Frame:
        container = tk.Frame(parent, bg=self.colors["bg"])
        
        # 顶部 Tab 栏
        tab_bar = tk.Frame(container, bg=self.colors["bg"])
        tab_bar.pack(fill=tk.X, anchor="w", padx=20, pady=(20, 10))

        # 内容区域 (Grid Stack)
        content_stack = tk.Frame(container, bg=self.colors["bg"])
        content_stack.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        content_stack.grid_rowconfigure(0, weight=1)
        content_stack.grid_columnconfigure(0, weight=1)

        # 内部 Tab 页面
        tab_frames = {}
        tab_frames["import"] = tk.Frame(content_stack, bg=self.colors["bg"])
        tab_frames["manage"] = tk.Frame(content_stack, bg=self.colors["bg"])
        tab_frames["movie_info"] = tk.Frame(content_stack, bg=self.colors["bg"])
        
        for frame in tab_frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

        # Tab 切换按钮引用
        tab_btns = {}

        def switch_maintain_tab(target: str):
            # 切换显示
            tab_frames[target].tkraise()
            
            # 更新按钮样式
            font_normal = ("Helvetica", 12)
            font_bold = ("Helvetica", 12, "bold")
            
            for key, btn in tab_btns.items():
                if key == target:
                    btn.configure(
                        bg=self.colors["white"],
                        fg=self.colors["brand"],
                        font=font_bold
                    )
                else:
                    btn.configure(
                        bg=self.colors["gray100"],
                        fg=self.colors["gray700"],
                        font=font_normal
                    )

        # 创建 Tab 按钮
        def create_tab_btn(key, text):
            btn = tk.Button(
                tab_bar,
                text=text,
                command=lambda: switch_maintain_tab(key),
                bd=0,
                padx=16,
                pady=8,
                relief=tk.FLAT,
                activebackground=self.colors["white"],
                activeforeground=self.colors["brand"],
            )
            btn.pack(side=tk.LEFT, padx=(0, 4))
            tab_btns[key] = btn

        create_tab_btn("import", "导入新视频")
        create_tab_btn("manage", "旧视频管理")
        create_tab_btn("movie_info", "影视讯息管理")

        # 初始化各 Tab 内容
        self._init_maintain_import(tab_frames["import"])
        self._init_maintain_manage(tab_frames["manage"])
        self._init_maintain_movie_info(tab_frames["movie_info"])

        # 默认显示第一个
        switch_maintain_tab("import")

        return container

    def _init_maintain_movie_info(self, parent):
        if not MovieDataCaptureService:
            tk.Label(parent, text="影视讯息服务不可用 (MovieDataCaptureService 未找到)", bg=self.colors["bg"], fg="red").pack(pady=20)
            return

        form = tk.Frame(parent, bg=self.colors["bg"])
        form.pack(fill=tk.X, pady=10)

        # Search input
        self.movie_info_keyword = tk.StringVar()
        entry = tk.Entry(form, textvariable=self.movie_info_keyword, width=40)
        entry.pack(side=tk.LEFT, padx=8)
        self._attach_entry_context_menu(entry)

        # Search buttons
        def do_search(search_type):
            keyword = self.movie_info_keyword.get().strip()
            if not keyword:
                messagebox.showwarning("提示", "请输入查询关键字")
                return

            # Disable buttons during search (simple way)
            # Better to show loading state
            
            # Run in thread to avoid blocking UI
            import threading
            def worker():
                svc = MovieDataCaptureService()
                try:
                    rows = svc.search_movie_info(keyword, search_type)
                    # Update UI in main thread
                    self.root.after(0, lambda: render_results(rows))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
                finally:
                    svc.close()
            
            threading.Thread(target=worker, daemon=True).start()

        tk.Button(form, text="查女艺人", command=lambda: do_search("actress"), bg=self.colors["white"], relief=tk.GROOVE).pack(side=tk.LEFT, padx=4)
        tk.Button(form, text="查视频", command=lambda: do_search("video"), bg=self.colors["white"], relief=tk.GROOVE).pack(side=tk.LEFT, padx=4)

        # Results table
        table_container = tk.Frame(parent, bg=self.colors["bg"])
        table_container.pack(fill=tk.BOTH, expand=True, pady=10)

        columns = ("actress_name", "video_code", "release_date", "updated_at")
        table = ttk.Treeview(table_container, columns=columns, show="headings")
        
        table.heading("actress_name", text="女艺人", anchor="w")
        table.heading("video_code", text="视频号", anchor="w")
        table.heading("release_date", text="发布日期", anchor="w")
        table.heading("updated_at", text="更新时间", anchor="w")

        table.column("actress_name", width=150)
        table.column("video_code", width=150)
        table.column("release_date", width=120)
        table.column("updated_at", width=180)

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
                    row.release_date or "",
                    row.updated_at
                ))

    def _init_maintain_import(self, parent):
        form = tk.Frame(parent, bg=self.colors["bg"])
        form.pack(fill=tk.X, pady=10)

        tk.Label(form, text="扫描路径", bg=self.colors["bg"], fg=self.colors["gray800"], font=("Helvetica", 12)).pack(side=tk.LEFT)
        self.scan_dir_var = tk.StringVar()
        entry = tk.Entry(form, textvariable=self.scan_dir_var, width=50)
        entry.pack(side=tk.LEFT, padx=8)
        self._attach_entry_context_menu(entry)

        def choose_dir():
            current = (self.scan_dir_var.get() or "").strip()
            initialdir = current if current and os.path.isdir(current) else self._last_scan_dir
            d = filedialog.askdirectory(initialdir=initialdir)
            if d:
                self.scan_dir_var.set(d)
                self._last_scan_dir = d

        tk.Button(form, text="选择目录", command=choose_dir, bg=self.colors["white"], relief=tk.GROOVE).pack(side=tk.LEFT, padx=8)

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
            log_text.see(tk.END)

        # 文件名调整逻辑
        def do_filename_adjustment():
            import threading
            path = self.scan_dir_var.get().strip()
            if not path:
                messagebox.showwarning("提示", "请先选择扫描路径")
                return
            
            log_text.delete("1.0", tk.END)
            status.configure(text=f"准备文件名调整: {path}")
            pb.pack(anchor="w", pady=4)
            pb.configure(value=0)

            def worker():
                def on_progress(current, total, message):
                    progress = (current / total) * 100 if total > 0 else 0
                    
                    def update_ui():
                        pb.configure(value=progress)
                        append_log(message)
                        status.configure(text=f"正在调整... {current}/{total}")
                    
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
                    status.configure(text="文件名调整完成")
                
                self.root.after(0, finish)
            threading.Thread(target=worker, daemon=True).start()

        # 维护逻辑
        def do_maintain():
            import threading
            path = self.scan_dir_var.get().strip()
            if not path:
                messagebox.showwarning("提示", "请先选择扫描路径")
                return

            log_text.delete("1.0", tk.END)
            status.configure(text=f"准备扫描: {path}")
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
                        messagebox.showerror("系统错误", f"执行维护时发生未捕获异常:\n{error}")
                        status.configure(text=f"系统错误: {error}")
                        return

                    if result and result.get("success"):
                        status.configure(text=f"维护完成: 处理 {result.get('processed_count')} 个文件")
                    else:
                        msg = result.get("message") if result else "未知错误"
                        messagebox.showerror("失败", msg)
                        status.configure(text=f"失败: {msg}")

                self.root.after(0, finish)

            threading.Thread(target=worker, daemon=True).start()

        btn_row = tk.Frame(parent, bg=self.colors["white"])
        btn_row.pack(anchor="w", pady=4)
        tk.Button(btn_row, text="文件名调整", command=do_filename_adjustment, bg=self.colors["white"], relief=tk.GROOVE).pack(side=tk.LEFT, padx=6)
        tk.Button(btn_row, text="开始维护", command=do_maintain, bg=self.colors["white"], relief=tk.GROOVE).pack(side=tk.LEFT, padx=6)

    def _init_maintain_manage(self, parent):
        tools_section = tk.Frame(parent, bg=self.colors["bg"])
        tools_section.pack(fill=tk.X, pady=10)
        
        tools_row = tk.Frame(tools_section, bg=self.colors["white"])
        tools_row.pack(anchor="w", pady=4)

        # 结果表格容器
        table_container = tk.Frame(parent, bg=self.colors["bg"])
        table_container.pack(fill=tk.BOTH, expand=True, pady=10)

        columns = ("video", "file_path", "file_size", "duration", "resolution", "updated_time")
        table = ttk.Treeview(table_container, columns=columns, show="headings")
        
        header_texts = {
            "video": "视频",
            "file_path": "路径",
            "file_size": "大小",
            "duration": "时长",
            "resolution": "分辨率",
            "updated_time": "更新时间"
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

        vsb = ttk.Scrollbar(table_container, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=vsb.set)
        table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        table.bind("<Double-1>", lambda e: self._on_table_double_click(table, e))
        # 兼容 macOS 和 Windows 的右键绑定
        for sequence in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
            table.bind(sequence, lambda e: self._on_table_right_click(table, e))

        # 损坏视频按钮
        btn_broken = tk.Button(tools_row, text="损坏视频", bg=self.colors["white"], relief=tk.GROOVE)
        
        def show_broken_videos():
            import threading, queue
            q = queue.Queue()
            orig = btn_broken.cget("text")
            btn_broken.configure(state=tk.DISABLED, text="加载中...")
            
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
                    self._render_table(table, res)
                except queue.Empty:
                    self.root.after(100, check)
            
            threading.Thread(target=worker, daemon=True).start()
            check()

        btn_broken.configure(command=show_broken_videos)
        btn_broken.pack(side=tk.LEFT, padx=6)

        # 重复视频按钮
        btn_dup = tk.Button(tools_row, text="重复视频", bg=self.colors["white"], relief=tk.GROOVE)
        
        def show_duplicate_videos():
            import threading, queue
            q = queue.Queue()
            orig = btn_dup.cget("text")
            btn_dup.configure(state=tk.DISABLED, text="加载中...")
            
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
            empty_values[0] = "暂无数据"
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
                elif col in ("tags", "labels"): values.append(tags_label)
                elif col == "file_path":
                    fp = r.get("file_path")
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
                    values.append("喜欢" if pref_status == "like" else "不喜欢" if pref_status == "dislike" else "")
                else: values.append(str(r.get(col, "")))
            
            tags = ()
            if pref_status == "like": tags = ("pref_like",)
            elif pref_status == "dislike": tags = ("pref_dislike",)
            
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
                    messagebox.showerror("文件不存在", f"无法访问视频文件：\n{file_path}\n\n该文件可能已被移动、删除或所在的驱动器未连接。")
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
            messagebox.showerror("打开目录失败", str(e))

    def _on_table_right_click(self, table: ttk.Treeview, event: tk.Event):
        item = table.identify_row(event.y)
        if not item: return
        row = getattr(table, "_row_cache", {}).get(item, {})
        file_path = row.get("file_path")
        if not file_path: return
        
        menu = tk.Menu(self.root, tearoff=0)
        setattr(table, "_context_menu", menu)
        video_label = row.get("video") or row.get("filename") or ""
        
        menu.add_command(label="标记为喜欢", command=lambda: self._set_row_preference(table, item, video_label, "like"))
        menu.add_command(label="标记为不喜欢 (Trash)", command=lambda: self._set_row_preference(table, item, video_label, "dislike"))
        menu.add_command(label="清除偏好", command=lambda: self._set_row_preference(table, item, video_label, None))
        menu.add_separator()
        
        players = self._get_system_video_players()
        for name, path in players.items():
            menu.add_command(label=name, command=lambda p=path: self._play_video_with_player(Path(file_path), p))
            
        try:
            menu.tk_popup(event.x_root, event.y_root)
        except Exception:
            return

    def _set_row_preference(self, table: ttk.Treeview, item_id: str, video_code: str, status: str | None) -> None:
        try: set_video_preference(video_code, status)
        except: return
        
        row = getattr(table, "_row_cache", {}).get(item_id)
        if row: row["preference"] = status
        
        values = list(table.item(item_id, "values") or [])
        cols = list(table["columns"])
        if "preference" in cols:
            idx = cols.index("preference")
            display = "喜欢" if status == "like" else "不喜欢" if status == "dislike" else ""
            values[idx] = display
            table.item(item_id, values=values)
            
        if status == "like": table.item(item_id, tags=("pref_like",))
        elif status == "dislike": table.item(item_id, tags=("pref_dislike",))
        else: table.item(item_id, tags=())

    def _show_video_list_window(self, title: str, rows: list[dict]) -> None:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("980x520")
        
        container = tk.Frame(win, bg=self.colors["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        
        table = ttk.Treeview(container, columns=("video", "file_size", "path"), show="headings")
        table.heading("video", text="视频")
        table.heading("file_size", text="大小")
        table.heading("path", text="路径")
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
            messagebox.showerror("播放失败", str(e))

    def _play_video_with_player(self, video_path: Path, player_path: str):
        try:
            if not player_path: self._play_video(str(video_path))
            elif sys.platform == "darwin": os.system(f'open -a "{player_path}" "{video_path}"')
            else: os.system(f'"{player_path}" "{video_path}"')
        except Exception as e:
            messagebox.showerror("播放失败", str(e))

    def _get_system_video_players(self):
        players = {"默认播放器": None}
        
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
