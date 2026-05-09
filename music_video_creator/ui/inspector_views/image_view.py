import os
import tkinter as tk

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

from ._helpers import info_row, fmt_size


class ImageView:
    def __init__(self, body: tk.Frame, colors: dict):
        self._body        = body
        self._colors      = colors
        self._pil_src     = None
        self._preview_lbl = None

    def build(self, node: dict):
        path = node.get("path", "")
        bg   = self._colors["bg_darkest"]

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

        info_row(self._body, "Name", os.path.basename(path), self._colors)
        info_row(self._body, "Size", fmt_size(path),          self._colors)

    def on_resize(self, width: int):
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
