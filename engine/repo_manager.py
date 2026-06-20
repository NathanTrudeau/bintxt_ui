"""RepoManager — owns all repo state, YAML creation, extract, build, cleanup.

This is the central engine the UI talks to. It never imports tkinter.
"""

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Ensure bintxt submodule is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from bintxt.core.yaml_loader import load_yaml
from bintxt.core.operations import pack, unpack, compute_checksum, sidecar_ext
from bintxt.core.config import get_validation


# ── Default config values ─────────────────────────────────────────────────────

DEFAULT_RULES = {
    'word_bits':          8,
    'address_bits':       32,
    'words_per_line':     6,
    'endianness':         'little',
    'checksum_algorithm': 'crc32',
}

DEFAULT_VALIDATION = {
    'fail_on_duplicate_addresses':     True,
    'fail_on_non_monotonic_addresses': True,
    'fail_on_stride_mismatch':         False,
    'fail_on_invalid_hex':             True,
    'fail_on_invalid_word_count':      True,
    'fail_on_partial_word':            False,
    'fail_on_missing_label_address':   False,
    'checksum_required':               False,
}


# ── YAML serialiser (minimal, schema-specific, no PyYAML required) ────────────

def _serialize_cfg(cfg: dict) -> str:
    p = cfg['paths']
    d = cfg.get('defaults', DEFAULT_RULES)
    o = cfg.get('output', {})
    v = cfg.get('validation', DEFAULT_VALIDATION)
    bins = cfg.get('binaries') or []

    def _bool(val):
        return 'true' if val else 'false'

    lines = [
        "version: 1",
        "",
        "paths:",
        f"  config_dir: {p['config_dir']}",
        f"  build_dir:  {p['build_dir']}",
        f"  log_dir:    {p['log_dir']}",
        "",
        "defaults:",
        f"  address_bits:       {d.get('address_bits', 32)}",
        f"  word_bits:          {d.get('word_bits', 8)}",
        f"  words_per_line:     {d.get('words_per_line', 6)}",
        f"  endianness:         {d.get('endianness', 'little')}",
        f"  checksum_algorithm: {d.get('checksum_algorithm', 'crc32')}",
        "",
        "output:",
        f"  keep_runs:             {o.get('keep_runs', 10)}",
        f"  track_checksum:        {_bool(o.get('track_checksum', False))}",
        f"  generate_yaml_example: {_bool(o.get('generate_yaml_example', False))}",
        "",
        "validation:",
    ]
    for k, default in DEFAULT_VALIDATION.items():
        lines.append(f"  {k}: {_bool(v.get(k, default))}")

    lines.append("")
    lines.append("binaries:")

    for entry in bins:
        fmt = entry.get('format') or {}
        chk = entry.get('checksum') or {}
        labels = entry.get('labels') or []
        lines += [
            "",
            f"  - file: {entry['file']}",
            f"    label: {_bool(entry.get('label', False))}",
            "    format:",
            f"      address_bits:   {fmt.get('address_bits', d.get('address_bits', 32))}",
            f"      word_bits:      {fmt.get('word_bits', d.get('word_bits', 8))}",
            f"      words_per_line: {fmt.get('words_per_line', d.get('words_per_line', 6))}",
            f"      endianness:     {fmt.get('endianness', d.get('endianness', 'little'))}",
            "    checksum:",
            f"      algorithm: {chk.get('algorithm', d.get('checksum_algorithm', 'crc32'))}",
            "    labels:",
        ]
        if labels:
            for lbl in labels:
                addr = int(lbl.get('address', 0))
                name = lbl.get('label', '')
                lines.append(f"      - address: 0x{addr:08x}")
                lines.append(f"        label:   {name}")
        else:
            lines.append("      []")

    return '\n'.join(lines) + '\n'


# ── Bin cfg dict builder ───────────────────────────────────────────────────────

def _make_bin_cfg(entry: dict, defaults: dict) -> dict:
    fmt = entry.get('format') or {}
    chk = entry.get('checksum') or {}
    return {
        'file':               entry['file'],
        'label':              bool(entry.get('label', False)),
        'address_bits':       int(fmt.get('address_bits',   defaults.get('address_bits', 32))),
        'word_bits':          int(fmt.get('word_bits',       defaults.get('word_bits', 8))),
        'words_per_line':     int(fmt.get('words_per_line',  defaults.get('words_per_line', 6))),
        'endianness':         str(fmt.get('endianness',      defaults.get('endianness', 'little'))),
        'checksum_algorithm': str(chk.get('algorithm',       defaults.get('checksum_algorithm', 'crc32'))),
        'labels':             list(entry.get('labels') or []),
    }


