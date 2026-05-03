import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os


class MusicVideoCreator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Music Video Creator")
        self.geometry("900x650")
        self.resizable(True, True)

        # App state
        self.audio_path = None
        self.image_entries = []  # list of dicts: {path, duration, thumbnail}

        self._build_ui()

    def _build_ui(self):
        # ── Top bar ──────────────────────────────────────────────
        top = tk.Frame(self, bg="#2b2b2b", pady=8)
        top.pack(fill=tk.X)
        tk.Label(
            top, text="🎬 Music Video Creator",
            font=("Helvetica", 16, "bold"),
            bg="#2b2b2b", fg="white"
        ).pack(side=tk.LEFT, padx=16)

        # ── Main content: left panel + right preview ─────────────
        content = tk.Frame(self)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.Frame(content, width=560)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left.pack_propagate(False)

        right = tk.Frame(content, width=300, bg="#1e1e1e", relief=tk.SUNKEN, bd=1)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        # ── Section 1: Audio file ────────────────────────────────
        self._section_audio(left)

        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)

        # ── Section 2: Image list ────────────────────────────────
        self._section_images(left)

        # ── Right panel: summary / info ──────────────────────────
        self._panel_summary(right)

        # ── Bottom bar: Generate button ──────────────────────────
        self._build_bottom_bar()

    # ── Audio section ────────────────────────────────────────────
    def _section_audio(self, parent):
        frame = tk.LabelFrame(parent, text=" 1. Audio File ", font=("Helvetica", 10, "bold"), padx=8, pady=6)
        frame.pack(fill=tk.X, pady=(0, 4))

        row = tk.Frame(frame)
        row.pack(fill=tk.X)

        self.audio_label = tk.Label(row, text="No file selected", fg="gray", anchor="w")
        self.audio_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Button(
            row, text="Browse…", command=self._pick_audio,
            bg="#4a90d9", fg="white", relief=tk.FLAT, padx=10
        ).pack(side=tk.RIGHT)

    # ── Images section ───────────────────────────────────────────
    def _section_images(self, parent):
        header = tk.Frame(parent)
        header.pack(fill=tk.X)

        tk.Label(header, text=" 2. Images & Timing", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(
            header, text="+ Add Image", command=self._add_image,
            bg="#5cb85c", fg="white", relief=tk.FLAT, padx=8
        ).pack(side=tk.RIGHT)

        # Scrollable list
        container = tk.Frame(parent, relief=tk.SUNKEN, bd=1)
        container.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

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

        self._update_empty_label()

    def _update_empty_label(self):
        for w in self.image_list_frame.winfo_children():
            if getattr(w, "_is_empty_label", False):
                w.destroy()

        if not self.image_entries:
            lbl = tk.Label(
                self.image_list_frame,
                text='Click "+ Add Image" to add images with durations.',
                fg="gray", pady=20
            )
            lbl._is_empty_label = True
            lbl.pack()

    # ── Right summary panel ──────────────────────────────────────
    def _panel_summary(self, parent):
        tk.Label(
            parent, text="Summary", font=("Helvetica", 11, "bold"),
            bg="#1e1e1e", fg="white"
        ).pack(pady=(14, 6))

        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)

        info = tk.Frame(parent, bg="#1e1e1e")
        info.pack(fill=tk.X, padx=14, pady=10)

        def row(label, var):
            f = tk.Frame(info, bg="#1e1e1e")
            f.pack(fill=tk.X, pady=2)
            tk.Label(f, text=label, bg="#1e1e1e", fg="#aaa", anchor="w", width=14).pack(side=tk.LEFT)
            tk.Label(f, textvariable=var, bg="#1e1e1e", fg="white", anchor="w").pack(side=tk.LEFT)

        self.sv_audio = tk.StringVar(value="—")
        self.sv_images = tk.StringVar(value="0")
        self.sv_duration = tk.StringVar(value="0 s")

        row("Audio:", self.sv_audio)
        row("Images:", self.sv_images)
        row("Total time:", self.sv_duration)

    # ── Bottom bar ───────────────────────────────────────────────
    def _build_bottom_bar(self):
        bar = tk.Frame(self, bg="#2b2b2b", pady=8)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(bar, textvariable=self.status_var, bg="#2b2b2b", fg="#aaa").pack(side=tk.LEFT, padx=16)

        tk.Button(
            bar, text="▶  Generate Video",
            command=self._generate_video,
            bg="#e05c00", fg="white", font=("Helvetica", 11, "bold"),
            relief=tk.FLAT, padx=16, pady=4
        ).pack(side=tk.RIGHT, padx=16)

    # ── Actions ──────────────────────────────────────────────────
    def _pick_audio(self):
        path = filedialog.askopenfilename(
            title="Select audio file",
            filetypes=[("Audio files", "*.mp3 *.wav *.aac *.ogg *.flac"), ("All files", "*.*")]
        )
        if path:
            self.audio_path = path
            name = os.path.basename(path)
            self.audio_label.config(text=name, fg="black")
            self.sv_audio.set(name)
            self.status_var.set(f"Audio loaded: {name}")

    def _add_image(self):
        paths = filedialog.askopenfilenames(
            title="Select image(s)",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]
        )
        for path in paths:
            self._add_image_row(path)
        self._refresh_summary()

    def _add_image_row(self, path):
        entry = {"path": path, "duration_var": tk.DoubleVar(value=3.0)}
        self.image_entries.append(entry)

        # Build row widget
        row = tk.Frame(self.image_list_frame, relief=tk.RIDGE, bd=1, padx=6, pady=4)
        row.pack(fill=tk.X, padx=4, pady=2)
        entry["row_widget"] = row

        # Thumbnail
        try:
            img = Image.open(path)
            img.thumbnail((48, 48))
            photo = ImageTk.PhotoImage(img)
            entry["photo"] = photo
            tk.Label(row, image=photo).pack(side=tk.LEFT, padx=(0, 8))
        except Exception:
            tk.Label(row, text="[img]", width=6).pack(side=tk.LEFT)

        # Filename
        name = os.path.basename(path)
        tk.Label(row, text=name, anchor="w", wraplength=260).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Duration spinner
        tk.Label(row, text="Duration (s):").pack(side=tk.LEFT, padx=(8, 2))
        spin = ttk.Spinbox(
            row, from_=0.5, to=300, increment=0.5,
            textvariable=entry["duration_var"], width=6,
            command=self._refresh_summary
        )
        spin.pack(side=tk.LEFT)

        # Remove button
        def remove(e=entry, r=row):
            self.image_entries.remove(e)
            r.destroy()
            self._update_empty_label()
            self._refresh_summary()

        tk.Button(
            row, text="✕", command=remove,
            fg="red", relief=tk.FLAT, padx=4
        ).pack(side=tk.RIGHT)

        self._update_empty_label()

    def _refresh_summary(self):
        total = sum(e["duration_var"].get() for e in self.image_entries)
        self.sv_images.set(str(len(self.image_entries)))
        self.sv_duration.set(f"{total:.1f} s")

    def _generate_video(self):
        # Validation (video generation comes in a later step)
        if not self.audio_path:
            messagebox.showwarning("Missing audio", "Please select an audio file first.")
            return
        if not self.image_entries:
            messagebox.showwarning("No images", "Please add at least one image.")
            return
        messagebox.showinfo(
            "Coming soon",
            "Video generation will be wired up in the next step.\n\n"
            f"Audio: {os.path.basename(self.audio_path)}\n"
            f"Images: {len(self.image_entries)}\n"
            f"Total time: {sum(e['duration_var'].get() for e in self.image_entries):.1f}s"
        )


if __name__ == "__main__":
    app = MusicVideoCreator()
    app.mainloop()
