import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading

from music_video_creator.app_state import AppState
from music_video_creator.project import new_project, save_project, load_project, VPROJ_EXTENSION
from music_video_creator.services.video_generator import VideoGenerator
from music_video_creator.services.audio_transcriber import AudioTranscriber
from music_video_creator.services.lyric_file_loader import LyricFileLoader
from music_video_creator.services.lyric_aligner import LyricAligner
from music_video_creator.ui.menu_bar import MenuBar
from music_video_creator.ui.ribbon_bar import RibbonBar
from music_video_creator.ui.summary_panel import SummaryPanel
from music_video_creator.ui.bottom_bar import BottomBar
from music_video_creator.ui.audio_section import AudioSection
from music_video_creator.ui.header_bar import HeaderBar
from music_video_creator.ui.main_layout import MainLayout
from music_video_creator.ui.main_notebook import MainNotebook
from music_video_creator.ui.lyrics_tab import LyricsTab
from music_video_creator.ui.image_timing_tab import ImageTimingTab
from music_video_creator.ui.image_list import ImageList
from music_video_creator.ui.lyrics_controller import LyricsController

class MusicVideoCreator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Music Video Creator")
        self.geometry("1000x700")
        self.resizable(True, True)

        self.state = AppState()
        self._project_path = None

        self.audio_transcriber = AudioTranscriber()
        self.lyric_file_loader = LyricFileLoader()
        self.lyric_aligner = LyricAligner()

        self._build_ui()
        self._bind_shortcuts()

        self.video_generator = VideoGenerator(self.bottom_bar.set_status)

    # ─────────────────────────────────────────────────────────────
    # UI bootstrap
    # ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        callbacks = {
            "new":  self._new_project,
            "open": self._load_project,
            "save": self._save_project,
            "exit": self.destroy,
        }
        MenuBar(self, callbacks)
        self.ribbon_bar = RibbonBar(self, callbacks)
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
        self.image_timing_tab = ImageTimingTab(parent, self._add_image)
        self.image_list_frame = self.image_timing_tab.get_image_list_frame()

        self.image_list = ImageList(
            self.image_list_frame,
            self.state,
            self._on_image_list_changed
        )

    def _build_lyrics_tab(self, parent):
        self.lyrics_tab = LyricsTab(parent, self._clear_switch_points)
        self.lyrics_controller = LyricsController(
            self.lyrics_tab,
            self.state,
            self._on_lyrics_changed
        )

    def _on_lyrics_changed(self):
        self._update_switch_counter()
        self._refresh_summary()

    def _on_image_list_changed(self):
        self._refresh_summary()
        self._update_switch_counter()
        self._update_generate_button()

    # ─────────────────────────────────────────────────────────────
    # Summary panel + Bottom bar (unchanged)
    # ─────────────────────────────────────────────────────────────
    def _panel_summary(self, parent):
        self.summary_panel = SummaryPanel(parent, self._generate_video)


    def _build_bottom_bar(self):
        self.bottom_bar = BottomBar(self)

    def _update_generate_button(self):
        has_audio = self.state.audio_path is not None
        has_images = len(self.state.image_entries) > 0

        needed_points = max(0, len(self.state.image_entries) - 1)
        has_points = len(self.state.switch_points) == needed_points

        ready = has_audio and has_images and has_points and self.state.generating == False

        self.summary_panel.set_generate_enabled(ready)

    # ─────────────────────────────────────────────────────────────
    # Keyboard shortcuts
    # ─────────────────────────────────────────────────────────────
    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda _: self._new_project())
        self.bind("<Control-o>", lambda _: self._load_project())
        self.bind("<Control-s>", lambda _: self._save_project())

    # ─────────────────────────────────────────────────────────────
    # Project actions
    # ─────────────────────────────────────────────────────────────
    def _update_title(self):
        if self._project_path:
            name = os.path.basename(self._project_path)
            self.title(f"Music Video Creator — {name}")
        else:
            self.title("Music Video Creator")

    def _new_project(self):
        if self.state.audio_path or self.state.image_entries:
            if not messagebox.askyesno("New Project",
                    "This will clear the current project. Continue?"):
                return

        path = filedialog.asksaveasfilename(
            title="New Project — choose location and name",
            defaultextension=VPROJ_EXTENSION,
            filetypes=[("Video project", f"*{VPROJ_EXTENSION}"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            new_project(path)
            self._reset_ui()
            self._project_path = path
            self._update_title()
            project_dir = os.path.dirname(path)
            self.bottom_bar.set_status(
                f"Project created: {os.path.basename(path)}  "
                f"| out: {os.path.join(project_dir, 'out')}  "
                f"| gen: {os.path.join(project_dir, 'gen')}"
            )
        except Exception as exc:
            messagebox.showerror("Create Failed", str(exc))

    def _load_project(self):
        path = filedialog.askopenfilename(
            title="Load Project",
            filetypes=[("Video project", f"*{VPROJ_EXTENSION}"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            data = load_project(path)
            self._apply_project(data, path)
        except Exception as exc:
            messagebox.showerror("Load Failed", str(exc))

    def _save_project(self):
        if not self._project_path:
            messagebox.showinfo(
                "No Project",
                "Create or load a project first  (Project → New Project or Load Project)."
            )
            return
        try:
            save_project(self.state, self._project_path)
            self.bottom_bar.set_status(f"Saved: {os.path.basename(self._project_path)}")
        except Exception as exc:
            messagebox.showerror("Save Failed", str(exc))

    def _reset_ui(self):
        self.state.audio_path = None
        self.audio_section.reset()
        self.summary_panel.set_audio("—")

        self.state.switch_points = []
        self.state.transcription_words = []
        self.image_list.clear_all()
        self.lyrics_controller.reset()
        self.main_notebook.disable_lyrics_tab()

        self._refresh_summary()
        self._update_switch_counter()
        self._update_generate_button()

    def _apply_project(self, data: dict, filepath: str):
        self._reset_ui()

        audio_path = data.get("audio_path")
        if audio_path:
            self.state.audio_path = audio_path
            name = os.path.basename(audio_path)
            self.audio_section.set_audio_name(name)
            self.audio_section.set_transcribe_enabled(True)
            self.summary_panel.set_audio(name)

        for img in data.get("images", []):
            self.image_list.add_image_row(img["path"])

        for i, img in enumerate(data.get("images", [])):
            if i < len(self.state.image_entries):
                self.state.image_entries[i]["load_var"].set(img["load_time"])

        if self.state.image_entries:
            self.image_list.refresh_first_row()

        words = data.get("transcription_words", [])
        if words:
            self.state.transcription_words = words
            self.lyrics_controller.render()
            self.main_notebook.enable_lyrics_tab()

        switch_points = data.get("switch_points", [])
        if switch_points:
            self.state.switch_points = list(switch_points)
            if words:
                self.lyrics_controller.restore_switch_point_styles()

        self._project_path = filepath
        self._update_title()
        self._refresh_summary()
        self._update_switch_counter()
        self._update_generate_button()
        self.bottom_bar.set_status(f"Opened: {os.path.basename(filepath)}")

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

        self._update_generate_button()

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
            self.lyrics_controller.render()
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
        self.lyrics_controller.render()
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
        self.lyrics_controller.render()
        self.bottom_bar.set_status(f"Lyrics aligned successfully — {len(aligned_words)} words")
        self._update_switch_counter()

    # ─────────────────────────────────────────────────────────────
    # Rest of the code (lyrics interaction, images, generation, etc.)
    # ─────────────────────────────────────────────────────────────
    def _clear_switch_points(self):
        self.lyrics_controller.clear_switch_points()

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
        self.lyrics_tab.set_counter_text(msg)
        self.summary_panel.set_points(have, needed)
        self._update_generate_button()

    def _add_image(self):
        self.image_list.add_images_from_dialog()

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

        initial_dir = (
            os.path.join(os.path.dirname(self._project_path), "out")
            if self._project_path else None
        )
        out_path = filedialog.asksaveasfilename(
            title="Save video as…",
            initialdir=initial_dir,
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4")]
        )
        if not out_path:
            return

        self.summary_panel.set_output(os.path.basename(out_path))
        self.state.generating = True
        self.summary_panel.set_generating(True)
        self._update_generate_button()

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
        self.summary_panel.set_generating(False)
        self._update_generate_button()
        self.bottom_bar.set_status(f"Done! Saved to: {out_path}")
        messagebox.showinfo("Success", f"Video saved to:\n\n{out_path}")

    def _on_error(self, message):
        self.state.generating = False
        self.summary_panel.set_generating(False)
        self._update_generate_button()
        self.bottom_bar.set_status("Generation failed.")
        messagebox.showerror("Error", message)

if __name__ == "__main__":
    app = MusicVideoCreator()
    app.mainloop()