import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

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


class MusicVideoCreator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Music Video Creator")
        self.geometry("1200x700")
        self.resizable(True, True)

        self.state = AppState()
        self._project_paths                = {}   # root_id -> filepath
        self._current_clip_id              = None
        self._current_asset_id             = None
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
                                          on_remove_project=self._on_remove_project)

        # ── Inspector Column (center, stretches) ──────────────────
        self.inspector_column = tk.PanedWindow(self.workspace, orient=tk.VERTICAL,
                                               sashwidth=5, sashrelief=tk.FLAT,
                                               bg="#444", bd=0)
        self.workspace.add(self.inspector_column, minsize=200, stretch="always")

        self.project_inspector_frame = tk.Frame(self.inspector_column, bg="#1e1e1e")
        self.inspector_column.add(self.project_inspector_frame,
                                  height=300, minsize=80, stretch="always")
        self.inspector_panel = InspectorPanel(self.project_inspector_frame,
                                              on_close=self._close_project_inspector)

        self.asset_inspector_frame = tk.Frame(self.inspector_column, bg="#1e1e1e")
        self.inspector_column.add(self.asset_inspector_frame,
                                  height=300, minsize=80, stretch="always")
        self.asset_inspector_panel = AssetInspectorPanel(self.asset_inspector_frame,
                                                          on_close=self._close_asset_inspector)

        # ── Asset Panel (right) ───────────────────────────────────
        self.asset_pane = tk.Frame(self.workspace, bg="#252525")
        self.workspace.add(self.asset_pane, width=210, minsize=100, stretch="never")
        self.asset_panel = AssetPanel(self.asset_pane,
                                      on_select=self._on_asset_selected,
                                      on_close=self._close_asset_panel,
                                      on_selection_change=self._on_asset_selection_change)

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
            self._current_clip_id  = None
            self._current_asset_id = item_id
            parent_id       = node.get("parent_id")
            parent_node     = self.project_panel.get_node(parent_id)
            parent_duration = parent_node.get("duration") or 0.0
            self.inspector_panel.show_asset_in_clip(
                node,
                on_update=lambda st, iid=item_id: self.project_panel.update_node(
                    iid, start_time=st
                ),
                parent_duration=parent_duration,
                on_reorder=self._reorder_asset_in_clip,
            )
            self._update_reorder_buttons()
        elif node_type == "video":
            self._current_clip_id  = None
            self._current_asset_id = None
            total_dur = self.project_panel.get_total_duration(item_id)
            self.inspector_panel.show_project(node, total_dur)
        elif node_type == "video_clip":
            self._current_clip_id  = item_id
            self._current_asset_id = None
            self.inspector_panel.show_video_clip(
                node,
                on_update=lambda name, dur: self.project_panel.update_node(
                    item_id, name=name, duration=dur
                ),
                on_add_assets=self._add_assets_to_clip,
            )
            self._on_asset_selection_change()

    def _on_asset_selection_change(self):
        assets = self.asset_panel.get_selected_assets()
        self.inspector_panel.set_add_button_state(len(assets) > 0)
        if len(assets) == 1:
            self.asset_inspector_panel.show_asset(assets[0])
        elif len(assets) > 1:
            self.asset_inspector_panel.show_multi_select(assets)
        else:
            self.asset_inspector_panel.clear()

    def _add_assets_to_clip(self):
        if not self._current_clip_id:
            return
        for asset in self.asset_panel.get_selected_assets():
            self.project_panel.add_asset_to_clip(self._current_clip_id, asset)

    def _reorder_asset_in_clip(self, direction: int):
        if not self._current_asset_id:
            return
        self.project_panel.move_child(self._current_asset_id, direction)
        self._update_reorder_buttons()

    def _update_reorder_buttons(self):
        if not self._current_asset_id:
            return
        idx, total = self.project_panel.get_child_position(self._current_asset_id)
        self.inspector_panel.set_reorder_button_state(idx > 0, idx < total - 1)

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
        self._rebuild_inspector_column()

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
        for frame in (self.project_inspector_frame, self.asset_inspector_frame):
            try:
                self.inspector_column.forget(frame)
            except Exception:
                pass
        if self._project_inspector_visible.get():
            self.inspector_column.add(self.project_inspector_frame,
                                      height=300, minsize=80, stretch="always")
        if self._asset_inspector_visible.get():
            self.inspector_column.add(self.asset_inspector_frame,
                                      height=300, minsize=80, stretch="always")

    def _view_toggle_project_inspector(self):
        self._rebuild_inspector_column()

    def _view_toggle_asset_inspector(self):
        self._rebuild_inspector_column()

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
        self._last_asset_w  = 210
        self._rebuild_inspector_column()
        self._rebuild_panes()

    # ─────────────────────────────────────────────────────────────
    # Theme
    # ─────────────────────────────────────────────────────────────
    def _set_theme(self, name: str):
        colors = THEMES[name]
        self._theme_name.set(name)
        self.workspace.config(bg=colors["sash"])
        self.inspector_column.config(bg=colors["sash"])
        self.project_pane.config(bg=colors["bg_dark"])
        self.project_inspector_frame.config(bg=colors["bg_darkest"])
        self.asset_inspector_frame.config(bg=colors["bg_darkest"])
        self.asset_pane.config(bg=colors["bg_dark"])
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
            self.title("Music Video Creator")
        elif count == 1:
            path = next(iter(self._project_paths.values()))
            self.title(f"Music Video Creator — {os.path.basename(path)}")
        else:
            self.title(f"Music Video Creator ({count} projects)")

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


if __name__ == "__main__":
    app = MusicVideoCreator()
    app.mainloop()
