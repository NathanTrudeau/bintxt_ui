"""Main application window."""

import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from .file_panel import FilePanel
from .log_panel import LogPanel
from .git_panel import GitPanel

# ── Theme constants ───────────────────────────────────────────────────────────
BG       = "#1e1e2e"
SURFACE  = "#181825"
SURFACE2 = "#24243a"
BORDER   = "#313244"
TEXT     = "#cdd6f4"
MUTED    = "#6c7086"
ACCENT   = "#89b4fa"
GREEN    = "#a6e3a1"
YELLOW   = "#f9e2af"
RED      = "#f38ba8"
FONT     = ("Segoe UI", 10)
FONT_SM  = ("Segoe UI", 9)
FONT_B   = ("Segoe UI", 10, "bold")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("bintxt_ui")
        self.geometry("1200x750")
        self.minsize(900, 600)
        self.configure(bg=BG)

        self.repo_path: Path | None = None

        self._style()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

    # ── ttk style ─────────────────────────────────────────────────────────────

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".",
            background=BG, foreground=TEXT,
            fieldbackground=SURFACE2, font=FONT,
            bordercolor=BORDER, troughcolor=SURFACE,
            insertcolor=TEXT, selectbackground=ACCENT,
            selectforeground=BG,
        )
        s.configure("TFrame",   background=BG)
        s.configure("TSash",    sashthickness=4, background=BORDER)
        s.configure("TButton",
            background=SURFACE2, foreground=TEXT,
            borderwidth=1, relief="flat", padding=(8, 4),
            font=FONT,
        )
        s.map("TButton",
            background=[("active", ACCENT), ("pressed", ACCENT)],
            foreground=[("active", BG),     ("pressed", BG)],
        )
        s.configure("Accent.TButton",
            background=ACCENT, foreground=BG, font=FONT_B,
        )
        s.map("Accent.TButton",
            background=[("active", "#74c7ec"), ("pressed", "#74c7ec")],
        )
        s.configure("TLabel",   background=BG,      foreground=TEXT, font=FONT)
        s.configure("Muted.TLabel", background=BG,  foreground=MUTED, font=FONT_SM)
        s.configure("TEntry",
            fieldbackground=SURFACE2, foreground=TEXT,
            borderwidth=1, relief="flat", font=FONT,
        )
        s.configure("TCombobox",
            fieldbackground=SURFACE2, foreground=TEXT,
            borderwidth=1, font=FONT,
        )
        s.map("TCombobox",
            fieldbackground=[("readonly", SURFACE2)],
            selectbackground=[("readonly", SURFACE2)],
        )
        s.configure("Treeview",
            background=SURFACE, foreground=TEXT,
            fieldbackground=SURFACE, borderwidth=0,
            rowheight=24, font=FONT,
        )
        s.configure("Treeview.Heading",
            background=SURFACE2, foreground=MUTED,
            borderwidth=0, font=FONT_SM,
        )
        s.map("Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", BG)],
        )
        s.configure("TPanedwindow", background=BORDER)

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=SURFACE, height=44)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        # Logo / title
        tk.Label(bar, text="  bintxt_ui", bg=SURFACE, fg=ACCENT,
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=(8, 16))

        ttk.Button(bar, text="Open Repo",   command=self._open_repo).pack(side="left", padx=2)
        ttk.Separator(bar, orient="vertical").pack(side="left", padx=8, fill="y", pady=8)
        ttk.Button(bar, text="▶  Run All",  command=self._run_all,
                   style="Accent.TButton").pack(side="left", padx=2)
        ttk.Button(bar, text="Pack",        command=self._run_pack).pack(side="left", padx=2)
        ttk.Button(bar, text="Unpack",      command=self._run_unpack).pack(side="left", padx=2)
        ttk.Button(bar, text="Verify",      command=self._run_verify).pack(side="left", padx=2)

        self._repo_label = tk.Label(bar, text="No repo open", bg=SURFACE, fg=MUTED, font=FONT_SM)
        self._repo_label.pack(side="right", padx=16)

    # ── Body ──────────────────────────────────────────────────────────────────

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(side="top", fill="both", expand=True)

        # Horizontal split: left (files) | right (log + git stacked)
        h_pane = ttk.PanedWindow(body, orient="horizontal")
        h_pane.pack(fill="both", expand=True, padx=0, pady=0)

        # Left — file panel
        self.file_panel = FilePanel(h_pane, app=self)
        h_pane.add(self.file_panel, weight=1)

        # Right — vertical split: log on top, git on bottom
        v_pane = ttk.PanedWindow(h_pane, orient="vertical")
        h_pane.add(v_pane, weight=2)

        self.log_panel = LogPanel(v_pane)
        v_pane.add(self.log_panel, weight=3)

        self.git_panel = GitPanel(v_pane, app=self)
        v_pane.add(self.git_panel, weight=1)

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=SURFACE, height=22)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)
        self._status_var = tk.StringVar(value="Ready")
        tk.Label(bar, textvariable=self._status_var,
                 bg=SURFACE, fg=MUTED, font=FONT_SM,
                 anchor="w").pack(side="left", padx=8)

    def set_status(self, msg: str):
        self._status_var.set(msg)
        self.update_idletasks()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _open_repo(self):
        path = filedialog.askdirectory(title="Select repo folder")
        if not path:
            return
        self.repo_path = Path(path)
        short = self.repo_path.name
        self._repo_label.config(text=f"  {short}  ", fg=ACCENT)
        self.title(f"bintxt_ui — {short}")
        self.file_panel.load_repo(self.repo_path)
        self.git_panel.load_repo(self.repo_path)
        self.set_status(f"Opened: {self.repo_path}")

    def _require_repo(self) -> bool:
        if self.repo_path is None:
            messagebox.showwarning("No Repo", "Open a repo folder first.")
            return False
        return True

    def _run_all(self):
        if not self._require_repo():
            return
        self.file_panel.run_pipeline(mode="all")

    def _run_pack(self):
        if not self._require_repo():
            return
        self.file_panel.run_pipeline(mode="pack")

    def _run_unpack(self):
        if not self._require_repo():
            return
        self.file_panel.run_pipeline(mode="unpack")

    def _run_verify(self):
        if not self._require_repo():
            return
        self.file_panel.run_pipeline(mode="verify")
