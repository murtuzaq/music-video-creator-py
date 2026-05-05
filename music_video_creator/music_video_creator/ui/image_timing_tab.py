import tkinter as tk
from tkinter import ttk


class ImageTimingTab:
    def __init__(self, parent, on_add_image):
        self.frame = parent

        header = tk.Frame(parent)
        header.pack(fill=tk.X, pady=(6, 2))

        tk.Label(
            header,
            text=" 2. Images & Timing",
            font=("Helvetica", 10, "bold")
        ).pack(side=tk.LEFT)

        tk.Button(
            header,
            text="+ Add Image",
            command=on_add_image,
            bg="#5cb85c",
            fg="white",
            relief=tk.FLAT,
            padx=8
        ).pack(side=tk.RIGHT)

        tk.Label(
            parent,
            text='Image 1 always plays first. Each subsequent image has a "Load in" time (seconds into the audio).',
            fg="#888",
            font=("Helvetica", 8),
            anchor="w"
        ).pack(fill=tk.X, padx=4)

        container = tk.Frame(parent, relief=tk.SUNKEN, bd=1)
        container.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        self.image_list_frame = tk.Frame(canvas)

        self.image_list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.image_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def get_image_list_frame(self):
        return self.image_list_frame