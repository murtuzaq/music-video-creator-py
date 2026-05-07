import tkinter as tk


class MenuBar(tk.Menu):
    def __init__(self, root, callbacks: dict, variables: dict = None):
        super().__init__(root)
        variables = variables or {}

        # ── File menu (asset loading) ─────────────────────────────
        file_menu = tk.Menu(self, tearoff=0)
        file_menu.add_command(label="Open Image(s)…", command=callbacks["open_images"])
        file_menu.add_command(label="Open Audio…",    command=callbacks["open_audio"])
        file_menu.add_separator()
        file_menu.add_command(label="Exit",           command=callbacks["exit"])
        self.add_cascade(label="File", menu=file_menu)

        # ── View menu ─────────────────────────────────────────────
        view_menu = tk.Menu(self, tearoff=0)
        view_menu.add_checkbutton(
            label="Asset Panel",
            variable=variables.get("assets_visible"),
            onvalue=True, offvalue=False,
            command=callbacks["view_toggle_assets"],
        )
        view_menu.add_separator()
        view_menu.add_command(label="Reset View", command=callbacks["view_reset"])
        self.add_cascade(label="View", menu=view_menu)

        # ── Project menu ──────────────────────────────────────────
        project_menu = tk.Menu(self, tearoff=0)
        project_menu.add_command(label="New Project",  accelerator="Ctrl+N", command=callbacks["new"])
        project_menu.add_command(label="Load Project", accelerator="Ctrl+O", command=callbacks["open"])
        project_menu.add_separator()
        project_menu.add_command(label="Save Project", accelerator="Ctrl+S", command=callbacks["save"])
        project_menu.add_separator()
        project_menu.add_command(label="Exit",                                command=callbacks["exit"])
        self.add_cascade(label="Project", menu=project_menu)

        root.config(menu=self)
