"""Main application window."""

import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from engine.repo_manager import RepoManager
from .file_panel  import FilePanel
from .detail_panel import DetailPanel
from .log_panel   import LogPanel
from .git_panel   import GitPanel

# ── Theme ─────────────────────────────────────────────────────────────────────
BG      = "#1e1e2e"
SURFACE = "#181825"
BORDER  = "#313244"
TEXT    = "#cdd6f4"
MUTED   = "#6c7086"
ACCENT  = "#89b4fa"
GREEN   = "#a6e3a1"
YELLOW  = "#f9e2af"
FONT    = ("Segoe UI", 10)
FONT_SM = ("Segoe UI", 9)
FONT_B  = ("Segoe UI", 10, "bold")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("bintxt_ui")
        self.geometry("1300x800")
        self.minsize(1000, 650)
        self.configure(bg=BG)

        self.repo:    RepoManager | None = None
        self.repo_path: Path | None     = None

        self._style()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

        # Keyboard shortcuts
        self.bind("<F5>",        lambda _: self._run_build())
        self.bind("<Control-r>", lambda _: self._refresh())
        self.bind("<Control-o>", lambda _: self._open_repo())

    # ── ttk style ─────────────────────────────────────────────────────────────

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT,
            fieldbackground=SURFACE, font=FONT,
            bordercolor=BORDER, troughcolor=SURFACE,
            insertcolor=TEXT, selectbackground=ACCENT, selectforeground=BG)
        s.configure("TFrame",   background=BG)
        s.configure("TSash",    sashthickness=5, background=BORDER)
        s.configure("TButton",  background=SURFACE, foreground=TEXT,
            borderwidth=1, relief="flat", padding=(8, 4))
        s.map("TButton",
            background=[("active", ACCENT), ("pressed", ACCENT)],
            foreground=[("active", BG),     ("pressed", BG)])
        s.configure("Accent.TButton", background=ACCENT, foreground=BG, font=FONT_B)
        s.map("Accent.TButton",
            background=[("active", "#74c7ec"), ("pressed", "#74c7ec")])
        s.configure("Warn.TButton", background="#f9e2af", foreground=BG, font=FONT_B)
        s.map("Warn.TButton",
            background=[("active", "#fab387"), ("pressed", "#fab387")])
        s.configure("TLabel",   background=BG,     foreground=TEXT, font=FONT)
        s.configure("Muted.TLabel", background=BG, foreground=MUTED, font=FONT_SM)
        s.configure("TEntry",   fieldbackground=SURFACE, foreground=TEXT,
            borderwidth=1, relief="flat")
        s.configure("TCombobox", fieldbackground=SURFACE, foreground=TEXT,
            borderwidth=1)
        s.map("TCombobox",
            fieldbackground=[("readonly", SURFACE)],
            selectbackground=[("readonly", SURFACE)])
        s.configure("Treeview", background=SURFACE, foreground=TEXT,
            fieldbackground=SURFACE, borderwidth=0, rowheight=24)
        s.configure("Treeview.Heading", background=SURFACE,
            foreground=MUTED, borderwidth=0, font=FONT_SM)
        s.map("Treeview",
            background=[("selected", ACCENT)],
            foreground=[("selected", BG)])
        s.configure("TPanedwindow", background=BORDER)
        s.configure("TSeparator",   background=BORDER)

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=SURFACE, height=46)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        tk.Label(bar, text="  bintxt_ui", bg=SURFACE, fg=ACCENT,
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=(8, 16))

        ttk.Button(bar, text="Open Repo",
                   command=self._open_repo).pack(side="left", padx=2, pady=6)

        ttk.Separator(bar, orient="vertical").pack(side="left", padx=8, fill="y", pady=8)

        self._init_btn = ttk.Button(bar, text="⚡ Initialize",
                                    command=self._run_initialize,
                                    style="Warn.TButton")
        self._init_btn.pack(side="left", padx=2, pady=6)
        self._init_btn.pack_forget()  # hidden until fresh repo opened

        ttk.Button(bar, text="▶  Build", command=self._run_build,
                   style="Accent.TButton").pack(side="left", padx=2, pady=6)

        ttk.Button(bar, text="Cleanup",
                   command=self._run_cleanup).pack(side="left", padx=2, pady=6)

        ttk.Separator(bar, orient="vertical").pack(side="left", padx=8, fill="y", pady=8)

        ttk.Button(bar, text="⟳ Refresh",
                   command=self._refresh).pack(side="left", padx=2, pady=6)

        self._repo_label = tk.Label(bar, text="No repo open",
                                    bg=SURFACE, fg=MUTED, font=FONT_SM)
        self._repo_label.pack(side="right", padx=16)

    # ── Body ──────────────────────────────────────────────────────────────────

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(side="top", fill="both", expand=True)

        # Horizontal: left (file list) | right (detail + log + git stacked)
        h = ttk.PanedWindow(body, orient="horizontal")
        h.pack(fill="both", expand=True)

        self.file_panel = FilePanel(h, app=self)
        h.add(self.file_panel, weight=1)

        right = ttk.PanedWindow(h, orient="vertical")
        h.add(right, weight=3)

        self.detail_panel = DetailPanel(right, app=self)
        right.add(self.detail_panel, weight=4)

        bottom = ttk.PanedWindow(right, orient="horizontal")
        right.add(bottom, weight=2)

        self.log_panel = LogPanel(bottom)
        bottom.add(self.log_panel, weight=2)

        self.git_panel = GitPanel(bottom, app=self)
        bottom.add(self.git_panel, weight=1)

    # ── Status bar ────────────────────────────────────────────────────────────

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=SURFACE, height=22)
        bar.pack(side="bottom", fill="x")
        bar.pack_propagate(False)
        self._status_var = tk.StringVar(value="Ready  |  F5 = Build  |  Ctrl+O = Open Repo")
        tk.Label(bar, textvariable=self._status_var,
                 bg=SURFACE, fg=MUTED, font=FONT_SM, anchor="w").pack(side="left", padx=8)

    def set_status(self, msg: str):
        self._status_var.set(msg)
        self.update_idletasks()

    # ── Actions ───────────────────────────────────────────────────────────────

    def _open_repo(self):
        path = filedialog.askdirectory(title="Select config_files repo")
        if not path:
            return
        self.repo_path = Path(path)
        self.repo      = RepoManager(self.repo_path)
        short = self.repo_path.name
        self._repo_label.config(text=f"  {short}  ", fg=ACCENT)
        self.title(f"bintxt_ui — {short}")

        if self.repo.is_fresh:
            self._init_btn.pack(side="left", padx=2, pady=6, after=self._init_btn)
            # Re-pack to show it
            self._show_init_btn()
            self.set_status(f"Fresh repo: {self.repo_path}  —  click ⚡ Initialize to get started")
            self.log_panel.info(f"Opened: {self.repo_path}")
            self.log_panel.warn("No bintxt_cfg.yaml found. Click ⚡ Initialize to discover and extract binaries.")
        else:
            self._hide_init_btn()
            self.repo.load_cfg()
            self.set_status(f"Opened: {self.repo_path}")
            self.log_panel.info(f"Opened: {self.repo_path}")

        self.file_panel.load_repo(self.repo)
        self.git_panel.load_repo(self.repo_path)
        self.detail_panel.clear()

    def _show_init_btn(self):
        bar_children = self._init_btn.master.pack_slaves()
        self._init_btn.pack(side="left", padx=2, pady=6)

    def _hide_init_btn(self):
        self._init_btn.pack_forget()

    def _require_repo(self) -> bool:
        if self.repo is None:
            messagebox.showwarning("No Repo", "Open a repo folder first.")
            return False
        return True

    def _run_initialize(self):
        if not self._require_repo():
            return
        self.log_panel.clear()
        self.log_panel.section("Initialize")
        self.set_status("Initializing…")

        def _worker():
            try:
                bases = self.repo.initialize(self.log_panel)
                self.after(0, lambda: self._post_initialize(bases))
            except Exception as e:
                self.log_panel.error(f"Initialize failed: {e}")
                self.after(0, lambda: self.set_status("Initialize failed."))

        threading.Thread(target=_worker, daemon=True).start()

    def _post_initialize(self, bases):
        self._hide_init_btn()
        self.file_panel.load_repo(self.repo)
        self.set_status(f"Initialized — {len(bases)} file(s) extracted")

    def _run_build(self):
        if not self._require_repo():
            return
        if self.repo.is_fresh:
            messagebox.showwarning("Not Initialized", "Run Initialize first.")
            return
        self.log_panel.clear()
        self.log_panel.section("Build")
        self.set_status("Building…")

        selected = self.file_panel.selected_bases()
        bases    = selected if selected else None

        def _worker():
            try:
                out = self.repo.build(bases, self.log_panel)
                self.after(0, lambda: self.set_status(f"Build complete → {out.relative_to(self.repo_path)}"))
            except Exception as e:
                self.log_panel.error(f"Build failed: {e}")
                self.after(0, lambda: self.set_status("Build failed."))

        threading.Thread(target=_worker, daemon=True).start()

    def _run_cleanup(self):
        if not self._require_repo():
            return
        if self.repo.is_fresh:
            messagebox.showwarning("Not Initialized", "Run Initialize first.")
            return
        if not messagebox.askyesno(
            "Cleanup",
            "This will:\n"
            "• Update .gitignore so .bin files are ignored\n"
            "• Untrack any .bin files currently in git\n"
            "• Leave .txt + bintxt_cfg.yaml ready to commit\n\n"
            "Proceed?"
        ):
            return
        self.log_panel.clear()
        self.log_panel.section("Cleanup")
        self.repo.cleanup(self.log_panel)
        self.git_panel.load_repo(self.repo_path)
        self.set_status("Cleanup done — commit .txt + YAML in the Git panel")

    def _refresh(self):
        if self.repo is None:
            return
        if not self.repo.is_fresh:
            self.repo.load_cfg()
        self.file_panel.load_repo(self.repo)
        self.set_status("Refreshed")

    def on_file_selected(self, base: str):
        """Called by FilePanel when user selects a file."""
        self.detail_panel.load_file(base, self.repo)
