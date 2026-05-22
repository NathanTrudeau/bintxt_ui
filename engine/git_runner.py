"""Git integration — subprocess wrappers for branch, tag, commit, push operations.

All methods take repo_path: Path and operate against that directory.
Credentials (SSH key or HTTPS token) are configured externally via git config
or environment — this module does not handle auth directly.
"""

import subprocess
from pathlib import Path


class GitError(Exception):
    pass


def _run(args: list, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise GitError(result.stderr.strip() or result.stdout.strip())
    return result


# ── Read ──────────────────────────────────────────────────────────────────────

def current_branch(repo_path: Path) -> str:
    return _run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], repo_path).stdout.strip()


def list_branches(repo_path: Path) -> list[str]:
    out = _run(['git', 'branch', '--list', '--format=%(refname:short)'], repo_path).stdout
    return [b.strip() for b in out.splitlines() if b.strip()]


def list_tags(repo_path: Path) -> list[str]:
    out = _run(['git', 'tag', '--list'], repo_path).stdout
    return [t.strip() for t in out.splitlines() if t.strip()]


def status(repo_path: Path) -> str:
    return _run(['git', 'status', '--short'], repo_path).stdout


def remotes(repo_path: Path) -> list[str]:
    out = _run(['git', 'remote'], repo_path).stdout
    return [r.strip() for r in out.splitlines() if r.strip()]


# ── Write ─────────────────────────────────────────────────────────────────────

def create_branch(repo_path: Path, branch_name: str, checkout: bool = True):
    _run(['git', 'branch', branch_name], repo_path)
    if checkout:
        _run(['git', 'checkout', branch_name], repo_path)


def checkout_branch(repo_path: Path, branch_name: str):
    _run(['git', 'checkout', branch_name], repo_path)


def stage_all(repo_path: Path):
    _run(['git', 'add', '-A'], repo_path)


def commit(repo_path: Path, message: str):
    _run(['git', 'commit', '-m', message], repo_path)


def create_tag(repo_path: Path, tag_name: str, message: str = ''):
    if message:
        _run(['git', 'tag', '-a', tag_name, '-m', message], repo_path)
    else:
        _run(['git', 'tag', tag_name], repo_path)


def push(repo_path: Path, remote: str = 'origin', branch: str = '', tags: bool = False):
    args = ['git', 'push', remote]
    if branch:
        args.append(branch)
    if tags:
        args.append('--tags')
    _run(args, repo_path)
