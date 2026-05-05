import tkinter as tk
from tkinter import ttk


class SummaryPanel:
    def __init__(self, parent):
        self.audio_var = tk.StringVar(value="—")
        self.images_var = tk.StringVar(value="0")
        self.points_var = tk.StringVar(value="0 / 0")
        self.output_var = tk.StringVar(value="—")

        self.__build(parent)

    def set_audio(self, value):
        self.audio_var.set(value)

    def set_images(self, value):
        self.images_var.set(str(value))

    def set_points(self, have, needed):
        self.points_var.set(f"{have} / {needed}")

    def set_output(self, value):
        self.output_var.set(value)

    def __build(self, parent):
        tk.Label(parent, text="Summary", font=("Helvetica", 11, "bold"),
                 bg="#1e1e1e", fg="white").pack(pady=(14, 6))
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)

        info = tk.Frame(parent, bg="#1e1e1e")
        info.pack(fill=tk.X, padx=14, pady=10)

        self.__row(info, "Audio:", self.audio_var)
        self.__row(info, "Images:", self.images_var)
        self.__row(info, "Load points:", self.points_var)
        self.__row(info, "Output:", self.output_var)

    def __row(self, parent, label, var):
        frame = tk.Frame(parent, bg="#1e1e1e")
        frame.pack(fill=tk.X, pady=2)
        tk.Label(frame, text=label, bg="#1e1e1e", fg="#aaa", anchor="w", width=12).pack(side=tk.LEFT)
        tk.Label(frame, textvariable=var, bg="#1e1e1e", fg="white", anchor="w",
                 wraplength=140, justify=tk.LEFT).pack(side=tk.LEFT)
