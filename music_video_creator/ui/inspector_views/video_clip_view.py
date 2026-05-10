import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

from ._helpers import field_label

_TICK_STEPS = (0.05, 0.1, 0.2, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300)

_LANE_TOP  = 10
_LANE_BOT  = 46
_LABEL_Y   = 58
_CUE_Y     = 74
_STRIP_H   = 90


def _nice_tick(total: float, target_count: int = 6) -> float:
    target = max(1e-6, total / target_count)
    for step in _TICK_STEPS:
        if step >= target:
            return step
    return _TICK_STEPS[-1]


def _cue_min_gap(cues: list) -> float:
    """Return the smallest gap between consecutive cue start times, or 0 if not enough cues."""
    if len(cues) < 2:
        return 0.0
    gaps = [cues[i + 1]["start"] - cues[i]["start"]
            for i in range(len(cues) - 1)
            if cues[i + 1]["start"] > cues[i]["start"]]
    return min(gaps) if gaps else 0.0


class VideoClipView:
    def __init__(self, body: tk.Frame, colors: dict,
                 on_update=None, on_add_assets=None, auto_space_var=None,
                 get_children=None, on_remove_audio_clip=None):
        self._body                = body
        self._colors              = colors
        self._on_update           = on_update
        self._on_add_assets       = on_add_assets
        self._auto_space_var      = auto_space_var or tk.BooleanVar(value=False)
        self._get_children        = get_children
        self._on_remove_audio_clip = on_remove_audio_clip
        self._add_btn             = None
        self._name_var            = tk.StringVar()
        self._dur_var             = tk.StringVar()
        self._node                = None
        self._preview_lbl         = None
        self._strip_canvas        = None
        self._playhead_t          = 0.0
        self._pil_cache           = {}
        self._audio_clip_frame    = None
        self._add_ac_btn          = None

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

        # ── Audio Clip section ────────────────────────────────────
        ttk.Separator(self._body, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(2, 6))
        ac_hdr = tk.Frame(self._body, bg=bg)
        ac_hdr.pack(fill=tk.X, pady=(0, 2))
        tk.Label(ac_hdr, text="Audio Clip", bg=bg,
                 fg=self._colors["fg_dim_alt"],
                 font=("Helvetica", 8)).pack(side=tk.LEFT)
        self._add_ac_btn = tk.Button(
            ac_hdr, text="+",
            command=self._do_add_assets,
            bg="#555555", fg="#999",
            activebackground="#555555", activeforeground="#999",
            relief=tk.FLAT, bd=0, padx=6, pady=1,
            font=("Helvetica", 9, "bold"), cursor="",
        )
        self._add_ac_btn.pack(side=tk.RIGHT)
        self._audio_clip_frame = tk.Frame(self._body, bg=bg)
        self._audio_clip_frame.pack(fill=tk.X, pady=(2, 8))
        self._refresh_audio_clip_section()

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
                       text="Auto-space",
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

    def set_add_audio_clip_button_state(self, enabled: bool):
        if not self._add_ac_btn:
            return
        try:
            if enabled:
                self._add_ac_btn.config(bg="#28a745", fg="white",
                                        activebackground="#1e7e34", activeforeground="white",
                                        cursor="hand2")
            else:
                self._add_ac_btn.config(bg="#555555", fg="#999",
                                        activebackground="#555555", activeforeground="#999",
                                        cursor="")
        except tk.TclError:
            pass

    def refresh_timeline(self):
        self._refresh_audio_clip_section()
        self._draw_strip()
        self._update_preview()

    def update_duration(self, dur: float):
        self._node["duration"] = dur
        self._dur_var.set(str(dur))
        self._draw_strip()

    def on_resize(self, width: int):
        self._draw_strip()
        self._update_preview()

    # ── Private ───────────────────────────────────────────────────

    def _refresh_audio_clip_section(self):
        if not self._audio_clip_frame:
            return
        try:
            for w in self._audio_clip_frame.winfo_children():
                w.destroy()
        except tk.TclError:
            return

        bg  = self._colors["bg_darkest"]
        children = self._get_children() if self._get_children else []
        ac = next((n for n in children if n.get("type") == "audio_clip"), None)

        if ac:
            name = ac.get("name") or "Audio Clip"
            dur  = float(ac.get("duration") or 0.0)
            tk.Label(self._audio_clip_frame,
                     text=f"🎵  {name}  ({dur:.1f}s)",
                     bg=bg, fg="#8e44ad",
                     font=("Helvetica", 8, "bold"),
                     anchor="w", wraplength=170).pack(side=tk.LEFT, fill=tk.X, expand=True)
            if self._on_remove_audio_clip:
                tk.Button(self._audio_clip_frame, text="×",
                          command=self._do_remove_audio_clip,
                          bg=bg, fg=self._colors["fg_dim_alt"],
                          relief=tk.FLAT, bd=0,
                          font=("Helvetica", 11),
                          cursor="hand2",
                          activebackground=self._colors.get("bg_medium", "#2b2b2b"),
                          activeforeground=self._colors["fg_primary"]).pack(side=tk.RIGHT)
        else:
            tk.Label(self._audio_clip_frame,
                     text="None — add a .info file from Assets",
                     bg=bg, fg=self._colors["fg_dim"],
                     font=("Helvetica", 8), anchor="w").pack(side=tk.LEFT)

    def _do_remove_audio_clip(self):
        if self._on_remove_audio_clip:
            self._on_remove_audio_clip()
        self._refresh_audio_clip_section()
        self._draw_strip()
        self._update_preview()

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

    def _get_ac_and_cues(self, children: list):
        """Return (ac_node_or_None, sorted_cues_list)."""
        ac = next((n for n in children if n.get("type") == "audio_clip"), None)
        cues = sorted((ac.get("_cues") or []) if ac else [],
                      key=lambda c: c.get("start", 0.0))
        return ac, cues

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

        children     = self._get_children() if self._get_children else []
        _, cues      = self._get_ac_and_cues(children)
        direct_audio = [n for n in children if n.get("type") == "audio"]
        direct_imgs  = sorted([n for n in children if n.get("type") == "image"],
                              key=lambda n: n.get("start_time") or 0.0)

        px_per_s = (w - 4) / dur

        def _bar_label(x0, x1, y_mid, text):
            bar_w = x1 - x0
            if bar_w > 16:
                max_c = max(1, int(bar_w / 6))
                lbl   = text[:max_c - 1] + "…" if len(text) > max_c else text
                c.create_text((x0 + x1) / 2, y_mid, text=lbl,
                              fill="white", font=("Helvetica", 7), anchor="center")

        # ── Cue marker background lines ───────────────────────────
        for cue in cues:
            t = float(cue.get("start", 0.0))
            if t > dur + 1e-9:
                break
            x = 2 + t * px_per_s
            c.create_line(x, _LANE_TOP, x, _LANE_BOT,
                          fill="#6a3d6a", dash=(3, 3), width=1)

        # ── Direct audio bars (blue) ──────────────────────────────
        for n in direct_audio:
            t0 = float(n.get("start_time") or 0.0)
            t1 = t0 + float(n.get("_audio_dur") or 0.0)
            x0 = 2 + t0 * px_per_s
            x1 = max(x0 + 3, 2 + t1 * px_per_s)
            c.create_rectangle(x0, _LANE_TOP, x1, _LANE_BOT, fill="#4a90d9", outline="")
            _bar_label(x0, x1, (_LANE_TOP + _LANE_BOT) / 2, n.get("name") or "audio")

        # ── Image bars (green) ────────────────────────────────────
        for i, n in enumerate(direct_imgs):
            t0 = float(n.get("start_time") or 0.0)
            t1 = float(direct_imgs[i + 1].get("start_time") or 0.0) if i + 1 < len(direct_imgs) else dur
            if t1 is None:
                t1 = dur
            x0 = 2 + t0 * px_per_s
            x1 = max(x0 + 3, 2 + t1 * px_per_s)
            c.create_rectangle(x0, _LANE_TOP, x1, _LANE_BOT, fill="#5cb85c", outline="")
            _bar_label(x0, x1, (_LANE_TOP + _LANE_BOT) / 2, n.get("name") or "img")

        # ── Time ticks (min interval ≥ min cue gap) ───────────────
        inc = _nice_tick(dur)
        min_gap = _cue_min_gap(cues)
        if min_gap > 0 and inc < min_gap:
            for step in _TICK_STEPS:
                if step >= min_gap:
                    inc = step
                    break
            else:
                inc = _TICK_STEPS[-1]

        t = 0.0
        while t <= dur + 1e-9:
            x     = 2 + t * px_per_s
            label = f"{int(t)}s" if abs(t - round(t)) < 1e-6 else f"{t:.1f}s"
            c.create_line(x, _LANE_BOT + 2, x, _LANE_BOT + 6, fill=dim, width=1)
            c.create_text(x, _LABEL_Y, text=label, anchor="n",
                          fill=dim, font=("Helvetica", 7))
            t = round(t + inc, 10)

        # ── Cue text labels ───────────────────────────────────────
        for cue in cues:
            t    = float(cue.get("start", 0.0))
            text = (cue.get("text") or "").strip()
            if not text or t > dur + 1e-9:
                continue
            x = 2 + t * px_per_s
            c.create_text(x + 2, _CUE_Y, text=text[:18],
                          anchor="nw", fill="#9b59b6", font=("Helvetica", 6))

        # ── Playhead ──────────────────────────────────────────────
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
