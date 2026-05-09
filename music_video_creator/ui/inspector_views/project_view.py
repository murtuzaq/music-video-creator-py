import tkinter as tk
from ._helpers import fmt_duration, info_row


class ProjectView:
    def __init__(self, body: tk.Frame, colors: dict):
        self._body   = body
        self._colors = colors

    def build(self, node: dict, total_duration: float):
        bg   = self._colors["bg_darkest"]
        name = node.get("name") or "Untitled Project"
        tk.Label(self._body, text="📹", bg=bg, fg="#e05c00",
                 font=("Helvetica", 40)).pack(pady=(14, 6))
        info_row(self._body, "Name",     name,                       self._colors)
        info_row(self._body, "Duration", fmt_duration(total_duration), self._colors)

    def on_resize(self, width: int):
        pass
