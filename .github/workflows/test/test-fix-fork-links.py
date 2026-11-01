"""Tests for upstream URL rewriting and repository file selection."""

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "fix-fork-links.py"
_spec = importlib.util.spec_from_file_location("fix_fork_links", _SCRIPT)
assert _spec is not None and _spec.loader is not None
ffl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ffl)


@pytest.mark.parametrize(
  "before, after",
  [
    (
      '_FUNC_BASE="https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc"',
      '_FUNC_BASE="https://raw.githubusercontent.com/pranavmishra90/ProxmoxVE/main/misc"',
    ),
    (
      "# License: MIT | https://github.com/community-scripts/ProxmoxVE/raw/main/LICENSE",
      "# License: MIT | https://github.com/pranavmishra90/ProxmoxVE/raw/main/LICENSE",
    ),
    (
      "git clone https://github.com/community-scripts/core",
      "git clone https://github.com/pranavmishra90/pve-scripts-core",
    ),
    (
      "https://github.com/community-scripts/core/raw/main/x.sh",
      "https://github.com/pranavmishra90/pve-scripts-core/raw/main/x.sh",
    ),
  ],
)
def test_rewrites_upstream_urls(before, after):
  """Rewrite supported URLs for the main and core upstream repositories."""
  assert ffl.rewrite_text(before) == after


@pytest.mark.parametrize(
  "text",
  [
    "if [[ ! -f /usr/local/community-scripts/diagnostics ]]; then",
    'echo "DIAGNOSTICS=no" >/usr/local/community-scripts/diagnostics',
    'CFG="$HOME/.config/community-scripts/default.vars"',
    "https://github.com/community-scripts/ProxmoxVED/raw/main/x",
    "https://github.com/community-scripts/telemetry-service/blob/main/docs/PRIVACY.md",
    "https://github.com/community-scripts/corefoo",
    'REPO_SLUG="community-scripts/ProxmoxVE"',
  ],
)
def test_leaves_other_references_untouched(text):
  """Preserve local paths, unrelated repositories, and prefix lookalikes."""
  assert ffl.rewrite_text(text) == text


def test_idempotent():
  """Applying the rewrite more than once does not alter the result further."""
  once = ffl.rewrite_text("https://github.com/community-scripts/ProxmoxVE/x")
  assert ffl.rewrite_text(once) == once


def test_multiple_matches_on_one_line():
  """Rewrite each supported repository reference in the same input string."""
  text = (
    "a=https://github.com/community-scripts/ProxmoxVE b=https://github.com/community-scripts/core"
  )
  assert ffl.rewrite_text(text) == (
    "a=https://github.com/pranavmishra90/ProxmoxVE b=https://github.com/pranavmishra90/pve-scripts-core"
  )


def test_rewrite_file_and_dry_run(tmp_path):
  """Dry-run reports a change without writing; normal mode writes it once."""
  f = tmp_path / "a.sh"
  f.write_text("https://github.com/community-scripts/ProxmoxVE\n")
  assert ffl.rewrite_file(f, dry_run=True) is True
  assert "community-scripts" in f.read_text()
  assert ffl.rewrite_file(f) is True
  assert f.read_text() == "https://github.com/pranavmishra90/ProxmoxVE\n"
  assert ffl.rewrite_file(f) is False


def test_preserves_crlf(tmp_path):
  """Retain Windows line endings while rewriting file contents."""
  f = tmp_path / "a.sh"
  f.write_bytes(b"https://github.com/community-scripts/core\r\n")
  ffl.rewrite_file(f)
  assert f.read_bytes() == b"https://github.com/pranavmishra90/pve-scripts-core\r\n"


def test_rewrite_repo_filters_files_and_dirs(tmp_path):
  """Scan supported shell suffixes while excluding configured directories."""
  url = "https://github.com/community-scripts/ProxmoxVE\n"
  for rel in [
    "ct/a.sh",
    "misc/b.func",
    "tools/c.bash",
    "README.md",
    ".github/w.sh",
    ".git/d.sh",
  ]:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(url)

  changed = {p.relative_to(tmp_path).as_posix() for p in ffl.rewrite_repo(tmp_path)}

  assert changed == {"ct/a.sh", "misc/b.func", "tools/c.bash"}
  assert (tmp_path / "README.md").read_text() == url
  assert (tmp_path / ".github/w.sh").read_text() == url
  assert (tmp_path / ".git/d.sh").read_text() == url


def test_skips_binary_files(tmp_path):
  """Leave files that cannot be decoded as UTF-8 unchanged."""
  f = tmp_path / "bin.sh"
  f.write_bytes(b"\xff\xfe\x00community-scripts")
  assert ffl.rewrite_file(f) is False


def test_main_dry_run(tmp_path, capsys):
  """Report prospective CLI changes without modifying the target file."""
  f = tmp_path / "a.sh"
  f.write_text("https://github.com/community-scripts/core\n")
  assert ffl.main([str(tmp_path), "--dry-run"]) == 0
  assert "1 file(s) would be updated" in capsys.readouterr().out
  assert "community-scripts" in f.read_text()
