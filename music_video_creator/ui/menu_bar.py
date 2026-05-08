import tkinter as tk


class MenuBar(tk.Menu):
    def __init__(self, root, callbacks: dict, variables: dict = None):
        super().__init__(root)
        variables = variables or {}
        self._get_sel_type = callbacks.get("get_selection_type", lambda: None)

        # ── File menu ─────────────────────────────────────────────
        self._file_menu = tk.Menu(self, tearoff=0,
                                   postcommand=self._update_file_items)
        self._file_menu.add_command(label="Add Image…", command=callbacks["add_image"])
        self._file_menu.add_command(label="Add Audio…", command=callbacks["add_audio"])
        self._file_menu.add_separator()
        self._file_menu.add_command(label="Exit",       command=callbacks["exit"])
        self.add_cascade(label="File", menu=self._file_menu)

        # ── View menu ─────────────────────────────────────────────
        view_menu = tk.Menu(self, tearoff=0)
        view_menu.add_checkbutton(
            label="Project Panel",
            variable=variables.get("assets_visible"),
            onvalue=True, offvalue=False,
            command=callbacks["view_toggle_assets"],
        )
        view_menu.add_checkbutton(
            label="Inspector",
            variable=variables.get("inspector_visible"),
            onvalue=True, offvalue=False,
            command=callbacks["view_toggle_inspector"],
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

        # ── Window menu ───────────────────────────────────────────
        _theme_var = variables.get("theme")
        window_menu = tk.Menu(self, tearoff=0)
        window_menu.add_radiobutton(label="Dark",  value="dark",  variable=_theme_var,
                                    command=lambda: callbacks["set_theme"]("dark"))
        window_menu.add_radiobutton(label="Light", value="light", variable=_theme_var,
                                    command=lambda: callbacks["set_theme"]("light"))
        self.add_cascade(label="Window", menu=window_menu)

        root.config(menu=self)

    def _update_file_items(self):
        sel = self._get_sel_type()
        can_add_image = sel in ("video", "audio")
        can_add_audio = sel == "video"
        self._file_menu.entryconfig(0, state=tk.NORMAL if can_add_image else tk.DISABLED)
        self._file_menu.entryconfig(1, state=tk.NORMAL if can_add_audio else tk.DISABLED)
