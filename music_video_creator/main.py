import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import threading

from music_video_creator.app_state import AppState
from music_video_creator.services.video_generator import VideoGenerator
from music_video_creator.services.audio_transcriber import AudioTranscriber
from music_video_creator.services.lyric_file_loader import LyricFileLoader
from music_video_creator.services.lyric_aligner import LyricAligner
from music_video_creator.ui.summary_panel import SummaryPanel
from music_video_creator.ui.bottom_bar import BottomBar
from music_video_creator.ui.audio_section import AudioSection
from music_video_creator.ui.header_bar import HeaderBar
from music_video_creator.ui.main_layout import MainLayout
from music_video_creator.ui.main_notebook import MainNotebook

class MusicVideoCreator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Music Video Creator")
        self.geometry("1000x700")
        self.resizable(True, True)

        self.state = AppState()
        self.audio_transcriber = AudioTranscriber()
        self.lyric_file_loader = LyricFileLoader()
        self.lyric_aligner = LyricAligner()

        self._build_ui()

        self.video_generator = VideoGenerator(self.bottom_bar.set_status)

    # ─────────────────────────────────────────────────────────────
    # UI bootstrap
    # ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.header_bar = HeaderBar(self)
        self.main_layout = MainLayout(self)

        self._section_audio(self.main_layout.left)
        ttk.Separator(self.main_layout.left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        self._build_notebook(self.main_layout.left)
        self._panel_summary(self.main_layout.right)
        self._build_bottom_bar()

    # ─────────────────────────────────────────────────────────────
    # Audio section
    # ─────────────────────────────────────────────────────────────
    def _section_audio(self, parent):
        self.audio_section = AudioSection(
            parent,
            self._pick_audio,
            self._pick_lyrics,
            self._start_transcription
        )

    # ─────────────────────────────────────────────────────────────
    # Notebook
    # ─────────────────────────────────────────────────────────────
    def _build_notebook(self, parent):
        self.main_notebook = MainNotebook(parent)

        self.notebook = self.main_notebook.notebook
        self.tab_lyrics = self.main_notebook.lyrics_tab

        self._build_images_tab(self.main_notebook.images_tab)
        self._build_lyrics_tab(self.main_notebook.lyrics_tab)

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
        self.summary_panel = SummaryPanel(parent)


    def _build_bottom_bar(self):
        self.bottom_bar = BottomBar(self, self._generate_video)

    # ─────────────────────────────────────────────────────────────
    # Audio actions
    # ─────────────────────────────────────────────────────────────
    def _pick_audio(self):
        path = filedialog.askopenfilename(
            title="Select audio file",
            filetypes=[("Audio files", "*.mp3 *.wav *.aac *.ogg *.flac"), ("All files", "*.*")]
        )
        if path:
            self.state.audio_path = path
            name = os.path.basename(path)
            self.audio_section.set_audio_name(name)
            self.summary_panel.set_audio(name)
            self.bottom_bar.set_status(f"Audio loaded: {name}")
            self.audio_section.set_transcribe_enabled(True)

    def _pick_lyrics(self):
        """Load lyrics from text file and optionally align to audio"""
        if not self.state.audio_path:
            messagebox.showwarning("No Audio", "Please load an audio file first.")
            return

        path = filedialog.askopenfilename(
            title="Select Lyrics File",
            filetypes=[("Text files", "*.txt *.lrc"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            self.state.transcription_words = self.lyric_file_loader.load(path)

            if not self.state.transcription_words:
                messagebox.showwarning("Empty lyrics", "No words found in the file.")
                return

            self.state.switch_points = []
            self.bottom_bar.set_status(f"Loaded {len(self.state.transcription_words)} words from: {os.path.basename(path)}")
            self._render_lyrics()
            self.main_notebook.enable_lyrics_tab()
            self.main_notebook.select_lyrics_tab()
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
        if not self.state.audio_path:
            return
        self.audio_section.set_transcribe_enabled(False)
        self.audio_section.set_transcribe_text("Transcribing…")
        self.bottom_bar.set_progress(True)
        self.bottom_bar.set_status("Transcribing audio...")
        threading.Thread(target=self._run_transcription, daemon=True).start()

    def _run_transcription(self):
        try:
            self.after(0, lambda: self.bottom_bar.set_status("Loading Whisper model…"))
            words = self.audio_transcriber.transcribe(self.state.audio_path)
            self.after(0, self._on_transcription_done, words)

        except Exception as exc:
            self.after(0, self._on_transcription_error, str(exc))

    def _on_transcription_done(self, words):
        self.state.transcription_words = words
        self.state.switch_points = []
        self.bottom_bar.set_progress(False)
        self.audio_section.set_transcribe_enabled(True)
        self.audio_section.set_transcribe_text("🎤 Re-transcribe")
        self.bottom_bar.set_status(f"Transcription complete — {len(words)} words found.")
        self._render_lyrics()
        self.main_notebook.enable_lyrics_tab()
        self.main_notebook.select_lyrics_tab()
        self._update_switch_counter()

    def _on_transcription_error(self, msg):
        self.bottom_bar.set_progress(False)
        self.audio_section.set_transcribe_enabled(True)
        self.audio_section.set_transcribe_text("🎤 Transcribe Lyrics")
        self.bottom_bar.set_status("Transcription failed.")
        messagebox.showerror("Transcription failed", f"Error:\n\n{msg}")

    # ─────────────────────────────────────────────────────────────
    # Lyrics Alignment
    # ─────────────────────────────────────────────────────────────
    def _align_lyrics_to_audio(self):
        if not self.state.audio_path or not self.state.transcription_words:
            return
        self.bottom_bar.set_progress(True)
        self.bottom_bar.set_status("Aligning lyrics to audio...")
        threading.Thread(target=self._run_lyrics_alignment, daemon=True).start()

    def _run_lyrics_alignment(self):
        try:
            aligned_words = self.lyric_aligner.align(
                self.state.audio_path,
                self.state.transcription_words
            )
            self.after(0, self._on_alignment_done, aligned_words)

        except Exception as exc:
            self.after(0, lambda e=exc: messagebox.showerror("Alignment Failed", str(e)))
            self.after(0, self.bottom_bar.set_progress, False)

    def _on_alignment_done(self, aligned_words):
        self.state.transcription_words = aligned_words
        self.bottom_bar.set_progress(False)
        self._render_lyrics()
        self.bottom_bar.set_status(f"Lyrics aligned successfully — {len(aligned_words)} words")
        self._update_switch_counter()

    # ─────────────────────────────────────────────────────────────
    # Rest of the code (lyrics interaction, images, generation, etc.)
    # ─────────────────────────────────────────────────────────────
    def _render_lyrics(self):
        txt = self.lyrics_text
        txt.config(state=tk.NORMAL)
        txt.delete("1.0", tk.END)

        prev_end = -1
        for i, w in enumerate(self.state.transcription_words):
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
        ts  = self.state.transcription_words[idx]["start"]
        tag = f"w{idx}"

        if ts in self.state.switch_points:
            self.state.switch_points.remove(ts)
            self._set_word_style(tag, False)
        else:
            needed = max(0, len(self.state.image_entries) - 1)
            if needed > 0 and len(self.state.switch_points) >= needed:
                messagebox.showinfo("Enough load points", 
                    f"You already have {needed} load point(s). Remove one first.")
                return
            self.state.switch_points.append(ts)
            self.state.switch_points.sort()
            self._set_word_style(tag, True)

        self._update_switch_counter()
        self._apply_switch_points()

    def _hover_word(self, idx, entering):
        tag = f"w{idx}"
        txt = self.lyrics_text
        txt.config(state=tk.NORMAL)
        if entering and self.state.transcription_words[idx]["start"] not in self.state.switch_points:
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
        self.state.switch_points.clear()
        txt = self.lyrics_text
        txt.config(state=tk.NORMAL)
        txt.tag_remove("switch", "1.0", tk.END)
        txt.config(state=tk.DISABLED)
        self._update_switch_counter()
        self._apply_switch_points()

    def _apply_switch_points(self):
        pts = sorted(self.state.switch_points)
        for i, entry in enumerate(self.state.image_entries[1:]):
            if i < len(pts):
                entry["load_var"].set(round(pts[i], 2))
        self._refresh_summary()

    def _update_switch_counter(self):
        needed = max(0, len(self.state.image_entries) - 1)
        have   = len(self.state.switch_points)
        if needed == 0:
            msg = "Add images, then click words to set load times."
        elif have < needed:
            msg = f"Click {needed - have} more word(s) to set load times."
        elif have == needed:
            msg = f"✓ All load times set. Ready to generate!"
        else:
            msg = f"⚠ {have} points selected but only {needed} needed."
        self.counter_var.set(msg)
        self.summary_panel.set_points(have, needed)

    def _update_empty_label(self):
        for w in self.image_list_frame.winfo_children():
            if getattr(w, "_is_empty_label", False):
                w.destroy()
        if not self.state.image_entries:
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
        default_load = 3.0 * len(self.state.image_entries)
        entry = {"path": path, "load_var": tk.DoubleVar(value=default_load)}
        self.state.image_entries.append(entry)

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
            self.state.image_entries.remove(e)
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
        for i, entry in enumerate(self.state.image_entries):
            if i == 0:
                entry["load_inner"].pack_forget()
                entry["first_lbl"].pack()
            else:
                entry["first_lbl"].pack_forget()
                entry["load_inner"].pack()

    def _refresh_summary(self):
        self.summary_panel.set_images(len(self.state.image_entries))

    # Video generation methods (unchanged - _generate_video, _run_generation, etc.)
    def _generate_video(self):
        if self.state.generating:
            return
        if not self.state.audio_path:
            messagebox.showwarning("Missing audio", "Please select an audio file first.")
            return
        if not self.state.image_entries:
            messagebox.showwarning("No images", "Please add at least one image.")
            return

        if len(self.state.image_entries) > 1:
            load_times = [e["load_var"].get() for e in self.state.image_entries[1:]]
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

        self.summary_panel.set_output(os.path.basename(out_path))
        self.state.generating = True
        self.bottom_bar.set_generating(True)

        jobs = [(self.state.image_entries[0]["path"], None)]
        for e in self.state.image_entries[1:]:
            jobs.append((e["path"], e["load_var"].get()))

        threading.Thread(target=self._run_generation, args=(jobs, self.state.audio_path, out_path), daemon=True).start()

    def _run_generation(self, jobs, audio_path, out_path):
        try:
            self.video_generator.generate(jobs, audio_path, out_path)
            self.after(0, self._on_success, out_path)
        except Exception as exc:
            self.after(0, self._on_error, str(exc))

    def _on_success(self, out_path):
        self.state.generating = False
        self.bottom_bar.set_generating(False)
        self.bottom_bar.set_status(f"Done! Saved to: {out_path}")
        messagebox.showinfo("Success", f"Video saved to:\n\n{out_path}")

    def _on_error(self, message):
        self.state.generating = False
        self.bottom_bar.set_generating(False)
        self.bottom_bar.set_status("Generation failed.")
        messagebox.showerror("Error", message)

if __name__ == "__main__":
    app = MusicVideoCreator()
    app.mainloop()