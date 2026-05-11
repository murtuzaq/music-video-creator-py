import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "utility", "git_version_py"))
import git_version
_VERSION = git_version.get(_ROOT)

from music_video_creator.app_state import AppState
from music_video_creator.project import new_project, save_project, load_project, VPROJ_EXTENSION
from music_video_creator.ui.project_panel import ProjectPanel
from music_video_creator.ui.inspector_panel import InspectorPanel
from music_video_creator.ui.asset_panel import AssetPanel
from music_video_creator.ui.asset_inspector_panel import AssetInspectorPanel
from music_video_creator.ui.menu_bar import MenuBar
from music_video_creator.ui.ribbon_bar import RibbonBar
from music_video_creator.ui.bottom_bar import BottomBar
from music_video_creator.ui.header_bar import HeaderBar
from music_video_creator.ui.theme import THEMES


def _audio_file_duration(path: str) -> float:
    """Return audio file length in seconds; 0.0 if unreadable."""
    if not path:
        return 0.0
    try:
        import wave
        with wave.open(path) as f:
            return f.getnframes() / float(f.getframerate())
    except Exception:
        pass
    try:
        from mutagen import File as _MFile
        af = _MFile(path)
        if af and af.info:
            return float(af.info.length)
    except Exception:
        pass
    return 0.0


