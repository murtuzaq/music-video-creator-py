import tkinter as tk
from tkinter import ttk

from .asset_inspector_views.single_asset_view import SingleAssetView
from .asset_inspector_views.multi_select_view  import MultiSelectView

_DARK = {
    "bg_darkest": "#1e1e1e",
    "bg_medium":  "#2b2b2b",
    "fg_primary": "white",
    "fg_dim":     "#555",
    "fg_dim_alt": "#888",
    "fg_value":   "#ddd",
}


class AssetInspectorPanel:
    def __init__(self, parent, on_close=None):
        self._current_node = None
        self._current_view = None
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
        self._clear()
        view = SingleAssetView(self._body, self._colors)
        view.build(node)
        self._current_view = view

    def show_multi_select(self, nodes: list):
        self._current_node = None
        self._clear()
        if not nodes:
            self._show_empty()
            return
        view = MultiSelectView(self._body, self._colors)
        view.build(nodes)
        self._current_view = view

    def clear(self):
        self._current_node = None
        self._current_view = None
        self._show_empty()

    # ── Private ───────────────────────────────────────────────────

    def _clear(self):
        self._current_view = None
        for w in self._body.winfo_children():
            w.destroy()

    def _show_empty(self):
        self._clear()
        bg = self._colors["bg_darkest"]
        tk.Label(self._body, text="Select an asset\nto preview",
                 bg=bg, fg=self._colors["fg_dim"],
                 font=("Helvetica", 9), justify=tk.CENTER).pack(expand=True)

    def _on_resize(self, _event):
        if self._current_view:
            self._current_view.on_resize(self._body.winfo_width())
