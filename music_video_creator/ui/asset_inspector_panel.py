import tkinter as tk
from tkinter import ttk
import os

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

_DARK = {
    "bg_darkest": "#1e1e1e",
    "fg_primary": "white",
    "fg_dim":     "#555",
    "fg_dim_alt": "#888",
    "fg_value":   "#ddd",
}


def _fmt_size(path: str) -> str:
    try:
        b = os.path.getsize(path)
        if b < 1024:      return f"{b} B"
        if b < 1024 ** 2: return f"{b / 1024:.1f} KB"
        return f"{b / 1024 ** 2:.1f} MB"
    except Exception:
        return "—"


class AssetInspectorPanel:
    def __init__(self, parent, on_close=None):
        self._pil_src      = None
        self._preview_lbl  = None
        self._current_node = None
        self._colors       = dict(_DARK)

        self.frame = tk.Frame(parent, bg="#1e1e1e")
        self.frame.pack(fill=tk.BOTH, expand=True)

        self._header_frame = tk.Frame(self.frame, bg="#1e1e1e")
        self._header_frame.pack(fill=tk.X)
        self._header_lbl = tk.Label(
            self._header_frame, text="Asset Inspector", bg="#1e1e1e", fg="white",
            font=("Helvetica", 10, "bold"), anchor="w", padx=10, pady=7,
        )
        self._header_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._close_btn = tk.Button(self._header_frame, text="×", command=on_close,
                                    bg="#1e1e1e", fg="#888", relief=tk.FLAT,
                                    font=("Helvetica", 12), padx=8, pady=3,
                                    cursor="hand2", activebackground="#2b2b2b",
                                    activeforeground="white", bd=0)
        self._close_btn.pack(side=tk.RIGHT)
        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        self._body = tk.Frame(self.frame, bg="#1e1e1e")
        self._body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self._body.bind("<Configure>", self._on_resize)

        self._show_empty()

    # ── Public API ────────────────────────────────────────────────

    def apply_theme(self, colors):
        self._colors = colors
        bg = colors["bg_darkest"]
        self.frame.config(bg=bg)
        self._header_frame.config(bg=bg)
        self._header_lbl.config(bg=bg, fg=colors["fg_primary"])
        self._close_btn.config(bg=bg, fg=colors["fg_dim_alt"],
                               activebackground=colors["bg_medium"],
                               activeforeground=colors["fg_primary"])
        self._body.config(bg=bg)
        if self._current_node:
            self.show_asset(self._current_node)
        else:
            self._show_empty()

    def show_asset(self, node: dict):
        self._current_node = node
        ntype = node.get("type", "")
        if ntype == "image":
            self._show_image(node["path"])
        elif ntype == "audio":
            self._show_audio(node["path"])
        else:
            self._show_empty()

    def clear(self):
        self._current_node = None
        self._show_empty()

    # ── Private ───────────────────────────────────────────────────

    def _show_image(self, path: str):
        self._clear_body()
        bg = self._colors["bg_darkest"]

        self._preview_lbl = tk.Label(self._body, bg=bg)
        self._preview_lbl.pack(pady=(4, 8))

        if _PIL:
            try:
                self._pil_src = Image.open(path)
                self._refresh_preview()
            except Exception:
                self._pil_src = None
                tk.Label(self._body, text="[no preview]",
                         bg=bg, fg=self._colors["fg_dim"]).pack()

        self._info_row("Name", os.path.basename(path))
        self._info_row("Size", _fmt_size(path))
        self._info_row("Type", os.path.splitext(path)[1].upper().lstrip("."))

    def _show_audio(self, path: str):
        self._clear_body()
        bg = self._colors["bg_darkest"]
        tk.Label(self._body, text="♪", bg=bg, fg="#4a90d9",
                 font=("Helvetica", 40)).pack(pady=(14, 6))
        self._info_row("Name", os.path.basename(path))
        self._info_row("Size", _fmt_size(path))
        self._info_row("Type", os.path.splitext(path)[1].upper().lstrip("."))

    def _show_empty(self):
        self._clear_body()
        bg = self._colors["bg_darkest"]
        tk.Label(
            self._body,
            text="Select an asset\nto preview",
            bg=bg, fg=self._colors["fg_dim"],
            font=("Helvetica", 9), justify=tk.CENTER,
        ).pack(expand=True)

    def _clear_body(self):
        self._pil_src     = None
        self._preview_lbl = None
        for w in self._body.winfo_children():
            w.destroy()

    def _info_row(self, label: str, value: str):
        bg = self._colors["bg_darkest"]
        row = tk.Frame(self._body, bg=bg)
        row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=label + ":", bg=bg, fg=self._colors["fg_dim_alt"],
                 font=("Helvetica", 8), width=5, anchor="w").pack(side=tk.LEFT)
        val_lbl = tk.Label(row, text=value, bg=bg, fg=self._colors["fg_value"],
                           font=("Helvetica", 8), anchor="w", justify=tk.LEFT)
        val_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        row.bind("<Configure>",
                 lambda e, l=val_lbl: l.configure(wraplength=max(1, e.width - 52)))

    def _on_resize(self, _event):
        if self._pil_src:
            self._refresh_preview()

    def _refresh_preview(self):
        if not self._pil_src or not self._preview_lbl:
            return
        w = max(60, self._body.winfo_width() - 20)
        img = self._pil_src.copy()
        img.thumbnail((w, 160))
        photo = ImageTk.PhotoImage(img)
        self._preview_lbl.config(image=photo)
        self._preview_lbl._photo = photo
