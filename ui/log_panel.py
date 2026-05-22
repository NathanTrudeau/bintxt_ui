"""Log panel — scrolling output console with colour-coded lines."""

import tkinter as tk
from tkinter import ttk

BG      = "#181825"
TEXT    = "#cdd6f4"
MUTED   = "#6c7086"
GREEN   = "#a6e3a1"
YELLOW  = "#f9e2af"
RED     = "#f38ba8"
ACCENT  = "#89b4fa"
CYAN    = "#89dceb"
SURFACE = "#1e1e2e"
BORDER  = "#313244"
FONT_MONO = ("Consolas", 9) if tk.TkVersion >= 8.6 else ("Courier", 9)


class LogPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=SURFACE)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  Output", bg=SURFACE, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(side="left", pady=6)
        ttk.Button(hdr, text="Clear", command=self.clear).pack(side="right", padx=4, pady=2)

        text_frame = tk.Frame(self, bg=BG)
        text_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self._text = tk.Text(
            text_frame,
            bg=BG, fg=TEXT, insertbackground=TEXT,
            font=FONT_MONO,
            wrap="none",
            relief="flat",
            borderwidth=0,
            state="disabled",
            cursor="arrow",
        )
        vsb = ttk.Scrollbar(text_frame, orient="vertical",   command=self._text.yview)
        hsb = ttk.Scrollbar(text_frame, orient="horizontal",  command=self._text.xview)
        self._text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right",  fill="y")
        hsb.pack(side="bottom", fill="x")
        self._text.pack(side="left",  fill="both", expand=True)

        # Colour tags
        self._text.tag_configure("ok",      foreground=GREEN)
        self._text.tag_configure("error",   foreground=RED)
        self._text.tag_configure("warn",    foreground=YELLOW)
        self._text.tag_configure("info",    foreground=CYAN)
        self._text.tag_configure("section", foreground=ACCENT,
                                 font=("Consolas", 9, "bold"))
        self._text.tag_configure("muted",   foreground=MUTED)

    # ── Write API (thread-safe via after) ──────────────────────────────────────

    def _write(self, msg: str, tag: str = ""):
        self._text.after(0, self._append, msg, tag)

    def _append(self, msg: str, tag: str):
        self._text.configure(state="normal")
        if tag:
            self._text.insert("end", msg + "\n", tag)
        else:
            self._text.insert("end", msg + "\n")
        self._text.configure(state="disabled")
        self._text.see("end")

    # ── Public log methods — match bintxt Logger interface ────────────────────

    def ok(self,      msg): self._write(f"  ✓ {msg}", "ok")
    def error(self,   msg): self._write(f"  ✗ {msg}", "error")
    def err(self,     msg): self.error(msg)
    def warn(self,    msg): self._write(f"  ⚠ {msg}", "warn")
    def info(self,    msg): self._write(f"  · {msg}", "info")
    def section(self, msg): self._write(f"\n── {msg} ──", "section")
    def write(self,   msg, console=False): self._write(msg)

    def clear(self):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")
