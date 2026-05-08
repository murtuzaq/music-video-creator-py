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
        self._project_total_duration = 0.0
        self._colors                 = dict(_DARK)
        self._name_var     = tk.StringVar()
        self._dur_var      = tk.StringVar()

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

        self._body = tk.Frame(self.frame, bg="#1e1e1e")
        self._body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._body.bind("<Configure>", self._on_resize)

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
        self._body.config(bg=bg)
        if self._current_type == "image":
            self.show_image(self._current_node)
        elif self._current_type == "video":
            self.show_project(self._current_node, self._project_total_duration)
        elif self._current_type == "audio":
            self.show_audio(self._current_node)
        elif self._current_type == "video_clip":
            self.show_video_clip(self._current_node, self._on_update)
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

    def show_video_clip(self, node: dict, on_update=None):
        self._current_type = "video_clip"
        self._current_node = node
        self._on_update    = on_update
        self._clear()
        bg = self._colors["bg_darkest"]

        tk.Label(self._body, text="🎞", bg=bg, fg="#9b59b6",
                 font=("Helvetica", 40)).pack(pady=(14, 6))

        self._field_label("Name")
        self._name_var.set(node.get("name") or "")
        name_entry = tk.Entry(self._body, textvariable=self._name_var,
                              bg=self._colors.get("bg_dark", "#252525"),
                              fg=self._colors["fg_value"],
                              insertbackground=self._colors["fg_primary"],
                              relief=tk.FLAT, bd=4,
                              font=("Helvetica", 9))
        name_entry.pack(fill=tk.X, pady=(0, 8))

        self._field_label("Duration (seconds)")
        dur = node.get("duration")
        self._dur_var.set(str(dur) if dur is not None else "0")
        dur_entry = tk.Entry(self._body, textvariable=self._dur_var,
                             bg=self._colors.get("bg_dark", "#252525"),
                             fg=self._colors["fg_value"],
                             insertbackground=self._colors["fg_primary"],
                             relief=tk.FLAT, bd=4,
                             font=("Helvetica", 9))
        dur_entry.pack(fill=tk.X, pady=(0, 12))

        tk.Button(self._body, text="Apply Changes",
                  command=self._apply_clip_changes,
                  bg="#9b59b6", fg="white",
                  activebackground="#7d3c98", activeforeground="white",
                  relief=tk.FLAT, bd=0, padx=10, pady=5,
                  font=("Helvetica", 9, "bold"), cursor="hand2").pack(anchor="w")

    def clear(self):
        self._pil_src                = None
        self._preview_lbl            = None
        self._current_type           = None
        self._current_node           = None
        self._on_update              = None
        self._project_total_duration = 0.0
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

    def _on_resize(self, _event):
        if self._pil_src:
            self._refresh_preview()

    def _refresh_preview(self):
        if not self._pil_src or not self._preview_lbl:
            return
        w = max(60, self._body.winfo_width() - 20)
        img = self._pil_src.copy()
        img.thumbnail((w, 240))
        photo = ImageTk.PhotoImage(img)
        self._preview_lbl.config(image=photo)
        self._preview_lbl._photo = photo
