import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import threading


class MusicVideoCreator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Music Video Creator")
        self.geometry("1000x700")
        self.resizable(True, True)

        self.audio_path = None
        self.image_entries = []
        self._generating = False

        # Lyrics / transcription state
        self.transcription_words = []   # [{text, start, end}, ...]
        self.switch_points = []         # sorted list of selected start timestamps

        self._build_ui()

    # ─────────────────────────────────────────────────────────────
    # UI bootstrap
    # ─────────────────────────────────────────────────────────────
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

        # Left: tabbed panel
        left = tk.Frame(content)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right: summary
        right = tk.Frame(content, width=260, bg="#1e1e1e", relief=tk.SUNKEN, bd=1)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        self._section_audio(left)
        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        self._build_notebook(left)
        self._panel_summary(right)
        self._build_bottom_bar()

    # ─────────────────────────────────────────────────────────────
    # Audio section
    # ─────────────────────────────────────────────────────────────
    def _section_audio(self, parent):
        frame = tk.LabelFrame(parent, text=" 1. Audio File ", font=("Helvetica", 10, "bold"), padx=8, pady=6)
        frame.pack(fill=tk.X)

        row = tk.Frame(frame)
        row.pack(fill=tk.X)

        self.audio_label = tk.Label(row, text="No file selected", fg="gray", anchor="w")
        self.audio_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.transcribe_btn = tk.Button(
            row, text="🎤 Transcribe Lyrics", command=self._start_transcription,
            bg="#7b5ea7", fg="white", relief=tk.FLAT, padx=8, state=tk.DISABLED
        )
        self.transcribe_btn.pack(side=tk.RIGHT, padx=(4, 0))

        tk.Button(
            row, text="Browse…", command=self._pick_audio,
            bg="#4a90d9", fg="white", relief=tk.FLAT, padx=10
        ).pack(side=tk.RIGHT)

    # ─────────────────────────────────────────────────────────────
    # Tabbed notebook: Images | Lyrics
    # ─────────────────────────────────────────────────────────────
    def _build_notebook(self, parent):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1 — Images & Timing
        tab_images = tk.Frame(self.notebook)
        self.notebook.add(tab_images, text="  🖼  Images & Timing  ")
        self._build_images_tab(tab_images)

        # Tab 2 — Lyrics (locked until transcription)
        self.tab_lyrics = tk.Frame(self.notebook)
        self.notebook.add(self.tab_lyrics, text="  🎤  Lyrics  ", state="disabled")
        self._build_lyrics_tab(self.tab_lyrics)

    # ── Images tab ───────────────────────────────────────────────
    def _build_images_tab(self, parent):
        header = tk.Frame(parent)
        header.pack(fill=tk.X, pady=(6, 2))

        tk.Label(header, text=" 2. Images & Timing", font=("Helvetica", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(
            header, text="+ Add Image", command=self._add_image,
            bg="#5cb85c", fg="white", relief=tk.FLAT, padx=8
        ).pack(side=tk.RIGHT)

        tk.Label(
            parent,
            text='"Switch after" = seconds until next image. Last image plays until audio ends.',
            fg="#888", font=("Helvetica", 8), anchor="w"
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

        self._update_empty_label()

    # ── Lyrics tab ───────────────────────────────────────────────
    def _build_lyrics_tab(self, parent):
        # Counter / instruction bar
        bar = tk.Frame(parent, bg="#2b2b2b", pady=4)
        bar.pack(fill=tk.X)

        self.counter_var = tk.StringVar(value="Load audio and click 'Transcribe Lyrics' to begin.")
        tk.Label(bar, textvariable=self.counter_var, bg="#2b2b2b", fg="#ddd",
                 font=("Helvetica", 9)).pack(side=tk.LEFT, padx=10)

        tk.Button(
            bar, text="Clear all switch points", command=self._clear_switch_points,
            bg="#555", fg="white", relief=tk.FLAT, padx=8
        ).pack(side=tk.RIGHT, padx=8)

        # Word display area
        text_frame = tk.Frame(parent)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        self.lyrics_text = tk.Text(
            text_frame, wrap=tk.WORD, font=("Helvetica", 13),
            cursor="arrow", state=tk.DISABLED,
            padx=12, pady=10, spacing1=4, spacing3=4
        )
        lscroll = ttk.Scrollbar(text_frame, command=self.lyrics_text.yview)
        self.lyrics_text.configure(yscrollcommand=lscroll.set)
        self.lyrics_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lscroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Text widget tags
        self.lyrics_text.tag_config("word",   foreground="#ddd",    font=("Helvetica", 13))
        self.lyrics_text.tag_config("switch", foreground="white",   background="#c0671a",
                                    font=("Helvetica", 13, "bold"))
        self.lyrics_text.tag_config("hover",  foreground="white",   background="#555")

        self.lyrics_text.tag_bind("word",   "<Button-1>",    self._on_word_click)
        self.lyrics_text.tag_bind("switch", "<Button-1>",    self._on_word_click)
        self.lyrics_text.tag_bind("word",   "<Enter>",       lambda e: self._word_hover(e, True))
        self.lyrics_text.tag_bind("word",   "<Leave>",       lambda e: self._word_hover(e, False))
        self.lyrics_text.tag_bind("switch", "<Enter>",       lambda e: self._word_hover(e, True))
        self.lyrics_text.tag_bind("switch", "<Leave>",       lambda e: self._word_hover(e, False))

    # ─────────────────────────────────────────────────────────────
    # Summary panel
    # ─────────────────────────────────────────────────────────────
    def _panel_summary(self, parent):
        tk.Label(parent, text="Summary", font=("Helvetica", 11, "bold"),
                 bg="#1e1e1e", fg="white").pack(pady=(14, 6))
        ttk.Separator(parent, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10)

        info = tk.Frame(parent, bg="#1e1e1e")
        info.pack(fill=tk.X, padx=14, pady=10)

        def row(label, var):
            f = tk.Frame(info, bg="#1e1e1e")
            f.pack(fill=tk.X, pady=2)
            tk.Label(f, text=label, bg="#1e1e1e", fg="#aaa", anchor="w", width=12).pack(side=tk.LEFT)
            tk.Label(f, textvariable=var, bg="#1e1e1e", fg="white", anchor="w",
                     wraplength=140, justify=tk.LEFT).pack(side=tk.LEFT)

        self.sv_audio   = tk.StringVar(value="—")
        self.sv_images  = tk.StringVar(value="0")
        self.sv_timed   = tk.StringVar(value="0 s")
        self.sv_points  = tk.StringVar(value="0")
        self.sv_output  = tk.StringVar(value="—")

        row("Audio:",        self.sv_audio)
        row("Images:",       self.sv_images)
        row("Timed slides:", self.sv_timed)
        row("Switch pts:",   self.sv_points)
        row("Output:",       self.sv_output)

    # ─────────────────────────────────────────────────────────────
    # Bottom bar
    # ─────────────────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────────────────
    # Audio actions
    # ─────────────────────────────────────────────────────────────
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
            self.transcribe_btn.config(state=tk.NORMAL)

    # ─────────────────────────────────────────────────────────────
    # Transcription
    # ─────────────────────────────────────────────────────────────
    def _start_transcription(self):
        if not self.audio_path:
            return
        self.transcribe_btn.config(state=tk.DISABLED, text="Transcribing…")
        self._set_progress(True)
        self._set_status("Transcribing audio (this may take a minute the first time)…")
        thread = threading.Thread(target=self._run_transcription, daemon=True)
        thread.start()

    def _run_transcription(self):
        try:
            import whisper
            self.after(0, lambda: self._set_status("Loading Whisper model…"))
            model = whisper.load_model("base")
            self.after(0, lambda: self._set_status("Transcribing…"))
            result = model.transcribe(self.audio_path, word_timestamps=True)

            words = []
            for seg in result.get("segments", []):
                for w in seg.get("words", []):
                    clean = w["word"].strip()
                    if clean:
                        words.append({"text": clean, "start": w["start"], "end": w["end"]})

            self.after(0, self._on_transcription_done, words)
        except Exception as exc:
            self.after(0, self._on_transcription_error, str(exc))

    def _on_transcription_done(self, words):
        self.transcription_words = words
        self.switch_points = []
        self._set_progress(False)
        self.transcribe_btn.config(state=tk.NORMAL, text="🎤 Re-transcribe")
        self._set_status(f"Transcription complete — {len(words)} words found.")
        self._render_lyrics()
        self.notebook.tab(self.tab_lyrics, state="normal")
        self.notebook.select(self.tab_lyrics)
        self._update_switch_counter()

    def _on_transcription_error(self, msg):
        self._set_progress(False)
        self.transcribe_btn.config(state=tk.NORMAL, text="🎤 Transcribe Lyrics")
        self._set_status("Transcription failed.")
        messagebox.showerror("Transcription failed", f"Error:\n\n{msg}")

    def _render_lyrics(self):
        txt = self.lyrics_text
        txt.config(state=tk.NORMAL)
        txt.delete("1.0", tk.END)

        prev_end = -1
        for i, w in enumerate(self.transcription_words):
            # Add a newline for noticeable gaps (> 2 s silence)
            if prev_end >= 0 and w["start"] - prev_end > 2.0:
                txt.insert(tk.END, "\n\n")

            tag_name = f"w{i}"
            display = w["text"] + " "
            txt.insert(tk.END, display, ("word", tag_name))
            txt.tag_bind(tag_name, "<Button-1>", lambda e, idx=i: self._toggle_word(idx))
            txt.tag_bind(tag_name, "<Enter>",    lambda e, idx=i: self._hover_word(idx, True))
            txt.tag_bind(tag_name, "<Leave>",    lambda e, idx=i: self._hover_word(idx, False))
            prev_end = w["end"]

        txt.config(state=tk.DISABLED)

    # ─────────────────────────────────────────────────────────────
    # Word click / hover
    # ─────────────────────────────────────────────────────────────
    def _toggle_word(self, idx):
        w = self.transcription_words[idx]
        ts = w["start"]
        tag = f"w{idx}"

        if ts in self.switch_points:
            self.switch_points.remove(ts)
            self._set_word_style(tag, selected=False)
        else:
            needed = max(0, len(self.image_entries) - 1)
            if needed > 0 and len(self.switch_points) >= needed:
                messagebox.showinfo(
                    "Enough switch points",
                    f"You already have {needed} switch point(s) — one per image transition.\n"
                    "Remove one first, or add more images."
                )
                return
            self.switch_points.append(ts)
            self.switch_points.sort()
            self._set_word_style(tag, selected=True)

        self._update_switch_counter()
        self._apply_switch_points()

    def _hover_word(self, idx, entering):
        tag = f"w{idx}"
        ts = self.transcription_words[idx]["start"]
        is_selected = ts in self.switch_points

        txt = self.lyrics_text
        txt.config(state=tk.NORMAL)
        if entering and not is_selected:
            txt.tag_add("hover", f"{tag}.first", f"{tag}.last")
        else:
            txt.tag_remove("hover", "1.0", tk.END)
        txt.config(state=tk.DISABLED)

    def _set_word_style(self, tag, selected):
        txt = self.lyrics_text
        txt.config(state=tk.NORMAL)
        if selected:
            txt.tag_add("switch", f"{tag}.first", f"{tag}.last")
        else:
            txt.tag_remove("switch", f"{tag}.first", f"{tag}.last")
        txt.config(state=tk.DISABLED)

    # These generic tag binds exist as fallback but individual w# tags handle clicks
    def _on_word_click(self, event): pass
    def _word_hover(self, event, entering): pass

    def _clear_switch_points(self):
        self.switch_points.clear()
        txt = self.lyrics_text
        txt.config(state=tk.NORMAL)
        txt.tag_remove("switch", "1.0", tk.END)
        txt.config(state=tk.DISABLED)
        self._update_switch_counter()
        self._apply_switch_points()

    # ─────────────────────────────────────────────────────────────
    # Apply switch points → image switch_vars
    # ─────────────────────────────────────────────────────────────
    def _apply_switch_points(self):
        """Convert selected word timestamps into 'switch after' values for each image."""
        pts = sorted(self.switch_points)
        prev = 0.0
        for i, entry in enumerate(self.image_entries[:-1]):  # skip last image
            if i < len(pts):
                entry["switch_var"].set(round(pts[i] - prev, 2))
                prev = pts[i]
        self._refresh_summary()

    def _update_switch_counter(self):
        needed = max(0, len(self.image_entries) - 1)
        have   = len(self.switch_points)
        if needed == 0:
            msg = "Add images in the Images tab, then click words here to set switch points."
        elif have < needed:
            remaining = needed - have
            msg = f"Click {remaining} more word(s) to set all {needed} switch point(s)."
        elif have == needed:
            msg = f"✓ All {needed} switch point(s) set. Ready to generate!"
        else:
            msg = f"⚠ {have} switch points selected but only {needed} needed. Remove some."
        self.counter_var.set(msg)
        self.sv_points.set(f"{have} / {needed}")

    # ─────────────────────────────────────────────────────────────
    # Image list actions
    # ─────────────────────────────────────────────────────────────
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

    def _add_image(self):
        paths = filedialog.askopenfilenames(
            title="Select image(s)",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]
        )
        for path in paths:
            self._add_image_row(path)
        self._refresh_last_row()
        self._refresh_summary()
        self._update_switch_counter()

    def _add_image_row(self, path):
        entry = {"path": path, "switch_var": tk.DoubleVar(value=3.0)}
        self.image_entries.append(entry)

        row = tk.Frame(self.image_list_frame, relief=tk.RIDGE, bd=1, padx=6, pady=4)
        row.pack(fill=tk.X, padx=4, pady=2)
        entry["row_widget"] = row

        try:
            img = Image.open(path)
            img.thumbnail((48, 48))
            photo = ImageTk.PhotoImage(img)
            entry["photo"] = photo
            tk.Label(row, image=photo).pack(side=tk.LEFT, padx=(0, 8))
        except Exception:
            tk.Label(row, text="[img]", width=6).pack(side=tk.LEFT)

        name = os.path.basename(path)
        tk.Label(row, text=name, anchor="w", wraplength=220).pack(side=tk.LEFT, fill=tk.X, expand=True)

        def remove(e=entry, r=row):
            self.image_entries.remove(e)
            r.destroy()
            self._update_empty_label()
            self._refresh_last_row()
            self._refresh_summary()
            self._update_switch_counter()

        tk.Button(row, text="✕", command=remove, fg="red", relief=tk.FLAT, padx=4).pack(side=tk.RIGHT)

        timing_frame = tk.Frame(row)
        timing_frame.pack(side=tk.RIGHT, padx=(8, 4))
        entry["timing_frame"] = timing_frame

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

        until_lbl = tk.Label(timing_frame, text="Until end of audio",
                             fg="#5cb85c", font=("Helvetica", 9, "italic"))
        entry["until_lbl"] = until_lbl

        self._update_empty_label()

    def _refresh_last_row(self):
        for i, entry in enumerate(self.image_entries):
            is_last = (i == len(self.image_entries) - 1)
            if is_last:
                entry["switch_inner"].pack_forget()
                entry["until_lbl"].pack()
            else:
                entry["until_lbl"].pack_forget()
                entry["switch_inner"].pack()

    def _refresh_summary(self):
        timed = sum(
            e["switch_var"].get() for e in self.image_entries[:-1]
        ) if self.image_entries else 0
        self.sv_images.set(str(len(self.image_entries)))
        if self.image_entries:
            self.sv_timed.set(f"{timed:.1f} s + last until end")
        else:
            self.sv_timed.set("0 s")

    # ─────────────────────────────────────────────────────────────
    # Video generation
    # ─────────────────────────────────────────────────────────────
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

            self._set_status("Loading audio…")
            audio = AudioFileClip(audio_path)
            audio_duration = audio.duration

            timed_total = sum(s for _, s in jobs[:-1]) if len(jobs) > 1 else 0
            last_duration = audio_duration - timed_total

            if last_duration <= 0:
                raise ValueError(
                    f"Switch times total {timed_total:.1f}s but audio is only "
                    f"{audio_duration:.1f}s. Reduce switch times."
                )

            clips = []
            for i, (img_path, switch) in enumerate(jobs, 1):
                self._set_status(f"Processing image {i} of {len(jobs)}…")
                duration = switch if switch is not None else last_duration
                clip = ImageClip(img_path, duration=duration).with_fps(24)
                clips.append(clip)

            self._set_status("Joining clips…")
            video = concatenate_videoclips(clips, method="compose")

            if audio.duration > video.duration:
                audio = audio.subclipped(0, video.duration)

            video = video.with_audio(audio)

            self._set_status("Rendering — this may take a moment…")
            video.write_videofile(
                out_path, codec="libx264", audio_codec="aac", fps=24, logger=None
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

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────
    def _set_generating(self, state: bool):
        self._generating = state
        if state:
            self.generate_btn.config(state=tk.DISABLED, text="Generating…")
            self._set_progress(True)
        else:
            self.generate_btn.config(state=tk.NORMAL, text="▶  Generate Video")
            self._set_progress(False)

    def _set_progress(self, running: bool):
        if running:
            self.progress.pack(side=tk.LEFT, padx=16, pady=4)
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.pack_forget()

    def _set_status(self, msg: str):
        self.after(0, lambda: self.status_var.set(msg))


if __name__ == "__main__":
    app = MusicVideoCreator()
    app.mainloop()
