import tkinter as tk
import webbrowser


def build_layout(app) -> None:
    app.root.grid_rowconfigure(0, weight=1)
    app.root.grid_columnconfigure(1, weight=1)

    app.sidebar = tk.Frame(app.root, bg=app.colors["sidebar_bg"], width=250)
    app.sidebar.grid(row=0, column=0, sticky="nsew")
    app.sidebar.grid_propagate(False)

    app.brand_label = tk.Label(
        app.sidebar,
        text=app.settings.app_title,
        bg=app.colors["sidebar_bg"],
        fg=app.colors["gray800"],
        font=app.fonts["title"],
        padx=28,
        pady=36,
    )
    app.brand_label.pack(anchor="w")

    app.nav_btns = {}
    add_sidebar_btn(app, "query", app.t("sidebar.query"), lambda: app.show_page("query"))
    add_sidebar_btn(app, "maintain", app.t("sidebar.maintain"), lambda: app.show_page("maintain"))

    version_text = app.app_meta.get("version", "V1.0")

    bottom_frame = tk.Frame(app.sidebar, bg=app.colors["sidebar_bg"], padx=28, pady=28)
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

    app.about_link = tk.Label(
        bottom_frame,
        text=version_text,
        bg=app.colors["sidebar_bg"],
        fg=app.colors["gray700"],
        font=app.fonts["link"],
        cursor="hand2",
    )
    app.about_link.pack(anchor="w")
    app.about_link.bind("<Button-1>", lambda e: show_about(app))

    app.main_area = tk.Frame(app.root, bg=app.colors["bg"])
    app.main_area.grid(row=0, column=1, sticky="nsew")
    app.main_area.grid_rowconfigure(1, weight=1)
    app.main_area.grid_columnconfigure(0, weight=1)

    app.header = tk.Frame(app.main_area, bg=app.colors["bg"], height=64)
    app.header.grid(row=0, column=0, sticky="ew")
    app.header.pack_propagate(False)

    app.sidebar_visible = True
    app.toggle_btn = tk.Button(
        app.header,
        text="☰",
        font=app.fonts["title"],
        bg=app.colors["bg"],
        fg=app.colors["gray700"],
        bd=0,
        relief=tk.FLAT,
        activebackground=app.colors["gray100"],
        command=app.toggle_sidebar,
        cursor="hand2",
    )
    app.toggle_btn.pack(side=tk.LEFT, padx=24, pady=12)


def show_about(app) -> None:
    dialog = tk.Toplevel(app.root)
    dialog.title(app.t("about.title"))
    dialog.geometry("400x260")
    dialog.resizable(False, False)

    dialog.update_idletasks()
    x = app.root.winfo_x() + (app.root.winfo_width() // 2) - (dialog.winfo_width() // 2)
    y = app.root.winfo_y() + (app.root.winfo_height() // 2) - (dialog.winfo_height() // 2)
    dialog.geometry(f"+{x}+{y}")
    dialog.transient(app.root)
    dialog.grab_set()
    dialog.focus_set()

    container = tk.Frame(dialog, bg=app.colors["white"], padx=20, pady=20)
    container.pack(fill=tk.BOTH, expand=True)

    tk.Label(
        container,
        text=app.settings.app_title or app.t("app.title"),
        bg=app.colors["white"],
        fg=app.colors["gray800"],
        font=("Helvetica", 20, "bold"),
    ).pack(pady=(10, 5))

    version = app.app_meta.get("version", "V1.0")
    tk.Label(
        container,
        text=f"Version {version}",
        bg=app.colors["white"],
        fg=app.colors["gray700"],
        font=("Helvetica", 12),
    ).pack(pady=(0, 20))

    link_url = app.app_meta.get("developer_url") or app.app_meta.get("homepage") or ""
    if link_url:
        link_text = "GitHub Repository"
        if "github.com" in link_url:
            try:
                parts = link_url.rstrip("/").split("/")
                if len(parts) >= 2:
                    link_text = f"GitHub: {parts[-2]}/{parts[-1]}"
            except Exception:
                pass

        link_label = tk.Label(
            container,
            text=link_text,
            bg=app.colors["white"],
            fg=app.colors["gray800"],
            font=("Helvetica", 11, "underline"),
            cursor="hand2",
        )
        link_label.pack(pady=5)
        link_label.bind("<Button-1>", lambda e: webbrowser.open(link_url))

    license_name = app.app_meta.get("license", "MIT")
    tk.Label(
        container,
        text=f"License: {license_name}",
        bg=app.colors["white"],
        fg=app.colors["gray700"],
        font=("Helvetica", 10),
    ).pack(pady=(5, 0))

    tk.Label(
        container,
        text="Copyright © 2025 XJJ Housekeeper Contributors",
        bg=app.colors["white"],
        fg=app.colors["gray700"],
        font=("Helvetica", 10),
    ).pack(side=tk.BOTTOM, pady=10)


def add_sidebar_btn(app, key: str, text: str, command) -> None:
    btn = tk.Button(
        app.sidebar,
        text=text,
        bg=app.colors["sidebar_bg"],
        fg=app.colors["sidebar_fg"],
        font=app.fonts["base"],
        bd=0,
        relief=tk.FLAT,
        activebackground=app.colors["sidebar_hover"],
        activeforeground=app.colors["gray800"],
        anchor="w",
        padx=24,
        pady=14,
        command=command,
        cursor="hand2",
    )
    btn.pack(fill=tk.X, pady=2)
    app.nav_btns[key] = btn
