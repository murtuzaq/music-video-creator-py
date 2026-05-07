import tkinter as tk
from tkinter import ttk


class MainNotebook:
    def __init__(self, parent):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.images_tab = tk.Frame(self.notebook)
        self.notebook.add(self.images_tab, text="  🖼  Images & Timing  ")

        self.lyrics_tab = tk.Frame(self.notebook)
        self.notebook.add(self.lyrics_tab, text="  🎤  Lyrics  ", state="disabled")

    def enable_lyrics_tab(self):
        self.notebook.tab(self.lyrics_tab, state="normal")

    def select_lyrics_tab(self):
        self.notebook.select(self.lyrics_tab)

    def disable_lyrics_tab(self):
        self.notebook.tab(self.lyrics_tab, state="disabled")
        self.notebook.select(self.images_tab)