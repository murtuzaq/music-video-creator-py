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

        self.transcription_words = []
        self.switch_points = []   # absolute timestamps selected in lyrics

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

        left = tk.Frame(content)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

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
            row, text="📄 Load Lyrics", command=self._pick_lyrics,
            bg="#9b59b6", fg="white", relief=tk.FLAT, padx=8
        ).pack(side=tk.RIGHT, padx=4)

        tk.Button(
            row, text="Browse…", command=self._pick_audio,
            bg="#4a90d9", fg="white", relief=tk.FLAT, padx=10
        ).pack(side=tk.RIGHT)

    # ─────────────────────────────────────────────────────────────
    # Notebook
    # ─────────────────────────────────────────────────────────────
    def _build_notebook(self, parent):
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        tab_images = tk.Frame(self.notebook)
        self.notebook.add(tab_images, text="  🖼  Images & Timing  ")
        self._build_images_tab(tab_images)

        self.tab_lyrics = tk.Frame(self.notebook)
        self.notebook.add(self.tab_lyrics, text="  🎤  Lyrics  ", state="disabled")
        self._build_lyrics_tab(self.tab_lyrics)

    # (rest of UI methods unchanged - _build_images_tab, _build_lyrics_tab, etc.)
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
            text='Image 1 always plays first. Each subsequent image has a "Load in" time (seconds into the audio).',
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

    def _build_lyrics_tab(self, parent):
        bar = tk.Frame(parent, bg="#2b2b2b", pady=4)
        bar.pack(fill=tk.X)

        self.counter_var = tk.StringVar(value="Load audio and click 'Transcribe Lyrics' or 'Load Lyrics' to begin.")
        tk.Label(bar, textvariable=self.counter_var, bg="#2b2b2b", fg="#ddd",
                 font=("Helvetica", 9)).pack(side=tk.LEFT, padx=10)

        tk.Button(
            bar, text="Clear all", command=self._clear_switch_points,
            bg="#555", fg="white", relief=tk.FLAT, padx=8
        ).pack(side=tk.RIGHT, padx=8)

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

        self.lyrics_text.tag_config("word",   foreground="#ddd",  font=("Helvetica", 13))
        self.lyrics_text.tag_config("switch", foreground="white", background="#c0671a",
                                    font=("Helvetica", 13, "bold"))
        self.lyrics_text.tag_config("hover",  foreground="white", background="#555")

    # ─────────────────────────────────────────────────────────────
    # Summary panel + Bottom bar (unchanged)
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

        self.sv_audio  = tk.StringVar(value="—")
        self.sv_images = tk.StringVar(value="0")
        self.sv_points = tk.StringVar(value="0 / 0")
        self.sv_output = tk.StringVar(value="—")

        row("Audio:",      self.sv_audio)
        row("Images:",     self.sv_images)
        row("Load points:", self.sv_points)
        row("Output:",     self.sv_output)

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

    def _pick_lyrics(self):
        """Load lyrics from text file and optionally align to audio"""
        if not self.audio_path:
            messagebox.showwarning("No Audio", "Please load an audio file first.")
            return

        path = filedialog.askopenfilename(
            title="Select Lyrics File",
            filetypes=[("Text files", "*.txt *.lrc"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()

            # Split into words
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            words = []
            for line in lines:
                for w in line.split():
                    clean = w.strip('.,!?()[]{}"\'').strip()
                    if clean:
                        words.append(clean)

            if not words:
                messagebox.showwarning("Empty lyrics", "No words found in the file.")
                return

            # Create placeholder transcription
            self.transcription_words = []
            current_time = 0.0
            for w in words:
                self.transcription_words.append({
                    "text": w,
                    "start": round(current_time, 2),
                    "end": round(current_time + 0.4, 2)
                })
                current_time += 0.5

            self.switch_points = []
            self._set_status(f"Loaded {len(words)} words from: {os.path.basename(path)}")
            self._render_lyrics()
            self.notebook.tab(self.tab_lyrics, state="normal")
            self.notebook.select(self.tab_lyrics)
            self._update_switch_counter()

            # Ask to align
            if messagebox.askyesno("Align Lyrics?", 
                "Lyrics loaded.\n\n"
                "Would you like to automatically align them to the audio for better timing?"):
                self._align_lyrics_to_audio()

        except Exception as e:
            messagebox.showerror("Lyrics Load Failed", str(e))

    # ─────────────────────────────────────────────────────────────
    # Transcription (original)
    # ─────────────────────────────────────────────────────────────
    def _start_transcription(self):
        if not self.audio_path:
            return
        self.transcribe_btn.config(state=tk.DISABLED, text="Transcribing…")
        self._set_progress(True)
        self._set_status("Transcribing audio...")
        threading.Thread(target=self._run_transcription, daemon=True).start()

    def _run_transcription(self):
        try:
            import shutil
            if not shutil.which("ffmpeg"):
                raise EnvironmentError("ffmpeg is not installed...")  # (same as before)

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

    # ─────────────────────────────────────────────────────────────
    # Lyrics Alignment
    # ─────────────────────────────────────────────────────────────
    def _align_lyrics_to_audio(self):
        if not self.audio_path or not self.transcription_words:
            return
        self._set_progress(True)
        self._set_status("Aligning lyrics to audio...")
        threading.Thread(target=self._run_lyrics_alignment, daemon=True).start()

    def _run_lyrics_alignment(self):
        try:
            import whisper
            model = whisper.load_model("base")
            
            result = model.transcribe(self.audio_path, word_timestamps=True)
            
            trans_words = []
            for seg in result.get("segments", []):
                for w in seg.get("words", []):
                    clean = w["word"].strip('.,!?')
                    if clean:
                        trans_words.append({
                            "text": clean.lower(),
                            "start": w["start"],
                            "end": w["end"]
                        })

            # Match provided lyrics to real transcription
            aligned = []
            t_idx = 0
            for orig in self.transcription_words:
                orig_lower = orig["text"].lower()
                best_match = None
                best_score = -1
                best_i = t_idx
                for i in range(t_idx, min(t_idx + 30, len(trans_words))):
                    score = self._word_similarity(orig_lower, trans_words[i]["text"])
                    if score > best_score:
                        best_score = score
                        best_match = trans_words[i]
                        best_i = i
                if best_match and best_score > 0.5:
                    aligned.append({
                        "text": orig["text"],
                        "start": best_match["start"],
                        "end": best_match["end"]
                    })
                    t_idx = best_i + 1
                else:
                    aligned.append(orig)  # fallback

            self.after(0, self._on_alignment_done, aligned)

        except Exception as exc:
            self.after(0, lambda e=exc: messagebox.showerror("Alignment Failed", str(e)))
            self.after(0, self._set_progress, False)

    def _word_similarity(self, a, b):
        if not a or not b:
            return 0.0
        set_a = set(a)
        set_b = set(b)
        return len(set_a & set_b) / max(len(set_a), len(set_b))

    def _on_alignment_done(self, aligned_words):
        self.transcription_words = aligned_words
        self._set_progress(False)
        self._render_lyrics()
        self._set_status(f"Lyrics aligned successfully — {len(aligned_words)} words")
        self._update_switch_counter()

    # ─────────────────────────────────────────────────────────────
    # Rest of the code (lyrics interaction, images, generation, etc.)
    # ─────────────────────────────────────────────────────────────
    def _render_lyrics(self):
        txt = self.lyrics_text
        txt.config(state=tk.NORMAL)
        txt.delete("1.0", tk.END)

        prev_end = -1
        for i, w in enumerate(self.transcription_words):
            if prev_end >= 0 and w["start"] - prev_end > 2.0:
                txt.insert(tk.END, "\n\n")

            tag_name = f"w{i}"
            txt.insert(tk.END, w["text"] + " ", ("word", tag_name))
            txt.tag_bind(tag_name, "<Button-1>", lambda e, idx=i: self._toggle_word(idx))
            txt.tag_bind(tag_name, "<Enter>",    lambda e, idx=i: self._hover_word(idx, True))
            txt.tag_bind(tag_name, "<Leave>",    lambda e, idx=i: self._hover_word(idx, False))
            prev_end = w["end"]

        txt.config(state=tk.DISABLED)

    def _toggle_word(self, idx):
        ts  = self.transcription_words[idx]["start"]
        tag = f"w{idx}"

        if ts in self.switch_points:
            self.switch_points.remove(ts)
            self._set_word_style(tag, False)
        else:
            needed = max(0, len(self.image_entries) - 1)
            if needed > 0 and len(self.switch_points) >= needed:
                messagebox.showinfo("Enough load points", 
                    f"You already have {needed} load point(s). Remove one first.")
                return
            self.switch_points.append(ts)
            self.switch_points.sort()
            self._set_word_style(tag, True)

        self._update_switch_counter()
        self._apply_switch_points()

    def _hover_word(self, idx, entering):
        tag = f"w{idx}"
        txt = self.lyrics_text
        txt.config(state=tk.NORMAL)
        if entering and self.transcription_words[idx]["start"] not in self.switch_points:
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

    def _clear_switch_points(self):
        self.switch_points.clear()
        txt = self.lyrics_text
        txt.config(state=tk.NORMAL)
        txt.tag_remove("switch", "1.0", tk.END)
        txt.config(state=tk.DISABLED)
        self._update_switch_counter()
        self._apply_switch_points()

    def _apply_switch_points(self):
        pts = sorted(self.switch_points)
        for i, entry in enumerate(self.image_entries[1:]):
            if i < len(pts):
                entry["load_var"].set(round(pts[i], 2))
        self._refresh_summary()

    def _update_switch_counter(self):
        needed = max(0, len(self.image_entries) - 1)
        have   = len(self.switch_points)
        if needed == 0:
            msg = "Add images, then click words to set load times."
        elif have < needed:
            msg = f"Click {needed - have} more word(s) to set load times."
        elif have == needed:
            msg = f"✓ All load times set. Ready to generate!"
        else:
            msg = f"⚠ {have} points selected but only {needed} needed."
        self.counter_var.set(msg)
        self.sv_points.set(f"{have} / {needed}")

    def _update_empty_label(self):
        for w in self.image_list_frame.winfo_children():
            if getattr(w, "_is_empty_label", False):
                w.destroy()
        if not self.image_entries:
            lbl = tk.Label(self.image_list_frame, text='Click "+ Add Image" to add images.', fg="gray", pady=20)
            lbl._is_empty_label = True
            lbl.pack()

    def _add_image(self):
        paths = filedialog.askopenfilenames(
            title="Select image(s)",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")]
        )
        for path in paths:
            self._add_image_row(path)
        self._refresh_first_row()
        self._refresh_summary()
        self._update_switch_counter()

    def _add_image_row(self, path):
        default_load = 3.0 * len(self.image_entries)
        entry = {"path": path, "load_var": tk.DoubleVar(value=default_load)}
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
            self._refresh_first_row()
            self._refresh_summary()
            self._update_switch_counter()

        tk.Button(row, text="✕", command=remove, fg="red", relief=tk.FLAT, padx=4).pack(side=tk.RIGHT)

        timing_frame = tk.Frame(row)
        timing_frame.pack(side=tk.RIGHT, padx=(8, 4))
        entry["timing_frame"] = timing_frame

        first_lbl = tk.Label(timing_frame, text="Plays first", fg="#5cb85c", font=("Helvetica", 9, "italic"))
        entry["first_lbl"] = first_lbl

        load_inner = tk.Frame(timing_frame)
        entry["load_inner"] = load_inner
        tk.Label(load_inner, text="Load in:").pack(side=tk.LEFT)
        spin = ttk.Spinbox(load_inner, from_=0.1, to=7200, increment=0.5,
                           textvariable=entry["load_var"], width=7, command=self._refresh_summary)
        spin.pack(side=tk.LEFT, padx=(4, 2))
        tk.Label(load_inner, text="s").pack(side=tk.LEFT)
        entry["spin"] = spin

        self._update_empty_label()

    def _refresh_first_row(self):
        for i, entry in enumerate(self.image_entries):
            if i == 0:
                entry["load_inner"].pack_forget()
                entry["first_lbl"].pack()
            else:
                entry["first_lbl"].pack_forget()
                entry["load_inner"].pack()

    def _refresh_summary(self):
        self.sv_images.set(str(len(self.image_entries)))

    # Video generation methods (unchanged - _generate_video, _run_generation, etc.)
    def _generate_video(self):
        if self._generating:
            return
        if not self.audio_path:
            messagebox.showwarning("Missing audio", "Please select an audio file first.")
            return
        if not self.image_entries:
            messagebox.showwarning("No images", "Please add at least one image.")
            return

        if len(self.image_entries) > 1:
            load_times = [e["load_var"].get() for e in self.image_entries[1:]]
            for i in range(1, len(load_times)):
                if load_times[i] <= load_times[i - 1]:
                    messagebox.showerror("Invalid load times", 
                        f"Image {i+2} load time must be after previous image.")
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

        jobs = [(self.image_entries[0]["path"], None)]
        for e in self.image_entries[1:]:
            jobs.append((e["path"], e["load_var"].get()))

        threading.Thread(target=self._run_generation, args=(jobs, self.audio_path, out_path), daemon=True).start()

    def _run_generation(self, jobs, audio_path, out_path):
        try:
            from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
            audio = AudioFileClip(audio_path)
            audio_duration = audio.duration

            load_times = [0.0] + [lt for _, lt in jobs[1:]]
            if load_times[-1] >= audio_duration:
                raise ValueError("Last image load time is after audio end.")

            durations = []
            for i in range(len(load_times)):
                if i < len(load_times) - 1:
                    durations.append(load_times[i + 1] - load_times[i])
                else:
                    durations.append(audio_duration - load_times[i])

            clips = []
            for i, ((img_path, _), duration) in enumerate(zip(jobs, durations), 1):
                self._set_status(f"Processing image {i}/{len(jobs)}...")
                clip = ImageClip(img_path, duration=duration).with_fps(24)
                clips.append(clip)

            video = concatenate_videoclips(clips, method="compose")
            if audio.duration > video.duration:
                audio = audio.subclipped(0, video.duration)
            video = video.with_audio(audio)

            self._set_status("Rendering video...")
            video.write_videofile(out_path, codec="libx264", audio_codec="aac", fps=24, logger=None)

            self.after(0, self._on_success, out_path)

        except Exception as exc:
            self.after(0, self._on_error, str(exc))

    def _on_success(self, out_path):
        self._set_generating(False)
        self._set_status(f"Done! Saved to: {out_path}")
        messagebox.showinfo("Success", f"Video saved to:\n\n{out_path}")

    def _on_error(self, message):
        self._set_generating(False)
        self._set_status("Generation failed.")
        messagebox.showerror("Error", message)

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