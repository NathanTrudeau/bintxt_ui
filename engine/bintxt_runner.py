"""Wrapper around bintxt/core — exposes pack, unpack, verify to the UI layer.

Import pattern:
    from bintxt.core import pack, unpack, verify, load_yaml, Logger
    from bintxt.core.config import validate_cfg, get_defaults, get_binary_cfg

The bintxt submodule is pinned to a specific commit in .gitmodules.
Run `git submodule update --remote` to pull the latest core changes.
"""

import sys
from pathlib import Path

# bintxt is a git submodule at ./bintxt/
_SUBMODULE = Path(__file__).parent.parent / 'bintxt'
if str(_SUBMODULE) not in sys.path:
    sys.path.insert(0, str(_SUBMODULE.parent))

from bintxt.core import (  # noqa: E402
    pack, unpack, verify,
    load_yaml, validate_cfg,
    get_defaults, get_validation, get_output_cfg, get_binary_cfg, default_bin_cfg,
    load_state, save_state,
    Logger,
)

__all__ = [
    'pack', 'unpack', 'verify',
    'load_yaml', 'validate_cfg',
    'get_defaults', 'get_validation', 'get_output_cfg',
    'get_binary_cfg', 'default_bin_cfg',
    'load_state', 'save_state',
    'Logger',
]
