import os
import tkinter as tk

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


class SingleAssetView:
    def __init__(self, body: tk.Frame, colors: dict):
        self._body        = body
        self._colors      = colors
        self._pil_src     = None
        self._preview_lbl = None

    def build(self, node: dict):
        ntype = node.get("type", "")
        path  = node.get("path", "")
        if ntype == "image":
            self._build_image(path)
        elif ntype == "audio":
            self._build_audio(path)

    def on_resize(self, _width: int):
        self._refresh_preview()

    def _build_image(self, path: str):
        bg = self._colors["bg_darkest"]
        self._preview_lbl = tk.Label(self._body, bg=bg)
        self._preview_lbl.pack(pady=(4, 8))

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
        self._info_row("Type", os.path.splitext(path)[1].upper().lstrip("."))

    def _build_audio(self, path: str):
        bg = self._colors["bg_darkest"]
        tk.Label(self._body, text="♪", bg=bg, fg="#4a90d9",
                 font=("Helvetica", 40)).pack(pady=(14, 6))
        self._info_row("Name", os.path.basename(path))
        self._info_row("Size", _fmt_size(path))
        self._info_row("Type", os.path.splitext(path)[1].upper().lstrip("."))

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

    def _refresh_preview(self):
        if not self._pil_src or not self._preview_lbl:
            return
        w = max(60, self._body.winfo_width() - 20)
        img = self._pil_src.copy()
        img.thumbnail((w, 160))
        photo = ImageTk.PhotoImage(img)
        self._preview_lbl.config(image=photo)
        self._preview_lbl._photo = photo
