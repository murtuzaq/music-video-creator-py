import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

from ._helpers import field_label

_TICK_STEPS = (0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300)

_LANE_TOP = 10
_LANE_BOT = 46
_LABEL_Y  = 58
_STRIP_H  = 72


def _nice_tick(total: float, target_count: int = 6) -> float:
    target = max(1e-6, total / target_count)
    for step in _TICK_STEPS:
        if step >= target:
            return step
    return _TICK_STEPS[-1]


class VideoClipView:
    def __init__(self, body: tk.Frame, colors: dict,
                 on_update=None, on_add_assets=None, auto_space_var=None,
                 get_children=None):
        self._body           = body
        self._colors         = colors
        self._on_update      = on_update
        self._on_add_assets  = on_add_assets
        self._auto_space_var = auto_space_var or tk.BooleanVar(value=False)
        self._get_children   = get_children
        self._add_btn        = None
        self._name_var       = tk.StringVar()
        self._dur_var        = tk.StringVar()
        self._node           = None
        self._preview_lbl    = None
        self._strip_canvas   = None
        self._playhead_t     = 0.0
        self._pil_cache      = {}

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
                       bg=bg,
                       fg=self._colors["fg_value"],
                       selectcolor=self._colors.get("bg_dark", "#252525"),
                       activebackground=bg,
                       activeforeground=self._colors["fg_primary"],
                       font=("Helvetica", 9),
                       cursor="hand2").pack(anchor="w")

        # ── Clip Preview ──────────────────────────────────────────
        ttk.Separator(self._body, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(10, 8))

        hdr = tk.Frame(self._body, bg=bg)
        hdr.pack(fill=tk.X, pady=(0, 6))
        tk.Label(hdr, text="Clip Preview", bg=bg,
                 fg=self._colors["fg_dim_alt"],
                 font=("Helvetica", 8)).pack(side=tk.LEFT)

        self._preview_lbl = tk.Label(self._body, bg=bg)
        self._preview_lbl.pack(pady=(0, 6))

        self._strip_canvas = tk.Canvas(
            self._body,
            bg=self._colors.get("bg_dark", "#252525"),
            height=_STRIP_H, highlightthickness=1,
            highlightbackground=self._colors.get("bg_medium", "#2b2b2b"))
        self._strip_canvas.pack(fill=tk.X, pady=(0, 8))
        c = self._strip_canvas
        c.bind("<Configure>", lambda _e: self._draw_strip())
        c.bind("<Button-1>",  self._on_strip_click)
        c.bind("<B1-Motion>", self._on_strip_drag)
        c.config(cursor="sb_h_double_arrow")

        self._draw_strip()
        self._update_preview()

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

    def refresh_timeline(self):
        self._draw_strip()
        self._update_preview()

    def on_resize(self, width: int):
        self._draw_strip()
        self._update_preview()

    # ── Private ───────────────────────────────────────────────────

    def _do_add_assets(self):
        if self._on_add_assets:
            self._on_add_assets()
        self.refresh_timeline()

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
        self._draw_strip()

    def _on_strip_click(self, event):
        self._set_playhead_from_x(event.x)

    def _on_strip_drag(self, event):
        self._set_playhead_from_x(event.x)

    def _set_playhead_from_x(self, x: int):
        dur = self._node.get("duration") or 0.0
        if dur <= 0:
            return
        c = self._strip_canvas
        if not c:
            return
        w = c.winfo_width()
        if w <= 4:
            return
        t = (x - 2) / ((w - 4) / dur)
        self._playhead_t = max(0.0, min(t, dur))
        self._draw_strip()
        self._update_preview()

    def _draw_strip(self):
        c = self._strip_canvas
        if not c:
            return
        try:
            w = c.winfo_width()
            h = c.winfo_height()
        except tk.TclError:
            return
        if w <= 1 or h <= 1:
            return

        c.delete("all")
        dim = self._colors["fg_dim_alt"]
        dur = self._node.get("duration") or 0.0

        if dur <= 0:
            c.create_text(w // 2, h // 2,
                          text="Set clip duration to enable preview",
                          fill=dim, font=("Helvetica", 8))
            return

        children = self._get_children() if self._get_children else []
        assets   = sorted(children, key=lambda n: n.get("start_time") or 0.0)
        px_per_s = (w - 4) / dur

        # ── asset bars ─────────────────────────────────────────────
        for i, n in enumerate(assets):
            t0    = n.get("start_time") or 0.0
            ntype = n.get("type", "image")

            if ntype == "audio":
                t1 = t0 + (n.get("_audio_dur") or 0.0)
            else:
                t1 = assets[i + 1].get("start_time") if i + 1 < len(assets) else dur
                t1 = t1 or dur

            x0    = 2 + t0 * px_per_s
            x1    = max(x0 + 3, 2 + t1 * px_per_s)
            color = "#4a90d9" if ntype == "audio" else "#5cb85c"

            c.create_rectangle(x0, _LANE_TOP, x1, _LANE_BOT, fill=color, outline="")

            bar_w = x1 - x0
            if bar_w > 16:
                label     = n.get("name") or ntype
                max_chars = max(1, int(bar_w / 6))
                if len(label) > max_chars:
                    label = label[:max_chars - 1] + "…"
                c.create_text((x0 + x1) / 2, (_LANE_TOP + _LANE_BOT) / 2,
                              text=label, fill="white",
                              font=("Helvetica", 7), anchor="center")

        # ── time ticks ─────────────────────────────────────────────
        inc = _nice_tick(dur)
        t   = 0.0
        while t <= dur + 1e-9:
            x     = 2 + t * px_per_s
            label = f"{int(t)}s" if abs(t - round(t)) < 1e-6 else f"{t:.1f}s"
            c.create_line(x, _LANE_BOT + 2, x, _LANE_BOT + 6, fill=dim, width=1)
            c.create_text(x, _LABEL_Y, text=label, anchor="n",
                          fill=dim, font=("Helvetica", 7))
            t = round(t + inc, 10)

        # ── playhead ───────────────────────────────────────────────
        px = 2 + self._playhead_t * px_per_s
        c.create_polygon(px - 5, 0, px + 5, 0, px, 8, fill="white", outline="")
        c.create_line(px, 0, px, _LANE_BOT + 2, fill="white", width=2)

    def _update_preview(self):
        lbl = self._preview_lbl
        if not lbl:
            return

        if not _PIL:
            lbl.config(image="", text="PIL not available",
                       fg=self._colors["fg_dim"], font=("Helvetica", 8))
            return

        children = self._get_children() if self._get_children else []
        images   = sorted(
            [n for n in children if n.get("type") == "image"],
            key=lambda n: n.get("start_time") or 0.0,
        )

        active_path = None
        for n in reversed(images):
            if (n.get("start_time") or 0.0) <= self._playhead_t + 1e-9:
                active_path = n.get("path")
                break

        if not active_path:
            lbl.config(image="", text="No image at this position",
                       fg=self._colors["fg_dim"], font=("Helvetica", 8))
            lbl._photo = None
            return

        if active_path not in self._pil_cache:
            try:
                self._pil_cache[active_path] = Image.open(active_path)
            except Exception:
                self._pil_cache[active_path] = None

        pil_img = self._pil_cache.get(active_path)
        if not pil_img:
            lbl.config(image="", text="Cannot load image",
                       fg=self._colors["fg_dim"], font=("Helvetica", 8))
            lbl._photo = None
            return

        w     = max(60, self._body.winfo_width() - 20)
        thumb = pil_img.copy()
        thumb.thumbnail((w, 200))
        photo = ImageTk.PhotoImage(thumb)
        lbl.config(image=photo, text="")
        lbl._photo = photo
