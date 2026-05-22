"""Main application window — placeholder for Phase 1 implementation."""

import tkinter as tk
from tkinter import ttk


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("bintxt_ui")
        self.geometry("1100x700")
        self.configure(bg="#1e1e2e")
        self._build_placeholder()

    def _build_placeholder(self):
        lbl = tk.Label(
            self,
            text="bintxt_ui\n\nScaffold — implementation coming.",
            bg="#1e1e2e",
            fg="#cdd6f4",
            font=("Segoe UI", 16),
            justify="center",
        )
        lbl.pack(expand=True)