# ── RepoManager ───────────────────────────────────────────────────────────────

class RepoManager:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.cfg_file  = repo_path / 'bintxt_cfg.yaml'
        self._cfg: dict | None = None

    # ── State queries ─────────────────────────────────────────────────────────

    @property
    def is_fresh(self) -> bool:
        """True if no bintxt_cfg.yaml exists yet."""
        return not self.cfg_file.exists()

    def discover_bins(self) -> list[Path]:
        """All .bin files in repo root (excludes build/)."""
        return sorted(
            p for p in self.repo_path.glob('*.bin')
            if p.parent == self.repo_path
        )

    def discover_txts(self) -> list[Path]:
        return sorted(
            p for p in self.repo_path.glob('*.txt')
            if p.parent == self.repo_path
        )

    def all_bases(self) -> list[str]:
        bins = {p.stem for p in self.discover_bins()}
        txts = {p.stem for p in self.discover_txts()}
        return sorted(bins | txts)

    def txt_path(self, base: str) -> Path:
        return self.repo_path / f'{base}.txt'

    def bin_path(self, base: str) -> Path:
        return self.repo_path / f'{base}.bin'

    # ── Config access ─────────────────────────────────────────────────────────

    def load_cfg(self) -> dict:
        self._cfg = load_yaml(self.cfg_file.read_text(encoding='utf-8'))
        return self._cfg

    def save_cfg(self):
        self.cfg_file.write_text(_serialize_cfg(self._cfg), encoding='utf-8')

    def cfg(self) -> dict:
        if self._cfg is None and not self.is_fresh:
            self.load_cfg()
        return self._cfg or {}

    def _defaults(self) -> dict:
        return self.cfg().get('defaults') or DEFAULT_RULES

    def get_entry(self, filename: str) -> dict | None:
        for e in (self.cfg().get('binaries') or []):
            if e.get('file') == filename:
                return e
        return None

    def get_bin_cfg(self, filename: str) -> dict:
        entry = self.get_entry(filename) or {'file': filename}
        return _make_bin_cfg(entry, self._defaults())

    def get_rules(self, filename: str) -> dict:
        bc = self.get_bin_cfg(filename)
        return {
            'word_bits':          bc['word_bits'],
            'address_bits':       bc['address_bits'],
            'words_per_line':     bc['words_per_line'],
            'endianness':         bc['endianness'],
            'checksum_algorithm': bc['checksum_algorithm'],
        }

    def get_labels(self, filename: str) -> list[dict]:
        entry = self.get_entry(filename)
        return list(entry.get('labels') or []) if entry else []

    # ── Mutations ─────────────────────────────────────────────────────────────

    def update_rules(self, filename: str, rules: dict):
        """Update extraction rules for a file and save YAML."""
        entry = self._ensure_entry(filename)
        if 'format' not in entry:
            entry['format'] = {}
        entry['format'].update({
            'address_bits':   rules.get('address_bits',   entry['format'].get('address_bits', 32)),
            'word_bits':      rules.get('word_bits',       entry['format'].get('word_bits', 8)),
            'words_per_line': rules.get('words_per_line',  entry['format'].get('words_per_line', 6)),
            'endianness':     rules.get('endianness',      entry['format'].get('endianness', 'little')),
        })
        if 'checksum_algorithm' in rules:
            entry.setdefault('checksum', {})['algorithm'] = rules['checksum_algorithm']
        self.save_cfg()

    def update_labels(self, filename: str, labels: list[dict]):
        """Update labels list for a file and save YAML."""
        entry = self._ensure_entry(filename)
        entry['labels'] = labels
        entry['label'] = bool(labels)
        self.save_cfg()

    def _ensure_entry(self, filename: str) -> dict:
        bins = self._cfg.setdefault('binaries', [])
        for e in bins:
            if e.get('file') == filename:
                return e
        entry = {
            'file':     filename,
            'label':    False,
            'format':   dict(DEFAULT_RULES),
            'checksum': {'algorithm': 'crc32'},
            'labels':   [],
        }
        bins.append(entry)
        return entry

    # ── Initialize ────────────────────────────────────────────────────────────

    def initialize(self, log) -> list[str]:
        """Discover bins, create YAML, unpack all. Returns list of base names processed."""
        bins = self.discover_bins()
        if not bins:
            log.warn("No .bin files found in repo root.")
            return []

        # Build fresh cfg
        self._cfg = {
            'version': 1,
            'paths': {
                'config_dir': '.',
                'build_dir':  'build',
                'log_dir':    'logs',
            },
            'defaults': dict(DEFAULT_RULES),
            'output': {
                'keep_runs':             10,
                'track_checksum':        False,
                'generate_yaml_example': False,
            },
            'validation': dict(DEFAULT_VALIDATION),
            'binaries': [
                {
                    'file':     p.name,
                    'label':    False,
                    'format':   dict(DEFAULT_RULES),
                    'checksum': {'algorithm': 'crc32'},
                    'labels':   [],
                }
                for p in bins
            ],
        }
        self.save_cfg()
        log.ok(f"Created bintxt_cfg.yaml ({len(bins)} entries)")

        processed = []
        val_cfg = dict(DEFAULT_VALIDATION)

        for p in bins:
            base    = p.stem
            bin_cfg = self.get_bin_cfg(p.name)
            log.info(f"Extracting {p.name} ...")
            txt = unpack(p, bin_cfg, val_cfg, log)
            if txt is not None:
                self.txt_path(base).write_text(txt, encoding='utf-8')
                log.ok(f"{base}.txt written ({len(txt.splitlines())} lines)")
                processed.append(base)
            else:
                log.error(f"Failed to extract {p.name}")

        return processed

    # ── Re-extract single file ────────────────────────────────────────────────

    def reextract(self, base: str, log) -> str | None:
        """Re-unpack .bin using current rules. Writes .txt and returns content."""
        bin_p = self.bin_path(base)
        if not bin_p.exists():
            log.warn(f"{base}.bin not found — cannot re-extract")
            return None
        bin_cfg = self.get_bin_cfg(f'{base}.bin')
        val_cfg = dict(DEFAULT_VALIDATION)
        txt = unpack(bin_p, bin_cfg, val_cfg, log)
        if txt is not None:
            self.txt_path(base).write_text(txt, encoding='utf-8')
            log.ok(f"{base}.txt updated")
        return txt

    # ── Build ─────────────────────────────────────────────────────────────────

    def build(self, bases: list[str] | None, log) -> Path:
        """Pack .txt → .bin into build/<timestamp>/. Returns the build dir."""
        ts       = datetime.now().strftime('%Y-%m-%d_%I-%M-%S%p')
        build_dir = self.repo_path / 'build' / ts
        build_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Build dir: build/{ts}")

        val_cfg = dict(DEFAULT_VALIDATION)
        targets = bases if bases is not None else self.all_bases()

        for base in targets:
            txt_p = self.txt_path(base)
            if not txt_p.exists():
                log.warn(f"{base}.txt not found — skipping")
                continue
            bin_cfg = self.get_bin_cfg(f'{base}.bin')
            data = pack(txt_p, bin_cfg, val_cfg, log)
            if data is not None:
                out = build_dir / f'{base}.bin'
                out.write_bytes(data)
                algo = bin_cfg['checksum_algorithm']
                chk  = compute_checksum(data, algo)
                log.ok(f"Built {base}.bin  ({len(data)}B)  {algo.upper()}: {chk}")
            else:
                log.error(f"Build FAILED: {base}")

        return build_dir

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def cleanup(self, log):
        """Update .gitignore so .txt/.yaml are tracked, .bin is ignored.
        Unstage any tracked .bin files."""
        gi_path = self.repo_path / '.gitignore'
        lines   = gi_path.read_text(encoding='utf-8').splitlines() if gi_path.exists() else []

        # Remove entries that would hide .txt or .yaml
        lines = [l for l in lines if l.strip() not in ('*.txt', '*.yaml', '*.yml')]

        # Ensure *.bin is ignored
        if '*.bin' not in lines:
            lines.append('*.bin')

        gi_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        log.ok(".gitignore updated — .bin ignored, .txt/.yaml tracked")

        # Untrack any .bin files git is currently tracking
        try:
            result = subprocess.run(
                ['git', 'ls-files', '--error-unmatch', '*.bin'],
                cwd=str(self.repo_path), capture_output=True, text=True
            )
            if result.returncode == 0:
                subprocess.run(
                    ['git', 'rm', '--cached', '*.bin'],
                    cwd=str(self.repo_path), capture_output=True
                )
                log.ok("Untracked .bin files from git index")
        except Exception:
            pass

        log.info("Ready to commit — stage .txt + bintxt_cfg.yaml in the Git panel")
