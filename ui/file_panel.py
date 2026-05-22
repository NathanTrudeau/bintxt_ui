"""File panel — shows .bin/.txt pairs with sync status; triggers pipeline operations."""

import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

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

# Status display values
_ST_SYNCED   = ("✓ synced",    GREEN)
_ST_TXT_ONLY = ("· txt only",  ACCENT)
_ST_BIN_ONLY = ("· bin only",  YELLOW)
_ST_MODIFIED = ("⚠ modified",  YELLOW)
_ST_NO_YAML  = ("? no YAML",   MUTED)
_ST_UNKNOWN  = ("— unknown",   MUTED)


class FilePanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app = app
        self.repo_path: Path | None = None
        self._build()

    def _build(self):
        # Header
        hdr = tk.Frame(self, bg=SURFACE)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  Config Files", bg=SURFACE, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(side="left", pady=6)
        ttk.Button(hdr, text="⟳ Refresh",
                   command=self._refresh).pack(side="right", padx=4, pady=2)

        # Filter bar
        fbar = tk.Frame(self, bg=BG)
        fbar.pack(fill="x", padx=4, pady=(4, 0))
        tk.Label(fbar, text="Filter:", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        self._filter_var = tk.StringVar()
        self._filter_var.trace_add("write", lambda *_: self._apply_filter())
        ttk.Entry(fbar, textvariable=self._filter_var, width=20).pack(side="left", padx=4)

        # Treeview
        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=("file", "status", "has_yaml"),
            show="headings",
            selectmode="extended",
        )
        self._tree.heading("file",     text="File",     anchor="w")
        self._tree.heading("status",   text="Status",   anchor="w")
        self._tree.heading("has_yaml", text="YAML",     anchor="w")
        self._tree.column("file",      width=160, stretch=True)
        self._tree.column("status",    width=100, stretch=False)
        self._tree.column("has_yaml",  width=60,  stretch=False)

        # Tag colours
        self._tree.tag_configure("synced",   foreground=GREEN)
        self._tree.tag_configure("modified", foreground=YELLOW)
        self._tree.tag_configure("bin_only", foreground=YELLOW)
        self._tree.tag_configure("txt_only", foreground=ACCENT)
        self._tree.tag_configure("no_yaml",  foreground=MUTED)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Right-click menu
        self._ctx = tk.Menu(self, tearoff=0, bg=SURFACE, fg=TEXT,
                            activebackground=ACCENT, activeforeground=BG)
        self._ctx.add_command(label="Pack selected",    command=lambda: self.run_pipeline("pack",   selected=True))
        self._ctx.add_command(label="Unpack selected",  command=lambda: self.run_pipeline("unpack", selected=True))
        self._ctx.add_command(label="Verify selected",  command=lambda: self.run_pipeline("verify", selected=True))
        self._ctx.add_separator()
        self._ctx.add_command(label="Show in Explorer", command=self._show_in_explorer)
        self._tree.bind("<Button-3>", self._show_ctx)

        self._all_rows = []   # cache for filter

    # ── Load ──────────────────────────────────────────────────────────────────

    def load_repo(self, repo_path: Path):
        self.repo_path = repo_path
        self._refresh()

    def _refresh(self):
        if self.repo_path is None:
            return
        self._tree.delete(*self._tree.get_children())
        self._all_rows = []

        cfg_file = self.repo_path / 'bintxt_cfg.yaml'
        cfg = {}
        if cfg_file.exists():
            try:
                sys.path.insert(0, str(self.repo_path.parent))
                from bintxt.core.yaml_loader import load_yaml
                cfg = load_yaml(cfg_file.read_text(encoding='utf-8'))
            except Exception:
                pass

        yaml_files = {Path(e.get('file', '')).stem
                      for e in (cfg.get('binaries') or [])
                      if e.get('file')}

        cfg_dir = self.repo_path / (cfg.get('paths', {}).get('config_dir') or 'configs')
        if not cfg_dir.exists():
            self.app.set_status("configs/ folder not found")
            return

        txt_stems = {p.stem for p in cfg_dir.glob('*.txt')}
        bin_stems = {p.stem for p in cfg_dir.glob('*.bin')}
        all_bases = sorted(txt_stems | bin_stems)

        # Try to load state for hash comparison
        state = {}
        try:
            from bintxt.core.state import load_state, txt_hash
            state = load_state(self.repo_path)
        except Exception:
            pass

        for base in all_bases:
            has_txt  = base in txt_stems
            has_bin  = base in bin_stems
            has_yaml = base in yaml_files

            if has_txt and has_bin:
                status_text, tag = _ST_SYNCED
                # Check hash
                txt_p = cfg_dir / f'{base}.txt'
                try:
                    prev = state.get(base, {}).get('txt_hash')
                    curr = txt_hash(txt_p)
                    if prev and curr and prev != curr:
                        status_text, tag = _ST_MODIFIED
                        tag = "modified"
                    else:
                        tag = "synced"
                except Exception:
                    tag = "synced"
            elif has_txt and not has_bin:
                status_text, _ = _ST_TXT_ONLY
                tag = "txt_only"
            elif has_bin and not has_txt:
                status_text, _ = _ST_BIN_ONLY
                tag = "bin_only"
            else:
                status_text, _ = _ST_UNKNOWN
                tag = "no_yaml"

            yaml_str = "✓" if has_yaml else "—"
            if not has_yaml:
                tag = "no_yaml"

            row = (base, status_text, yaml_str)
            iid = self._tree.insert("", "end", iid=base, values=row, tags=(tag,))
            self._all_rows.append((iid, row))

        self.app.set_status(f"{len(all_bases)} file(s) found in {cfg_dir.name}/")
        self._apply_filter()

    def _apply_filter(self):
        query = self._filter_var.get().lower()
        for iid, row in self._all_rows:
            try:
                if query and query not in row[0].lower():
                    self._tree.detach(iid)
                else:
                    self._tree.reattach(iid, "", "end")
            except tk.TclError:
                pass

    # ── Pipeline ──────────────────────────────────────────────────────────────

    def run_pipeline(self, mode: str = "all", selected: bool = False):
        if self.repo_path is None:
            return

        bases = None
        if selected:
            sel = self._tree.selection()
            if not sel:
                messagebox.showinfo("Nothing selected", "Select one or more files first.")
                return
            bases = list(sel)

        self.app.log_panel.clear()
        self.app.set_status(f"Running {mode}…")
        self.app.log_panel.info(f"▶  {mode.upper()}" + (f" — {', '.join(bases)}" if bases else " — all files"))

        def _worker():
            try:
                _run_bintxt(self.repo_path, mode=mode, bases=bases, log=self.app.log_panel)
            except Exception as e:
                self.app.log_panel.error(f"FATAL: {e}")
            finally:
                self.after(0, self._refresh)
                self.after(0, lambda: self.app.set_status("Done."))

        threading.Thread(target=_worker, daemon=True).start()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _show_ctx(self, event):
        row = self._tree.identify_row(event.y)
        if row:
            if row not in self._tree.selection():
                self._tree.selection_set(row)
            try:
                self._ctx.tk_popup(event.x_root, event.y_root)
            finally:
                self._ctx.grab_release()

    def _show_in_explorer(self):
        if self.repo_path is None:
            return
        import subprocess, os
        cfg_dir = self.repo_path / 'configs'
        if cfg_dir.exists():
            if sys.platform == "win32":
                os.startfile(str(cfg_dir))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(cfg_dir)])
            else:
                subprocess.Popen(["xdg-open", str(cfg_dir)])


