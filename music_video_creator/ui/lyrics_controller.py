import tkinter as tk
from tkinter import messagebox


class LyricsController:
    def __init__(self, lyrics_tab, state, on_changed):
        self.lyrics_tab = lyrics_tab
        self.state = state
        self.on_changed = on_changed
        self.text = lyrics_tab.get_text_widget()

    def render(self):
        txt = self.text
        txt.config(state=tk.NORMAL)
        txt.delete("1.0", tk.END)

        prev_end = -1

        for i, word in enumerate(self.state.transcription_words):
            if prev_end >= 0 and word["start"] - prev_end > 2.0:
                txt.insert(tk.END, "\n\n")

            tag_name = f"w{i}"
            txt.insert(tk.END, word["text"] + " ", ("word", tag_name))
            txt.tag_bind(tag_name, "<Button-1>", lambda e, idx=i: self.__toggle_word(idx))
            txt.tag_bind(tag_name, "<Enter>", lambda e, idx=i: self.__hover_word(idx, True))
            txt.tag_bind(tag_name, "<Leave>", lambda e, idx=i: self.__hover_word(idx, False))

            prev_end = word["end"]

        txt.config(state=tk.DISABLED)

    def clear_switch_points(self):
        self.state.switch_points.clear()

        txt = self.text
        txt.config(state=tk.NORMAL)
        txt.tag_remove("switch", "1.0", tk.END)
        txt.config(state=tk.DISABLED)

        self.on_changed()

    def __toggle_word(self, idx):
        timestamp = self.state.transcription_words[idx]["start"]
        tag = f"w{idx}"

        if timestamp in self.state.switch_points:
            self.state.switch_points.remove(timestamp)
            self.__set_word_style(tag, False)
        else:
            needed = max(0, len(self.state.image_entries) - 1)

            if needed > 0 and len(self.state.switch_points) >= needed:
                messagebox.showinfo(
                    "Enough load points",
                    f"You already have {needed} load point(s). Remove one first."
                )
                return

            self.state.switch_points.append(timestamp)
            self.state.switch_points.sort()
            self.__set_word_style(tag, True)

        self.__apply_switch_points()
        self.on_changed()

    def __hover_word(self, idx, entering):
        tag = f"w{idx}"

        txt = self.text
        txt.config(state=tk.NORMAL)

        if entering and self.state.transcription_words[idx]["start"] not in self.state.switch_points:
            txt.tag_add("hover", f"{tag}.first", f"{tag}.last")
        else:
            txt.tag_remove("hover", "1.0", tk.END)

        txt.config(state=tk.DISABLED)

    def __set_word_style(self, tag, selected):
        txt = self.text
        txt.config(state=tk.NORMAL)

        if selected:
            txt.tag_add("switch", f"{tag}.first", f"{tag}.last")
        else:
            txt.tag_remove("switch", f"{tag}.first", f"{tag}.last")

        txt.config(state=tk.DISABLED)

    def __apply_switch_points(self):
        points = sorted(self.state.switch_points)

        for i, entry in enumerate(self.state.image_entries[1:]):
            if i < len(points):
                entry["load_var"].set(round(points[i], 2))