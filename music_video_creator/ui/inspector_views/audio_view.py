import os
import tkinter as tk
from ._helpers import info_row, fmt_size


class AudioView:
    def __init__(self, body: tk.Frame, colors: dict):
        self._body   = body
        self._colors = colors

    def build(self, node: dict):
        path = node.get("path", "")
        bg   = self._colors["bg_darkest"]
        tk.Label(self._body, text="♪", bg=bg, fg="#4a90d9",
                 font=("Helvetica", 52)).pack(pady=(20, 8))
        info_row(self._body, "Name", os.path.basename(path), self._colors)
        info_row(self._body, "Size", fmt_size(path),          self._colors)

    def on_resize(self, width: int):
        pass
