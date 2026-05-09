import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False


class MultiSelectView:
    def __init__(self, body: tk.Frame, colors: dict):
        self._body         = body
        self._colors       = colors
        self._multi_photos = []

    def build(self, nodes: list):
        self._multi_photos.clear()
        bg    = self._colors["bg_darkest"]
        count = len(nodes)

        tk.Label(self._body,
                 text=f"{count} asset{'s' if count > 1 else ''} selected",
                 bg=bg, fg=self._colors["fg_dim_alt"],
                 font=("Helvetica", 8)).pack(anchor="w", pady=(0, 4))

        scroll_frame = tk.Frame(self._body, bg=bg)
        scroll_frame.pack(fill=tk.BOTH, expand=True)

        c   = tk.Canvas(scroll_frame, bg=bg, highlightthickness=0)
        vsb = ttk.Scrollbar(scroll_frame, orient=tk.VERTICAL, command=c.yview)
        c.configure(yscrollcommand=vsb.set)
        c.bind("<MouseWheel>",
               lambda e: c.yview_scroll(int(-1 * e.delta / 120), "units"))

        inner = tk.Frame(c, bg=bg)
        win   = c.create_window((0, 0), window=inner, anchor="nw")

        THUMB = 60
        PAD   = 3

        labels = []
        for node in nodes:
            ntype = node.get("type", "image")
            if ntype == "image" and _PIL:
                try:
                    img = Image.open(node.get("path", ""))
                    img.thumbnail((THUMB, THUMB))
                    photo = ImageTk.PhotoImage(img)
                    lbl = tk.Label(inner, image=photo, bg=bg,
                                   width=THUMB, height=THUMB)
                    lbl._photo = photo
                    self._multi_photos.append(photo)
                except Exception:
                    lbl = tk.Label(inner, text="?", bg=bg,
                                   fg=self._colors["fg_dim"],
                                   font=("Helvetica", 18),
                                   width=THUMB // 8, height=THUMB // 16)
            else:
                lbl = tk.Label(inner, text="♪", bg=bg, fg="#4a90d9",
                               font=("Helvetica", 22),
                               width=THUMB // 8, height=THUMB // 16)
            labels.append(lbl)

        state = {"cols": 0}

        def _layout(_event=None):
            w = inner.winfo_width()
            if w <= 1:
                return
            cols = max(1, w // (THUMB + PAD * 2))
            if cols == state["cols"]:
                return
            for col in range(state["cols"]):
                inner.columnconfigure(col, weight=0, minsize=0)
            state["cols"] = cols
            for col in range(cols):
                inner.columnconfigure(col, weight=1)
            for i, lbl in enumerate(labels):
                lbl.grid(row=i // cols, column=i % cols,
                         padx=PAD, pady=PAD, sticky="nsew")

        def _update_scroll(_event=None):
            c.configure(scrollregion=c.bbox("all"))

        inner.bind("<Configure>", lambda e: (_layout(), _update_scroll()))
        c.bind("<Configure>",     lambda e: c.itemconfig(win, width=e.width))

        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        c.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def on_resize(self, _width: int):
        pass
