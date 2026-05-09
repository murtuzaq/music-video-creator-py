import os
import tkinter as tk


def fmt_duration(seconds: float) -> str:
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def fmt_size(path: str) -> str:
    try:
        b = os.path.getsize(path)
        if b < 1024:      return f"{b} B"
        if b < 1024 ** 2: return f"{b / 1024:.1f} KB"
        return f"{b / 1024 ** 2:.1f} MB"
    except Exception:
        return "—"


def field_label(body: tk.Frame, text: str, colors: dict):
    tk.Label(body, text=text, bg=colors["bg_darkest"],
             fg=colors["fg_dim_alt"],
             font=("Helvetica", 8), anchor="w").pack(fill=tk.X)


def info_row(body: tk.Frame, label: str, value: str, colors: dict):
    bg = colors["bg_darkest"]
    row = tk.Frame(body, bg=bg)
    row.pack(fill=tk.X, pady=2)
    tk.Label(row, text=label + ":", bg=bg, fg=colors["fg_dim_alt"],
             font=("Helvetica", 8), width=5, anchor="w").pack(side=tk.LEFT)
    val_lbl = tk.Label(row, text=value, bg=bg, fg=colors["fg_value"],
                       font=("Helvetica", 8), anchor="w", justify=tk.LEFT)
    val_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
    row.bind("<Configure>",
             lambda e, l=val_lbl: l.configure(wraplength=max(1, e.width - 52)))
