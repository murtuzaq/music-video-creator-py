import tkinter as tk
from tkinter import filedialog

from music_video_creator.ui.image_row import ImageRow


class ImageList:
    def __init__(self, parent, state, on_changed):
        self.parent = parent
        self.state = state
        self.on_changed = on_changed

        self.update_empty_label()

    def add_images_from_dialog(self):
        paths = filedialog.askopenfilenames(
            title="Select image(s)",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("All files", "*.*")
            ]
        )

        for path in paths:
            self.add_image_row(path)

        self.refresh_first_row()
        self.notify_changed()

    def add_image_row(self, path):
        default_load = 3.0 * len(self.state.image_entries)
        load_var = tk.DoubleVar(value=default_load)

        entry = {
            "path": path,
            "load_var": load_var,
            "row": None
        }

        def remove():
            self.state.image_entries.remove(entry)
            entry["row"].destroy()
            self.update_empty_label()
            self.refresh_first_row()
            self.notify_changed()

        entry["row"] = ImageRow(
            self.parent,
            path,
            load_var,
            remove,
            self.notify_changed
        )

        self.state.image_entries.append(entry)
        self.update_empty_label()

    def refresh_first_row(self):
        for i, entry in enumerate(self.state.image_entries):
            if i == 0:
                entry["row"].show_first_mode()
            else:
                entry["row"].show_timed_mode()

    def update_empty_label(self):
        for widget in self.parent.winfo_children():
            if getattr(widget, "_is_empty_label", False):
                widget.destroy()

        if not self.state.image_entries:
            label = tk.Label(
                self.parent,
                text='Click "+ Add Image" to add images.',
                fg="gray",
                pady=20
            )
            label._is_empty_label = True
            label.pack()

    def clear_all(self):
        for entry in list(self.state.image_entries):
            entry["row"].destroy()
        self.state.image_entries.clear()
        self.update_empty_label()

    def notify_changed(self):
        self.on_changed()