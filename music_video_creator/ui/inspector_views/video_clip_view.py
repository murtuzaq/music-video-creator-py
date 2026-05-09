import tkinter as tk
from tkinter import ttk
from ._helpers import field_label


class VideoClipView:
    def __init__(self, body: tk.Frame, colors: dict,
                 on_update=None, on_add_assets=None, auto_space_var=None):
        self._body           = body
        self._colors         = colors
        self._on_update      = on_update
        self._on_add_assets  = on_add_assets
        self._auto_space_var = auto_space_var or tk.BooleanVar(value=False)
        self._add_btn        = None
        self._name_var       = tk.StringVar()
        self._dur_var        = tk.StringVar()
        self._node           = None

    def build(self, node: dict):
        self._node = node
        bg = self._colors["bg_darkest"]

        # ── icon row + Add button ─────────────────────────────────
        icon_row = tk.Frame(self._body, bg=bg)
        icon_row.pack(fill=tk.X, pady=(14, 8))
        tk.Label(icon_row, text="🎞", bg=bg, fg="#9b59b6",
                 font=("Helvetica", 36)).pack(side=tk.LEFT)
        self._add_btn = tk.Button(icon_row, text="+ Add",
                                  command=self._do_add_assets,
                                  bg="#555555", fg="#999",
                                  activebackground="#555555", activeforeground="#999",
                                  relief=tk.FLAT, bd=0, padx=10, pady=5,
                                  font=("Helvetica", 9, "bold"), cursor="")
        self._add_btn.pack(side=tk.RIGHT, padx=4)

        # ── Name ──────────────────────────────────────────────────
        field_label(self._body, "Name", self._colors)
        self._name_var.set(node.get("name") or "")
        self._name_var.trace_add("write", self._on_name_change)
        tk.Entry(self._body, textvariable=self._name_var,
                 bg=self._colors.get("bg_dark", "#252525"),
                 fg=self._colors["fg_value"],
                 insertbackground=self._colors["fg_primary"],
                 relief=tk.FLAT, bd=4,
                 font=("Helvetica", 9)).pack(fill=tk.X, pady=(0, 8))

        # ── Duration ──────────────────────────────────────────────
        field_label(self._body, "Duration (seconds)", self._colors)
        dur = node.get("duration")
        self._dur_var.set(str(dur) if dur is not None else "0")
        self._dur_var.trace_add("write", self._on_dur_change)
        tk.Entry(self._body, textvariable=self._dur_var,
                 bg=self._colors.get("bg_dark", "#252525"),
                 fg=self._colors["fg_value"],
                 insertbackground=self._colors["fg_primary"],
                 relief=tk.FLAT, bd=4,
                 font=("Helvetica", 9)).pack(fill=tk.X, pady=(0, 8))

        # ── Auto Spacing ──────────────────────────────────────────
        ttk.Separator(self._body, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(10, 8))

        tk.Checkbutton(self._body,
                       text="Auto-space on reorder",
                       variable=self._auto_space_var,
                       bg=self._colors["bg_darkest"],
                       fg=self._colors["fg_value"],
                       selectcolor=self._colors.get("bg_dark", "#252525"),
                       activebackground=self._colors["bg_darkest"],
                       activeforeground=self._colors["fg_primary"],
                       font=("Helvetica", 9),
                       cursor="hand2").pack(anchor="w")

    # ── Public ────────────────────────────────────────────────────

    def set_add_button_state(self, enabled: bool):
        if not self._add_btn:
            return
        try:
            if enabled:
                self._add_btn.config(bg="#28a745", fg="white",
                                     activebackground="#1e7e34", activeforeground="white",
                                     cursor="hand2")
            else:
                self._add_btn.config(bg="#555555", fg="#999",
                                     activebackground="#555555", activeforeground="#999",
                                     cursor="")
        except tk.TclError:
            pass

    def on_resize(self, width: int):
        pass

    # ── Private ───────────────────────────────────────────────────

    def _do_add_assets(self):
        if self._on_add_assets:
            self._on_add_assets()

    def _do_auto_space(self):
        if self._on_auto_space:
            self._on_auto_space()

    def _on_name_change(self, *_):
        name = self._name_var.get().strip() or (self._node.get("name") or "Video Clip")
        self._node["name"] = name
        if self._on_update:
            self._on_update(name, self._node.get("duration") or 0.0)

    def _on_dur_change(self, *_):
        try:
            dur = float(self._dur_var.get().strip())
            if dur < 0:
                raise ValueError
        except ValueError:
            return
        self._node["duration"] = dur
        if self._on_update:
            self._on_update(self._node.get("name") or "Video Clip", dur)
