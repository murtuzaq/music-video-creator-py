import json
import os
import tkinter as tk
from tkinter import ttk, filedialog

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff", ".tif"}
_INFO_EXT  = {".info"}

_ICON_COLORS = {
    "folder":     "#888888",
    "image":      "#5cb85c",
    "audio_clip": "#8e44ad",
}


def _make_icon(color: str):
    if not _PIL:
        return None
    img = Image.new("RGB", (14, 14), color)
    return ImageTk.PhotoImage(img)


def _read_audio_path(info_path: str) -> str:
    try:
        with open(info_path, "r", encoding="utf-8") as f:
            return json.load(f).get("audio_path", "")
    except Exception:
        return ""


def _scan_audio_folder(root_path: str) -> dict:
    """Recursively build a tree dict for .info files that have an audio_path."""
    name = os.path.basename(root_path) or root_path
    children = []
    try:
        entries = sorted(
            os.scandir(root_path),
            key=lambda e: (not e.is_dir(), e.name.lower()),
        )
        for entry in entries:
            if entry.is_dir():
                child = _scan_audio_folder(entry.path)
                if child["children"]:
                    children.append(child)
            elif entry.is_file() and os.path.splitext(entry.name)[1].lower() in _INFO_EXT:
                audio_path = _read_audio_path(entry.path)
                if audio_path:
                    children.append({"name": entry.name, "path": entry.path,
                                     "type": "audio_clip", "children": []})
    except PermissionError:
        pass
    return {"name": name, "path": root_path, "type": "folder", "children": children}


def _scan_images_folder(root_path: str) -> dict:
    """Recursively build a tree dict for image files only."""
    name = os.path.basename(root_path) or root_path
    children = []
    try:
        entries = sorted(
            os.scandir(root_path),
            key=lambda e: (not e.is_dir(), e.name.lower()),
        )
        for entry in entries:
            if entry.is_dir():
                child = _scan_images_folder(entry.path)
                if child["children"]:
                    children.append(child)
            elif entry.is_file():
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in _IMAGE_EXT:
                    children.append({"name": entry.name, "path": entry.path,
                                     "type": "image", "children": []})
    except PermissionError:
        pass
    return {"name": name, "path": root_path, "type": "folder", "children": children}


