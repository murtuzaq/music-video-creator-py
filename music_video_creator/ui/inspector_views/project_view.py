import tkinter as tk
from tkinter import ttk

from ._helpers import fmt_duration, info_row

_BTN_ON  = {"bg": "#28a745", "fg": "white",  "activebackground": "#1e7e34",
             "activeforeground": "white", "cursor": "hand2"}
_BTN_OFF = {"bg": "#555555", "fg": "#888888", "activebackground": "#555555",
             "activeforeground": "#888888", "cursor": ""}


class ProjectView:
    def __init__(self, body: tk.Frame, colors: dict):
        self._body         = body
        self._colors       = colors
        self._on_generate  = None
        self._has_valid    = False
        self._gen_btn      = None
        self._hint_lbl     = None
        self._prog_frame   = None
        self._prog_bar     = None
        self._prog_lbl     = None

    def build(self, node: dict, total_duration: float,
              on_generate=None, has_valid_clips: bool = False):
        self._on_generate = on_generate
        self._has_valid   = has_valid_clips
        bg   = self._colors["bg_darkest"]
        name = node.get("name") or "Untitled Project"

        tk.Label(self._body, text="📹", bg=bg, fg="#e05c00",
                 font=("Helvetica", 40)).pack(pady=(14, 6))
        info_row(self._body, "Name",     name,                        self._colors)
        info_row(self._body, "Duration", fmt_duration(total_duration), self._colors)

        ttk.Separator(self._body, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(12, 10))

        style = _BTN_ON if has_valid_clips else _BTN_OFF
        self._gen_btn = tk.Button(
            self._body, text="Generate Video",
            command=self._on_gen_click,
            state="normal" if has_valid_clips else "disabled",
            relief=tk.FLAT, bd=0,
            padx=16, pady=8,
            font=("Helvetica", 10, "bold"),
            **style,
        )
        self._gen_btn.pack(fill=tk.X, padx=8)

        if not has_valid_clips:
            self._hint_lbl = tk.Label(
                self._body,
                text="Add a video clip with\nduration > 0 to generate",
                bg=bg, fg=self._colors["fg_dim"],
                font=("Helvetica", 8), justify=tk.CENTER,
            )
            self._hint_lbl.pack(pady=(4, 0))

        # Progress area (hidden until generation starts)
        self._prog_frame = tk.Frame(self._body, bg=bg)
        self._prog_bar   = ttk.Progressbar(self._prog_frame, mode="determinate", maximum=100)
        self._prog_bar.pack(fill=tk.X)
        self._prog_lbl   = tk.Label(self._prog_frame, text="", bg=bg,
                                     fg=self._colors["fg_dim_alt"],
                                     font=("Helvetica", 8))
        self._prog_lbl.pack(pady=(2, 0))

    # ── Public ────────────────────────────────────────────────────

    def set_progress(self, fraction: float, message: str):
        if not self._prog_frame:
            return

        if not self._prog_frame.winfo_ismapped():
            self._prog_frame.pack(fill=tk.X, padx=8, pady=(10, 0))

        if fraction < 0:
            self._prog_bar["value"] = 0
            self._prog_lbl.config(text=f"Error: {message}", fg="#e74c3c")
            self._set_btn_enabled(True)
            return

        self._prog_bar["value"] = int(fraction * 100)
        self._prog_lbl.config(text=message, fg=self._colors["fg_dim_alt"])

        if fraction >= 1.0:
            self._set_btn_enabled(True)
        else:
            self._set_btn_enabled(False)

    def on_resize(self, width: int):
        pass

    # ── Private ───────────────────────────────────────────────────

    def _on_gen_click(self):
        if self._on_generate:
            self._on_generate()

    def _set_btn_enabled(self, enabled: bool):
        if not self._gen_btn:
            return
        active = enabled and self._has_valid
        state  = "normal" if active else "disabled"
        style  = _BTN_ON if active else _BTN_OFF
        self._gen_btn.config(state=state, **style)
