# music_video_creator/ui/bottom_bar.py

import tkinter as tk
from tkinter import ttk


class BottomBar:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg="#2b2b2b", pady=6)
        self.frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.progress = ttk.Progressbar(self.frame, mode="indeterminate", length=200)
        self.progress.pack(side=tk.LEFT, padx=16, pady=4)
        self.progress.pack_forget()

        self.status_var = tk.StringVar(value="Ready.")
        self._status_lbl = tk.Label(
            self.frame,
            textvariable=self.status_var,
            bg="#2b2b2b",
            fg="#aaa"
        )
        self._status_lbl.pack(side=tk.LEFT, padx=16)

    # ─────────────────────────────────────────

    def set_status(self, msg):
        self.status_var.set(msg)

    def apply_theme(self, colors):
        self.frame.config(bg=colors["bg_medium"])
        self._status_lbl.config(bg=colors["bg_medium"], fg=colors["fg_secondary"])

    def set_progress(self, running):
        if running:
            self.progress.pack(side=tk.LEFT, padx=16, pady=4)
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.pack_forget()