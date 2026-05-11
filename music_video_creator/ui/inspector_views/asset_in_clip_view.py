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

_PREVIEW_H_DEFAULT  = 200
_PREVIEW_H_MIN      = 60
_PREVIEW_H_MAX      = 600

_TIMELINE_H_DEFAULT = 160
_TIMELINE_H_MIN     = 80
_TIMELINE_H_MAX     = 600


def _nice_tick(view_dur: float) -> float:
    """Return a tick interval that gives ~8 ticks across view_dur."""
    target = max(1e-6, view_dur / 8)
    for step in _TICK_STEPS:
        if step >= target:
            return step
    return _TICK_STEPS[-1]


_CUE_X0      = LX + 4
_CUE_X1      = LX + 14
_CUE_TEXT_X  = LX + 16


class AssetInClipView:
    def __init__(self, body: tk.Frame, colors: dict,
                 on_update=None, on_reorder=None, on_manual_adjust=None,
                 cues=None, show_lyrics=False, on_toggle_lyrics=None):
        self._body              = body
        self._colors            = colors
        self._on_update         = on_update
        self._on_reorder        = on_reorder
        self._on_manual_adjust  = on_manual_adjust
        self._cues              = cues or []
        self._show_lyrics_var   = tk.BooleanVar(value=show_lyrics and bool(cues))
        self._on_toggle_lyrics  = on_toggle_lyrics
        self._lyrics_chk        = None
        self._up_btn            = None
        self._down_btn          = None
        self._pil_src           = None
        self._preview_lbl       = None
        self._preview_frame     = None
        self._preview_h         = _PREVIEW_H_DEFAULT
        self._pane_resize_y0    = None
        self._pane_resize_h0    = None
        self._start_var              = tk.StringVar()
        self._suppress_manual        = False
        self._timeline_canvas        = None
        self._timeline_h             = _TIMELINE_H_DEFAULT
        self._timeline_resize_y0     = None
        self._timeline_resize_h0     = None
        self._view_duration     = 0.0
        self._parent_duration   = 0.0
        self._node              = None

    def build(self, node: dict, parent_duration: float):
        self._node            = node
        self._parent_duration = parent_duration
        self._view_duration   = max(0.01, parent_duration)
        bg    = self._colors["bg_darkest"]
        ntype = node.get("type", "image")
        path  = node.get("path") or ""

        # ── Preview pane ──────────────────────────────────────────────
        self._preview_frame = tk.Frame(self._body, bg=bg, height=self._preview_h)
        self._preview_frame.pack(fill=tk.X)
        self._preview_frame.pack_propagate(False)

        if ntype == "image" and _PIL and path:
            try:
                self._pil_src     = Image.open(path)
                self._preview_lbl = tk.Label(self._preview_frame, bg=bg)
                self._preview_lbl.pack(fill=tk.BOTH, expand=True)
                self._refresh_preview()
            except Exception:
                self._pil_src = None
                tk.Label(self._preview_frame, text="(preview unavailable)",
                         bg=bg, fg=self._colors["fg_dim"],
                         font=("Helvetica", 8)).pack(expand=True)
        elif ntype == "audio":
            tk.Label(self._preview_frame, text="♪", bg=bg, fg="#4a90d9",
                     font=("Helvetica", 32)).pack(expand=True)
        else:
            tk.Label(self._preview_frame, text="No preview",
                     bg=bg, fg=self._colors["fg_dim"],
                     font=("Helvetica", 8)).pack(expand=True)

        # ── Drag handle between panes ─────────────────────────────────
        handle = tk.Frame(self._body,
                          bg=self._colors.get("bg_medium", "#2b2b2b"),
                          height=6, cursor="sb_v_double_arrow")
        handle.pack(fill=tk.X)
        handle.bind("<Button-1>",  self._on_pane_resize_start)
        handle.bind("<B1-Motion>", self._on_pane_resize_drag)

        # ── Controls pane ─────────────────────────────────────────────
        ctrl = tk.Frame(self._body, bg=bg)
        ctrl.pack(fill=tk.X)

        # reorder buttons
        order_row = tk.Frame(ctrl, bg=bg)
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

        # start-time field
        field_label(ctrl, "Start Time (seconds)", self._colors)
        self._start_var.set(str(node.get("start_time") or 0.0))
        self._start_var.trace_add("write", self._on_start_change)
        tk.Entry(ctrl, textvariable=self._start_var,
                 bg=self._colors.get("bg_dark", "#252525"),
                 fg=self._colors["fg_value"],
                 insertbackground=self._colors["fg_primary"],
                 relief=tk.FLAT, bd=4,
                 font=("Helvetica", 9)).pack(fill=tk.X, pady=(0, 8))

        # timeline header
        hdr = tk.Frame(ctrl, bg=bg)
        hdr.pack(fill=tk.X, pady=(8, 2))
        tk.Label(hdr, text="Timeline  (↑↓ to move)", bg=bg,
                 fg=self._colors["fg_dim_alt"],
                 font=("Helvetica", 8)).pack(side=tk.LEFT)
        if self._cues:
            self._lyrics_chk = tk.Checkbutton(
                hdr, text="Lyrics",
                variable=self._show_lyrics_var,
                command=self._on_lyrics_toggle_click,
                bg=bg, fg=self._colors["fg_value"],
                selectcolor=self._colors.get("bg_dark", "#252525"),
                activebackground=bg,
                activeforeground=self._colors["fg_primary"],
                font=("Helvetica", 8), cursor="hand2",
            )
            self._lyrics_chk.pack(side=tk.LEFT, padx=(8, 0))
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

        # timeline canvas
        self._timeline_canvas = tk.Canvas(ctrl,
                                          bg=bg, highlightthickness=1,
                                          highlightcolor=self._colors.get("bg_dark", "#252525"),
                                          height=self._timeline_h)
        self._timeline_canvas.pack(fill=tk.X, pady=(0, 0))
        c = self._timeline_canvas
        c.bind("<Configure>", lambda _e: self._draw_timeline())
        c.bind("<Button-1>",  self._on_timeline_click)
        c.bind("<Enter>",     lambda _e: (c.focus_set(),
                                          c.config(cursor="crosshair")))
        c.bind("<Leave>",     lambda _e: c.config(cursor=""))
        c.bind("<Up>",        lambda e:  self._move_in_time(-1))
        c.bind("<Down>",      lambda e:  self._move_in_time(1))

        # timeline resize handle
        tl_handle = tk.Frame(ctrl,
                             bg=self._colors.get("bg_medium", "#2b2b2b"),
                             height=6, cursor="sb_v_double_arrow")
        tl_handle.pack(fill=tk.X, pady=(0, 4))
        tl_handle.bind("<Button-1>",  self._on_timeline_resize_start)
        tl_handle.bind("<B1-Motion>", self._on_timeline_resize_drag)

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

    def _on_pane_resize_start(self, event):
        self._pane_resize_y0          = event.y_root
        self._pane_resize_h0          = (self._preview_frame.winfo_height()
                                          if self._preview_frame else self._preview_h)
        self._pane_resize_timeline_h0 = (self._timeline_canvas.winfo_height()
                                          if self._timeline_canvas else self._timeline_h)

    def _on_pane_resize_drag(self, event):
        if self._pane_resize_y0 is None or not self._preview_frame:
            return
        delta = event.y_root - self._pane_resize_y0
        self._preview_h  = int(max(_PREVIEW_H_MIN,  min(_PREVIEW_H_MAX,  self._pane_resize_h0          + delta)))
        self._timeline_h = int(max(_TIMELINE_H_MIN, min(_TIMELINE_H_MAX, self._pane_resize_timeline_h0 - delta)))
        try:
            self._preview_frame.config(height=self._preview_h)
        except tk.TclError:
            pass
        if self._timeline_canvas:
            try:
                self._timeline_canvas.config(height=self._timeline_h)
            except tk.TclError:
                pass
        self._refresh_preview()

    def _on_timeline_resize_start(self, event):
        self._timeline_resize_y0 = event.y_root
        self._timeline_resize_h0 = (self._timeline_canvas.winfo_height()
                                     if self._timeline_canvas else self._timeline_h)

    def _on_timeline_resize_drag(self, event):
        if self._timeline_resize_y0 is None or not self._timeline_canvas:
            return
        delta = event.y_root - self._timeline_resize_y0
        new_h = max(_TIMELINE_H_MIN, min(_TIMELINE_H_MAX, self._timeline_resize_h0 + delta))
        self._timeline_h = int(new_h)
        try:
            self._timeline_canvas.config(height=self._timeline_h)
        except tk.TclError:
            pass

    def _on_lyrics_toggle_click(self):
        val = self._show_lyrics_var.get()
        if self._on_toggle_lyrics:
            self._on_toggle_lyrics(val)
        self._draw_timeline()

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
        dim       = self._colors["fg_dim_alt"]
        arrow     = "#28a745"
        font_size = max(7, min(14, h // 20))
        cue_size  = max(6, font_size - 1)

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

        # tick marks
        t = round((view_start // inc) * inc, 10)
        if t < view_start - 1e-9:
            t = round(t + inc, 10)
        while t <= view_end + 1e-9:
            y     = M_TOP + (t - view_start) * px_per_s
            label = f"{int(t)}s" if abs(t - round(t)) < 1e-6 else f"{t:.2f}s"
            c.create_line(LX - 8, y, LX + 5, y, fill=dim, width=1)
            c.create_text(LX - 10, y, text=label, anchor="e",
                          fill=dim, font=("Helvetica", font_size))
            t = round(t + inc, 10)

        # cue markers — only when lyrics checkbox is on
        for cue in (self._cues if self._show_lyrics_var.get() else []):
            t = float(cue.get("start", 0.0))
            if t < view_start - 1e-9 or t > view_end + 1e-9:
                continue
            y    = M_TOP + (t - view_start) * px_per_s
            text = (cue.get("text") or "").strip()
            c.create_line(_CUE_X0, y, _CUE_X1, y, fill="#9b59b6", width=1)
            if text:
                c.create_text(_CUE_TEXT_X, y, text=text[:22], anchor="w",
                              fill="#9b59b6", font=("Helvetica", cue_size))

        # marker arrow at start_time
        st  = max(view_start, min(start_time, view_end))
        y_a = M_TOP + (st - view_start) * px_per_s
        c.create_polygon(LX, y_a, LX - 12, y_a - 6, LX - 12, y_a + 6,
                         fill=arrow, outline="")
        c.create_text(LX + 7, y_a, text=f"{start_time:.3f}s", anchor="w",
                      fill=arrow, font=("Helvetica", font_size, "bold"))

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
        h = max(60, (self._preview_frame.winfo_height()
                     if self._preview_frame else self._preview_h) - 10)
        img = self._pil_src.copy()
        img.thumbnail((w, h))
        photo = ImageTk.PhotoImage(img)
        self._preview_lbl.config(image=photo)
        self._preview_lbl._photo = photo
