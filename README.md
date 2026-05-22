# bintxt_ui

**Standalone GUI for the [bintxt](https://github.com/NathanTrudeau/bintxt) binary ↔ text pipeline.**

Open any repo folder that uses `bintxt_cfg.yaml`, perform pack/unpack/verify operations via button presses, and manage branches and tags — all without touching the terminal.

Designed for engineers version-controlling binary config files per SOC serial number, where each device variant lives on its own branch to prevent config overwrites.

---

## Status

🚧 **In development — scaffold only.**

---

## Requirements

- Python 3.8+
- `tkinter` (included in standard Python distributions)
- No pip installs required

---

## Setup

```bash
# Clone with submodule
git clone --recurse-submodules https://github.com/NathanTrudeau/bintxt_ui.git
cd bintxt_ui

# Or if already cloned without submodule:
git submodule update --init --recursive
```

## Run

```bash
python main.py
```

---

## Architecture

```
bintxt_ui/
├── main.py                  ← entry point
├── ui/
│   ├── app.py               ← main window
│   ├── file_panel.py        ← .bin/.txt pair list + sync status
│   ├── git_panel.py         ← branch/tag/commit/push
│   └── log_panel.py         ← live output console
├── engine/
│   ├── bintxt_runner.py     ← imports bintxt/core directly
│   └── git_runner.py        ← subprocess git wrappers
└── bintxt/                  ← git submodule (pinned commit)
    ├── bintxt.sh
    ├── core/                ← Python package — imported by bintxt_runner.py
    └── ...
```

### Updating the bintxt submodule

```bash
git submodule update --remote bintxt
git add bintxt
git commit -m "bump bintxt submodule to latest"
```

---

## Workflow (planned)

1. **Open Repo** — folder picker; reads `bintxt_cfg.yaml`
2. **File Panel** — shows all `.bin`/`.txt` pairs with sync status
3. **Actions** — Pack / Unpack / Verify per file or all at once
4. **Git Panel** — current branch, staged changes, commit, create branch (e.g. `sn-A4F2`), tag, push
