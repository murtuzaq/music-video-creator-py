import tkinter as tk


class HeaderBar:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg="#2b2b2b", pady=8)
        self.frame.pack(fill=tk.X)

        tk.Label(
            self.frame,
            text="🎬 Music Video Creator",
            font=("Helvetica", 16, "bold"),
            bg="#2b2b2b",
            fg="white"
        ).pack(side=tk.LEFT, padx=16)