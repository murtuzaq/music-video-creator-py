import json
import os
import re
import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageTk, ImageDraw
    _PIL = True
except ImportError:
    _PIL = False

_ICON_SPEC = {
    "audio":      "#4a90d9",
    "image":      "#5cb85c",
    "video_clip": "#9b59b6",
    "audio_clip": "#8e44ad",
}


def _read_info_duration(path: str) -> float:
    try:
        with open(path, "r", encoding="utf-8") as f:
            info = json.load(f)
        return float(info.get("duration_seconds", 0.0))
    except Exception:
        return 0.0


def _make_icon(color: str):
    if not _PIL:
        return None
    img = Image.new("RGB", (14, 14), color)
    return ImageTk.PhotoImage(img)


def _make_camera_icon():
    if not _PIL:
        return None
    img = Image.new("RGBA", (14, 14), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 3, 13, 12], fill="#e05c00")   # body
    d.rectangle([4, 1, 8,  3],  fill="#e05c00")   # viewfinder bump
    d.ellipse(  [2, 4, 11, 11], fill="white")     # lens ring
    d.ellipse(  [4, 6,  9,  9], fill="#e05c00")   # lens centre
    return ImageTk.PhotoImage(img)


class ProjectPanel:
    def __init__(self, parent, on_select=None, on_close=None, on_remove_project=None):
        self._on_select         = on_select
        self._on_remove_project = on_remove_project
        self._icons             = {t: _make_icon(c) for t, c in _ICON_SPEC.items()}
        self._icons["video"]    = _make_camera_icon()
        self._nodes             = {}    # item_id -> {"type","path","name","duration"}
        self._video_clip_count  = 0
        self._ctx_root_id       = None  # project root under the active right-click

        self.frame = tk.Frame(parent, bg="#252525")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # ── header ────────────────────────────────────────────────
        self._header_frame = tk.Frame(self.frame, bg="#252525")
        self._header_frame.pack(fill=tk.X)
        self._header_lbl = tk.Label(self._header_frame, text="Project", bg="#252525", fg="white",
                                    font=("Helvetica", 10, "bold"),
                                    anchor="w", padx=10, pady=7)
        self._header_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._close_btn = tk.Button(self._header_frame, text="×", command=on_close,
                                    bg="#252525", fg="#888", relief=tk.FLAT,
                                    font=("Helvetica", 12), padx=8, pady=3,
                                    cursor="hand2", activebackground="#2b2b2b",
                                    activeforeground="white", bd=0)
        self._close_btn.pack(side=tk.RIGHT)
        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # ── treeview ──────────────────────────────────────────────
        self._style = ttk.Style()
        self._style.theme_use("default")
        self._style.configure("Project.Treeview",
                              background="#252525",
                              foreground="#cccccc",
                              fieldbackground="#252525",
                              borderwidth=0,
                              rowheight=24,
                              font=("Helvetica", 9))
        self._style.map("Project.Treeview",
                        background=[("selected", "#4a4a7a")],
                        foreground=[("selected", "#ffffff")])

        self._container = tk.Frame(self.frame, bg="#252525")
        self._container.pack(fill=tk.BOTH, expand=True)

        self._tree = ttk.Treeview(self._container, style="Project.Treeview",
                                   show="tree", selectmode="browse")
        sb = ttk.Scrollbar(self._container, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.bind("<MouseWheel>",
                        lambda e: self._tree.yview_scroll(int(-1 * e.delta / 120), "units"))
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.bind("<Button-3>", self._on_right_click)

        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── right-click context menu ───────────────────────────────
        self._ctx_menu = tk.Menu(self._tree, tearoff=0)
        self._ctx_menu.add_command(label="Add Video Clip", command=self._new_video_clip)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="Remove Project",  command=self._remove_ctx_project)

    # ── Theme ─────────────────────────────────────────────────────

    def apply_theme(self, colors):
        bg = colors["bg_dark"]
        self.frame.config(bg=bg)
        self._header_frame.config(bg=bg)
        self._header_lbl.config(bg=bg, fg=colors["fg_primary"])
        self._close_btn.config(bg=bg, fg=colors["fg_dim_alt"],
                               activebackground=colors["bg_medium"],
                               activeforeground=colors["fg_primary"])
        self._container.config(bg=bg)
        self._style.configure("Project.Treeview",
                              background=colors["bg_dark"],
                              foreground=colors["fg_secondary_alt"],
                              fieldbackground=colors["bg_dark"])
        self._style.map("Project.Treeview",
                        background=[("selected", colors["selected_bg"])],
                        foreground=[("selected", colors["selected_fg"])])

    # ── Public API ────────────────────────────────────────────────

    def add_root(self, project_name: str) -> str:
        """Add a project root node without clearing existing projects."""
        item_id = self._tree.insert("", "end",
                                    text=f"  {project_name}",
                                    image=self._icons.get("video"),
                                    open=True)
        self._nodes[item_id] = {"type": "video", "path": None, "name": project_name,
                                 "duration": None, "start_time": None}
        return item_id

    def add_project(self, tree_data: dict) -> str:
        """Deserialise and add one project tree without clearing existing projects."""
        return self._dict_to_tree("", tree_data)

    def add_node(self, parent_id: str, node_type: str, path: str) -> str:
        name = os.path.basename(path) if path else node_type
        item_id = self._tree.insert(parent_id, "end",
                                    text=f"  {name}",
                                    image=self._icons.get(node_type),
                                    open=True)
        self._nodes[item_id] = {"type": node_type, "path": path, "name": None, "duration": None}
        self._tree.item(parent_id, open=True)
        return item_id

    def update_node(self, item_id: str, name: str = None,
                    duration: float = None, start_time: float = None):
        node = self._nodes.get(item_id)
        if not node:
            return
        if name is not None:
            node["name"] = name
            self._tree.item(item_id, text=f"  {name}")
        if duration is not None:
            node["duration"] = duration
        if start_time is not None:
            node["start_time"] = start_time

    def get_node(self, item_id: str) -> dict:
        return self._nodes.get(item_id, {})

    def get_children(self, item_id: str) -> list:
        """Returns list of (child_item_id, node_dict) for direct children."""
        return [(cid, dict(self._nodes.get(cid, {}), item_id=cid))
                for cid in self._tree.get_children(item_id)]

    def get_child_position(self, item_id: str) -> tuple:
        """Returns (index, total) of item_id among its siblings."""
        parent_id = self._tree.parent(item_id)
        if not parent_id:
            return 0, 1
        siblings = list(self._tree.get_children(parent_id))
        idx = siblings.index(item_id) if item_id in siblings else 0
        return idx, len(siblings)

    def move_child(self, item_id: str, direction: int):
        """Move item_id up (-1) or down (+1) among its siblings."""
        parent_id = self._tree.parent(item_id)
        if not parent_id:
            return
        siblings = list(self._tree.get_children(parent_id))
        if item_id not in siblings:
            return
        new_idx = siblings.index(item_id) + direction
        if 0 <= new_idx < len(siblings):
            self._tree.move(item_id, parent_id, new_idx)

    def remove_child(self, item_id: str):
        """Remove a child node from the tree and internal dict."""
        self._purge_node(item_id)
        self._tree.delete(item_id)

    def add_asset_to_clip(self, clip_id: str, asset: dict) -> str:
        ntype  = asset.get("type", "image")
        path   = asset.get("path")
        name   = asset.get("name") or (os.path.basename(path) if path else ntype)
        duration = _read_info_duration(path) if ntype == "audio_clip" else None
        item_id = self._tree.insert(clip_id, "end",
                                    text=f"  {name}",
                                    image=self._icons.get(ntype),
                                    open=True)
        self._nodes[item_id] = {"type": ntype, "path": path, "name": name,
                                 "duration": duration, "start_time": 0.0}
        self._tree.item(clip_id, open=True)
        return item_id

    def remove_project(self, root_id: str):
        self._purge_node(root_id)
        self._tree.delete(root_id)

    def get_selected_type(self):
        sel = self._tree.selection()
        if not sel:
            return None
        return self._nodes.get(sel[0], {}).get("type")

    def get_selected_item(self):
        sel = self._tree.selection()
        if not sel:
            return None, None
        item_id = sel[0]
        return item_id, self._nodes.get(item_id)

    def get_root_id(self):
        roots = self._tree.get_children("")
        return roots[0] if roots else None

    def get_all_root_ids(self) -> list:
        return list(self._tree.get_children(""))

    def get_project_data(self, root_id: str) -> dict:
        return self._node_to_dict(root_id)

    def get_total_duration(self, root_id: str) -> float:
        if not root_id:
            return 0.0
        total = 0.0
        for child_id in self._tree.get_children(root_id):
            node = self._nodes.get(child_id, {})
            if node.get("type") == "video_clip":
                total += node.get("duration") or 0.0
        return total

    def get_tree_data(self):
        roots = self._tree.get_children("")
        return [self._node_to_dict(r) for r in roots] if roots else []

    def clear(self):
        for item in self._tree.get_children(""):
            self._tree.delete(item)
        self._nodes.clear()
        self._video_clip_count = 0
        self._ctx_root_id = None

    def rebuild(self, tree_data):
        self.clear()
        if isinstance(tree_data, list):
            for item in tree_data:
                self._dict_to_tree("", item)
        elif isinstance(tree_data, dict):
            self._dict_to_tree("", tree_data)

    # ── Private ───────────────────────────────────────────────────

    def _new_video_clip(self):
        root_id = self._ctx_root_id
        if not root_id:
            return
        self._video_clip_count += 1
        name    = f"Video Clip - {self._video_clip_count}"
        item_id = self._tree.insert(root_id, "end",
                                    text=f"  {name}",
                                    image=self._icons.get("video_clip"),
                                    open=True)
        self._nodes[item_id] = {"type": "video_clip", "path": None,
                                 "name": name, "duration": 0.0, "start_time": None}
        self._tree.item(root_id, open=True)
        self._tree.selection_set(item_id)
        if self._on_select:
            self._on_select(dict(self._nodes[item_id], item_id=item_id, parent_id=root_id))

    def _remove_ctx_project(self):
        root_id = self._ctx_root_id
        if not root_id:
            return
        self._purge_node(root_id)
        self._tree.delete(root_id)
        if self._on_remove_project:
            self._on_remove_project(root_id)
        self._ctx_root_id = None

    def _on_right_click(self, event):
        item = self._tree.identify_row(event.y)
        if not item:
            return
        node = self._nodes.get(item, {})
        if node.get("type") == "video":
            self._ctx_root_id = item
            self._tree.selection_set(item)
            self._ctx_menu.post(event.x_root, event.y_root)

    def _purge_node(self, item_id: str):
        for child in self._tree.get_children(item_id):
            self._purge_node(child)
        self._nodes.pop(item_id, None)

    def _node_to_dict(self, item_id: str) -> dict:
        node = self._nodes.get(item_id, {})
        return {
            "type":       node.get("type"),
            "path":       node.get("path"),
            "name":       node.get("name"),
            "duration":   node.get("duration"),
            "start_time": node.get("start_time"),
            "children":   [self._node_to_dict(c)
                           for c in self._tree.get_children(item_id)],
        }

    def _dict_to_tree(self, parent_id: str, node_data: dict) -> str:
        node_type = node_data.get("type", "image")
        path      = node_data.get("path")
        name      = node_data.get("name") or (os.path.basename(path) if path else node_type)
        icon      = self._icons.get(node_type)
        item_id   = self._tree.insert(parent_id, "end",
                                       text=f"  {name}",
                                       image=icon,
                                       open=True)
        self._nodes[item_id] = {
            "type":       node_type,
            "path":       path,
            "name":       node_data.get("name"),
            "duration":   node_data.get("duration"),
            "start_time": node_data.get("start_time"),
        }
        if node_type == "video_clip":
            m = re.search(r"\d+$", name)
            if m:
                self._video_clip_count = max(self._video_clip_count, int(m.group()))
        for child in node_data.get("children", []):
            self._dict_to_tree(item_id, child)
        return item_id

    def _on_tree_select(self, _event=None):
        item_id, node = self.get_selected_item()
        if item_id and node and self._on_select:
            parent_id = self._tree.parent(item_id)
            self._on_select(dict(node, item_id=item_id, parent_id=parent_id))
