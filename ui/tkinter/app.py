from __future__ import annotations

import sys
from pathlib import Path
import re
import os

# 兼容直接运行：确保项目根目录在 sys.path 中
if __package__ is None or __package__ == "":
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from ui.services import search_videos, start_maintain
except Exception as e:
    print(f"导入服务失败: {e}")
    # 提供降级占位，避免启动失败
    def search_videos(keyword: str):
        return []
    def start_maintain(path: str, labels: str = None, logical_path: str = None):
        return {"success": False, "message": "服务不可用"}


APP_TITLE = "XJJ Housekeeper"


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
            # 素雅浅蓝配色，用于按钮与选中态
            "accent": "#60A5FA",
            "selected_bg": "#EEF2FF",
            "selected_border": "#C7D2FE",
        }

        self._init_styles()
        self._build_layout()
        self._build_top_nav()
        self._build_content()

        # 默认显示查询页
        self.current_route = "query"
        self._update_nav_selection()
        self.show_query_page()

    def _build_layout(self) -> None:
        # 顶部品牌栏
        self.topbar = tk.Frame(self.root, bg=self.colors["white"], height=48, bd=0, highlightthickness=0)
        self.topbar.pack(side=tk.TOP, fill=tk.X)
        brand = tk.Label(
            self.topbar,
            text=APP_TITLE,
            bg=self.colors["white"],
            fg=self.colors["gray800"],
            padx=16,
            font=("Helvetica", 14, "bold"),
        )
        brand.pack(side=tk.LEFT)

        # 主体区域：取消左侧边栏，使用顶部水平导航，右侧内容占满
        self.main = tk.Frame(self.root, bg=self.colors["bg"])  # 全局背景
        self.main.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.content = tk.Frame(self.main, bg=self.colors["bg"])  # 内容容器满宽
        self.content.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

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

    def _build_top_nav(self) -> None:
        # 顶部水平导航：放在 topbar 右侧，左边品牌不变
        self.nav_items: dict[str, tk.Label] = {}

        nav = tk.Frame(self.topbar, bg=self.colors["white"], height=48)
        nav.pack(side=tk.RIGHT, padx=12)

        def make_nav(key: str, text: str, command):
            lbl = tk.Label(
                nav,
                text=text,
                bg=self.colors["white"],
                fg=self.colors["gray800"],
                font=("Helvetica", 12, "bold"),
                padx=12, pady=8
            )
            lbl.pack(side=tk.LEFT, padx=4)
            lbl.bind("<Button-1>", lambda _e: command())
            self.nav_items[key] = lbl
            return lbl

        self.nav_query = make_nav("query", "查询", self.show_query_page)
        self.nav_maintain = make_nav("maintain", "维护", self.show_maintain_page)

    def _build_content(self) -> None:
        # 内容区域占位，用于切换不同页面
        self.content_inner = tk.Frame(self.content, bg=self.colors["bg"])  # 动态替换
        self.content_inner.pack(fill=tk.BOTH, expand=True)

    def _clear_content(self) -> None:
        for child in self.content_inner.winfo_children():
            child.destroy()

    def _update_nav_selection(self) -> None:
        # 顶部水平导航选中态：高亮文字并加底部指示线
        for key, lbl in self.nav_items.items():
            selected = (key == self.current_route)
            if selected:
                lbl.configure(
                    bg=self.colors["accent"],
                    fg=self.colors["white"],
                    font=("Helvetica", 12, "bold"),
                    highlightthickness=0
                )
            else:
                lbl.configure(
                    bg=self.colors["white"],
                    fg=self.colors["gray800"],
                    font=("Helvetica", 12, "bold"),
                    highlightthickness=0
                )


    # 页面：查询
    def show_query_page(self) -> None:
        self.current_route = "query"
        self._update_nav_selection()
        self._clear_content()

        container = tk.Frame(self.content_inner, bg=self.colors["bg"]) 
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # 输入区
        form = tk.Frame(container, bg=self.colors["bg"]) 
        form.pack(fill=tk.X)

        tk.Label(form, text="视频码", bg=self.colors["bg"], fg=self.colors["gray800"], font=("Helvetica", 12)).pack(side=tk.LEFT)
        self.query_var = tk.StringVar()
        entry = tk.Entry(form, textvariable=self.query_var, width=40)
        entry.pack(side=tk.LEFT, padx=8)

        # 结果表格（提前创建，避免输入回调引用未准备好的表格导致渲染阻塞）
        table_container = tk.Frame(container, bg=self.colors["bg"]) 
        table_container.pack(fill=tk.BOTH, expand=True, pady=12)
        columns = ("video", "file_path", "file_size", "duration", "resolution")
        table = ttk.Treeview(table_container, columns=columns, show="headings")
        left_cols = {"video", "file_path"}
        right_cols = {"file_size", "duration", "resolution"}
        for col, text in zip(columns, ("视频", "路径", "大小", "时长", "分辨率")):
            # 表头对齐
            table.heading(col, text=text, anchor="w" if col in left_cols else "e")
            # 单元格对齐与列宽
            width = 360 if col == "file_path" else 150
            table.column(col, width=width, anchor="w" if col in left_cols else "e")
        table.pack(fill=tk.BOTH, expand=True)

        # 输入即搜（模糊匹配 video_code）
        def do_search_live():
            keyword = self.query_var.get()
            results = search_videos(keyword) or []
            self._render_table(table, results)

        def do_search():
            # 保留按钮/回车触发，与实时搜索一致
            do_search_live()

        # 绑定输入事件（实时搜索）
        try:
            self.query_var.trace_add('write', lambda *_: do_search_live())
        except Exception:
            entry.bind("<KeyRelease>", lambda e: do_search_live())

        # 回车直接触发查询
        entry.bind("<Return>", lambda e: do_search())
        tk.Button(form, text="搜索", command=do_search, bg=self.colors["white"], fg="#000000", relief=tk.GROOVE).pack(side=tk.LEFT, padx=8)

        # 绑定事件
        table.bind("<Double-1>", lambda e: self._on_table_double_click(table, e))
        table.bind("<Button-3>", lambda e: self._on_table_right_click(table, e))

        # 初始提示
        self._render_table(table, [])

        # 切回查询页后立即聚焦并刷新渲染，避免需点击才完全渲染
        try:
            entry.focus_set()
        except Exception:
            pass
        self.root.update_idletasks()

    def _render_table(self, table: ttk.Treeview, rows: list[dict]) -> None:
        # 为行绑定源数据（用于双击/右键操作）
        if not hasattr(self, "_row_cache"):
            self._row_cache = {}
        else:
            self._row_cache.clear()
        for item in table.get_children():
            table.delete(item)
        if not rows:
            # 空状态占位
            table.insert("", tk.END, values=("暂无数据", "", "", "", ""))
            return
        for r in rows:
            file_path = r.get("file_path")
            dir_path = Path(file_path).parent if file_path else ""
            item_id = table.insert(
                "", tk.END,
                values=(r.get("video"), str(dir_path), r.get("file_size"), r.get("duration"), r.get("resolution"))
            )
            self._row_cache[item_id] = r

    # 页面：维护
    def show_maintain_page(self) -> None:
        self.current_route = "maintain"
        self._update_nav_selection()
        self._clear_content()

        container = tk.Frame(self.content_inner, bg=self.colors["bg"]) 
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        form = tk.Frame(container, bg=self.colors["bg"]) 
        form.pack(fill=tk.X)

        tk.Label(form, text="扫描路径", bg=self.colors["bg"], fg=self.colors["gray800"], font=("Helvetica", 12)).pack(side=tk.LEFT)
        self.scan_dir_var = tk.StringVar()
        entry = tk.Entry(form, textvariable=self.scan_dir_var, width=50)
        entry.pack(side=tk.LEFT, padx=8)

        def choose_dir():
            d = filedialog.askdirectory()
            if d:
                self.scan_dir_var.set(d)

        tk.Button(form, text="选择目录", command=choose_dir, bg=self.colors["white"], fg=self.colors["gray800"], relief=tk.GROOVE).pack(side=tk.LEFT, padx=8)

        status = tk.Label(container, text="", bg=self.colors["bg"], fg=self.colors["gray700"]) 
        status.pack(fill=tk.X, pady=12)

        # 日志输出区域（逐一打印维护的文件）
        log_frame = tk.Frame(container, bg=self.colors["bg"])
        log_frame.pack(fill=tk.BOTH, expand=True, pady=6)
        log_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL)
        log_text = tk.Text(log_frame, height=10, bg=self.colors["white"], fg=self.colors["gray800"], wrap="none")
        log_scroll.config(command=log_text.yview)
        log_text.config(yscrollcommand=log_scroll.set)
        log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # 进度条（真实进度，品牌蓝，默认隐藏，开始时显示）
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Blue.Horizontal.TProgressbar",
            troughcolor=self.colors["gray100"],
            background=self.colors["brand"],
        )
        pb = ttk.Progressbar(container, mode="determinate", length=360, style="Blue.Horizontal.TProgressbar")
        # 默认隐藏
        pb_visible = False

        def append_log(line: str):
            # 追加日志到文本框并滚动到底部
            log_text.insert(tk.END, line + "\n")
            log_text.see(tk.END)

        def do_maintain():
            import threading
            path = self.scan_dir_var.get().strip()
            if not path:
                messagebox.showwarning("提示", "请先选择扫描路径")
                return

            # 清理旧日志并重置状态
            log_text.delete("1.0", tk.END)
            status.configure(text=f"准备扫描目录: {path}")

            # 显示进度条（开始前隐藏，点击开始后显示）
            nonlocal pb_visible
            if not pb_visible:
                pb.pack(anchor="w")
                pb_visible = True
            pb.configure(value=0, maximum=100)

            def worker():
                # 捕获服务的stdout输出，解析真实进度
                old_stdout = sys.stdout
                class Redirector:
                    def __init__(self):
                        self.buf = ""
                    def write(self_inner, s):
                        self_inner.buf += s
                        while "\n" in self_inner.buf:
                            line, self_inner.buf = self_inner.buf.split("\n", 1)
                            # 在主线程追加日志和解析进度
                            def handle_line():
                                append_log(line)
                                # 解析文件总数
                                m_total = re.search(r"发现\s+(\d+)\s+个视频文件", line)
                                if m_total:
                                    total = int(m_total.group(1))
                                    pb.configure(maximum=total, value=0)
                                # 解析当前处理进度
                                m_proc = re.search(r"处理文件\s+(\d+)/(\d+)", line)
                                if m_proc:
                                    cur = int(m_proc.group(1))
                                    total = int(m_proc.group(2))
                                    pb.configure(maximum=total, value=cur)
                                    status.configure(text=f"正在处理 {cur}/{total} …")
                            self.root.after(0, handle_line)
                    def flush(self_inner):
                        pass

                try:
                    sys.stdout = Redirector()
                    result = start_maintain(path)
                except Exception as e:
                    result = {"success": False, "message": str(e)}
                finally:
                    sys.stdout = old_stdout

                def finish():
                    # 完成后隐藏进度条
                    pb.configure(value=pb["maximum"]) if pb["maximum"] > 0 else None
                    pb.pack_forget()
                    nonlocal pb_visible
                    pb_visible = False

                    if result.get("success"):
                        # 成功不再弹窗，改为优雅摘要
                        processed = result.get("processed_count", 0)
                        total = result.get("total_files", pb["maximum"] if isinstance(pb["maximum"], int) else 0)
                        skipped = result.get("files_skipped", 0)
                        errors = result.get("errors", 0)
                        status.configure(text=f"完成：总计 {total}，处理 {processed}，跳过 {skipped}，错误 {errors}")
                    else:
                        # 失败仍弹窗提示
                        messagebox.showerror("失败", result.get("message", "维护失败"))
                        status.configure(text=f"失败：{result.get('message', '')}")

                self.root.after(0, finish)

            threading.Thread(target=worker, daemon=True).start()

        tk.Button(container, text="开始维护", command=do_maintain, bg=self.colors["white"], fg=self.colors["gray800"], relief=tk.GROOVE).pack(anchor="w")

    def _on_table_double_click(self, table: ttk.Treeview, event: tk.Event):
        """表格双击事件处理"""
        # 获取点击的行和列
        item = table.identify_row(event.y)
        column = table.identify_column(event.x)
        if not item:
            return
        
        # 获取行数据
        values = table.item(item, "values")
        if not values:
            return
        
        # 路径列索引为 #2；使用源数据中的 file_path 更准确
        row = self._row_cache.get(item, {})
        file_path = row.get("file_path")
        dir_path = str(Path(file_path).parent) if file_path else values[1]

        if column == "#2":
            if not dir_path:
                return
            if not Path(dir_path).exists():
                messagebox.showerror("错误", "当前目录不可达")
                return
            self._open_file_manager(dir_path)
        else:
            # 其他列双击播放视频：直接使用 file_path（避免视频码与文件名不一致问题）
            if not file_path or not Path(file_path).exists():
                messagebox.showerror("错误", "当前视频文件不可达")
                return
            self._play_video(str(file_path))
    
    def _on_table_right_click(self, table: ttk.Treeview, event: tk.Event):
        """表格右键事件处理"""
        # 获取点击的行
        item = table.identify_row(event.y)
        if not item:
            return
        
        # 获取行数据
        values = table.item(item, "values")
        if not values:
            return
        
        row = self._row_cache.get(item, {})
        file_path = row.get("file_path")
        if not file_path or not Path(file_path).exists():
            messagebox.showerror("错误", "当前视频文件不可达")
            return
        
        # 创建上下文菜单
        menu = tk.Menu(self.root, tearoff=0)
        
        # 获取系统安装的视频播放器
        players = self._get_system_video_players()
        
        # 添加播放器选项
        for player_name, player_path in players.items():
            menu.add_command(label=player_name, command=lambda p=player_path: self._play_video_with_player(Path(file_path), p))
        
        # 显示菜单
        menu.post(event.x_root, event.y_root)
    
    def _open_file_manager(self, path: str):
        """打开文件管理器"""
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                os.system(f"open '{path}'")
            else:  # Linux
                os.system(f"xdg-open '{path}'")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件管理器: {str(e)}")
    
    def _play_video(self, video_path: str):
        """使用默认播放器播放视频"""
        try:
            if sys.platform == "win32":
                os.startfile(video_path)
            elif sys.platform == "darwin":
                os.system(f"open '{video_path}'")
            else:  # Linux
                os.system(f"xdg-open '{video_path}'")
        except Exception as e:
            messagebox.showerror("播放失败", f"无法播放视频: {str(e)}")
            # 播放失败时打开文件管理器
            self._open_file_manager(Path(video_path).parent)
    
    def _get_system_video_players(self):
        """获取系统安装的视频播放器"""
        players = {}
        
        if sys.platform == "win32":
            # Windows 系统获取默认播放器和常见播放器
            players["默认播放器"] = None  # 使用默认方式打开
            # 可以添加更多常见播放器路径
        elif sys.platform == "darwin":
            # macOS 系统获取默认播放器和常见播放器
            players["默认播放器"] = None  # 使用默认方式打开
            players["QuickTime Player"] = "/Applications/QuickTime Player.app"
            players["VLC"] = "/Applications/VLC.app"
        else:  # Linux
            # Linux 系统获取默认播放器和常见播放器
            players["默认播放器"] = None  # 使用默认方式打开
            players["VLC"] = "vlc"
            players["Totem"] = "totem"
        
        return players
    
    def _play_video_with_player(self, video_path: Path, player_path: str):
        """使用指定播放器播放视频"""
        try:
            if not player_path:
                # 使用默认方式打开
                self._play_video(str(video_path))
            elif sys.platform == "win32":
                os.system(f'"{player_path}" "{video_path}"')
            elif sys.platform == "darwin":
                os.system(f'open -a "{player_path}" "{video_path}"')
            else:  # Linux
                os.system(f'{player_path} "{video_path}"')
        except Exception as e:
            messagebox.showerror("播放失败", f"无法使用该播放器播放视频: {str(e)}")
            # 播放失败时打开文件管理器
            self._open_file_manager(video_path.parent)
    
    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    XJJDesktopApp().run()