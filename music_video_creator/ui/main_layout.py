import tkinter as tk


class MainLayout:
    def __init__(self, parent):
        self.content = tk.Frame(parent)
        self.content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.left = tk.Frame(self.content)
        self.left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right = tk.Frame(
            self.content,
            width=260,
            bg="#1e1e1e",
            relief=tk.SUNKEN,
            bd=1
        )
        self.right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.right.pack_propagate(False)

    def apply_theme(self, colors):
        self.right.config(bg=colors["bg_darkest"])