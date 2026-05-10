import json
import os
import tkinter as tk
from tkinter import ttk

from ._helpers import field_label, fmt_duration

_TICK_STEPS = (0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300)
_LANE_TOP = 8
_LANE_BOT = 32
_LABEL_Y  = 42
_STRIP_H  = 52


def _nice_tick(total: float, target: int = 6) -> float:
    t = max(1e-6, total / target)
    for step in _TICK_STEPS:
        if step >= t:
            return step
    return _TICK_STEPS[-1]


class AudioClipView:
    def __init__(self, body: tk.Frame, colors: dict,
                 on_update=None, on_add_images=None,
                 on_reorder=None, on_manual_adjust=None,
                 get_children=None):
        self._body             = body
        self._colors           = colors
        self._on_update        = on_update
        self._on_add_images    = on_add_images
        self._on_reorder       = on_reorder
        self._on_manual_adjust = on_manual_adjust
        self._get_children     = get_children
        self._node             = None
        self._start_var        = tk.StringVar()
        self._suppress         = False
        self._up_btn           = None
        self._down_btn         = None
        self._strip_canvas     = None
        self._img_list_frame   = None

    def build(self, node: dict, parent_duration: float):
        self._node            = node
        self._parent_duration = parent_duration
        bg   = self._colors["bg_darkest"]
        path = node.get("path") or ""

        # ── icon + title ──────────────────────────────────────────
        tk.Label(self._body, text="🎵", bg=bg, fg="#8e44ad",
                 font=("Helvetica", 36)).pack(pady=(14, 4))
        tk.Label(self._body,
                 text=os.path.splitext(os.path.basename(path))[0] or "Audio Clip",
                 bg=bg, fg=self._colors["fg_primary"],
                 font=("Helvetica", 10, "bold"),
                 wraplength=200).pack()

        # ── info from .info file ──────────────────────────────────
        info = self._load_info(path)
        audio_path = info.get("audio_path", "")
        duration   = node.get("duration") or info.get("duration_seconds", 0.0)

        field_label(self._body, "Audio File", self._colors)
        tk.Label(self._body, text=os.path.basename(audio_path) or "—",
                 bg=bg, fg=self._colors["fg_value"],
                 font=("Helvetica", 8), anchor="w",
                 wraplength=200).pack(fill=tk.X, pady=(0, 6))

        field_label(self._body, "Duration", self._colors)
        tk.Label(self._body, text=fmt_duration(duration),
                 bg=bg, fg=self._colors["fg_value"],
                 font=("Helvetica", 8), anchor="w").pack(fill=tk.X, pady=(0, 8))

        ttk.Separator(self._body, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(4, 8))

        # ── reorder + start time ──────────────────────────────────
        order_row = tk.Frame(self._body, bg=bg)
        order_row.pack(fill=tk.X, pady=(0, 4))
        btn_kw = dict(relief=tk.FLAT, bd=0, padx=10, pady=3,
                      font=("Helvetica", 9, "bold"), cursor="hand2",
                      bg=self._colors.get("bg_dark", "#252525"),
                      fg=self._colors["fg_value"],
                      activebackground=self._colors.get("bg_medium", "#2b2b2b"),
                      activeforeground=self._colors["fg_primary"])
        self._up_btn   = tk.Button(order_row, text="▲  Up",
                                   command=lambda: self._do_reorder(-1), **btn_kw)
        self._down_btn = tk.Button(order_row, text="▼  Down",
                                   command=lambda: self._do_reorder(1), **btn_kw)
        self._up_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._down_btn.pack(side=tk.LEFT)

        field_label(self._body, "Start Time (seconds)", self._colors)
        self._start_var.set(str(node.get("start_time") or 0.0))
        self._start_var.trace_add("write", self._on_start_change)
        tk.Entry(self._body, textvariable=self._start_var,
                 bg=self._colors.get("bg_dark", "#252525"),
                 fg=self._colors["fg_value"],
                 insertbackground=self._colors["fg_primary"],
                 relief=tk.FLAT, bd=4,
                 font=("Helvetica", 9)).pack(fill=tk.X, pady=(0, 8))

        ttk.Separator(self._body, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(4, 8))

        # ── images section ────────────────────────────────────────
        img_hdr = tk.Frame(self._body, bg=bg)
        img_hdr.pack(fill=tk.X, pady=(0, 6))
        tk.Label(img_hdr, text="Images", bg=bg,
                 fg=self._colors["fg_dim_alt"],
                 font=("Helvetica", 8)).pack(side=tk.LEFT)
        add_btn = tk.Button(
            img_hdr, text="+ Add",
            command=self._do_add_images,
            bg="#555555", fg="#999",
            activebackground="#555555", activeforeground="#999",
            relief=tk.FLAT, bd=0, padx=8, pady=3,
            font=("Helvetica", 8, "bold"), cursor="",
        )
        add_btn.pack(side=tk.RIGHT)
        self._add_btn = add_btn

        # Mini strip showing images within this audio_clip's duration
        self._strip_canvas = tk.Canvas(
            self._body,
            bg=self._colors.get("bg_dark", "#252525"),
            height=_STRIP_H, highlightthickness=1,
            highlightbackground=self._colors.get("bg_medium", "#2b2b2b"))
        self._strip_canvas.pack(fill=tk.X, pady=(0, 6))
        self._strip_canvas.bind("<Configure>", lambda _e: self._draw_strip())

        # Cues section (read-only)
        cues = info.get("lyrics", {}).get("cues", [])
        if cues:
            ttk.Separator(self._body, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(4, 8))
            tk.Label(self._body, text="Lyrics Cues", bg=bg,
                     fg=self._colors["fg_dim_alt"],
                     font=("Helvetica", 8)).pack(anchor="w")
            self._build_cue_list(cues)

        self._draw_strip()

    # ── Public ────────────────────────────────────────────────────

    def set_reorder_button_state(self, can_go_up: bool, can_go_down: bool):
        for btn, enabled in ((self._up_btn, can_go_up), (self._down_btn, can_go_down)):
            if not btn:
                continue
            try:
                btn.config(state=tk.NORMAL if enabled else tk.DISABLED,
                           cursor="hand2" if enabled else "")
            except tk.TclError:
                pass

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

    def refresh_strip(self):
        self._draw_strip()

    def on_resize(self, width: int):
        self._draw_strip()

    # ── Private ───────────────────────────────────────────────────

    def _load_info(self, path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _do_reorder(self, direction: int):
        if self._on_reorder:
            self._on_reorder(direction)

    def _do_add_images(self):
        if self._on_add_images:
            self._on_add_images()
        self._draw_strip()

    def _on_start_change(self, *_):
        try:
            st = float(self._start_var.get().strip())
            if st < 0:
                raise ValueError
        except ValueError:
            return
        self._node["start_time"] = st
        if self._on_update:
            self._on_update(st)
        if self._on_manual_adjust and not self._suppress:
            self._on_manual_adjust()

    def _draw_strip(self):
        c = self._strip_canvas
        if not c:
            return
        try:
            w = c.winfo_width()
        except tk.TclError:
            return
        if w <= 1:
            return

        c.delete("all")
        dim      = self._colors["fg_dim_alt"]
        duration = self._node.get("duration") or 0.0

        if duration <= 0:
            c.create_text(w // 2, _STRIP_H // 2,
                          text="No duration", fill=dim, font=("Helvetica", 7))
            return

        children = self._get_children() if self._get_children else []
        images   = sorted(
            [n for _, n in children if n.get("type") == "image"],
            key=lambda n: n.get("start_time") or 0.0,
        )
        px_per_s = (w - 4) / duration

        for i, n in enumerate(images):
            t0 = n.get("start_time") or 0.0
            t1 = images[i + 1].get("start_time") if i + 1 < len(images) else duration
            if t1 is None:
                t1 = duration
            x0 = 2 + t0 * px_per_s
            x1 = max(x0 + 2, 2 + t1 * px_per_s)
            c.create_rectangle(x0, _LANE_TOP, x1, _LANE_BOT, fill="#5cb85c", outline="")
            bar_w = x1 - x0
            if bar_w > 14:
                label = n.get("name") or "img"
                max_c = max(1, int(bar_w / 6))
                c.create_text((x0 + x1) / 2, (_LANE_TOP + _LANE_BOT) / 2,
                              text=label[:max_c - 1] + "…" if len(label) > max_c else label,
                              fill="white", font=("Helvetica", 7), anchor="center")

        # Time ticks
        inc = _nice_tick(duration)
        t   = 0.0
        while t <= duration + 1e-9:
            x = 2 + t * px_per_s
            c.create_line(x, _LANE_BOT + 1, x, _LANE_BOT + 4, fill=dim, width=1)
            c.create_text(x, _LABEL_Y, text=f"{t:.0f}s" if t == int(t) else f"{t:.1f}s",
                          anchor="n", fill=dim, font=("Helvetica", 6))
            t = round(t + inc, 10)

    def _build_cue_list(self, cues: list):
        bg = self._colors["bg_darkest"]
        outer = tk.Frame(self._body, bg=bg)
        outer.pack(fill=tk.X, pady=(2, 4))

        vsb    = ttk.Scrollbar(outer, orient=tk.VERTICAL)
        canvas = tk.Canvas(outer, bg=bg, highlightthickness=0,
                           height=min(120, len(cues) * 18),
                           yscrollcommand=vsb.set)
        vsb.config(command=canvas.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.X, expand=True)

        inner = tk.Frame(canvas, bg=bg)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>",
                    lambda e: canvas.yview_scroll(int(-1 * e.delta / 120), "units"))

        for cue in cues:
            row = tk.Frame(inner, bg=bg)
            row.pack(fill=tk.X, pady=1)
            t = cue.get("start", 0.0)
            tk.Label(row, text=f"{int(t//60)}:{int(t%60):02d}",
                     bg=bg, fg=self._colors["fg_dim_alt"],
                     font=("Courier", 7), width=5, anchor="e").pack(side=tk.LEFT)
            tk.Label(row, text=cue.get("text", ""),
                     bg=bg, fg=self._colors["fg_value"],
                     font=("Helvetica", 7), anchor="w").pack(side=tk.LEFT, padx=(4, 0))
