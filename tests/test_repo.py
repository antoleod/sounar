"""The repository itself: nothing personal in it, every example setup documented, every link in the
docs pointing at something that exists."""
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
ADDRESS = re.compile(r"[0-9A-Fa-f]{2}([:_])[0-9A-Fa-f]{2}(?:\1[0-9A-Fa-f]{2}){4}")
# The prototype's speaker names, spelled so this file doesn't contain them.
HOME_DIR = "/" + "home" + "/"
PROTOTYPE_NAMES = ["".join(map(chr, (97, 109, 97, 121, 97))), "".join(map(chr, (101, 48, 110)))]


def tracked():
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, text=True).stdout
    files = [REPO / f for f in out.split("\0") if f]
    if not files:
        pytest.skip("not a git checkout")
    return [f for f in files if f.exists() and f.suffix not in (".png", ".jpg")]


def test_no_personal_strings():
    bad = []
    for f in tracked():
        text = f.read_text(errors="ignore")
        for m in ADDRESS.finditer(text):
            if set(m.group(0).replace(m.group(1), "")) - {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"} \
                    or not m.group(0).startswith("00"):
                bad.append(f"{f.relative_to(REPO)}: address {m.group(0)}")
        low = text.lower()
        for name in PROTOTYPE_NAMES:
            if re.search(rf"\b{name}\b", low):
                bad.append(f"{f.relative_to(REPO)}: a device name")
        if HOME_DIR in text:
            bad.append(f"{f.relative_to(REPO)}: a home directory")
    assert bad == []


def test_every_setup_documented():
    readme = (REPO / "setups/README.md").read_text()
    for f in (REPO / "setups").glob("*.toml"):
        assert f"({f.name})" in readme, f.name


LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def test_docs_links_resolve():
    broken = []
    for md in [f for f in tracked() if f.suffix == ".md"]:
        for target in LINK.findall(md.read_text()):
            if re.match(r"[a-z]+:", target):
                continue
            if not (md.parent / target).exists():
                broken.append(f"{md.relative_to(REPO)} -> {target}")
    assert broken == []


def test_community_files_present():
    for f in ("README.md", "LICENSE", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", "CHANGELOG.md",
              ".github/workflows/ci.yml", ".github/pull_request_template.md",
              ".github/ISSUE_TEMPLATE/bug_report.yml", ".github/ISSUE_TEMPLATE/share_setup.yml",
              ".github/ISSUE_TEMPLATE/idea.yml", ".github/ISSUE_TEMPLATE/config.yml"):
        assert (REPO / f).exists(), f
    assert "MIT License" in (REPO / "LICENSE").read_text()
