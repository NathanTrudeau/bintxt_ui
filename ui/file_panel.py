"""File panel — lists all .bin/.txt pairs with sync status."""

import tkinter as tk
from tkinter import ttk
from pathlib import Path

BG      = "#1e1e2e"
SURFACE = "#181825"
BORDER  = "#313244"
TEXT    = "#cdd6f4"
MUTED   = "#6c7086"
ACCENT  = "#89b4fa"
GREEN   = "#a6e3a1"
YELLOW  = "#f9e2af"
RED     = "#f38ba8"
FONT    = ("Segoe UI", 10)
FONT_SM = ("Segoe UI", 9)


class FilePanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app  = app
        self.repo = None
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=SURFACE)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  Files", bg=SURFACE, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(side="left", pady=6)

        fbar = tk.Frame(self, bg=BG)
        fbar.pack(fill="x", padx=4, pady=(4, 0))
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._apply_filter())
        ttk.Entry(fbar, textvariable=self._filter_var,
                  width=22).pack(side="left", padx=2)
        tk.Label(fbar, text="filter", bg=BG, fg=MUTED, font=FONT_SM).pack(side="left")

        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=("file", "status"),
            show="headings",
            selectmode="extended",
        )
        self._tree.heading("file",   text="File",   anchor="w")
        self._tree.heading("status", text="Status", anchor="w")
        self._tree.column("file",    width=160, stretch=True)
        self._tree.column("status",  width=90,  stretch=False)

        self._tree.tag_configure("ok",       foreground=GREEN)
        self._tree.tag_configure("txt_only", foreground=ACCENT)
        self._tree.tag_configure("bin_only", foreground=YELLOW)
        self._tree.tag_configure("no_yaml",  foreground=MUTED)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        self._all_rows: list[tuple] = []

    # ── Load ──────────────────────────────────────────────────────────────────

    def load_repo(self, repo):
        self.repo = repo
        self._tree.delete(*self._tree.get_children())
        self._all_rows = []

        if repo is None:
            return

        bins = {p.stem for p in repo.discover_bins()}
        txts = {p.stem for p in repo.discover_txts()}
        all_bases = sorted(bins | txts)

        for base in all_bases:
            has_bin = base in bins
            has_txt = base in txts

            if has_bin and has_txt:
                status, tag = "✓ ready", "ok"
            elif has_txt and not has_bin:
                status, tag = "· txt only", "txt_only"
            elif has_bin and not has_txt:
                status, tag = "⚠ bin only", "bin_only"
            else:
                status, tag = "— unknown", "no_yaml"

            iid = self._tree.insert("", "end", iid=base,
                                    values=(base, status), tags=(tag,))
            self._all_rows.append((iid, base, status))

        self._apply_filter()

    def _apply_filter(self):
        query = self._filter_var.get().lower()
        for iid, base, status in self._all_rows:
            try:
                if query and query not in base.lower():
                    self._tree.detach(iid)
                else:
                    self._tree.reattach(iid, "", "end")
            except tk.TclError:
                pass

    def _on_select(self, _event):
        sel = self._tree.selection()
        if sel:
            self.app.on_file_selected(sel[0])

    def selected_bases(self) -> list[str]:
        return list(self._tree.selection())
