import tkinter as tk
from tkinter import ttk
import os

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False


def _fmt_size(path: str) -> str:
    try:
        b = os.path.getsize(path)
        if b < 1024:      return f"{b} B"
        if b < 1024 ** 2: return f"{b / 1024:.1f} KB"
        return f"{b / 1024 ** 2:.1f} MB"
    except Exception:
        return "—"


class InspectorPanel:
    def __init__(self, parent):
        self._pil_src     = None   # original PIL image kept for re-scaling
        self._preview_lbl = None

        self.frame = tk.Frame(parent, bg="#1e1e1e")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # ── header ────────────────────────────────────────────────
        tk.Label(self.frame, text="Inspector", bg="#1e1e1e", fg="white",
                 font=("Helvetica", 10, "bold"),
                 anchor="w", padx=10, pady=7).pack(fill=tk.X)
        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # ── body ─────────────────────────────────────────────────
        self._body = tk.Frame(self.frame, bg="#1e1e1e")
        self._body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._body.bind("<Configure>", self._on_resize)

        self._show_empty()

    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    def show_image(self, asset: dict):
        self._clear()
        path = asset["path"]

        self._preview_lbl = tk.Label(self._body, bg="#1e1e1e")
        self._preview_lbl.pack(pady=(4, 10))

        if _PIL:
            try:
                self._pil_src = Image.open(path)
                self._refresh_preview()
            except Exception:
                self._pil_src = None
                tk.Label(self._body, text="[no preview]",
                         bg="#1e1e1e", fg="#555").pack()

        self._info_row("Name", os.path.basename(path))
        self._info_row("Size", _fmt_size(path))

    def show_audio(self, asset: dict):
        self._clear()
        path = asset["path"]

        tk.Label(self._body, text="♪", bg="#1e1e1e", fg="#4a90d9",
                 font=("Helvetica", 52)).pack(pady=(20, 8))

        self._info_row("Name", os.path.basename(path))
        self._info_row("Size", _fmt_size(path))

    def clear(self):
        self._pil_src     = None
        self._preview_lbl = None
        self._show_empty()

    # ─────────────────────────────────────────────────────────────
    # Private
    # ─────────────────────────────────────────────────────────────

    def _clear(self):
        self._pil_src     = None
        self._preview_lbl = None
        for w in self._body.winfo_children():
            w.destroy()

    def _show_empty(self):
        self._clear()
        tk.Label(self._body, text="Select an asset\nto preview",
                 bg="#1e1e1e", fg="#555",
                 font=("Helvetica", 9), justify=tk.CENTER).pack(expand=True)

    def _info_row(self, label: str, value: str):
        row = tk.Frame(self._body, bg="#1e1e1e")
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label + ":", bg="#1e1e1e", fg="#888",
                 font=("Helvetica", 8), width=5, anchor="w").pack(side=tk.LEFT)
        val_lbl = tk.Label(row, text=value, bg="#1e1e1e", fg="#ddd",
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
        self._preview_lbl._photo = photo   # prevent GC