# ── Pipeline runner (runs in worker thread) ───────────────────────────────────

def _run_bintxt(repo_path: Path, mode: str, bases, log):
    """Execute bintxt operations against repo_path using core/ directly."""
    sys.path.insert(0, str(repo_path.parent))
    from bintxt.core.yaml_loader import load_yaml
    from bintxt.core.config import (
        validate_cfg, get_defaults, get_validation, get_output_cfg,
        get_binary_cfg, default_bin_cfg,
    )
    from bintxt.core.operations import pack, unpack, verify, compute_checksum, sidecar_ext
    from bintxt.core.state import (
        load_state, save_state, cfg_fingerprint, txt_hash,
        has_hex_data, check_cfg_change, reformat_txt,
    )
    from bintxt.core.fs import setup_run_dirs, manage_gitignore, write_yaml_example
    import shutil
    from datetime import datetime

    cfg_file = repo_path / 'bintxt_cfg.yaml'
    if not cfg_file.exists():
        log.error("bintxt_cfg.yaml not found in repo root.")
        return

    cfg = load_yaml(cfg_file.read_text(encoding='utf-8'))
    errors = validate_cfg(cfg)
    if errors:
        for e in errors:
            log.error(e)
        return

    paths      = cfg['paths']
    config_dir = repo_path / paths['config_dir']
    build_dir  = repo_path / paths['build_dir']
    log_dir    = repo_path / paths['log_dir']
    defaults   = get_defaults(cfg)
    val_cfg    = get_validation(cfg)
    out_cfg    = get_output_cfg(cfg)

    run_dir, ts = setup_run_dirs(build_dir, log_dir, out_cfg['keep_runs'])
    run_state   = load_state(repo_path)
    new_state   = dict(run_state)

    txt_files = sorted(config_dir.glob('*.txt'))
    bin_files = sorted(config_dir.glob('*.bin'))
    all_bases = sorted(set(f.stem for f in txt_files) | set(f.stem for f in bin_files))

    if bases is not None:
        all_bases = [b for b in all_bases if b in bases]

    for base in all_bases:
        txt_path = config_dir / f'{base}.txt'
        bin_path = config_dir / f'{base}.bin'
        has_txt  = txt_path.exists()
        has_bin  = bin_path.exists()

        log.section(base)

        if has_txt and not has_hex_data(txt_path):
            log.warn(f"  {base}.txt — no hex data, skipping")
            continue

        bin_cfg       = get_binary_cfg(cfg, f'{base}.bin', defaults)
        no_yaml_entry = bin_cfg is None
        if no_yaml_entry:
            log.warn(f"  {base} — no YAML entry (discovery mode)")
            bin_cfg = default_bin_cfg(f'{base}.bin', defaults)

        packed_data  = None
        unpacked_txt = None

        # PACK
        if mode in ("all", "pack") and has_txt and not no_yaml_entry:
            packed_data = pack(txt_path, bin_cfg, val_cfg, log)
            if packed_data is not None:
                out_p = run_dir / 'packed' / f'{base}.bin'
                out_p.write_bytes(packed_data)
                shutil.copy2(out_p, build_dir / 'latest' / 'packed' / f'{base}.bin')
                algo  = bin_cfg['checksum_algorithm']
                chk   = compute_checksum(packed_data, algo)
                log.ok(f"  Packed: {base}.bin  ({len(packed_data)} bytes)  {algo.upper()}: {chk}")
            else:
                log.error(f"  Pack FAILED: {base}.txt")

        # UNPACK
        if mode in ("all", "unpack") and has_bin:
            unpacked_txt = unpack(bin_path, bin_cfg, val_cfg, log)
            if unpacked_txt is not None:
                if not has_txt:
                    (config_dir / f'{base}.txt').write_text(unpacked_txt, encoding='utf-8')
                moved_bin = run_dir / f'{base}.bin'
                shutil.move(str(bin_path), str(moved_bin))
                log.ok(f"  Unpacked: {base}.txt  ({len(unpacked_txt.splitlines())} lines)")
            else:
                log.error(f"  Unpack FAILED: {base}.bin")

        # VERIFY
        if mode in ("all", "verify") and not no_yaml_entry:
            if has_txt and packed_data is not None:
                ok = verify(txt_path.read_text(encoding='utf-8'), packed_data, bin_cfg,
                            f"verify_pack({base})", log)
            if has_txt and has_bin:
                bp = bin_path if bin_path.exists() else (run_dir / f'{base}.bin')
                if bp.exists():
                    ok = verify(txt_path.read_text(encoding='utf-8'), bp.read_bytes(),
                                bin_cfg, f"verify_source_pair({base})", log)

        # Update state
        fp    = cfg_fingerprint(bin_cfg)
        txt_p = config_dir / f'{base}.txt'
        new_state[base] = {
            'config':         fp,
            'txt_hash':       txt_hash(txt_p) if txt_p.exists() else None,
            'from_discovery': no_yaml_entry,
        }

    save_state(repo_path, new_state)
    log.info("\nDone.")
