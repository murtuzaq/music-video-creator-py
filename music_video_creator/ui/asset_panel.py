import tkinter as tk
from tkinter import ttk
import os

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

THUMB_W, THUMB_H = 44, 33
_NORMAL_BG   = "#333"
_SELECTED_BG = "#4a4a7a"


class AssetPanel:
    def __init__(self, parent, state, on_changed, on_select=None):
        self.state         = state
        self.on_changed    = on_changed
        self.on_select     = on_select
        self._photos       = {}    # path -> PhotoImage, keep alive
        self._selected_row = None  # currently highlighted row frame

        # ── outer frame ──────────────────────────────────────────
        self.frame = tk.Frame(parent, bg="#252525")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # ── header ───────────────────────────────────────────────
        tk.Label(self.frame, text="Assets", bg="#252525", fg="white",
                 font=("Helvetica", 10, "bold"),
                 anchor="w", padx=10, pady=7).pack(fill=tk.X)
        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # ── scrollable list ───────────────────────────────────────
        container = tk.Frame(self.frame, bg="#252525")
        container.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(container, bg="#252525", highlightthickness=0)
        self._sb     = ttk.Scrollbar(container, orient=tk.VERTICAL,
                                     command=self._canvas.yview)
        self._inner  = tk.Frame(self._canvas, bg="#252525")

        self._inner.bind("<Configure>", lambda e: self._canvas.configure(
            scrollregion=self._canvas.bbox("all")))

        self._cw = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._canvas.configure(yscrollcommand=self._sb.set)
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig(self._cw, width=e.width))
        self._canvas.bind("<MouseWheel>",
                          lambda e: self._canvas.yview_scroll(
                              int(-1 * (e.delta / 120)), "units"))

        self._sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    def add_asset(self, path: str, asset_type: str) -> bool:
        """Append an asset; returns False (and skips) if already listed."""
        if any(a["path"] == path for a in self.state.assets):
            return False
        entry = {"type": asset_type, "path": path}
        self.state.assets.append(entry)
        self._add_row(entry)
        self.on_changed()
        return True

    def clear(self):
        """Destroy all rows and reset state."""
        self._selected_row = None
        for w in self._inner.winfo_children():
            w.destroy()
        self._photos.clear()

    def rebuild(self):
        """Re-render every row from state.assets (call after project load)."""
        self.clear()
        for entry in self.state.assets:
            self._add_row(entry)

    # ─────────────────────────────────────────────────────────────
    # Private
    # ─────────────────────────────────────────────────────────────

    def _add_row(self, entry: dict):
        path       = entry["path"]
        asset_type = entry["type"]
        name       = os.path.basename(path)

        row = tk.Frame(self._inner, bg=_NORMAL_BG, pady=4, padx=4, cursor="hand2")
        row.pack(fill=tk.X, padx=4, pady=2)

        # Thumbnail or icon
        if asset_type == "image" and _PIL:
            photo = self._thumb(path)
            if photo:
                lbl = tk.Label(row, image=photo, bg=_NORMAL_BG, cursor="hand2")
                lbl.pack(side=tk.LEFT, padx=(0, 5))
            else:
                self._icon(row, "?", "#888")
        elif asset_type == "audio":
            self._icon(row, "♪", "#4a90d9")
        else:
            self._icon(row, "?", "#888")

        # Info block
        info = tk.Frame(row, bg=_NORMAL_BG)
        info.pack(side=tk.LEFT, fill=tk.X, expand=True)

        badge_bg  = "#7b5ea7" if asset_type == "image" else "#4a90d9"
        badge_txt = "IMG"     if asset_type == "image" else "AUD"
        badge = tk.Label(info, text=badge_txt, bg=badge_bg, fg="white",
                         font=("Helvetica", 7, "bold"), padx=3, pady=1)
        badge._is_badge = True   # skip during bg highlight sweep
        badge.pack(anchor="w")

        name_lbl = tk.Label(info, text=name, bg=_NORMAL_BG, fg="#ccc",
                            font=("Helvetica", 8), anchor="w", justify=tk.LEFT)
        name_lbl.pack(anchor="w", fill=tk.X)
        info.bind("<Configure>", lambda e, lbl=name_lbl: lbl.configure(wraplength=e.width))

        # Remove button
        def _remove(e=entry, r=row):
            if self._selected_row is r:
                self._selected_row = None
            self.state.assets.remove(e)
            r.destroy()
            self.on_changed()

        tk.Button(row, text="×", command=_remove,
                  bg=_NORMAL_BG, fg="#999", activebackground="#555",
                  activeforeground="white", relief=tk.FLAT,
                  font=("Helvetica", 12), padx=2, pady=0,
                  cursor="hand2").pack(side=tk.RIGHT, anchor="n")

        # ── click-to-select binding on every non-button widget ──
        def _select(_e=None, en=entry, r=row):
            self._set_row_bg(self._selected_row, _NORMAL_BG)
            self._selected_row = r
            self._set_row_bg(r, _SELECTED_BG)
            if self.on_select:
                self.on_select(en)

        self._bind_select(row, _select)

    def _bind_select(self, widget, callback):
        """Recursively bind <Button-1> on widget and descendants, skipping buttons."""
        if isinstance(widget, tk.Button):
            return
        widget.bind("<Button-1>", callback)
        for child in widget.winfo_children():
            self._bind_select(child, callback)

    def _set_row_bg(self, row, color: str):
        """Change background of a row and its children, preserving badge colours."""
        if row is None or not row.winfo_exists():
            return
        row.config(bg=color)
        for child in row.winfo_children():
            if isinstance(child, tk.Button) or getattr(child, "_is_badge", False):
                continue
            try:
                child.config(bg=color)
            except tk.TclError:
                pass
            for gc in child.winfo_children():
                if isinstance(gc, tk.Button) or getattr(gc, "_is_badge", False):
                    continue
                try:
                    gc.config(bg=color)
                except tk.TclError:
                    pass

    def _icon(self, parent, text: str, color: str):
        tk.Label(parent, text=text, bg=_NORMAL_BG, fg=color,
                 font=("Helvetica", 14), width=3,
                 cursor="hand2").pack(side=tk.LEFT, padx=(0, 5))

    def _thumb(self, path: str):
        if path in self._photos:
            return self._photos[path]
        try:
            img   = Image.open(path)
            img.thumbnail((THUMB_W, THUMB_H))
            photo = ImageTk.PhotoImage(img)
            self._photos[path] = photo
            return photo
        except Exception:
            return None
