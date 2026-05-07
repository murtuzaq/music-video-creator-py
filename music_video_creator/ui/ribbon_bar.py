import tkinter as tk
from tkinter import ttk


class RibbonBar(ttk.Frame):
    def __init__(self, parent, callbacks: dict):
        super().__init__(parent, relief=tk.GROOVE, padding=(4, 2))
        self.pack(fill=tk.X, padx=0, pady=0)

        self._btn("New Project",  callbacks["new"],  "New project  (Ctrl+N)")
        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=2)
        self._btn("Load Project", callbacks["open"], "Load project  (Ctrl+O)")
        self._btn("Save Project", callbacks["save"], "Save project  (Ctrl+S)")

    def _btn(self, text: str, command, tooltip: str = ""):
        b = ttk.Button(self, text=text, command=command)
        b.pack(side=tk.LEFT, padx=2, pady=1)
        if tooltip:
            _Tooltip(b, tooltip)


class _Tooltip:
    def __init__(self, widget, text: str):
        self._text = text
        self._tip = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event):
        w = event.widget
        x = w.winfo_rootx() + 20
        y = w.winfo_rooty() + w.winfo_height() + 2
        self._tip = tk.Toplevel(w)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self._tip, text=self._text, background="#ffffe0",
                 relief=tk.SOLID, borderwidth=1, font=("Segoe UI", 8)).pack()

    def _hide(self, _):
        if self._tip:
            self._tip.destroy()
            self._tip = None
