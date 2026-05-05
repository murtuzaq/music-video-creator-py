import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


class ImageRow:
    def __init__(self, parent, path, load_var, on_remove, on_refresh_summary):
        self.path = path
        self.load_var = load_var
        self.photo = None

        self.row = tk.Frame(parent, relief=tk.RIDGE, bd=1, padx=6, pady=4)
        self.row.pack(fill=tk.X, padx=4, pady=2)

        self.__draw_image_preview()
        self.__draw_name()
        self.__draw_remove_button(on_remove)
        self.__draw_timing(on_refresh_summary)

    def destroy(self):
        self.row.destroy()

    def show_first_mode(self):
        self.load_inner.pack_forget()
        self.first_lbl.pack()

    def show_timed_mode(self):
        self.first_lbl.pack_forget()
        self.load_inner.pack()

    def __draw_image_preview(self):
        try:
            img = Image.open(self.path)
            img.thumbnail((48, 48))
            self.photo = ImageTk.PhotoImage(img)
            tk.Label(self.row, image=self.photo).pack(side=tk.LEFT, padx=(0, 8))
        except Exception:
            tk.Label(self.row, text="[img]", width=6).pack(side=tk.LEFT)

    def __draw_name(self):
        name = os.path.basename(self.path)
        tk.Label(
            self.row,
            text=name,
            anchor="w",
            wraplength=220
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def __draw_remove_button(self, on_remove):
        tk.Button(
            self.row,
            text="✕",
            command=on_remove,
            fg="red",
            relief=tk.FLAT,
            padx=4
        ).pack(side=tk.RIGHT)

    def __draw_timing(self, on_refresh_summary):
        timing_frame = tk.Frame(self.row)
        timing_frame.pack(side=tk.RIGHT, padx=(8, 4))

        self.first_lbl = tk.Label(
            timing_frame,
            text="Plays first",
            fg="#5cb85c",
            font=("Helvetica", 9, "italic")
        )

        self.load_inner = tk.Frame(timing_frame)

        tk.Label(self.load_inner, text="Load in:").pack(side=tk.LEFT)

        ttk.Spinbox(
            self.load_inner,
            from_=0.1,
            to=7200,
            increment=0.5,
            textvariable=self.load_var,
            width=7,
            command=on_refresh_summary
        ).pack(side=tk.LEFT, padx=(4, 2))

        tk.Label(self.load_inner, text="s").pack(side=tk.LEFT)