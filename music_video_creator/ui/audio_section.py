import tkinter as tk


class AudioSection:
    def __init__(self, parent, on_pick_audio, on_pick_lyrics, on_transcribe):
        self.frame = tk.LabelFrame(
            parent,
            text=" 1. Audio File ",
            font=("Helvetica", 10, "bold"),
            padx=8,
            pady=6
        )
        self.frame.pack(fill=tk.X)

        row = tk.Frame(self.frame)
        row.pack(fill=tk.X)

        self.audio_label = tk.Label(row, text="No file selected", fg="gray", anchor="w")
        self.audio_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.transcribe_btn = tk.Button(
            row,
            text="🎤 Transcribe Lyrics",
            command=on_transcribe,
            bg="#7b5ea7",
            fg="white",
            relief=tk.FLAT,
            padx=8,
            state=tk.DISABLED
        )
        self.transcribe_btn.pack(side=tk.RIGHT, padx=(4, 0))

        tk.Button(
            row,
            text="📄 Load Lyrics",
            command=on_pick_lyrics,
            bg="#9b59b6",
            fg="white",
            relief=tk.FLAT,
            padx=8
        ).pack(side=tk.RIGHT, padx=4)

        tk.Button(
            row,
            text="Browse…",
            command=on_pick_audio,
            bg="#4a90d9",
            fg="white",
            relief=tk.FLAT,
            padx=10
        ).pack(side=tk.RIGHT)

    def apply_theme(self, colors):
        pass  # AudioSection uses system-default frame bg; accent buttons keep fixed colors

    def set_audio_name(self, name):
        self.audio_label.config(text=name, fg="black")

    def set_transcribe_enabled(self, enabled):
        if enabled:
            self.transcribe_btn.config(state=tk.NORMAL)
        else:
            self.transcribe_btn.config(state=tk.DISABLED)

    def set_transcribe_text(self, text):
        self.transcribe_btn.config(text=text)

    def reset(self):
        self.audio_label.config(text="No file selected", fg="gray")
        self.transcribe_btn.config(state=tk.DISABLED, text="🎤 Transcribe Lyrics")