class MusicVideoCreator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Music Video Creator {_VERSION}")
        self.geometry("1200x700")
        self.resizable(True, True)

        self.state = AppState()
        self._project_paths                = {}   # root_id -> filepath
        self._current_clip_id              = None
        self._current_asset_id             = None
        self._active_generation            = None  # {root_id, fraction, message, active}
        self._auto_space_enabled           = tk.BooleanVar(value=False)
        self._auto_space_enabled.trace_add("write", self._on_auto_space_changed)
        self._current_asset_clip_id        = None
        self._assets_visible               = tk.BooleanVar(value=True)
        self._project_inspector_visible    = tk.BooleanVar(value=True)
        self._asset_inspector_visible      = tk.BooleanVar(value=True)
        self._asset_panel_visible          = tk.BooleanVar(value=True)
        self._last_sash_pos                = 210
        self._last_asset_w                 = 210
        self._theme_name                   = tk.StringVar(value="dark")

        self._build_ui()
        self._bind_shortcuts()

    # ─────────────────────────────────────────────────────────────
    # UI bootstrap
    # ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        callbacks = {
            "new":                     self._new_project,
            "open":                    self._load_project,
            "save":                    self._save_project,
            "exit":                    self.destroy,
            "add_asset_folder":        self._add_asset_folder,
            "view_toggle_assets":              self._view_toggle_assets,
            "view_toggle_project_inspector":   self._view_toggle_project_inspector,
            "view_toggle_asset_inspector":     self._view_toggle_asset_inspector,
            "view_toggle_asset_panel":         self._view_toggle_asset_panel,
            "view_reset":                      self._view_reset,
            "set_theme":                       self._set_theme,
            "tools_audio_asset_creator":       self._open_audio_asset_creator,
        }
        variables = {
            "assets_visible":            self._assets_visible,
            "project_inspector_visible": self._project_inspector_visible,
            "asset_inspector_visible":   self._asset_inspector_visible,
            "asset_panel_visible":       self._asset_panel_visible,
            "theme":                     self._theme_name,
        }
        MenuBar(self, callbacks, variables)
        self.ribbon_bar = RibbonBar(self, callbacks)
        self.header_bar = HeaderBar(self)

        # ── Workspace ─────────────────────────────────────────────
        self.workspace = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                                        sashwidth=5, sashrelief=tk.FLAT,
                                        bg="#444", bd=0)
        self.workspace.pack(fill=tk.BOTH, expand=True)

        # ── Project Panel (left) ──────────────────────────────────
        self.project_pane = tk.Frame(self.workspace, bg="#252525")
        self.workspace.add(self.project_pane, width=210, minsize=100, stretch="never")
        self.project_panel = ProjectPanel(self.project_pane,
                                          on_select=self._on_project_node_selected,
                                          on_close=self._close_project_panel,
                                          on_remove_project=self._on_remove_project,
                                          on_remove_child=self._on_child_removed)

        # ── Inspector (center, stretches) ─────────────────────────
        self.inspector_column = tk.PanedWindow(self.workspace, orient=tk.VERTICAL,
                                               sashwidth=5, sashrelief=tk.FLAT,
                                               bg="#444", bd=0)
        self.workspace.add(self.inspector_column, minsize=200, stretch="always")

        self.project_inspector_frame = tk.Frame(self.inspector_column, bg="#1e1e1e")
        self.inspector_column.add(self.project_inspector_frame,
                                  minsize=80, stretch="always")
        self.inspector_panel = InspectorPanel(self.project_inspector_frame,
                                              on_close=self._close_project_inspector)

        # ── Asset Panel (right) ───────────────────────────────────
        self.asset_pane = tk.Frame(self.workspace, bg="#252525")
        self.workspace.add(self.asset_pane, width=240, minsize=150, stretch="never")

        self.asset_split = tk.PanedWindow(self.asset_pane, orient=tk.VERTICAL,
                                          sashwidth=5, sashrelief=tk.FLAT,
                                          bg="#444", bd=0)
        self.asset_split.pack(fill=tk.BOTH, expand=True)

        self.asset_tree_frame = tk.Frame(self.asset_split, bg="#252525")
        self.asset_split.add(self.asset_tree_frame, height=300, minsize=100, stretch="always")
        self.asset_panel = AssetPanel(self.asset_tree_frame,
                                      on_select=self._on_asset_selected,
                                      on_close=self._close_asset_panel,
                                      on_selection_change=self._on_asset_selection_change)

        self.asset_inspector_frame = tk.Frame(self.asset_split, bg="#1e1e1e")
        self.asset_split.add(self.asset_inspector_frame, height=250, minsize=80, stretch="never")
        self.asset_inspector_panel = AssetInspectorPanel(self.asset_inspector_frame,
                                                          on_close=self._close_asset_inspector)

        self._build_bottom_bar()

    def _build_bottom_bar(self):
        self.bottom_bar = BottomBar(self)

    # ─────────────────────────────────────────────────────────────
    # Panel callbacks
    # ─────────────────────────────────────────────────────────────
    def _on_project_node_selected(self, node: dict):
        node_type = node.get("type")
        item_id   = node.get("item_id")
        if node_type in ("image", "audio"):
            self._current_clip_id        = None
            self._current_asset_id       = item_id
            self._current_asset_clip_id  = node.get("parent_id")
            parent_id       = node.get("parent_id")
            parent_node     = self.project_panel.get_node(parent_id)
            parent_duration = parent_node.get("duration") or 0.0
            cues = []
            if parent_node.get("_show_lyrics"):
                import json as _json, os as _os
                ac_path = parent_node.get("audio_clip_path", "")
                if ac_path and _os.path.isfile(ac_path):
                    try:
                        with open(ac_path, "r", encoding="utf-8") as _f:
                            _info = _json.load(_f)
                        cues = sorted(
                            _info.get("lyrics", {}).get("cues", []),
                            key=lambda c: c.get("start", 0.0),
                        )
                    except Exception:
                        cues = []
            self.inspector_panel.show_asset_in_clip(
                node,
                on_update=lambda st, iid=item_id: self.project_panel.update_node(
                    iid, start_time=st
                ),
                parent_duration=parent_duration,
                on_reorder=self._reorder_asset_in_clip,
                on_manual_adjust=self._on_asset_manual_adjust,
                cues=cues,
            )
            self._update_reorder_buttons()
        elif node_type == "video":
            self._current_clip_id        = None
            self._current_asset_id       = None
            self._current_asset_clip_id  = None
            total_dur = self.project_panel.get_total_duration(item_id)
            gen       = self._active_generation
            is_gen    = (gen is not None
                         and gen["root_id"] == item_id
                         and gen["active"])
            self.inspector_panel.show_project(
                node, total_dur,
                on_generate=lambda iid=item_id: self._start_generate(iid),
                has_valid_clips=self._has_valid_clips(item_id),
                generating=is_gen,
                generate_fraction=gen["fraction"] if is_gen else 0.0,
                generate_message=gen["message"] if is_gen else "",
            )
        elif node_type == "video_clip":
            same_clip = (item_id == self._current_clip_id or
                         item_id == self._current_asset_clip_id)
            if not same_clip:
                self._auto_space_enabled.set(False)
            self._current_clip_id        = item_id
            self._current_asset_id       = None
            self._current_asset_clip_id  = None
            self.inspector_panel.show_video_clip(
                node,
                on_update=lambda name, dur, iid=item_id: self._on_clip_update(iid, name, dur),
                on_add_assets=self._add_assets_to_clip,
                auto_space_var=self._auto_space_enabled,
                get_children=lambda iid=item_id: self._get_clip_preview_children(iid),
                on_remove_audio_clip=self._remove_audio_clip_from_clip,
                get_node=lambda iid=item_id: self.project_panel.get_node(iid),
            )
            self._on_asset_selection_change()

    def _on_asset_selection_change(self):
        assets = self.asset_panel.get_selected_assets()
        has_ac    = any(a.get("type") == "audio_clip" for a in assets)
        has_image = any(a.get("type") == "image" for a in assets)
        self.inspector_panel.set_add_button_state(has_image)
        self.inspector_panel.set_add_audio_clip_button_state(has_ac)
        if len(assets) == 1:
            self.asset_inspector_panel.show_asset(assets[0])
        elif len(assets) > 1:
            self.asset_inspector_panel.show_multi_select(assets)
        else:
            self.asset_inspector_panel.clear()

    def _sync_clip_duration_from_audio_clip(self, clip_id: str):
        import json as _json
        node = self.project_panel.get_node(clip_id)
        path = node.get("audio_clip_path", "")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                info = _json.load(f)
            dur = float(info.get("duration_seconds", 0.0))
        except Exception:
            return
        if dur > 0:
            self.project_panel.update_node(clip_id, duration=dur)
            if self._current_clip_id == clip_id:
                self.inspector_panel.update_clip_duration(dur)

    def _remove_audio_clip_from_clip(self):
        if not self._current_clip_id:
            return
        self.project_panel.get_node(self._current_clip_id).pop("audio_clip_path", None)
        self._refresh_clip_preview()

    def _add_assets_to_clip(self):
        if not self._current_clip_id:
            return
        for asset in self.asset_panel.get_selected_assets():
            atype = asset.get("type")
            if atype == "audio_clip":
                self.project_panel.get_node(self._current_clip_id)["audio_clip_path"] = asset["path"]
                self._sync_clip_duration_from_audio_clip(self._current_clip_id)
            elif atype == "image":
                self.project_panel.add_asset_to_clip(self._current_clip_id, asset)
        if self._auto_space_enabled.get():
            self._auto_space_clip()
        self._refresh_clip_preview()

    def _on_clip_update(self, clip_id: str, name: str, dur: float):
        self.project_panel.update_node(clip_id, name=name, duration=dur)
        if self._auto_space_enabled.get():
            self._auto_space_clip()
            self._refresh_clip_preview()

    def _get_clip_preview_children(self, clip_id: str) -> list:
        result = []
        for _, n in self.project_panel.get_children(clip_id):
            node = dict(n)
            if node.get("type") == "audio":
                node["_audio_dur"] = _audio_file_duration(node.get("path"))
            result.append(node)
        return result

    def _auto_space_clip(self):
        clip_id = self._current_clip_id or self._current_asset_clip_id
        if not clip_id:
            return
        clip_node = self.project_panel.get_node(clip_id)
        clip_dur  = clip_node.get("duration") or 0.0
        children  = self.project_panel.get_children(clip_id)
        if not children or clip_dur <= 0:
            return

        num_images  = sum(1 for _, n in children if n.get("type") == "image")
        audio_total = sum(
            _audio_file_duration(n.get("path"))
            for _, n in children if n.get("type") == "audio"
        )
        image_slot = (clip_dur - audio_total) / num_images if num_images > 0 else 0.0

        current_time = 0.0
        for iid, n in children:
            ntype = n.get("type")
            self.project_panel.update_node(iid, start_time=round(current_time, 3))
            if ntype == "audio":
                current_time += _audio_file_duration(n.get("path"))
            else:
                current_time += image_slot

    def _on_auto_space_changed(self, *_):
        if self._auto_space_enabled.get():
            self._auto_space_clip()
            self._refresh_clip_preview()

    def _on_asset_manual_adjust(self):
        self._auto_space_enabled.set(False)

    def _refresh_clip_preview(self):
        self.inspector_panel.refresh_clip_timeline()

    def _reorder_asset_in_clip(self, direction: int):
        if not self._current_asset_id:
            return
        self.project_panel.move_child(self._current_asset_id, direction)
        self._update_reorder_buttons()
        if self._auto_space_enabled.get():
            self._auto_space_clip()
            node = self.project_panel.get_node(self._current_asset_id)
            self.inspector_panel.update_asset_start_time(node.get("start_time") or 0.0)
        self._refresh_clip_preview()

    def _update_reorder_buttons(self):
        if not self._current_asset_id:
            return
        idx, total = self.project_panel.get_child_position(self._current_asset_id)
        self.inspector_panel.set_reorder_button_state(idx > 0, idx < total - 1)

    def _on_child_removed(self, item_id: str, parent_id: str):
        if item_id in (self._current_asset_id, self._current_clip_id):
            # The removed item is the one currently shown in the inspector
            self._current_asset_id      = None
            self._current_asset_clip_id = None
            self._current_clip_id       = None
            self.inspector_panel.clear()
        elif parent_id == self._current_clip_id:
            # A child of the current clip was removed — refresh strip + AC section
            self.inspector_panel.refresh_clip_timeline()

    def _on_remove_project(self, root_id: str):
        self._project_paths.pop(root_id, None)
        self._update_title()
        self.inspector_panel.clear()

    def _on_asset_selected(self, node: dict):
        pass  # handled by _on_asset_selection_change

    def _add_asset_folder(self):
        self.asset_panel._load_folder()

    # ── Close-button helpers (mirror View-menu toggles) ───────────
    def _close_project_panel(self):
        self._assets_visible.set(False)
        self._rebuild_panes()

    def _close_project_inspector(self):
        self._project_inspector_visible.set(False)
        self._rebuild_inspector_column()

    def _close_asset_inspector(self):
        self._asset_inspector_visible.set(False)
        self._rebuild_asset_pane()

    def _close_asset_panel(self):
        self._asset_panel_visible.set(False)
        self._rebuild_panes()

    # ─────────────────────────────────────────────────────────────
    # View helpers
    # ─────────────────────────────────────────────────────────────
    def _rebuild_panes(self):
        for pane in (self.project_pane, self.inspector_column, self.asset_pane):
            try:
                self.workspace.forget(pane)
            except Exception:
                pass
        if self._assets_visible.get():
            self.workspace.add(self.project_pane, width=self._last_sash_pos,
                               minsize=100, stretch="never")
        self.workspace.add(self.inspector_column, minsize=200, stretch="always")
        if self._asset_panel_visible.get():
            self.workspace.add(self.asset_pane, width=self._last_asset_w,
                               minsize=100, stretch="never")
        self.after(10, self._apply_sashes)

    def _apply_sashes(self):
        total = self.workspace.winfo_width()
        if total <= 0:
            return
        sash = 0
        if self._assets_visible.get():
            self.workspace.sash_place(sash, self._last_sash_pos, 0)
            sash += 1
        if self._asset_panel_visible.get():
            self.workspace.sash_place(sash, total - self._last_asset_w, 0)

    def _rebuild_inspector_column(self):
        try:
            self.inspector_column.forget(self.project_inspector_frame)
        except Exception:
            pass
        if self._project_inspector_visible.get():
            self.inspector_column.add(self.project_inspector_frame,
                                      minsize=80, stretch="always")

    def _rebuild_asset_pane(self):
        for frame in (self.asset_tree_frame, self.asset_inspector_frame):
            try:
                self.asset_split.forget(frame)
            except Exception:
                pass
        self.asset_split.add(self.asset_tree_frame, minsize=100, stretch="always")
        if self._asset_inspector_visible.get():
            self.asset_split.add(self.asset_inspector_frame,
                                 height=250, minsize=80, stretch="never")

    def _view_toggle_project_inspector(self):
        self._rebuild_inspector_column()

    def _view_toggle_asset_inspector(self):
        self._rebuild_asset_pane()

    def _view_toggle_assets(self):
        if not self._assets_visible.get():
            try:
                self._last_sash_pos = self.workspace.sash_coord(0)[0]
            except Exception:
                pass
        self._rebuild_panes()

    def _view_toggle_asset_panel(self):
        if not self._asset_panel_visible.get():
            try:
                total = self.workspace.winfo_width()
                panes = self.workspace.panes()
                n     = len(panes)
                self._last_asset_w = total - self.workspace.sash_coord(n - 2)[0]
            except Exception:
                pass
        self._rebuild_panes()

    def _view_reset(self):
        self._assets_visible.set(True)
        self._project_inspector_visible.set(True)
        self._asset_inspector_visible.set(True)
        self._asset_panel_visible.set(True)
        self._last_sash_pos = 210
        self._last_asset_w  = 240
        self._rebuild_inspector_column()
        self._rebuild_asset_pane()
        self._rebuild_panes()

    # ─────────────────────────────────────────────────────────────
    # Theme
    # ─────────────────────────────────────────────────────────────
    def _set_theme(self, name: str):
        colors = THEMES[name]
        self._theme_name.set(name)
        self.workspace.config(bg=colors["sash"])
        self.inspector_column.config(bg=colors["sash"])
        self.asset_split.config(bg=colors["sash"])
        self.project_pane.config(bg=colors["bg_dark"])
        self.project_inspector_frame.config(bg=colors["bg_darkest"])
        self.asset_pane.config(bg=colors["bg_dark"])
        self.asset_tree_frame.config(bg=colors["bg_dark"])
        self.asset_inspector_frame.config(bg=colors["bg_darkest"])
        self.header_bar.apply_theme(colors)
        self.bottom_bar.apply_theme(colors)
        self.project_panel.apply_theme(colors)
        self.inspector_panel.apply_theme(colors)
        self.asset_inspector_panel.apply_theme(colors)
        self.asset_panel.apply_theme(colors)

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
        count = len(self._project_paths)
        if count == 0:
            self.title(f"Music Video Creator {_VERSION}")
        elif count == 1:
            path = next(iter(self._project_paths.values()))
            self.title(f"Music Video Creator {_VERSION} — {os.path.basename(path)}")
        else:
            self.title(f"Music Video Creator {_VERSION} ({count} projects)")

    def _new_project(self):
        path = filedialog.asksaveasfilename(
            title="New Project — choose location and name",
            defaultextension=VPROJ_EXTENSION,
            filetypes=[("Video project", f"*{VPROJ_EXTENSION}"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            new_project(path)
            project_name = os.path.splitext(os.path.basename(path))[0]
            root_id = self.project_panel.add_root(project_name)
            self._project_paths[root_id] = path
            self._update_title()
            self.bottom_bar.set_status(f"Project created: {os.path.basename(path)}")
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
        if not self._project_paths:
            messagebox.showinfo(
                "No Projects",
                "Create or load a project first  (Project → New Project or Load Project)."
            )
            return
        errors = []
        for root_id, path in self._project_paths.items():
            try:
                state = AppState()
                state.project_tree = self.project_panel.get_project_data(root_id)
                save_project(state, path)
            except Exception as exc:
                errors.append(f"{os.path.basename(path)}: {exc}")
        if errors:
            messagebox.showerror("Save Failed", "\n".join(errors))
        else:
            count = len(self._project_paths)
            noun  = "project" if count == 1 else "projects"
            self.bottom_bar.set_status(f"Saved {count} {noun}")

    def _reset_ui(self):
        self.state = AppState()
        self._project_paths.clear()
        self.project_panel.clear()
        self.inspector_panel.clear()
        self.asset_inspector_panel.clear()

    def _apply_project(self, data: dict, filepath: str):
        tree_data = data.get("project_tree")
        if tree_data:
            root_id = self.project_panel.add_project(tree_data)
            self._project_paths[root_id] = filepath
        self._update_title()
        self.bottom_bar.set_status(f"Opened: {os.path.basename(filepath)}")

    # ─────────────────────────────────────────────────────────────
    # Video generation
    # ─────────────────────────────────────────────────────────────
    def _has_valid_clips(self, root_id: str) -> bool:
        for _, n in self.project_panel.get_children(root_id):
            if n.get("type") == "video_clip" and (n.get("duration") or 0) > 0:
                return True
        return False

    def _start_generate(self, root_id: str):
        if not self._has_valid_clips(root_id):
            return
        if self._active_generation and self._active_generation["active"]:
            return
        out_path = filedialog.asksaveasfilename(
            title="Save Video As",
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4"), ("All files", "*.*")],
        )
        if not out_path:
            return

        self._active_generation = {
            "root_id": root_id,
            "fraction": 0.0,
            "message": "Starting…",
            "active": True,
        }

        project_data = self.project_panel.get_project_data(root_id)
        self.inspector_panel.update_generate_progress(0.0, "Starting…")

        def _progress(fraction, message):
            if self._active_generation:
                self._active_generation["fraction"] = fraction
                self._active_generation["message"]  = message
                done = fraction is not None and (fraction >= 1.0 or fraction < 0)
                if done:
                    self._active_generation["active"] = False
            self.inspector_panel.update_generate_progress(fraction, message)
            if fraction is not None and fraction >= 1.0:
                self.bottom_bar.set_status(f"Video saved: {os.path.basename(out_path)}")
            elif fraction is not None and fraction < 0:
                self.bottom_bar.set_status(f"Generation failed: {message}")

        import threading
        from music_video_creator.services.video_generator import generate

        def _run():
            try:
                generate(
                    project_data, out_path,
                    progress_callback=lambda p, m: self.after(
                        0, lambda p=p, m=m: _progress(p, m)
                    ),
                )
            except Exception as exc:
                self.after(0, lambda e=exc: _progress(-1, str(e)))

        threading.Thread(target=_run, daemon=True).start()

    # ─────────────────────────────────────────────────────────────
    # Tools
    # ─────────────────────────────────────────────────────────────
    def _open_audio_asset_creator(self):
        if hasattr(self, "_audio_asset_window") and self._audio_asset_window.winfo_exists():
            self._audio_asset_window.lift()
            self._audio_asset_window.focus_set()
            return
        import sys
        _tools_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "audioasset-creator")
        if _tools_path not in sys.path:
            sys.path.insert(0, _tools_path)
        from app_gui import App
        self._audio_asset_window = App(self)


if __name__ == "__main__":
    app = MusicVideoCreator()
    app.mainloop()
