import tkinter as tk

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

from ._helpers import field_label

# Nice tick intervals in seconds
_TICK_STEPS = (0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300)

M_TOP = 10
M_BOT = 10
LX    = 55


def _nice_tick(view_dur: float) -> float:
    """Return a tick interval that gives ~8 ticks across view_dur."""
    target = max(1e-6, view_dur / 8)
    for step in _TICK_STEPS:
        if step >= target:
            return step
    return _TICK_STEPS[-1]


class AssetInClipView:
    def __init__(self, body: tk.Frame, colors: dict,
                 on_update=None, on_reorder=None, on_manual_adjust=None):
        self._body              = body
        self._colors            = colors
        self._on_update         = on_update
        self._on_reorder        = on_reorder
        self._on_manual_adjust  = on_manual_adjust
        self._up_btn          = None
        self._down_btn        = None
        self._pil_src         = None
        self._preview_lbl     = None
        self._start_var        = tk.StringVar()
        self._suppress_manual  = False
        self._timeline_canvas  = None
        self._view_duration   = 0.0   # total seconds visible in the fixed canvas
        self._parent_duration = 0.0
        self._node            = None

    def build(self, node: dict, parent_duration: float):
        self._node            = node
        self._parent_duration = parent_duration
        self._view_duration   = max(0.01, parent_duration)  # start fully zoomed out
        bg    = self._colors["bg_darkest"]
        ntype = node.get("type", "image")
        path  = node.get("path") or ""

        # ── reorder buttons ───────────────────────────────────────
        order_row = tk.Frame(self._body, bg=bg)
        order_row.pack(fill=tk.X, pady=(8, 2))
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

        # ── preview ───────────────────────────────────────────────
        if ntype == "image" and _PIL and path:
            try:
                self._pil_src     = Image.open(path)
                self._preview_lbl = tk.Label(self._body, bg=bg)
                self._preview_lbl.pack(pady=(4, 6))
                self._refresh_preview()
            except Exception:
                self._pil_src = None
        elif ntype == "audio":
            tk.Label(self._body, text="♪", bg=bg, fg="#4a90d9",
                     font=("Helvetica", 32)).pack(pady=(8, 4))

        # ── start-time field ──────────────────────────────────────
        field_label(self._body, "Start Time (seconds)", self._colors)
        self._start_var.set(str(node.get("start_time") or 0.0))
        self._start_var.trace_add("write", self._on_start_change)
        tk.Entry(self._body, textvariable=self._start_var,
                 bg=self._colors.get("bg_dark", "#252525"),
                 fg=self._colors["fg_value"],
                 insertbackground=self._colors["fg_primary"],
                 relief=tk.FLAT, bd=4,
                 font=("Helvetica", 9)).pack(fill=tk.X, pady=(0, 8))

        # ── timeline header ───────────────────────────────────────
        hdr = tk.Frame(self._body, bg=bg)
        hdr.pack(fill=tk.X, pady=(8, 2))
        tk.Label(hdr, text="Timeline  (↑↓ to move)", bg=bg,
                 fg=self._colors["fg_dim_alt"],
                 font=("Helvetica", 8)).pack(side=tk.LEFT)
        tk.Button(hdr, text="+", command=self._zoom_in,
                  bg=self._colors.get("bg_dark", "#252525"),
                  fg=self._colors["fg_value"],
                  relief=tk.FLAT, bd=0, padx=6, pady=1,
                  font=("Helvetica", 9, "bold"), cursor="hand2").pack(side=tk.RIGHT)
        tk.Button(hdr, text="−", command=self._zoom_out,
                  bg=self._colors.get("bg_dark", "#252525"),
                  fg=self._colors["fg_value"],
                  relief=tk.FLAT, bd=0, padx=6, pady=1,
                  font=("Helvetica", 9, "bold"), cursor="hand2").pack(side=tk.RIGHT, padx=(0, 2))

        # ── timeline canvas ───────────────────────────────────────
        self._timeline_canvas = tk.Canvas(self._body,
                                          bg=bg, highlightthickness=1,
                                          highlightcolor=self._colors.get("bg_dark", "#252525"),
                                          height=160)
        self._timeline_canvas.pack(fill=tk.X, pady=(0, 4))
        c = self._timeline_canvas
        c.bind("<Configure>", lambda _e: self._draw_timeline())
        c.bind("<Button-1>",  self._on_timeline_click)
        c.bind("<Enter>",     lambda _e: (c.focus_set(),
                                          c.config(cursor="crosshair")))
        c.bind("<Leave>",     lambda _e: c.config(cursor=""))
        c.bind("<Up>",        lambda e:  self._move_in_time(-1))
        c.bind("<Down>",      lambda e:  self._move_in_time(1))

    # ── Public ────────────────────────────────────────────────────

    def update_start_time(self, start_time: float):
        self._node["start_time"] = start_time
        self._suppress_manual = True
        self._start_var.set(f"{start_time:.3f}")
        self._suppress_manual = False

    def set_reorder_button_state(self, can_go_up: bool, can_go_down: bool):
        for btn, enabled in ((self._up_btn, can_go_up), (self._down_btn, can_go_down)):
            if not btn:
                continue
            try:
                btn.config(state=tk.NORMAL if enabled else tk.DISABLED,
                           cursor="hand2" if enabled else "")
            except tk.TclError:
                pass

    def on_resize(self, width: int):
        self._refresh_preview()

    # ── Private ───────────────────────────────────────────────────

    def _do_reorder(self, direction: int):
        if self._on_reorder:
            self._on_reorder(direction)

    def _on_start_change(self, *_):
        try:
            start_time = float(self._start_var.get().strip())
            if start_time < 0:
                raise ValueError
        except ValueError:
            return
        self._node["start_time"] = start_time
        self._draw_timeline()
        if self._on_update:
            self._on_update(start_time)
        if self._on_manual_adjust and not self._suppress_manual:
            self._on_manual_adjust()

    def _move_in_time(self, direction: int):
        """Shift start_time by one tick step; timeline view follows."""
        try:
            current = float(self._start_var.get().strip())
        except ValueError:
            current = 0.0
        step    = _nice_tick(self._view_duration)
        new_val = round(current + direction * step, 10)
        new_val = max(0.0, min(new_val, self._parent_duration))
        self._start_var.set(f"{new_val:.3f}")

    def _zoom_in(self):
        """Halve the visible time window → finer detail."""
        self._view_duration = max(
            _TICK_STEPS[0] * 2,
            self._view_duration / 2
        )
        self._draw_timeline()

    def _zoom_out(self):
        """Double the visible time window → coarser view."""
        self._view_duration = min(
            max(0.01, self._parent_duration),
            self._view_duration * 2
        )
        self._draw_timeline()

    def _view_window(self, start_time: float):
        """Return (view_start, view_end) centered on start_time, clamped."""
        duration   = max(0.01, self._parent_duration)
        view_dur   = min(self._view_duration, duration)
        view_start = start_time - view_dur / 2
        view_start = max(0.0, min(view_start, duration - view_dur))
        return view_start, view_start + view_dur

    def _draw_timeline(self):
        c = self._timeline_canvas
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
        dim   = self._colors["fg_dim_alt"]
        arrow = "#28a745"

        try:
            start_time = float(self._start_var.get() or 0)
        except ValueError:
            start_time = 0.0

        view_start, view_end = self._view_window(start_time)
        view_dur   = view_end - view_start
        usable     = h - M_TOP - M_BOT
        px_per_s   = usable / max(view_dur, 1e-6)
        inc        = _nice_tick(view_dur)

        # vertical spine
        c.create_line(LX, M_TOP, LX, h - M_BOT, fill=dim, width=2)

        # tick marks — start at the first multiple of inc >= view_start
        t = round((view_start // inc) * inc, 10)
        if t < view_start - 1e-9:
            t = round(t + inc, 10)
        while t <= view_end + 1e-9:
            y     = M_TOP + (t - view_start) * px_per_s
            label = f"{int(t)}s" if abs(t - round(t)) < 1e-6 else f"{t:.2f}s"
            c.create_line(LX - 8, y, LX + 5, y, fill=dim, width=1)
            c.create_text(LX - 10, y, text=label, anchor="e",
                          fill=dim, font=("Helvetica", 7))
            t = round(t + inc, 10)

        # marker arrow at start_time
        st  = max(view_start, min(start_time, view_end))
        y_a = M_TOP + (st - view_start) * px_per_s
        c.create_polygon(LX, y_a, LX - 12, y_a - 6, LX - 12, y_a + 6,
                         fill=arrow, outline="")
        c.create_text(LX + 7, y_a, text=f"{start_time:.3f}s", anchor="w",
                      fill=arrow, font=("Helvetica", 7, "bold"))

    def _on_timeline_click(self, event):
        self._timeline_canvas.focus_set()
        try:
            start_time = float(self._start_var.get() or 0)
        except ValueError:
            start_time = 0.0
        view_start, view_end = self._view_window(start_time)
        view_dur   = view_end - view_start
        usable     = self._timeline_canvas.winfo_height() - M_TOP - M_BOT
        px_per_s   = usable / max(view_dur, 1e-6)
        inc        = _nice_tick(view_dur)
        t          = view_start + (event.y - M_TOP) / px_per_s
        snapped    = round(round(t / inc) * inc, 10)
        snapped    = max(0.0, min(snapped, self._parent_duration))
        self._start_var.set(f"{snapped:.3f}")

    def _refresh_preview(self):
        if not self._pil_src or not self._preview_lbl:
            return
        w = max(60, self._body.winfo_width() - 20)
        img = self._pil_src.copy()
        img.thumbnail((w, 240))
        photo = ImageTk.PhotoImage(img)
        self._preview_lbl.config(image=photo)
        self._preview_lbl._photo = photo
