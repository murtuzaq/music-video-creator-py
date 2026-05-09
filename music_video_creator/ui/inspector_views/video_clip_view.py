import tkinter as tk
from ._helpers import field_label


class VideoClipView:
    def __init__(self, body: tk.Frame, colors: dict,
                 on_update=None, on_add_assets=None):
        self._body          = body
        self._colors        = colors
        self._on_update     = on_update
        self._on_add_assets = on_add_assets
        self._add_btn       = None
        self._name_var      = tk.StringVar()
        self._dur_var       = tk.StringVar()
        self._node          = None

    def build(self, node: dict):
        self._node = node
        bg = self._colors["bg_darkest"]

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

        field_label(self._body, "Name", self._colors)
        self._name_var.set(node.get("name") or "")
        tk.Entry(self._body, textvariable=self._name_var,
                 bg=self._colors.get("bg_dark", "#252525"),
                 fg=self._colors["fg_value"],
                 insertbackground=self._colors["fg_primary"],
                 relief=tk.FLAT, bd=4,
                 font=("Helvetica", 9)).pack(fill=tk.X, pady=(0, 8))

        field_label(self._body, "Duration (seconds)", self._colors)
        dur = node.get("duration")
        self._dur_var.set(str(dur) if dur is not None else "0")
        tk.Entry(self._body, textvariable=self._dur_var,
                 bg=self._colors.get("bg_dark", "#252525"),
                 fg=self._colors["fg_value"],
                 insertbackground=self._colors["fg_primary"],
                 relief=tk.FLAT, bd=4,
                 font=("Helvetica", 9)).pack(fill=tk.X, pady=(0, 12))

        tk.Button(self._body, text="Apply Changes",
                  command=self._apply_changes,
                  bg="#9b59b6", fg="white",
                  activebackground="#7d3c98", activeforeground="white",
                  relief=tk.FLAT, bd=0, padx=10, pady=5,
                  font=("Helvetica", 9, "bold"), cursor="hand2").pack(anchor="w")

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

    def _do_add_assets(self):
        if self._on_add_assets:
            self._on_add_assets()

    def _apply_changes(self):
        name = self._name_var.get().strip()
        try:
            dur = float(self._dur_var.get().strip())
            if dur < 0:
                raise ValueError
        except ValueError:
            dur = 0.0
        if not name:
            name = self._node.get("name") or "Video Clip"
        self._node["name"]     = name
        self._node["duration"] = dur
        if self._on_update:
            self._on_update(name, dur)
