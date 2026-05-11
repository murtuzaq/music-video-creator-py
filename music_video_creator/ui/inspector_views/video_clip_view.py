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
    starts = sorted(float(c.get("start", 0.0)) for c in cues)
    if len(starts) < 2:
        return 0.0
    return min(b - a for a, b in zip(starts, starts[1:]) if b > a)


class VideoClipView:
    def __init__(self, body: tk.Frame, colors: dict,
                 on_update=None, on_add_assets=None, auto_space_var=None,
                 get_children=None, on_remove_audio_clip=None,
                 get_node=None):
        self._body                  = body
        self._colors                = colors
        self._on_update             = on_update
        self._on_add_assets         = on_add_assets
        self._auto_space_var        = auto_space_var or tk.BooleanVar(value=False)
        self._get_children          = get_children
        self._on_remove_audio_clip  = on_remove_audio_clip
        self._get_node              = get_node
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
        self._ac_btn_is_remove    = False
        self._show_lyrics_var     = tk.BooleanVar(value=False)
        self._lyrics_chk          = None
        self._cues                = []
        self._use_full_var        = tk.BooleanVar(value=True)
        self._ac_start_var        = tk.StringVar(value="0.0")
        self._ac_end_var          = tk.StringVar(value="0.0")
        self._ac_start_entry      = None
        self._ac_end_entry        = None
        self._ac_file_dur         = 0.0

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
        real_node = self._get_node() if self._get_node else node
        self._show_lyrics_var.set(real_node.get("_show_lyrics", False))
        self._lyrics_chk = tk.Checkbutton(
            hdr, text="Show Lyrics",
            variable=self._show_lyrics_var,
            bg=bg,
            fg=self._colors["fg_value"],
            selectcolor=self._colors.get("bg_dark", "#252525"),
            activebackground=bg,
            activeforeground=self._colors["fg_primary"],
            font=("Helvetica", 8),
            cursor="hand2",
            command=self._on_lyrics_toggle,
        )
        # Now the widget exists — sync visibility with current children
        self._update_lyrics_checkbox()

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
        # Don't override the button when it's acting as a remove ("-") button
        if getattr(self, "_ac_btn_is_remove", False):
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

        import json as _json, os as _os
        bg        = self._colors["bg_darkest"]
        dark      = self._colors.get("bg_dark", "#252525")
        dim       = self._colors["fg_dim"]
        real_node = self._get_node() if self._get_node else self._node
        path      = real_node.get("audio_clip_path", "") if real_node else ""

        self._ac_start_entry = None
        self._ac_end_entry   = None

        if path and _os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    info = _json.load(f)
                name = _os.path.splitext(_os.path.basename(path))[0]
                dur  = float(info.get("duration_seconds", 0.0))
                self._cues = sorted(info.get("lyrics", {}).get("cues", []),
                                    key=lambda c: c.get("start", 0.0))
            except Exception:
                name = _os.path.basename(path)
                dur  = 0.0
                self._cues = []

            self._ac_file_dur = dur

            tk.Label(self._audio_clip_frame,
                     text=f"🎵  {name}  ({dur:.1f}s)",
                     bg=bg, fg="#8e44ad",
                     font=("Helvetica", 8, "bold"),
                     anchor="w", wraplength=170).pack(fill=tk.X)

            # Read persisted values (fall back to full-file defaults)
            use_full  = real_node.get("audio_clip_use_full", True)
            if use_full is None:
                use_full = True
            start_t   = float(real_node.get("audio_clip_start") or 0.0)
            end_t     = float(real_node.get("audio_clip_end") or dur)
            self._use_full_var.set(use_full)
            self._ac_start_var.set(f"{start_t:.3f}")
            self._ac_end_var.set(f"{end_t:.3f}")

            # "Use entire audio file" checkbox
            tk.Checkbutton(
                self._audio_clip_frame,
                text="Use entire audio file",
                variable=self._use_full_var,
                command=self._on_use_full_toggle,
                bg=bg, fg=self._colors["fg_value"],
                selectcolor=dark,
                activebackground=bg,
                activeforeground=self._colors["fg_primary"],
                font=("Helvetica", 8),
                cursor="hand2",
            ).pack(anchor="w", pady=(4, 2))

            # Start / End rows
            entry_kw = dict(bg=dark, fg=self._colors["fg_value"],
                            insertbackground=self._colors["fg_primary"],
                            disabledbackground=bg, disabledforeground=dim,
                            relief=tk.FLAT, bd=3, font=("Helvetica", 8), width=7)
            lbl_kw   = dict(bg=bg, fg=self._colors["fg_dim_alt"],
                            font=("Helvetica", 8), width=5, anchor="w")

            for label, var, attr in (("Start", self._ac_start_var, "_ac_start_entry"),
                                     ("End",   self._ac_end_var,   "_ac_end_entry")):
                row = tk.Frame(self._audio_clip_frame, bg=bg)
                row.pack(fill=tk.X, pady=1)
                tk.Label(row, text=label + ":", **lbl_kw).pack(side=tk.LEFT)
                ent = tk.Entry(row, textvariable=var, **entry_kw)
                ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
                tk.Label(row, text="s", bg=bg, fg=dim,
                         font=("Helvetica", 8)).pack(side=tk.LEFT, padx=(3, 0))
                ent.bind("<FocusOut>", lambda e: self._on_ac_time_change())
                ent.bind("<Return>",   lambda e: self._on_ac_time_change())
                setattr(self, attr, ent)

            self._update_ac_fields()

            self._ac_btn_is_remove = True
            if self._add_ac_btn:
                self._add_ac_btn.config(
                    text="−", command=self._do_remove_audio_clip,
                    bg="#c0392b", fg="white",
                    activebackground="#96281b", activeforeground="white",
                    cursor="hand2")
        else:
            self._cues        = []
            self._ac_file_dur = 0.0
            tk.Label(self._audio_clip_frame,
                     text="None — add a .info file from Assets",
                     bg=bg, fg=dim,
                     font=("Helvetica", 8), anchor="w").pack(fill=tk.X)
            self._ac_btn_is_remove = False
            if self._add_ac_btn:
                self._add_ac_btn.config(
                    text="+", command=self._do_add_assets,
                    bg="#555555", fg="#999",
                    activebackground="#555555", activeforeground="#999",
                    cursor="")
        self._update_lyrics_checkbox()

    def _on_lyrics_toggle(self):
        val = self._show_lyrics_var.get()
        real_node = self._get_node() if self._get_node else self._node
        if real_node is not None:
            real_node["_show_lyrics"] = val
        self._draw_strip()

    def _on_use_full_toggle(self):
        use_full  = self._use_full_var.get()
        real_node = self._get_node() if self._get_node else self._node
        if real_node is not None:
            real_node["audio_clip_use_full"] = use_full
        self._update_ac_fields()
        if use_full:
            new_dur = self._ac_file_dur
        else:
            try:
                s = float(self._ac_start_var.get())
                e = float(self._ac_end_var.get())
                new_dur = max(0.0, e - s)
            except ValueError:
                new_dur = self._ac_file_dur
        self._dur_var.set(str(round(new_dur, 3)))

    def _update_ac_fields(self):
        enabled = not self._use_full_var.get()
        state   = tk.NORMAL if enabled else tk.DISABLED
        for ent in (self._ac_start_entry, self._ac_end_entry):
            if ent:
                try:
                    ent.config(state=state)
                except tk.TclError:
                    pass

    def _on_ac_time_change(self):
        real_node = self._get_node() if self._get_node else self._node
        if not real_node:
            return
        file_dur = self._ac_file_dur
        try:
            start = float(self._ac_start_var.get())
            start = max(0.0, min(start, file_dur))
        except ValueError:
            start = 0.0
        try:
            end = float(self._ac_end_var.get())
            end = max(start, min(end, file_dur))
        except ValueError:
            end = file_dur
        real_node["audio_clip_start"] = start
        real_node["audio_clip_end"]   = end
        self._ac_start_var.set(f"{start:.3f}")
        self._ac_end_var.set(f"{end:.3f}")
        self._dur_var.set(str(round(max(0.0, end - start), 3)))

    def _update_lyrics_checkbox(self):
        if not self._lyrics_chk:
            return
        if self._cues:
            self._lyrics_chk.pack(side=tk.RIGHT)
        else:
            self._lyrics_chk.pack_forget()
            self._show_lyrics_var.set(False)

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
        cues         = self._cues
        show_lyrics  = self._show_lyrics_var.get() and bool(cues)
        direct_audio = [n for n in children if n.get("type") == "audio"]
        direct_imgs  = sorted([n for n in children if n.get("type") == "image"],
                              key=lambda n: n.get("start_time") or 0.0)

        rn        = self._get_node() if self._get_node else self._node
        use_full  = rn.get("audio_clip_use_full", True) if rn else True
        ac_start  = 0.0 if (not rn or use_full) else float(rn.get("audio_clip_start") or 0.0)

        px_per_s = (w - 4) / dur

        def _bar_label(x0, x1, y_mid, text):
            bar_w = x1 - x0
            if bar_w > 16:
                max_c = max(1, int(bar_w / 6))
                lbl   = text[:max_c - 1] + "…" if len(text) > max_c else text
                c.create_text((x0 + x1) / 2, y_mid, text=lbl,
                              fill="white", font=("Helvetica", 7), anchor="center")

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

        # ── Cue marker lines (drawn after bars so they appear on top) ─
        if show_lyrics:
            for cue in cues:
                t_abs = float(cue.get("start", 0.0))
                t_rel = t_abs - ac_start
                if t_rel < -1e-9 or t_rel > dur + 1e-9:
                    continue
                x = 2 + t_rel * px_per_s
                c.create_line(x, _LANE_TOP, x, _LANE_BOT,
                              fill="#9b59b6", dash=(3, 3), width=1)

        # ── Time ticks (min interval ≥ min cue gap when lyrics on) ──
        inc = _nice_tick(dur)
        if show_lyrics:
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
            t_abs = ac_start + t
            label = f"{int(t_abs)}s" if abs(t_abs - round(t_abs)) < 1e-6 else f"{t_abs:.1f}s"
            c.create_line(x, _LANE_BOT + 2, x, _LANE_BOT + 6, fill=dim, width=1)
            c.create_text(x, _LABEL_Y, text=label, anchor="n",
                          fill=dim, font=("Helvetica", 7))
            t = round(t + inc, 10)

        # ── Cue text labels ───────────────────────────────────────
        if show_lyrics:
            for cue in cues:
                t_abs = float(cue.get("start", 0.0))
                t_rel = t_abs - ac_start
                text  = (cue.get("text") or "").strip()
                if not text or t_rel < -1e-9 or t_rel > dur + 1e-9:
                    continue
                x = 2 + t_rel * px_per_s
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