class AssetPanel:
    def __init__(self, parent, on_select=None, on_close=None, on_selection_change=None):
        self._on_select           = on_select
        self._on_selection_change = on_selection_change
        self._audio_nodes = {}   # item_id -> {"type": "audio_clip" | "folder", "path": ...}
        self._audio_roots = {}   # root_path -> item_id
        self._ctx_audio_item = None
        self._image_nodes = {}   # item_id -> {"type", "path"}
        self._image_roots = {}   # root_path -> item_id
        self._icons       = {k: _make_icon(c) for k, c in _ICON_COLORS.items()}
        self._ctx_item    = None

        self.frame = tk.Frame(parent, bg="#252525")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # ── header ────────────────────────────────────────────────
        self._header_frame = tk.Frame(self.frame, bg="#252525")
        self._header_frame.pack(fill=tk.X)
        self._header_lbl = tk.Label(
            self._header_frame, text="Assets", bg="#252525", fg="white",
            font=("Helvetica", 10, "bold"), anchor="w", padx=10, pady=7,
        )
        self._header_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._close_btn = tk.Button(
            self._header_frame, text="×", command=on_close,
            bg="#252525", fg="#888", relief=tk.FLAT,
            font=("Helvetica", 12), padx=8, pady=3,
            cursor="hand2", activebackground="#2b2b2b",
            activeforeground="white", bd=0)
        self._close_btn.pack(side=tk.RIGHT)
        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # ── shared treeview style ─────────────────────────────────
        self._style = ttk.Style()
        self._style.configure(
            "Asset.Treeview",
            background="#252525", foreground="#cccccc",
            fieldbackground="#252525", borderwidth=0,
            rowheight=24, font=("Helvetica", 9),
        )
        self._style.map(
            "Asset.Treeview",
            background=[("selected", "#4a4a7a")],
            foreground=[("selected", "#ffffff")],
        )

        # ── vertical split: audio top, images below ───────────────
        self._split = tk.PanedWindow(self.frame, orient=tk.VERTICAL,
                                     sashwidth=5, sashrelief=tk.FLAT,
                                     bg="#444", bd=0)
        self._split.pack(fill=tk.BOTH, expand=True)

        # ── Audio section ─────────────────────────────────────────
        self._audio_outer = tk.Frame(self._split, bg="#252525")
        self._split.add(self._audio_outer, height=150, minsize=60, stretch="never")

        audio_hdr = tk.Frame(self._audio_outer, bg="#252525")
        audio_hdr.pack(fill=tk.X)
        tk.Label(audio_hdr, text="Audio", bg="#252525", fg="#888",
                 font=("Helvetica", 8, "bold"), padx=10, pady=4).pack(side=tk.LEFT)
        ttk.Separator(self._audio_outer, orient=tk.HORIZONTAL).pack(fill=tk.X)

        audio_container = tk.Frame(self._audio_outer, bg="#252525")
        audio_container.pack(fill=tk.BOTH, expand=True)

        self._audio_tree = ttk.Treeview(
            audio_container, style="Asset.Treeview",
            show="tree", selectmode="browse",
        )
        audio_sb = ttk.Scrollbar(audio_container, orient=tk.VERTICAL,
                                  command=self._audio_tree.yview)
        self._audio_tree.configure(yscrollcommand=audio_sb.set)
        self._audio_tree.bind("<MouseWheel>",
                              lambda e: self._audio_tree.yview_scroll(
                                  int(-1 * e.delta / 120), "units"))
        self._audio_tree.bind("<<TreeviewSelect>>", self._on_audio_select)
        self._audio_tree.bind("<Button-3>", self._on_audio_right_click)
        audio_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._audio_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._audio_ctx = tk.Menu(self._audio_tree, tearoff=0)
        self._audio_ctx.add_command(label="Add Asset Folder…", command=self._load_folder)
        self._audio_ctx.add_separator()
        self._audio_ctx.add_command(label="Remove Folder", command=self._remove_ctx_audio_folder)

        # ── Image section ─────────────────────────────────────────
        self._image_outer = tk.Frame(self._split, bg="#252525")
        self._split.add(self._image_outer, minsize=60, stretch="always")

        image_hdr = tk.Frame(self._image_outer, bg="#252525")
        image_hdr.pack(fill=tk.X)
        tk.Label(image_hdr, text="Images", bg="#252525", fg="#888",
                 font=("Helvetica", 8, "bold"), padx=10, pady=4).pack(side=tk.LEFT)
        ttk.Separator(self._image_outer, orient=tk.HORIZONTAL).pack(fill=tk.X)

        image_container = tk.Frame(self._image_outer, bg="#252525")
        image_container.pack(fill=tk.BOTH, expand=True)

        self._image_tree = ttk.Treeview(
            image_container, style="Asset.Treeview",
            show="tree", selectmode="extended",
        )
        image_sb = ttk.Scrollbar(image_container, orient=tk.VERTICAL,
                                  command=self._image_tree.yview)
        self._image_tree.configure(yscrollcommand=image_sb.set)
        self._image_tree.bind("<MouseWheel>",
                              lambda e: self._image_tree.yview_scroll(
                                  int(-1 * e.delta / 120), "units"))
        self._image_tree.bind("<<TreeviewSelect>>", self._on_image_select)
        self._image_tree.bind("<Button-3>", self._on_image_right_click)
        image_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._image_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._image_ctx = tk.Menu(self._image_tree, tearoff=0)
        self._image_ctx.add_command(label="Add Asset Folder…", command=self._load_folder)
        self._image_ctx.add_separator()
        self._image_ctx.add_command(label="Remove Folder", command=self._remove_ctx_image_folder)

    # ── Public API ────────────────────────────────────────────────

    def get_selected_assets(self) -> list:
        result = []
        for item_id in self._audio_tree.selection():
            node = self._audio_nodes.get(item_id)
            if node and node["type"] == "audio_clip":
                result.append(node)
            break  # single select — stop after first
        seen = set()
        for item_id in self._image_tree.selection():
            node = self._image_nodes.get(item_id)
            if not node:
                continue
            if node["type"] == "folder":
                self._collect_from_folder(item_id, result, seen)
            elif item_id not in seen:
                result.append(node)
                seen.add(item_id)
        return result

    def apply_theme(self, colors):
        bg = colors["bg_dark"]
        self.frame.config(bg=bg)
        self._header_frame.config(bg=bg)
        self._header_lbl.config(bg=bg, fg=colors["fg_primary"])
        self._close_btn.config(bg=bg, fg=colors["fg_dim_alt"],
                               activebackground=colors["bg_medium"],
                               activeforeground=colors["fg_primary"])
        self._audio_outer.config(bg=bg)
        self._image_outer.config(bg=bg)
        self._style.configure(
            "Asset.Treeview",
            background=colors["bg_dark"],
            foreground=colors.get("fg_secondary_alt", colors["fg_secondary"]),
            fieldbackground=colors["bg_dark"],
        )
        self._style.map(
            "Asset.Treeview",
            background=[("selected", colors["selected_bg"])],
            foreground=[("selected", colors.get("selected_fg", colors["fg_primary"]))],
        )

    # ── Private ───────────────────────────────────────────────────

    def _load_folder(self):
        """Load a folder: .info audio files go to Audio section, images to Images section."""
        path = filedialog.askdirectory(title="Load Asset Folder")
        if not path:
            return
        if path not in self._audio_roots:
            tree_data = _scan_audio_folder(path)
            if tree_data["children"]:
                root_id = self._insert_audio_node("", tree_data, open_root=True)
                self._audio_roots[path] = root_id
        if path not in self._image_roots:
            tree_data = _scan_images_folder(path)
            if tree_data["children"]:
                root_id = self._insert_image_node("", tree_data, open_root=True)
                self._image_roots[path] = root_id

    def _insert_audio_node(self, parent_id: str, node: dict, open_root: bool = False) -> str:
        ntype   = node["type"]
        icon    = self._icons.get(ntype)
        is_root = parent_id == "" and ntype == "folder"
        item_id = self._audio_tree.insert(
            parent_id, "end",
            text=f"  {node['name']}",
            image=icon,
            open=(is_root and open_root),
        )
        self._audio_nodes[item_id] = {"type": ntype, "path": node["path"]}
        for child in node["children"]:
            self._insert_audio_node(item_id, child)
        return item_id

    def _purge_audio_node(self, item_id: str):
        for child in self._audio_tree.get_children(item_id):
            self._purge_audio_node(child)
        self._audio_nodes.pop(item_id, None)

    def _insert_image_node(self, parent_id: str, node: dict, open_root: bool = False) -> str:
        ntype   = node["type"]
        icon    = self._icons.get(ntype)
        is_root = parent_id == "" and ntype == "folder"
        item_id = self._image_tree.insert(
            parent_id, "end",
            text=f"  {node['name']}",
            image=icon,
            open=(is_root and open_root),
        )
        self._image_nodes[item_id] = {"type": ntype, "path": node["path"]}
        for child in node["children"]:
            self._insert_image_node(item_id, child)
        return item_id

    def _on_audio_select(self, _event=None):
        for item_id in self._audio_tree.selection():
            node = self._audio_nodes.get(item_id)
            if node and node["type"] == "audio_clip" and self._on_select:
                self._on_select(node)
            break
        if self._on_selection_change:
            self._on_selection_change()

    def _on_image_select(self, _event=None):
        for item_id in self._image_tree.selection():
            node = self._image_nodes.get(item_id)
            if node and node["type"] != "folder":
                if self._on_select:
                    self._on_select(node)
                break
        if self._on_selection_change:
            self._on_selection_change()

    def _on_audio_right_click(self, event):
        item = self._audio_tree.identify_row(event.y)
        is_root_folder = (
            item
            and self._audio_nodes.get(item, {}).get("type") == "folder"
            and self._audio_tree.parent(item) == ""
        )
        if is_root_folder:
            self._audio_tree.selection_set(item)
            self._ctx_audio_item = item
            self._audio_ctx.entryconfig("Remove Folder", state=tk.NORMAL)
        else:
            self._ctx_audio_item = None
            self._audio_ctx.entryconfig("Remove Folder", state=tk.DISABLED)
        self._audio_ctx.post(event.x_root, event.y_root)

    def _remove_ctx_audio_folder(self):
        item = self._ctx_audio_item
        if not item:
            return
        node = self._audio_nodes.get(item)
        if node:
            self._audio_roots.pop(node["path"], None)
        self._purge_audio_node(item)
        self._audio_tree.delete(item)
        self._ctx_audio_item = None

    def _on_image_right_click(self, event):
        item = self._image_tree.identify_row(event.y)
        is_root_folder = (
            item
            and self._image_nodes.get(item, {}).get("type") == "folder"
            and self._image_tree.parent(item) == ""
        )
        if is_root_folder:
            self._image_tree.selection_set(item)
            self._ctx_item = item
            self._image_ctx.entryconfig("Remove Folder", state=tk.NORMAL)
        else:
            self._ctx_item = None
            self._image_ctx.entryconfig("Remove Folder", state=tk.DISABLED)
        self._image_ctx.post(event.x_root, event.y_root)

    def _remove_ctx_image_folder(self):
        item = self._ctx_item
        if not item:
            return
        node = self._image_nodes.get(item)
        if node:
            self._image_roots.pop(node["path"], None)
        self._purge_image_node(item)
        self._image_tree.delete(item)
        self._ctx_item = None

    def _collect_from_folder(self, item_id: str, result: list, seen: set):
        for child_id in self._image_tree.get_children(item_id):
            node = self._image_nodes.get(child_id)
            if not node:
                continue
            if node["type"] == "folder":
                self._collect_from_folder(child_id, result, seen)
            elif child_id not in seen:
                result.append(node)
                seen.add(child_id)

    def _purge_image_node(self, item_id: str):
        for child in self._image_tree.get_children(item_id):
            self._purge_image_node(child)
        self._image_nodes.pop(item_id, None)
