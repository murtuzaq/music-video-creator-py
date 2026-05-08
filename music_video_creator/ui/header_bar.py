import tkinter as tk


class HeaderBar:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg="#2b2b2b", pady=8)
        self.frame.pack(fill=tk.X)

        self._lbl = tk.Label(
            self.frame,
            text="🎬 Music Video Creator",
            font=("Helvetica", 16, "bold"),
            bg="#2b2b2b",
            fg="white"
        )
        self._lbl.pack(side=tk.LEFT, padx=16)

    def apply_theme(self, colors):
        self.frame.config(bg=colors["bg_medium"])
        self._lbl.config(bg=colors["bg_medium"], fg=colors["fg_primary"])
