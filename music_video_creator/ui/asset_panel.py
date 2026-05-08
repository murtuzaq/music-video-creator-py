import os
import tkinter as tk
from tkinter import ttk, filedialog

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff", ".tif"}
_AUDIO_EXT = {".mp3", ".wav", ".aac", ".ogg", ".flac", ".m4a", ".wma"}

_ICON_COLORS = {
    "folder": "#888888",
    "image":  "#5cb85c",
    "audio":  "#4a90d9",
}


def _make_icon(color: str):
    if not _PIL:
        return None
    img = Image.new("RGB", (14, 14), color)
    return ImageTk.PhotoImage(img)


def _scan_folder(root_path: str) -> dict:
    """Recursively build a tree dict for a folder."""
    name = os.path.basename(root_path) or root_path
    children = []
    try:
        entries = sorted(
            os.scandir(root_path),
            key=lambda e: (not e.is_dir(), e.name.lower()),
        )
        for entry in entries:
            if entry.is_dir():
                child = _scan_folder(entry.path)
                if child["children"]:
                    children.append(child)
            elif entry.is_file():
                ext = os.path.splitext(entry.name)[1].lower()
                if ext in _IMAGE_EXT:
                    children.append({"name": entry.name, "path": entry.path,
                                     "type": "image", "children": []})
                elif ext in _AUDIO_EXT:
                    children.append({"name": entry.name, "path": entry.path,
                                     "type": "audio", "children": []})
    except PermissionError:
        pass
    return {"name": name, "path": root_path, "type": "folder", "children": children}


class AssetPanel:
    def __init__(self, parent, on_select=None, on_close=None):
        self._on_select = on_select
        self._nodes     = {}   # item_id -> {"type", "path"}
        self._roots     = {}   # root_path -> item_id (top-level loaded folders)
        self._icons     = {k: _make_icon(c) for k, c in _ICON_COLORS.items()}
        self._ctx_item  = None

        self.frame = tk.Frame(parent, bg="#252525")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # ── header ──────────────────────────────────────────────────
        self._header_frame = tk.Frame(self.frame, bg="#252525")
        self._header_frame.pack(fill=tk.X)

        self._header_lbl = tk.Label(
            self._header_frame, text="Assets", bg="#252525", fg="white",
            font=("Helvetica", 10, "bold"), anchor="w", padx=10, pady=7,
        )
        self._header_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._close_btn = tk.Button(self._header_frame, text="×", command=on_close,
                                    bg="#252525", fg="#888", relief=tk.FLAT,
                                    font=("Helvetica", 12), padx=8, pady=3,
                                    cursor="hand2", activebackground="#2b2b2b",
                                    activeforeground="white", bd=0)
        self._close_btn.pack(side=tk.RIGHT)

        ttk.Separator(self.frame, orient=tk.HORIZONTAL).pack(fill=tk.X)

        # ── treeview ─────────────────────────────────────────────────
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

        self._container = tk.Frame(self.frame, bg="#252525")
        self._container.pack(fill=tk.BOTH, expand=True)

        self._tree = ttk.Treeview(
            self._container, style="Asset.Treeview",
            show="tree", selectmode="browse",
        )
        sb = ttk.Scrollbar(self._container, orient=tk.VERTICAL,
                           command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.bind("<MouseWheel>",
                        lambda e: self._tree.yview_scroll(
                            int(-1 * e.delta / 120), "units"))
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.bind("<Button-3>", self._on_right_click)

        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # right-click context menu
        self._ctx_menu = tk.Menu(self._tree, tearoff=0)
        self._ctx_menu.add_command(label="Add Asset Folder…", command=self._load_folder)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="Remove Folder", command=self._remove_ctx_folder)

    # ── Public API ────────────────────────────────────────────────

    def apply_theme(self, colors):
        bg = colors["bg_dark"]
        self.frame.config(bg=bg)
        self._header_frame.config(bg=bg)
        self._header_lbl.config(bg=bg, fg=colors["fg_primary"])
        self._close_btn.config(bg=bg, fg=colors["fg_dim_alt"],
                               activebackground=colors["bg_medium"],
                               activeforeground=colors["fg_primary"])
        self._container.config(bg=bg)
        self._style.configure(
            "Asset.Treeview",
            background=colors["bg_dark"],
            foreground=colors["fg_secondary_alt"],
            fieldbackground=colors["bg_dark"],
        )
        self._style.map(
            "Asset.Treeview",
            background=[("selected", colors["selected_bg"])],
            foreground=[("selected", colors["selected_fg"])],
        )

    # ── Private ───────────────────────────────────────────────────

    def _load_folder(self):
        path = filedialog.askdirectory(title="Load Asset Folder")
        if not path or path in self._roots:
            return
        tree_data = _scan_folder(path)
        if not tree_data["children"]:
            return
        root_id = self._insert_node("", tree_data, open_root=True)
        self._roots[path] = root_id

    def _insert_node(self, parent_id: str, node: dict,
                     open_root: bool = False) -> str:
        ntype  = node["type"]
        icon   = self._icons.get(ntype)
        is_root = parent_id == "" and ntype == "folder"
        item_id = self._tree.insert(
            parent_id, "end",
            text=f"  {node['name']}",
            image=icon,
            open=(is_root and open_root),
        )
        self._nodes[item_id] = {"type": ntype, "path": node["path"]}
        for child in node["children"]:
            self._insert_node(item_id, child)
        return item_id

    def _on_tree_select(self, _event=None):
        sel = self._tree.selection()
        if not sel:
            return
        node = self._nodes.get(sel[0])
        if node and node["type"] != "folder" and self._on_select:
            self._on_select(node)

    def _on_right_click(self, event):
        item = self._tree.identify_row(event.y)
        is_root_folder = (
            item
            and self._nodes.get(item, {}).get("type") == "folder"
            and self._tree.parent(item) == ""
        )
        if is_root_folder:
            self._tree.selection_set(item)
            self._ctx_item = item
            self._ctx_menu.entryconfig("Remove Folder", state=tk.NORMAL)
        else:
            self._ctx_item = None
            self._ctx_menu.entryconfig("Remove Folder", state=tk.DISABLED)
        self._ctx_menu.post(event.x_root, event.y_root)

    def _remove_ctx_folder(self):
        item = self._ctx_item
        if not item:
            return
        node = self._nodes.get(item)
        if node:
            self._roots.pop(node["path"], None)
        self._purge_node(item)
        self._tree.delete(item)
        self._ctx_item = None

    def _purge_node(self, item_id: str):
        for child in self._tree.get_children(item_id):
            self._purge_node(child)
        self._nodes.pop(item_id, None)
