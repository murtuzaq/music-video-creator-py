import tkinter as tk
from tkinter import ttk

from .inspector_views.project_view       import ProjectView
from .inspector_views.image_view         import ImageView
from .inspector_views.audio_view         import AudioView
from .inspector_views.video_clip_view    import VideoClipView
from .inspector_views.asset_in_clip_view import AssetInClipView
from .inspector_views.audio_clip_view    import AudioClipView

_DARK = {
    "bg_darkest":   "#1e1e1e",
    "bg_dark":      "#252525",
    "bg_medium":    "#2b2b2b",
    "fg_primary":   "white",
    "fg_secondary": "#aaa",
    "fg_dim":       "#555",
    "fg_dim_alt":   "#888",
    "fg_value":     "#ddd",
    "selected_bg":  "#4a4a7a",
}


class InspectorPanel:
    def __init__(self, parent, on_close=None):
        self._current_type           = None
        self._current_node           = None
        self._current_view           = None
        self._on_update              = None
        self._on_add_assets          = None
        self._on_add_images          = None
        self._on_reorder             = None
        self._on_manual_adjust       = None
        self._on_generate            = None
        self._has_valid_clips        = False
        self._generating             = False
        self._generate_fraction      = 0.0
        self._generate_message       = ""
        self._auto_space_var         = None
        self._get_children           = None
        self._project_total_duration = 0.0
        self._parent_duration        = 0.0
        self._colors                 = dict(_DARK)

        self.frame = tk.Frame(parent, bg="#1e1e1e")
        self.frame.pack(fill=tk.BOTH, expand=True)

        self._header_frame = tk.Frame(self.frame, bg="#1e1e1e")
        self._header_frame.pack(fill=tk.X)
        self._header_lbl = tk.Label(self._header_frame, text="Inspector",
                                    bg="#1e1e1e", fg="white",
                                    font=("Helvetica", 10, "bold"),
                                    anchor="w", padx=10, pady=7)
        self._header_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._close_btn = tk.Button(self._header_frame, text="×", command=on_close,
                                    bg="#1e1e1e", fg="#888", relief=tk.FLAT,
                                    font=("Helvetica", 12), padx=8, pady=3,
                                    cursor="hand2", activebackground="#2b2b2b",
                                    activeforeground="white", bd=0)
        self._close_btn.pack(side=tk.RIGHT)
        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # ── Scrollable body ───────────────────────────────────────
        self._scroll_outer = tk.Frame(self.frame, bg="#1e1e1e")
        self._scroll_outer.pack(fill=tk.BOTH, expand=True)

        _vsb = ttk.Scrollbar(self._scroll_outer, orient=tk.VERTICAL)
        self._scroll_canvas = tk.Canvas(self._scroll_outer, bg="#1e1e1e",
                                        highlightthickness=0,
                                        yscrollcommand=_vsb.set)
        _vsb.config(command=self._scroll_canvas.yview)
        self._scroll_canvas.bind(
            "<MouseWheel>",
            lambda e: self._scroll_canvas.yview_scroll(
                int(-1 * e.delta / 120), "units"))
        _vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self._scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._body = tk.Frame(self._scroll_canvas, bg="#1e1e1e")
        self._body_win = self._scroll_canvas.create_window(
            (10, 10), window=self._body, anchor="nw")
        self._scroll_canvas.bind("<Configure>", self._on_scroll_canvas_resize)
        self._body.bind("<Configure>", self._on_body_configure)

        self._show_empty()

    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    def apply_theme(self, colors):
        self._colors = colors
        bg = colors["bg_darkest"]
        self.frame.config(bg=bg)
        self._header_frame.config(bg=bg)
        self._header_lbl.config(bg=bg, fg=colors["fg_primary"])
        self._close_btn.config(bg=bg, fg=colors["fg_dim_alt"],
                               activebackground=colors["bg_medium"],
                               activeforeground=colors["fg_primary"])
        self._scroll_outer.config(bg=bg)
        self._scroll_canvas.config(bg=bg)
        self._body.config(bg=bg)
        if self._current_type == "image":
            self.show_image(self._current_node)
        elif self._current_type == "video":
            self.show_project(self._current_node, self._project_total_duration,
                              self._on_generate, self._has_valid_clips,
                              self._generating, self._generate_fraction,
                              self._generate_message)
        elif self._current_type == "audio":
            self.show_audio(self._current_node)
        elif self._current_type == "video_clip":
            self.show_video_clip(self._current_node, self._on_update,
                                 self._on_add_assets, self._auto_space_var,
                                 self._get_children)
        elif self._current_type == "asset_in_clip":
            self.show_asset_in_clip(self._current_node, self._on_update,
                                    self._parent_duration, self._on_reorder,
                                    self._on_manual_adjust)
        elif self._current_type == "audio_clip":
            self.show_audio_clip(self._current_node, self._on_update,
                                 self._on_add_images, self._parent_duration,
                                 self._on_reorder, self._on_manual_adjust,
                                 self._get_children)
        else:
            self._show_empty()

    def show_image(self, asset: dict):
        self._current_type = "image"
        self._current_node = asset
        self._clear()
        view = ImageView(self._body, self._colors)
        view.build(asset)
        self._current_view = view

    def show_audio(self, asset: dict):
        self._current_type = "audio"
        self._current_node = asset
        self._clear()
        view = AudioView(self._body, self._colors)
        view.build(asset)
        self._current_view = view

    def show_project(self, node: dict, total_duration: float = 0.0,
                     on_generate=None, has_valid_clips: bool = False,
                     generating: bool = False,
                     generate_fraction=0.0, generate_message: str = ""):
        self._current_type           = "video"
        self._current_node           = node
        self._project_total_duration = total_duration
        self._on_generate            = on_generate
        self._has_valid_clips        = has_valid_clips
        self._generating             = generating
        self._generate_fraction      = generate_fraction
        self._generate_message       = generate_message
        self._clear()
        view = ProjectView(self._body, self._colors)
        view.build(node, total_duration,
                   on_generate=on_generate, has_valid_clips=has_valid_clips,
                   generating=generating,
                   generate_fraction=generate_fraction,
                   generate_message=generate_message)
        self._current_view = view

    def update_generate_progress(self, fraction, message: str):
        if self._current_view and hasattr(self._current_view, "set_progress"):
            self._current_view.set_progress(fraction, message)

    def show_video_clip(self, node: dict, on_update=None,
                        on_add_assets=None, auto_space_var=None,
                        get_children=None):
        self._current_type   = "video_clip"
        self._current_node   = node
        self._on_update      = on_update
        self._on_add_assets  = on_add_assets
        self._auto_space_var = auto_space_var
        self._get_children   = get_children
        self._clear()
        view = VideoClipView(self._body, self._colors, on_update, on_add_assets,
                             auto_space_var, get_children)
        view.build(node)
        self._current_view = view

    def show_asset_in_clip(self, node: dict, on_update=None,
                           parent_duration: float = 0.0, on_reorder=None,
                           on_manual_adjust=None):
        self._current_type     = "asset_in_clip"
        self._current_node     = node
        self._on_update        = on_update
        self._on_reorder       = on_reorder
        self._on_manual_adjust = on_manual_adjust
        self._parent_duration  = parent_duration
        self._clear()
        view = AssetInClipView(self._body, self._colors, on_update, on_reorder, on_manual_adjust)
        view.build(node, parent_duration)
        self._current_view = view

    def show_audio_clip(self, node: dict, on_update=None, on_add_images=None,
                        parent_duration: float = 0.0, on_reorder=None,
                        on_manual_adjust=None, get_children=None):
        self._current_type     = "audio_clip"
        self._current_node     = node
        self._on_update        = on_update
        self._on_add_images    = on_add_images
        self._on_reorder       = on_reorder
        self._on_manual_adjust = on_manual_adjust
        self._parent_duration  = parent_duration
        self._get_children     = get_children
        self._clear()
        view = AudioClipView(self._body, self._colors, on_update, on_add_images,
                             on_reorder, on_manual_adjust, get_children)
        view.build(node, parent_duration)
        self._current_view = view

    def refresh_clip_timeline(self):
        if self._current_view and hasattr(self._current_view, "refresh_timeline"):
            self._current_view.refresh_timeline()

    def update_asset_start_time(self, start_time: float):
        if self._current_view and hasattr(self._current_view, "update_start_time"):
            self._current_view.update_start_time(start_time)

    def set_reorder_button_state(self, can_go_up: bool, can_go_down: bool):
        if self._current_view and hasattr(self._current_view, "set_reorder_button_state"):
            self._current_view.set_reorder_button_state(can_go_up, can_go_down)

    def set_add_button_state(self, enabled: bool):
        if self._current_view and hasattr(self._current_view, "set_add_button_state"):
            self._current_view.set_add_button_state(enabled)

    def clear(self):
        self._current_type           = None
        self._current_node           = None
        self._current_view           = None
        self._on_update              = None
        self._on_add_assets          = None
        self._on_add_images          = None
        self._on_reorder             = None
        self._on_manual_adjust       = None
        self._on_generate            = None
        self._has_valid_clips        = False
        self._generating             = False
        self._generate_fraction      = 0.0
        self._generate_message       = ""
        self._auto_space_var         = None
        self._get_children           = None
        self._project_total_duration = 0.0
        self._parent_duration        = 0.0
        self._show_empty()

    # ─────────────────────────────────────────────────────────────
    # Private
    # ─────────────────────────────────────────────────────────────

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

    def _on_scroll_canvas_resize(self, event):
        new_width = event.width - 20
        self._scroll_canvas.itemconfig(self._body_win, width=new_width)
        if self._current_view:
            self._current_view.on_resize(new_width)

    def _on_body_configure(self, event):
        self._scroll_canvas.configure(
            scrollregion=(0, 0, event.width + 20, event.height + 20))
