import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import threading


class MusicVideoCreator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Music Video Creator")
        self.geometry("900x650")
        self.resizable(True, True)

        self.audio_path = None
        self.image_entries = []
        self._generating = False

        self._build_ui()

    def _build_ui(self):
        top = tk.Frame(self, bg="#2b2b2b", pady=8)
        top.pack(fill=tk.X)
        tk.Label(
            top, text="🎬 Music Video Creator",
            font=("Helvetica", 16, "bold"),
            bg="#2b2b2b", fg="white"
        ).pack(side=tk.LEFT, padx=16)

        content = tk.Frame(self)
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.Frame(content, width=560)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left.pack_propagate(False)

        right = tk.Frame(content, width=300, bg="#1e1e1e", relief=tk.SUNKEN, bd=1)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        self._section_audio(left)
        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        self._section_images(left)
        self._panel_summary(right)
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

        # Small help text
        tk.Label(
            parent,
            text='"Switch after" = seconds before the next image appears. The last image plays until the audio ends.',
            fg="#888", font=("Helvetica", 8), anchor="w"
        ).pack(fill=tk.X, pady=(2, 4))

        container = tk.Frame(parent, relief=tk.SUNKEN, bd=1)
        container.pack(fill=tk.BOTH, expand=True)

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
                text='Click "+ Add Image" to add images.',
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

        self.sv_audio    = tk.StringVar(value="—")
        self.sv_images   = tk.StringVar(value="0")
        self.sv_timed    = tk.StringVar(value="0 s timed")
        self.sv_output   = tk.StringVar(value="—")

        row("Audio:", self.sv_audio)
        row("Images:", self.sv_images)
        row("Timed slides:", self.sv_timed)
        row("Output:", self.sv_output)

    # ── Bottom bar ───────────────────────────────────────────────
    def _build_bottom_bar(self):
        bar = tk.Frame(self, bg="#2b2b2b", pady=6)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=200)
        self.progress.pack(side=tk.LEFT, padx=16, pady=4)
        self.progress.pack_forget()

        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(bar, textvariable=self.status_var, bg="#2b2b2b", fg="#aaa").pack(side=tk.LEFT, padx=16)

        self.generate_btn = tk.Button(
            bar, text="▶  Generate Video",
            command=self._generate_video,
            bg="#e05c00", fg="white", font=("Helvetica", 11, "bold"),
            relief=tk.FLAT, padx=16, pady=4
        )
        self.generate_btn.pack(side=tk.RIGHT, padx=16)

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
        self._refresh_last_row()
        self._refresh_summary()

    def _add_image_row(self, path):
        entry = {"path": path, "switch_var": tk.DoubleVar(value=3.0)}
        self.image_entries.append(entry)

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
        tk.Label(row, text=name, anchor="w", wraplength=220).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Remove button (far right)
        def remove(e=entry, r=row):
            self.image_entries.remove(e)
            r.destroy()
            self._update_empty_label()
            self._refresh_last_row()
            self._refresh_summary()

        tk.Button(row, text="✕", command=remove, fg="red", relief=tk.FLAT, padx=4).pack(side=tk.RIGHT)

        # Timing controls — stored so we can show/hide them
        timing_frame = tk.Frame(row)
        timing_frame.pack(side=tk.RIGHT, padx=(8, 4))
        entry["timing_frame"] = timing_frame

        # "Switch after" label + spinbox
        switch_inner = tk.Frame(timing_frame)
        switch_inner.pack()
        entry["switch_inner"] = switch_inner

        tk.Label(switch_inner, text="Switch after (s):").pack(side=tk.LEFT)
        spin = ttk.Spinbox(
            switch_inner, from_=0.5, to=3600, increment=0.5,
            textvariable=entry["switch_var"], width=6,
            command=self._refresh_summary
        )
        spin.pack(side=tk.LEFT)
        entry["spin"] = spin

        # "Until end" label (hidden by default, shown only for last image)
        until_lbl = tk.Label(timing_frame, text="Until end of audio", fg="#5cb85c", font=("Helvetica", 9, "italic"))
        entry["until_lbl"] = until_lbl

        self._update_empty_label()

    def _refresh_last_row(self):
        """Show spinbox for all rows except the last; last shows 'Until end of audio'."""
        for i, entry in enumerate(self.image_entries):
            is_last = (i == len(self.image_entries) - 1)
            if is_last:
                entry["switch_inner"].pack_forget()
                entry["until_lbl"].pack()
            else:
                entry["until_lbl"].pack_forget()
                entry["switch_inner"].pack()

    def _refresh_summary(self):
        # All switch times except the last image (last plays until audio ends)
        timed = sum(
            e["switch_var"].get()
            for e in self.image_entries[:-1]
        ) if self.image_entries else 0

        self.sv_images.set(str(len(self.image_entries)))
        if self.image_entries:
            self.sv_timed.set(f"{timed:.1f} s + last until end")
        else:
            self.sv_timed.set("0 s")

    # ── Video generation ─────────────────────────────────────────
    def _generate_video(self):
        if self._generating:
            return

        if not self.audio_path:
            messagebox.showwarning("Missing audio", "Please select an audio file first.")
            return
        if not self.image_entries:
            messagebox.showwarning("No images", "Please add at least one image.")
            return

        out_path = filedialog.asksaveasfilename(
            title="Save video as…",
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4")]
        )
        if not out_path:
            return

        self.sv_output.set(os.path.basename(out_path))
        self._set_generating(True)

        # Snapshot: list of (img_path, switch_after) — switch_after is None for the last image
        jobs = []
        for i, e in enumerate(self.image_entries):
            switch = e["switch_var"].get() if i < len(self.image_entries) - 1 else None
            jobs.append((e["path"], switch))

        thread = threading.Thread(
            target=self._run_generation,
            args=(jobs, self.audio_path, out_path),
            daemon=True
        )
        thread.start()

    def _run_generation(self, jobs, audio_path, out_path):
        try:
            self._set_status("Importing MoviePy…")
            from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

            # Load audio first so we know the total duration
            self._set_status("Loading audio…")
            audio = AudioFileClip(audio_path)
            audio_duration = audio.duration

            # Calculate durations
            # All images except last use their switch_after value as duration.
            # Last image gets whatever is left.
            timed_total = sum(switch for _, switch in jobs[:-1]) if len(jobs) > 1 else 0
            last_duration = audio_duration - timed_total

            if last_duration <= 0:
                raise ValueError(
                    f"Your 'switch after' times total {timed_total:.1f}s, "
                    f"but the audio is only {audio_duration:.1f}s long. "
                    f"Reduce the switch times so there is time left for the last image."
                )

            clips = []
            total = len(jobs)
            for i, (img_path, switch) in enumerate(jobs, 1):
                self._set_status(f"Processing image {i} of {total}…")
                duration = switch if switch is not None else last_duration
                clip = ImageClip(img_path, duration=duration).with_fps(24)
                clips.append(clip)

            self._set_status("Joining clips…")
            video = concatenate_videoclips(clips, method="compose")

            # Trim audio to exact video length (they should match, but just in case)
            if audio.duration > video.duration:
                audio = audio.subclipped(0, video.duration)

            video = video.with_audio(audio)

            self._set_status("Rendering video — this may take a moment…")
            video.write_videofile(
                out_path,
                codec="libx264",
                audio_codec="aac",
                fps=24,
                logger=None
            )

            video.close()
            audio.close()
            for c in clips:
                c.close()

            self.after(0, self._on_success, out_path)

        except Exception as exc:
            self.after(0, self._on_error, str(exc))

    def _on_success(self, out_path):
        self._set_generating(False)
        self._set_status(f"Done! Saved to: {out_path}")
        messagebox.showinfo("Video created!", f"Your music video was saved to:\n\n{out_path}")

    def _on_error(self, message):
        self._set_generating(False)
        self._set_status("Error during generation.")
        messagebox.showerror("Generation failed", f"Something went wrong:\n\n{message}")

    # ── Helpers ──────────────────────────────────────────────────
    def _set_generating(self, state: bool):
        self._generating = state
        if state:
            self.generate_btn.config(state=tk.DISABLED, text="Generating…")
            self.progress.pack(side=tk.LEFT, padx=16, pady=4)
            self.progress.start(12)
        else:
            self.generate_btn.config(state=tk.NORMAL, text="▶  Generate Video")
            self.progress.stop()
            self.progress.pack_forget()

    def _set_status(self, msg: str):
        self.after(0, lambda: self.status_var.set(msg))


if __name__ == "__main__":
    app = MusicVideoCreator()
    app.mainloop()
