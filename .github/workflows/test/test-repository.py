"""Validate fork-link cleanup against the checked-out shell scripts."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHELL_SUFFIXES = {".sh", ".func", ".bash"}
EXCLUDED_DIRS = {".git", ".github", "node_modules"}
UPSTREAM_URL = re.compile(rb"\.com/community-scripts/(?:ProxmoxVE|core)(?![A-Za-z0-9_.-])")


def test_repository_has_no_upstream_urls():
  """Fail with file and line details if upstream URLs remain after rewriting."""
  leftovers = []

  for path in sorted(ROOT.rglob("*")):
    relative_path = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRS for part in relative_path.parts):
      continue
    if not path.is_file() or path.suffix not in SHELL_SUFFIXES:
      continue

    for line_number, line in enumerate(path.read_bytes().splitlines(), start=1):
      for match in UPSTREAM_URL.finditer(line):
        leftovers.append(f"{relative_path}:{line_number}: {match.group().decode('ascii')}")

  assert not leftovers, "Unwanted upstream URLs remain:\n" + "\n".join(leftovers)
