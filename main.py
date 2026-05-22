"""bintxt_ui — entry point.

Launch the GUI:
    python main.py

Requirements: Python 3.8+, stdlib only (tkinter included).
"""

import sys
from pathlib import Path

# Ensure the bundled bintxt submodule is importable as 'bintxt.core'
sys.path.insert(0, str(Path(__file__).parent))

from ui.app import App


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
