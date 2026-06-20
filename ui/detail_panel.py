"""Detail panel — extraction rules editor, labels table, hex preview."""

import threading
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from pathlib import Path

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
MONO     = ("Consolas", 9)


class DetailPanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self.app   = app
        self._base: str | None = None
        self._repo = None
        self._build()

    def _build(self):
        # Header
        self._header = tk.Label(self, text="  Select a file", bg=SURFACE,
                                fg=MUTED, font=FONT_B, anchor="w")
        self._header.pack(fill="x", ipady=6)

        # Main split: left (rules + labels) | right (hex preview)
        pane = ttk.PanedWindow(self, orient="horizontal")
        pane.pack(fill="both", expand=True)

        # ── Left column ───────────────────────────────────────────────────────
        left = tk.Frame(pane, bg=BG)
        pane.add(left, weight=1)

        self._build_rules(left)
        self._build_labels(left)

        # ── Right column: hex preview ─────────────────────────────────────────
        right = tk.Frame(pane, bg=BG)
        pane.add(right, weight=2)

        hdr2 = tk.Frame(right, bg=SURFACE)
        hdr2.pack(fill="x")
        tk.Label(hdr2, text="  Hex Preview  (.txt content)",
                 bg=SURFACE, fg=TEXT, font=FONT_B).pack(side="left", pady=4)
        self._line_count = tk.Label(hdr2, text="", bg=SURFACE, fg=MUTED, font=FONT_SM)
        self._line_count.pack(side="right", padx=8)

        txt_frame = tk.Frame(right, bg=BG)
        txt_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self._preview = tk.Text(
            txt_frame, bg=SURFACE, fg=TEXT, font=MONO,
            wrap="none", relief="flat", borderwidth=0,
            state="disabled", cursor="arrow",
            insertbackground=TEXT,
        )
        vsb = ttk.Scrollbar(txt_frame, orient="vertical",   command=self._preview.yview)
        hsb = ttk.Scrollbar(txt_frame, orient="horizontal",  command=self._preview.xview)
        self._preview.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._preview.tag_configure("addr",  foreground=ACCENT)
        self._preview.tag_configure("label", foreground=YELLOW)
        self._preview.tag_configure("data",  foreground=TEXT)

        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self._preview.pack(side="left", fill="both", expand=True)

    # ── Rules section ─────────────────────────────────────────────────────────

    def _build_rules(self, parent):
        hdr = tk.Frame(parent, bg=SURFACE)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  Extraction Rules", bg=SURFACE,
                 fg=TEXT, font=FONT_B).pack(side="left", pady=4)

        grid = tk.Frame(parent, bg=BG)
        grid.pack(fill="x", padx=8, pady=6)

        def label(text, row):
            tk.Label(grid, text=text, bg=BG, fg=MUTED,
                     font=FONT_SM, anchor="w", width=16).grid(
                row=row, column=0, sticky="w", pady=2)

        # word_bits
        label("Word size (bits):", 0)
        self._word_bits = tk.StringVar(value="8")
        ttk.Combobox(grid, textvariable=self._word_bits,
                     values=["8", "16", "32", "64"],
                     state="readonly", width=10).grid(row=0, column=1, sticky="w", pady=2)

        # address_bits
        label("Address size (bits):", 1)
        self._addr_bits = tk.StringVar(value="32")
        ttk.Combobox(grid, textvariable=self._addr_bits,
                     values=["16", "32", "64"],
                     state="readonly", width=10).grid(row=1, column=1, sticky="w", pady=2)

        # words_per_line
        label("Words per line:", 2)
        self._wpl = tk.StringVar(value="6")
        ttk.Spinbox(grid, textvariable=self._wpl,
                    from_=1, to=32, width=10).grid(row=2, column=1, sticky="w", pady=2)

        # endianness
        label("Endianness:", 3)
        self._endian = tk.StringVar(value="little")
        ttk.Combobox(grid, textvariable=self._endian,
                     values=["little", "big"],
                     state="readonly", width=10).grid(row=3, column=1, sticky="w", pady=2)

        # checksum
        label("Checksum:", 4)
        self._checksum = tk.StringVar(value="crc32")
        ttk.Combobox(grid, textvariable=self._checksum,
                     values=["crc32", "md5", "sha256"],
                     state="readonly", width=10).grid(row=4, column=1, sticky="w", pady=2)

        btn_row = tk.Frame(parent, bg=BG)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="Apply Rules",
                   command=self._apply_rules,
                   style="Accent.TButton").pack(side="left")
        self._rules_status = tk.Label(btn_row, text="", bg=BG, fg=GREEN, font=FONT_SM)
        self._rules_status.pack(side="left", padx=8)

    # ── Labels section ────────────────────────────────────────────────────────

    def _build_labels(self, parent):
        hdr = tk.Frame(parent, bg=SURFACE)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  Labels", bg=SURFACE,
                 fg=TEXT, font=FONT_B).pack(side="left", pady=4)
        ttk.Button(hdr, text="+", width=3,
                   command=self._add_label).pack(side="right", padx=4, pady=2)
        ttk.Button(hdr, text="−", width=3,
                   command=self._del_label).pack(side="right", padx=0, pady=2)

        tbl_frame = tk.Frame(parent, bg=BG)
        tbl_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self._labels_tree = ttk.Treeview(
            tbl_frame,
            columns=("address", "name"),
            show="headings",
            selectmode="browse",
            height=6,
        )
        self._labels_tree.heading("address", text="Address",    anchor="w")
        self._labels_tree.heading("name",    text="Label Name", anchor="w")
        self._labels_tree.column("address",  width=100, stretch=False)
        self._labels_tree.column("name",     width=180, stretch=True)
        self._labels_tree.bind("<Double-1>", self._edit_label)

        lvsb = ttk.Scrollbar(tbl_frame, orient="vertical", command=self._labels_tree.yview)
        self._labels_tree.configure(yscrollcommand=lvsb.set)
        self._labels_tree.pack(side="left", fill="both", expand=True)
        lvsb.pack(side="right", fill="y")

        btn_row = tk.Frame(parent, bg=BG)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="Apply Labels",
                   command=self._apply_labels,
                   style="Accent.TButton").pack(side="left")
        self._labels_status = tk.Label(btn_row, text="", bg=BG, fg=GREEN, font=FONT_SM)
        self._labels_status.pack(side="left", padx=8)

    # ── Load ──────────────────────────────────────────────────────────────────

    def load_file(self, base: str, repo):
        self._base = base
        self._repo = repo
        self._header.config(text=f"  {base}", fg=TEXT)

        # Populate rules
        rules = repo.get_rules(f'{base}.bin')
        self._word_bits.set(str(rules['word_bits']))
        self._addr_bits.set(str(rules['address_bits']))
        self._wpl.set(str(rules['words_per_line']))
        self._endian.set(rules['endianness'])
        self._checksum.set(rules['checksum_algorithm'])
        self._rules_status.config(text="")

        # Populate labels table
        self._load_labels_table(repo.get_labels(f'{base}.bin'))
        self._labels_status.config(text="")

        # Load hex preview
        self._load_preview(repo.repo_path / f'{base}.txt')

    def clear(self):
        self._base = None
        self._header.config(text="  Select a file", fg=MUTED)
        self._labels_tree.delete(*self._labels_tree.get_children())
        self._set_preview("")
        self._line_count.config(text="")

    def _load_labels_table(self, labels: list[dict]):
        self._labels_tree.delete(*self._labels_tree.get_children())
        valid = [l for l in labels if isinstance(l, dict)]
        for lbl in sorted(valid, key=lambda l: int(l.get('address', 0))):
            addr = int(lbl.get('address', 0))
            name = lbl.get('label', '')
            self._labels_tree.insert("", "end",
                values=(f"0x{addr:08x}", name),
                tags=(str(addr),))

    def _load_preview(self, txt_path: Path):
        if txt_path.exists():
            content = txt_path.read_text(encoding='utf-8', errors='replace')
            self._set_preview(content)
        else:
            self._set_preview(f"(no .txt file yet — run Initialize or Apply Rules)")

    def _set_preview(self, content: str):
        self._preview.configure(state="normal")
        self._preview.delete("1.0", "end")
        if content:
            # Colour-code by line type
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith('@label'):
                    self._preview.insert("end", line + "\n", "label")
                elif stripped.startswith('#') or not stripped:
                    self._preview.insert("end", line + "\n", "data")
                elif ':' in stripped:
                    addr, _, rest = stripped.partition(':')
                    self._preview.insert("end", addr + ":", "addr")
                    self._preview.insert("end", rest + "\n", "data")
                else:
                    self._preview.insert("end", line + "\n", "data")
            lines = content.count('\n')
            self._line_count.config(text=f"{lines} lines")
        else:
            self._line_count.config(text="")
        self._preview.configure(state="disabled")

    # ── Apply rules ───────────────────────────────────────────────────────────

    def _apply_rules(self):
        if not self._base or not self._repo:
            return
        rules = {
            'word_bits':          int(self._word_bits.get()),
            'address_bits':       int(self._addr_bits.get()),
            'words_per_line':     int(self._wpl.get()),
            'endianness':         self._endian.get(),
            'checksum_algorithm': self._checksum.get(),
        }
        self._rules_status.config(text="Applying…", fg=YELLOW)
        self.update_idletasks()

        def _worker():
            try:
                self._repo.update_rules(f'{self._base}.bin', rules)
                txt = self._repo.reextract(self._base, self.app.log_panel)
                self.after(0, lambda: self._after_apply(txt, self._rules_status, "Rules applied"))
                self.after(0, lambda: self.app.file_panel.load_repo(self._repo))
            except Exception as e:
                self.after(0, lambda: self._rules_status.config(
                    text=f"Error: {e}", fg=RED))

        threading.Thread(target=_worker, daemon=True).start()

    def _after_apply(self, txt, status_label, msg):
        if txt is not None:
            self._set_preview(txt)
        status_label.config(text=f"✓ {msg}", fg=GREEN)

    # ── Labels ────────────────────────────────────────────────────────────────

    def _add_label(self):
        if not self._base:
            return
        addr_str = simpledialog.askstring(
            "Add Label", "Address (hex, e.g. 0x00000010):", parent=self)
        if not addr_str:
            return
        try:
            addr = int(addr_str, 16)
        except ValueError:
            messagebox.showerror("Invalid", "Enter a valid hex address.")
            return
        name = simpledialog.askstring(
            "Add Label", f"Label name for 0x{addr:08x}:", parent=self)
        if not name:
            return
        self._labels_tree.insert("", "end",
            values=(f"0x{addr:08x}", name), tags=(str(addr),))

    def _del_label(self):
        sel = self._labels_tree.selection()
        if sel:
            self._labels_tree.delete(*sel)

    def _edit_label(self, event):
        item = self._labels_tree.identify_row(event.y)
        if not item:
            return
        addr_str, name = self._labels_tree.item(item, "values")
        new_name = simpledialog.askstring(
            "Edit Label", f"Label name for {addr_str}:",
            initialvalue=name, parent=self)
        if new_name is not None:
            self._labels_tree.item(item, values=(addr_str, new_name))

    def _apply_labels(self):
        if not self._base or not self._repo:
            return
        labels = []
        for iid in self._labels_tree.get_children():
            addr_str, name = self._labels_tree.item(iid, "values")
            try:
                addr = int(addr_str, 16)
                labels.append({'address': addr, 'label': name})
            except ValueError:
                pass

        self._labels_status.config(text="Applying…", fg=YELLOW)
        self.update_idletasks()

        def _worker():
            try:
                self._repo.update_labels(f'{self._base}.bin', labels)
                txt = self._repo.reextract(self._base, self.app.log_panel)
                self.after(0, lambda: self._after_apply(txt, self._labels_status, "Labels applied"))
            except Exception as e:
                self.after(0, lambda: self._labels_status.config(
                    text=f"Error: {e}", fg=RED))

        threading.Thread(target=_worker, daemon=True).start()
