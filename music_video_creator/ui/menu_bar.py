import tkinter as tk


class MenuBar(tk.Menu):
    def __init__(self, root, callbacks: dict):
        super().__init__(root)

        project_menu = tk.Menu(self, tearoff=0)
        project_menu.add_command(label="New Project",  accelerator="Ctrl+N", command=callbacks["new"])
        project_menu.add_command(label="Load Project", accelerator="Ctrl+O", command=callbacks["open"])
        project_menu.add_separator()
        project_menu.add_command(label="Save Project", accelerator="Ctrl+S", command=callbacks["save"])
        project_menu.add_separator()
        project_menu.add_command(label="Exit",                                command=callbacks["exit"])

        self.add_cascade(label="Project", menu=project_menu)
        root.config(menu=self)
