#!/usr/bin/env python3
"""Rewrite upstream repository URLs in shell scripts to point at this fork.

Only references to ``community-scripts/ProxmoxVE`` and
``community-scripts/core`` that follow a ``.com/`` URL segment are changed.
Filesystem paths and references to other repositories are preserved. By
default, the command scans the current directory recursively; pass a root path
to scan another tree or use ``--dry-run`` to list changes without writing.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

EXTENSIONS = {".sh", ".func", ".bash"}
# Keep repository automation and generated/dependency trees outside the scan.
SKIP_DIRS = {".git", ".github", "node_modules"}

# Match URL-style references only; the lookahead prevents matching sibling
# repositories such as ProxmoxVED or similarly prefixed repository names.
REPLACEMENTS: list[tuple[re.Pattern[str], str]] = [
  (
    re.compile(r"(\.com/)community-scripts/ProxmoxVE(?![A-Za-z0-9_.-])"),
    r"\1pranavmishra90/ProxmoxVE",
  ),
  (
    re.compile(r"(\.com/)community-scripts/core(?![A-Za-z0-9_.-])"),
    r"\1pranavmishra90/pve-scripts-core",
  ),
]


def rewrite_text(text: str) -> str:
  """Replace configured upstream URLs in ``text``.

  The input is returned unchanged when no rule matches. Rules are applied in
  order, and local paths or unrelated repositories are not rewritten.
  """
  for pattern, repl in REPLACEMENTS:
    text = pattern.sub(repl, text)
  return text


def is_target_file(path: Path) -> bool:
  """Return whether ``path`` is a regular file with a supported suffix."""
  return path.is_file() and path.suffix in EXTENSIONS


def iter_target_files(root: Path):
  """Yield supported shell files beneath ``root`` in sorted path order.

  Directories listed in ``SKIP_DIRS`` are excluded at any depth, including
  version-control metadata, workflow automation, and installed dependencies.
  """
  for path in sorted(root.rglob("*")):
    if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
      continue
    if is_target_file(path):
      yield path


def rewrite_file(path: Path, dry_run: bool = False) -> bool:
  """Rewrite a supported text file in place when a rule matches.

  Args:
    path: File to inspect; callers are responsible for selecting its suffix.
    dry_run: Detect changes without writing the updated content.

  Returns:
    ``True`` if the file would change, including in dry-run mode; otherwise
    ``False``. Files that cannot be decoded as UTF-8 are left untouched.
  """
  try:
    original = path.read_text(encoding="utf-8", newline="")
  except UnicodeDecodeError:
    return False
  updated = rewrite_text(original)
  if updated == original:
    return False
  if not dry_run:
    path.write_text(updated, encoding="utf-8", newline="")
  return True


def rewrite_repo(root: Path, dry_run: bool = False) -> list[Path]:
  """Rewrite supported shell files beneath ``root``.

  Args:
    root: Directory tree to scan.
    dry_run: Detect changes without writing any files.

  Returns:
    Paths of files that were changed or would change in dry-run mode.
  """
  return [p for p in iter_target_files(root) if rewrite_file(p, dry_run)]


def main(argv: list[str] | None = None) -> int:
  """Run the command-line interface and report each affected file.

  The optional positional argument selects the scan root; ``--dry-run`` only
  reports files and does not modify them. Returns zero after a successful scan.
  """
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("root", nargs="?", default=".", type=Path)
  parser.add_argument("--dry-run", action="store_true")
  args = parser.parse_args(argv)

  changed = rewrite_repo(args.root.resolve(), args.dry_run)
  for path in changed:
    print(path)
  print(f"{len(changed)} file(s) {'would be ' if args.dry_run else ''}updated")
  return 0


if __name__ == "__main__":
  sys.exit(main())
