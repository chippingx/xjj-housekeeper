import tkinter as tk


def build_maintain_manage_tools(app, tools_row, table):
    def run_task(btn, fetcher):
        import threading
        import queue

        q = queue.Queue()
        orig = btn.cget("text")
        btn.configure(state=tk.DISABLED, text=app.t("button.loading"))
        app.render_table(table, [])

        def worker():
            try:
                res = fetcher()
            except Exception:
                res = []
            q.put(res or [])

        def check():
            try:
                res = q.get_nowait()
                btn.configure(state=tk.NORMAL, text=orig)
                res.sort(key=lambda x: x.get("video") or x.get("filename") or "")
                table._context_role = "maintain"
                app.render_table(table, res)
            except queue.Empty:
                app.root.after(100, check)

        threading.Thread(target=worker, daemon=True).start()
        check()

    def fetch_broken():
        from ui.services import VideoService
        local_service = VideoService()
        return local_service.broken_videos(ensure_accessible=True) or []

    btn_broken = app.make_action_button(tools_row, text=app.t("maintain.broken_button"))
    btn_broken.configure(command=lambda: run_task(btn_broken, fetch_broken))
    btn_broken.pack(side=tk.LEFT, padx=6)

    def fetch_duplicate():
        from ui.services import VideoService
        local_service = VideoService()
        return local_service.duplicate_videos(ensure_accessible=True) or []

    btn_dup = app.make_action_button(tools_row, text=app.t("maintain.duplicate_button"))
    btn_dup.configure(command=lambda: run_task(btn_dup, fetch_duplicate))
    btn_dup.pack(side=tk.LEFT, padx=6)
