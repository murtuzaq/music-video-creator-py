import os
import tkinter as tk
from tkinter import ttk

try:
    from PIL import Image, ImageTk
    _PIL = True
except ImportError:
    _PIL = False

_ICON_SPEC = {
    "video": "#e05c00",
    "audio": "#4a90d9",
    "image": "#5cb85c",
}


def _make_icon(color: str):
    if not _PIL:
        return None
    img = Image.new("RGB", (14, 14), color)
    return ImageTk.PhotoImage(img)


class ProjectPanel:
    def __init__(self, parent, on_select=None, on_close=None):
        self._on_select = on_select
        self._icons     = {t: _make_icon(c) for t, c in _ICON_SPEC.items()}
        self._nodes     = {}   # item_id -> {"type", "path", "name"}

        self.frame = tk.Frame(parent, bg="#252525")
        self.frame.pack(fill=tk.BOTH, expand=True)

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

        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

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

    def set_root(self, project_name: str) -> str:
        self.clear()
        item_id = self._tree.insert("", "end",
                                    text=f"  {project_name}",
                                    image=self._icons.get("video"),
                                    open=True)
        self._nodes[item_id] = {"type": "video", "path": None, "name": project_name}
        return item_id

    def add_node(self, parent_id: str, node_type: str, path: str) -> str:
        name = os.path.basename(path) if path else node_type
        item_id = self._tree.insert(parent_id, "end",
                                    text=f"  {name}",
                                    image=self._icons.get(node_type),
                                    open=True)
        self._nodes[item_id] = {"type": node_type, "path": path, "name": None}
        self._tree.item(parent_id, open=True)
        return item_id

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

    def get_tree_data(self):
        root_id = self.get_root_id()
        return self._node_to_dict(root_id) if root_id else None

    def clear(self):
        for item in self._tree.get_children(""):
            self._tree.delete(item)
        self._nodes.clear()

    def rebuild(self, tree_data: dict):
        self.clear()
        if tree_data:
            self._dict_to_tree("", tree_data)

    # ── Private ───────────────────────────────────────────────────

    def _node_to_dict(self, item_id: str) -> dict:
        node = self._nodes.get(item_id, {})
        return {
            "type":     node.get("type"),
            "path":     node.get("path"),
            "name":     node.get("name"),
            "children": [self._node_to_dict(c)
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
        self._nodes[item_id] = {"type": node_type, "path": path, "name": node_data.get("name")}
        for child in node_data.get("children", []):
            self._dict_to_tree(item_id, child)
        return item_id

    def _on_tree_select(self, _event=None):
        item_id, node = self.get_selected_item()
        if item_id and self._on_select:
            self._on_select(node)
