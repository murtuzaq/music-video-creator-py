import tkinter as tk
from tkinter import ttk


class LyricsTab:
    def __init__(self, parent, on_clear):
        self.frame = parent

        self._bar = tk.Frame(parent, bg="#2b2b2b", pady=4)
        self._bar.pack(fill=tk.X)

        self.counter_var = tk.StringVar(
            value="Load audio and click 'Transcribe Lyrics' or 'Load Lyrics' to begin."
        )

        self._counter_lbl = tk.Label(
            self._bar,
            textvariable=self.counter_var,
            bg="#2b2b2b",
            fg="#ddd",
            font=("Helvetica", 9)
        )
        self._counter_lbl.pack(side=tk.LEFT, padx=10)

        self._clear_btn = tk.Button(
            self._bar,
            text="Clear all",
            command=on_clear,
            bg="#555",
            fg="white",
            relief=tk.FLAT,
            padx=8
        )
        self._clear_btn.pack(side=tk.RIGHT, padx=8)

        text_frame = tk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            font=("Helvetica", 13),
            cursor="arrow",
            state=tk.DISABLED,
            padx=12,
            pady=10,
            spacing1=4,
            spacing3=4
        )

        scroll = ttk.Scrollbar(text_frame, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)

        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.text.tag_config("word", foreground="#ddd", font=("Helvetica", 13))
        self.text.tag_config(
            "switch",
            foreground="white",
            background="#c0671a",
            font=("Helvetica", 13, "bold")
        )
        self.text.tag_config("hover", foreground="white", background="#555")

    def apply_theme(self, colors):
        self._bar.config(bg=colors["bg_medium"])
        self._counter_lbl.config(bg=colors["bg_medium"], fg=colors["fg_value"])
        self._clear_btn.config(bg=colors["fg_dim"])
        self.text.config(bg=colors["text_bg"], fg=colors["text_fg"],
                         insertbackground=colors["text_cursor"])
        self.text.tag_config("word", foreground=colors["lyrics_word_fg"])
        self.text.tag_config("hover", foreground=colors["fg_primary"],
                             background=colors["lyrics_hover_bg"])

    def set_counter_text(self, text):
        self.counter_var.set(text)

    def get_text_widget(self):
        return self.text
