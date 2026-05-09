import tkinter as tk
from tkinter import ttk
import os

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

_DARK = {
    "bg_darkest": "#1e1e1e",
    "bg_dark":    "#252525",
    "bg_medium":  "#2b2b2b",
    "fg_primary": "white",
    "fg_secondary": "#aaa",
    "fg_dim":     "#555",
    "fg_dim_alt": "#888",
    "fg_value":   "#ddd",
    "selected_bg": "#4a4a7a",
}


def _fmt_duration(seconds: float) -> str:
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _fmt_size(path: str) -> str:
    try:
        b = os.path.getsize(path)
        if b < 1024:      return f"{b} B"
        if b < 1024 ** 2: return f"{b / 1024:.1f} KB"
        return f"{b / 1024 ** 2:.1f} MB"
    except Exception:
        return "—"


class InspectorPanel:
    def __init__(self, parent, on_close=None):
        self._pil_src      = None
        self._preview_lbl  = None
        self._current_type = None
        self._current_node = None
        self._on_update              = None
        self._on_add_assets          = None
        self._add_btn                = None
        self._project_total_duration = 0.0
        self._parent_duration        = 0.0
        self._timeline_increment     = 1.0
        self._timeline_canvas        = None
        self._colors                 = dict(_DARK)
        self._name_var               = tk.StringVar()
        self._dur_var                = tk.StringVar()
        self._start_var              = tk.StringVar()
        self._scroll_outer           = None
        self._scroll_canvas          = None
        self._body_win               = None

        self.frame = tk.Frame(parent, bg="#1e1e1e")
        self.frame.pack(fill=tk.BOTH, expand=True)

        self._header_frame = tk.Frame(self.frame, bg="#1e1e1e")
        self._header_frame.pack(fill=tk.X)
        self._header_lbl = tk.Label(self._header_frame, text="Project Inspector",
                                    bg="#1e1e1e", fg="white",
                                    font=("Helvetica", 10, "bold"),
                                    anchor="w", padx=10, pady=7)
        self._header_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._close_btn = tk.Button(self._header_frame, text="×", command=on_close,
                                    bg="#1e1e1e", fg="#888", relief=tk.FLAT,
                                    font=("Helvetica", 12), padx=8, pady=3,
                                    cursor="hand2", activebackground="#2b2b2b",
                                    activeforeground="white", bd=0)
        self._close_btn.pack(side=tk.RIGHT)
        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # ── Scrollable body ───────────────────────────────────────
        self._scroll_outer = tk.Frame(self.frame, bg="#1e1e1e")
        self._scroll_outer.pack(fill=tk.BOTH, expand=True)

        _vsb = ttk.Scrollbar(self._scroll_outer, orient=tk.VERTICAL)
        self._scroll_canvas = tk.Canvas(self._scroll_outer, bg="#1e1e1e",
                                        highlightthickness=0,
                                        yscrollcommand=_vsb.set)
        _vsb.config(command=self._scroll_canvas.yview)
        self._scroll_canvas.bind(
            "<MouseWheel>",
            lambda e: self._scroll_canvas.yview_scroll(
                int(-1 * e.delta / 120), "units"))
        _vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._body = tk.Frame(self._scroll_canvas, bg="#1e1e1e")
        self._body_win = self._scroll_canvas.create_window(
            (10, 10), window=self._body, anchor="nw")
        self._scroll_canvas.bind("<Configure>", self._on_scroll_canvas_resize)
        self._body.bind("<Configure>", self._on_body_configure)

        self._show_empty()

    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    def apply_theme(self, colors):
        self._colors = colors
        bg = colors["bg_darkest"]
        self.frame.config(bg=bg)
        self._header_frame.config(bg=bg)
        self._header_lbl.config(bg=bg, fg=colors["fg_primary"])
        self._close_btn.config(bg=bg, fg=colors["fg_dim_alt"],
                               activebackground=colors["bg_medium"],
                               activeforeground=colors["fg_primary"])
        self._scroll_outer.config(bg=bg)
        self._scroll_canvas.config(bg=bg)
        self._body.config(bg=bg)
        if self._current_type == "image":
            self.show_image(self._current_node)
        elif self._current_type == "video":
            self.show_project(self._current_node, self._project_total_duration)
        elif self._current_type == "audio":
            self.show_audio(self._current_node)
        elif self._current_type == "video_clip":
            self.show_video_clip(self._current_node, self._on_update, self._on_add_assets)
        elif self._current_type == "asset_in_clip":
            self.show_asset_in_clip(self._current_node, self._on_update,
                                    self._parent_duration)
        else:
            self._show_empty()

    def show_image(self, asset: dict):
        self._current_type = "image"
        self._current_node = asset
        self._clear()
        path = asset["path"]
        bg = self._colors["bg_darkest"]

        self._preview_lbl = tk.Label(self._body, bg=bg)
        self._preview_lbl.pack(pady=(4, 10))

        if _PIL:
            try:
                self._pil_src = Image.open(path)
                self._refresh_preview()
            except Exception:
                self._pil_src = None
                tk.Label(self._body, text="[no preview]",
                         bg=bg, fg=self._colors["fg_dim"]).pack()

        self._info_row("Name", os.path.basename(path))
        self._info_row("Size", _fmt_size(path))

    def show_project(self, node: dict, total_duration: float = 0.0):
        self._current_type           = "video"
        self._current_node           = node
        self._project_total_duration = total_duration
        self._clear()
        name = node.get("name") or "Untitled Project"
        bg   = self._colors["bg_darkest"]
        tk.Label(self._body, text="📹", bg=bg, fg="#e05c00",
                 font=("Helvetica", 40)).pack(pady=(14, 6))
        self._info_row("Name",     name)
        self._info_row("Duration", _fmt_duration(total_duration))

    def show_audio(self, asset: dict):
        self._current_type = "audio"
        self._current_node = asset
        self._clear()
        path = asset["path"]
        bg = self._colors["bg_darkest"]
        tk.Label(self._body, text="♪", bg=bg, fg="#4a90d9",
                 font=("Helvetica", 52)).pack(pady=(20, 8))
        self._info_row("Name", os.path.basename(path))
        self._info_row("Size", _fmt_size(path))

    def show_video_clip(self, node: dict, on_update=None, on_add_assets=None):
        self._current_type  = "video_clip"
        self._current_node  = node
        self._on_update     = on_update
        self._on_add_assets = on_add_assets
        self._clear()
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

        self._field_label("Name")
        self._name_var.set(node.get("name") or "")
        tk.Entry(self._body, textvariable=self._name_var,
                 bg=self._colors.get("bg_dark", "#252525"),
                 fg=self._colors["fg_value"],
                 insertbackground=self._colors["fg_primary"],
                 relief=tk.FLAT, bd=4,
                 font=("Helvetica", 9)).pack(fill=tk.X, pady=(0, 8))

        self._field_label("Duration (seconds)")
        dur = node.get("duration")
        self._dur_var.set(str(dur) if dur is not None else "0")
        tk.Entry(self._body, textvariable=self._dur_var,
                 bg=self._colors.get("bg_dark", "#252525"),
                 fg=self._colors["fg_value"],
                 insertbackground=self._colors["fg_primary"],
                 relief=tk.FLAT, bd=4,
                 font=("Helvetica", 9)).pack(fill=tk.X, pady=(0, 12))

        tk.Button(self._body, text="Apply Changes",
                  command=self._apply_clip_changes,
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

    def show_asset_in_clip(self, node: dict, on_update=None, parent_duration: float = 0.0):
        self._current_type    = "asset_in_clip"
        self._current_node    = node
        self._on_update       = on_update
        self._parent_duration = parent_duration
        self._add_btn         = None
        self._clear()
        bg    = self._colors["bg_darkest"]
        ntype = node.get("type", "image")
        path  = node.get("path") or ""

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
        self._field_label("Start Time (seconds)")
        self._start_var.set(str(node.get("start_time") or 0.0))
        tk.Entry(self._body, textvariable=self._start_var,
                 bg=self._colors.get("bg_dark", "#252525"),
                 fg=self._colors["fg_value"],
                 insertbackground=self._colors["fg_primary"],
                 relief=tk.FLAT, bd=4,
                 font=("Helvetica", 9)).pack(fill=tk.X, pady=(0, 6))

        tk.Button(self._body, text="Apply Changes",
                  command=self._apply_asset_in_clip,
                  bg="#5cb85c", fg="white",
                  activebackground="#449d44", activeforeground="white",
                  relief=tk.FLAT, bd=0, padx=10, pady=4,
                  font=("Helvetica", 9, "bold"), cursor="hand2").pack(anchor="w")

        # ── timeline header row ───────────────────────────────────
        hdr = tk.Frame(self._body, bg=bg)
        hdr.pack(fill=tk.X, pady=(8, 2))
        tk.Label(hdr, text="Timeline", bg=bg, fg=self._colors["fg_dim_alt"],
                 font=("Helvetica", 8)).pack(side=tk.LEFT)
        tk.Button(hdr, text="+", command=self._timeline_zoom_in,
                  bg=self._colors.get("bg_dark", "#252525"),
                  fg=self._colors["fg_value"],
                  relief=tk.FLAT, bd=0, padx=6, pady=1,
                  font=("Helvetica", 9, "bold"), cursor="hand2").pack(side=tk.RIGHT)
        tk.Button(hdr, text="−", command=self._timeline_zoom_out,
                  bg=self._colors.get("bg_dark", "#252525"),
                  fg=self._colors["fg_value"],
                  relief=tk.FLAT, bd=0, padx=6, pady=1,
                  font=("Helvetica", 9, "bold"), cursor="hand2").pack(side=tk.RIGHT, padx=(0, 2))

        # ── timeline canvas ───────────────────────────────────────
        self._timeline_canvas = tk.Canvas(self._body,
                                          bg=bg, highlightthickness=0, height=160)
        self._timeline_canvas.pack(fill=tk.X, pady=(0, 4))
        self._timeline_canvas.bind("<Configure>", lambda _e: self._draw_timeline())
        self._timeline_canvas.bind("<Button-1>", self._on_timeline_click)
        self._timeline_canvas.bind("<Enter>",
            lambda _e: self._timeline_canvas.config(cursor="crosshair"))
        self._timeline_canvas.bind("<Leave>",
            lambda _e: self._timeline_canvas.config(cursor=""))

    def clear(self):
        self._pil_src                = None
        self._preview_lbl            = None
        self._current_type           = None
        self._current_node           = None
        self._on_update              = None
        self._on_add_assets          = None
        self._add_btn                = None
        self._project_total_duration = 0.0
        self._parent_duration        = 0.0
        self._timeline_canvas        = None
        self._timeline_increment     = 1.0
        self._show_empty()

    # ─────────────────────────────────────────────────────────────
    # Private
    # ─────────────────────────────────────────────────────────────

    def _field_label(self, text: str):
        bg = self._colors["bg_darkest"]
        tk.Label(self._body, text=text, bg=bg,
                 fg=self._colors["fg_dim_alt"],
                 font=("Helvetica", 8), anchor="w").pack(fill=tk.X)

    def _apply_clip_changes(self):
        name = self._name_var.get().strip()
        dur_raw = self._dur_var.get().strip()
        try:
            dur = float(dur_raw)
            if dur < 0:
                raise ValueError
        except ValueError:
            dur = 0.0
        if not name:
            name = self._current_node.get("name") or "Video Clip"
        self._current_node["name"] = name
        self._current_node["duration"] = dur
        if self._on_update:
            self._on_update(name, dur)

    def _do_add_assets(self):
        if self._on_add_assets:
            self._on_add_assets()

    def _apply_asset_in_clip(self):
        try:
            start_time = float(self._start_var.get().strip())
            if start_time < 0:
                raise ValueError
        except ValueError:
            start_time = 0.0
        self._current_node["start_time"] = start_time
        self._draw_timeline()
        if self._on_update:
            self._on_update(start_time)

    def _timeline_zoom_in(self):
        self._timeline_increment = max(0.1, round(self._timeline_increment / 2, 10))
        self._draw_timeline()

    def _timeline_zoom_out(self):
        cap = max(1.0, self._parent_duration)
        self._timeline_increment = min(cap, round(self._timeline_increment * 2, 10))
        self._draw_timeline()

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
        dim    = self._colors["fg_dim_alt"]
        bg     = self._colors["bg_darkest"]
        arrow  = "#28a745"

        M_TOP  = 10
        M_BOT  = 10
        LINE_X = 55

        duration = max(0.01, self._parent_duration)
        try:
            start_time = float(self._start_var.get() or 0)
        except ValueError:
            start_time = 0.0
        inc = self._timeline_increment

        usable   = h - M_TOP - M_BOT
        px_per_s = usable / duration

        # vertical timeline
        c.create_line(LINE_X, M_TOP, LINE_X, h - M_BOT, fill=dim, width=2)

        # tick marks + labels
        t = 0.0
        while t <= duration + 1e-9:
            y = M_TOP + t * px_per_s
            c.create_line(LINE_X - 8, y, LINE_X + 5, y, fill=dim, width=1)
            label = f"{int(t)}s" if t == int(t) else f"{t:.1f}s"
            c.create_text(LINE_X - 10, y, text=label, anchor="e",
                          fill=dim, font=("Helvetica", 7))
            t = round(t + inc, 10)

        # arrow at start_time
        st  = max(0.0, min(start_time, duration))
        y_a = M_TOP + st * px_per_s
        c.create_polygon(
            LINE_X,      y_a,
            LINE_X - 12, y_a - 6,
            LINE_X - 12, y_a + 6,
            fill=arrow, outline="",
        )
        label = f"{start_time:.2f}s"
        c.create_text(LINE_X + 7, y_a, text=label, anchor="w",
                      fill=arrow, font=("Helvetica", 7, "bold"))

    def _clear(self):
        self._pil_src     = None
        self._preview_lbl = None
        for w in self._body.winfo_children():
            w.destroy()

    def _show_empty(self):
        self._clear()
        bg = self._colors["bg_darkest"]
        tk.Label(self._body, text="Select an asset\nto preview",
                 bg=bg, fg=self._colors["fg_dim"],
                 font=("Helvetica", 9), justify=tk.CENTER).pack(expand=True)

    def _info_row(self, label: str, value: str):
        bg = self._colors["bg_darkest"]
        row = tk.Frame(self._body, bg=bg)
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label + ":", bg=bg, fg=self._colors["fg_dim_alt"],
                 font=("Helvetica", 8), width=5, anchor="w").pack(side=tk.LEFT)
        val_lbl = tk.Label(row, text=value, bg=bg, fg=self._colors["fg_value"],
                           font=("Helvetica", 8), anchor="w", justify=tk.LEFT)
        val_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row.bind("<Configure>",
                 lambda e, l=val_lbl: l.configure(wraplength=max(1, e.width - 52)))

    def _on_scroll_canvas_resize(self, event):
        self._scroll_canvas.itemconfig(self._body_win, width=event.width - 20)
        if self._pil_src:
            self._refresh_preview()

    def _on_body_configure(self, event):
        self._scroll_canvas.configure(
            scrollregion=(0, 0, event.width + 20, event.height + 20))

    def _on_timeline_click(self, event):
        duration = max(0.01, self._parent_duration)
        inc = self._timeline_increment
        M_TOP = 10
        usable = self._timeline_canvas.winfo_height() - M_TOP - 10
        px_per_s = usable / duration
        t = (event.y - M_TOP) / px_per_s
        t_snapped = round(t / inc) * inc
        t_snapped = max(0.0, min(t_snapped, duration))
        self._start_var.set(f"{t_snapped:.2f}")
        self._draw_timeline()

    def _refresh_preview(self):
        if not self._pil_src or not self._preview_lbl:
            return
        w = max(60, self._body.winfo_width() - 20)
        img = self._pil_src.copy()
        img.thumbnail((w, 240))
        photo = ImageTk.PhotoImage(img)
        self._preview_lbl.config(image=photo)
        self._preview_lbl._photo = photo
