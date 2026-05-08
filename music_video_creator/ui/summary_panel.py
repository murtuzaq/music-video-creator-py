import tkinter as tk
from tkinter import ttk


class SummaryPanel:
    def __init__(self, parent, on_generate):
        self._parent = parent
        self.audio_var  = tk.StringVar(value="—")
        self.images_var = tk.StringVar(value="0")
        self.points_var = tk.StringVar(value="0 / 0")
        self.output_var = tk.StringVar(value="—")

        self.generate_btn = tk.Button(
            parent,
            text="▶  Generate Video",
            command=on_generate,
            bg="#e05c00",
            fg="white",
            font=("Helvetica", 11, "bold"),
            relief=tk.FLAT,
            padx=16,
            pady=8,
            state=tk.DISABLED
        )
        self.generate_btn.pack(fill=tk.X, padx=14, pady=(20, 8))

        self.progress = ttk.Progressbar(parent, mode="indeterminate")
        self.progress.pack(fill=tk.X, padx=14, pady=(4, 8))
        self.progress.pack_forget()

        self.__build(parent)

    def set_audio(self, value):
        self.audio_var.set(value)

    def set_images(self, value):
        self.images_var.set(str(value))

    def set_points(self, have, needed):
        self.points_var.set(f"{have} / {needed}")

    def set_output(self, value):
        self.output_var.set(value)

    def apply_theme(self, colors):
        bg = colors["bg_darkest"]
        self._title_lbl.config(bg=bg, fg=colors["fg_primary"])
        self._info_frame.config(bg=bg)
        for lbl_key, val_key in self._row_widgets:
            lbl_key.config(bg=bg, fg=colors["fg_secondary"])
            val_key.config(bg=bg, fg=colors["fg_primary"])
        for frame in self._row_frames:
            frame.config(bg=bg)

    def __build(self, parent):
        self._title_lbl = tk.Label(parent, text="Summary", font=("Helvetica", 11, "bold"),
                                   bg="#1e1e1e", fg="white")
        self._title_lbl.pack(pady=(14, 6))
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)

        self._info_frame = tk.Frame(parent, bg="#1e1e1e")
        self._info_frame.pack(fill=tk.X, padx=14, pady=10)

        self._row_widgets = []
        self._row_frames  = []
        self.__row(self._info_frame, "Audio:",       self.audio_var)
        self.__row(self._info_frame, "Images:",      self.images_var)
        self.__row(self._info_frame, "Load points:", self.points_var)
        self.__row(self._info_frame, "Output:",      self.output_var)

    def __row(self, parent, label, var):
        frame = tk.Frame(parent, bg="#1e1e1e")
        frame.pack(fill=tk.X, pady=2)
        lbl = tk.Label(frame, text=label, bg="#1e1e1e", fg="#aaa", anchor="w", width=12)
        lbl.pack(side=tk.LEFT)
        val = tk.Label(frame, textvariable=var, bg="#1e1e1e", fg="white", anchor="w",
                       wraplength=140, justify=tk.LEFT)
        val.pack(side=tk.LEFT)
        self._row_frames.append(frame)
        self._row_widgets.append((lbl, val))

    def set_generate_enabled(self, enabled):
        if enabled:
            self.generate_btn.config(state=tk.NORMAL)
        else:
            self.generate_btn.config(state=tk.DISABLED)

    def set_generating(self, generating):
        if generating:
            self.generate_btn.config(state=tk.DISABLED, text="Generating…")
            self.progress.pack(fill=tk.X, padx=14, pady=(4, 8))
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.pack_forget()
            self.generate_btn.config(text="▶  Generate Video")
