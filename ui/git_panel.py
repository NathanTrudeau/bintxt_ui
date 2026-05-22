"""Git panel — branch selector, commit, tag, push controls."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from pathlib import Path

from engine.git_runner import (
    GitError,
    current_branch, list_branches, list_tags,
    status, remotes,
    create_branch, checkout_branch,
    stage_all, commit,
    create_tag, push,
)

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
FONT_B  = ("Segoe UI", 10, "bold")


class GitPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.repo_path: Path | None = None
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=SURFACE)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  Git", bg=SURFACE, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(side="left", pady=6)
        ttk.Button(hdr, text="⟳ Refresh",
                   command=self._refresh).pack(side="right", padx=4, pady=2)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=8, pady=8)

        # Row 1 — branch controls
        row1 = tk.Frame(body, bg=BG)
        row1.pack(fill="x", pady=(0, 6))

        tk.Label(row1, text="Branch:", bg=BG, fg=MUTED, font=FONT_SM, width=9,
                 anchor="w").pack(side="left")
        self._branch_var = tk.StringVar()
        self._branch_cb = ttk.Combobox(row1, textvariable=self._branch_var,
                                       state="readonly", width=24, font=FONT)
        self._branch_cb.pack(side="left", padx=(0, 6))
        self._branch_cb.bind("<<ComboboxSelected>>", self._on_branch_select)

        ttk.Button(row1, text="New Branch", command=self._new_branch).pack(side="left", padx=2)

        # Row 2 — status indicator
        row2 = tk.Frame(body, bg=BG)
        row2.pack(fill="x", pady=(0, 6))
        tk.Label(row2, text="Status:", bg=BG, fg=MUTED, font=FONT_SM, width=9,
                 anchor="w").pack(side="left")
        self._status_var = tk.StringVar(value="—")
        tk.Label(row2, textvariable=self._status_var, bg=BG, fg=MUTED,
                 font=FONT_SM, anchor="w").pack(side="left")

        # Row 3 — commit
        row3 = tk.Frame(body, bg=BG)
        row3.pack(fill="x", pady=(0, 6))
        tk.Label(row3, text="Commit:", bg=BG, fg=MUTED, font=FONT_SM, width=9,
                 anchor="w").pack(side="left")
        self._commit_var = tk.StringVar()
        ttk.Entry(row3, textvariable=self._commit_var, width=36,
                  font=FONT).pack(side="left", padx=(0, 6))
        ttk.Button(row3, text="Stage & Commit",
                   command=self._do_commit).pack(side="left", padx=2)

        # Row 4 — tag + push
        row4 = tk.Frame(body, bg=BG)
        row4.pack(fill="x", pady=(0, 4))
        tk.Label(row4, text="Tag:", bg=BG, fg=MUTED, font=FONT_SM, width=9,
                 anchor="w").pack(side="left")
        self._tag_var = tk.StringVar()
        ttk.Entry(row4, textvariable=self._tag_var, width=20,
                  font=FONT).pack(side="left", padx=(0, 6))
        ttk.Button(row4, text="Create Tag",
                   command=self._do_tag).pack(side="left", padx=2)

        ttk.Separator(row4, orient="vertical").pack(side="left", padx=10, fill="y")

        self._remote_var = tk.StringVar()
        self._remote_cb = ttk.Combobox(row4, textvariable=self._remote_var,
                                       state="readonly", width=10, font=FONT)
        self._remote_cb.pack(side="left", padx=(0, 4))
        ttk.Button(row4, text="Push", style="Accent.TButton",
                   command=self._do_push).pack(side="left", padx=2)
        ttk.Button(row4, text="Push + Tags",
                   command=lambda: self._do_push(tags=True)).pack(side="left", padx=2)

    # ── Load ──────────────────────────────────────────────────────────────────

    def load_repo(self, repo_path: Path):
        self.repo_path = repo_path
        self._refresh()

    def _refresh(self):
        if self.repo_path is None:
            return
        try:
            branch  = current_branch(self.repo_path)
            branches = list_branches(self.repo_path)
            stat    = status(self.repo_path).strip()
            remote_list = remotes(self.repo_path)

            self._branch_cb['values'] = branches
            self._branch_var.set(branch)

            if stat:
                lines = stat.splitlines()
                self._status_var.set(f"{len(lines)} change(s)")
            else:
                self._status_var.set("clean")

            self._remote_cb['values'] = remote_list
            if remote_list and not self._remote_var.get():
                self._remote_var.set(remote_list[0])

        except GitError as e:
            self._status_var.set(f"git error: {e}")
        except Exception:
            self._status_var.set("not a git repo")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_branch_select(self, _event):
        selected = self._branch_var.get()
        if not self.repo_path or not selected:
            return
        try:
            checkout_branch(self.repo_path, selected)
            self.app.log_panel.ok(f"Switched to branch: {selected}")
            self._refresh()
        except GitError as e:
            messagebox.showerror("Git Error", str(e))

    def _new_branch(self):
        if not self.repo_path:
            return
        name = simpledialog.askstring(
            "New Branch",
            "Branch name:\n(e.g. sn-A4F2 for SOC serial A4F2)",
            parent=self,
        )
        if not name:
            return
        try:
            create_branch(self.repo_path, name, checkout=True)
            self.app.log_panel.ok(f"Created and checked out branch: {name}")
            self._refresh()
        except GitError as e:
            messagebox.showerror("Git Error", str(e))

    def _do_commit(self):
        if not self.repo_path:
            return
        msg = self._commit_var.get().strip()
        if not msg:
            messagebox.showwarning("Empty Message", "Enter a commit message first.")
            return
        def _worker():
            try:
                stage_all(self.repo_path)
                commit(self.repo_path, msg)
                self.app.log_panel.ok(f"Committed: {msg}")
                self._commit_var.set("")
                self.after(0, self._refresh)
            except GitError as e:
                self.after(0, lambda: messagebox.showerror("Git Error", str(e)))
        threading.Thread(target=_worker, daemon=True).start()

    def _do_tag(self):
        if not self.repo_path:
            return
        tag = self._tag_var.get().strip()
        if not tag:
            messagebox.showwarning("Empty Tag", "Enter a tag name first.")
            return
        msg = simpledialog.askstring(
            "Tag Message",
            f"Optional annotation for tag '{tag}'\n(leave blank for lightweight tag):",
            parent=self,
        ) or ""
        try:
            create_tag(self.repo_path, tag, message=msg)
            self.app.log_panel.ok(f"Created tag: {tag}")
            self._tag_var.set("")
        except GitError as e:
            messagebox.showerror("Git Error", str(e))

    def _do_push(self, tags: bool = False):
        if not self.repo_path:
            return
        remote = self._remote_var.get() or "origin"
        branch = self._branch_var.get()
        label  = f"{remote}/{branch}" + (" + tags" if tags else "")
        self.app.log_panel.info(f"Pushing to {label}…")
        def _worker():
            try:
                push(self.repo_path, remote=remote, branch=branch, tags=tags)
                self.app.log_panel.ok(f"Pushed to {label}")
                self.after(0, self._refresh)
            except GitError as e:
                self.after(0, lambda: messagebox.showerror("Git Push Error", str(e)))
        threading.Thread(target=_worker, daemon=True).start()
