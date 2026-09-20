"""Every local link and anchor in the authored documents resolves (F-010, AC-08).

The documentation check that shipped only proved that directories exist. A page
can be present and still be unreachable, or link to a file that was renamed. This
checks what a reader actually clicks: inline links, images and reference-style
links to local files and to `#anchors`, and that every page under `docs/` is
reachable from the two entry documents. External URLs are not fetched: a network
failure must never look like a broken local link.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from conftest import REPO_ROOT

AUTHORED_ROOTS = ("README.md", "CLAUDE.md", "scripts/README.md", "docs", ".claude")
ENTRY_DOCUMENTS = ("README.md", "docs/README.md")

FENCE = re.compile(r"(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1[ \t]*$")
INLINE_CODE = re.compile(r"`[^`\n]*`")
INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
REFERENCE_USE = re.compile(r"!?\[[^\]\n]+\]\[([^\]\n]*)\]")
REFERENCE_DEF = re.compile(r"(?m)^\s{0,3}\[([^\]\n]+)\]:\s*(\S+)")
HEADING = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$")


def strip_fences(text: str) -> str:
    """Remove fenced blocks, which quote links and headings without being
    either. Line count is preserved so a report can name the line."""
    def blank(match: re.Match) -> str:
        return "\n" * match.group(0).count("\n")
    return FENCE.sub(blank, text)


def strip_code(text: str) -> str:
    """Also remove inline code: a link written inside backticks is a quotation.
    Headings must NOT use this, because the text of an inline code span is part
    of the heading's anchor."""
    return INLINE_CODE.sub("", strip_fences(text))


def slug(heading: str) -> str:
    """GitHub's anchor for a heading."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = text.replace("`", "").replace("*", "")
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors_of(text: str) -> set[str]:
    seen: dict[str, int] = {}
    found = set()
    for match in HEADING.finditer(strip_fences(text)):
        base = slug(match.group(2))
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.add(base if count == 0 else f"{base}-{count}")
    return found


def is_external(target: str) -> bool:
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target)) or target.startswith("//")


def exists_exact(path: Path) -> bool:
    """Case-sensitive existence of every path component, so a link that works
    on Windows but not on Linux is reported. `path` must not have been through
    `resolve()`, which normalises case on case-insensitive filesystems."""
    path = Path(os.path.normpath(path))
    if not path.exists():
        return False
    try:
        current = Path(path.anchor)
        for part in path.parts[1:]:
            if part not in {p.name for p in current.iterdir()}:
                return False
            current = current / part
    except OSError:
        return False
    return True


def links_of(text: str) -> list[tuple[int, str]]:
    code_free = strip_code(text)
    found = []
    definitions = {m.group(1).lower(): m.group(2) for m in REFERENCE_DEF.finditer(code_free)}
    for number, line in enumerate(code_free.split("\n"), 1):
        for match in INLINE_LINK.finditer(line):
            found.append((number, match.group(1).strip("<>")))
        for match in REFERENCE_USE.finditer(line):
            key = (match.group(1) or "").lower()
            if key in definitions:
                found.append((number, definitions[key].strip("<>")))
    return found


def broken_links(files: list[Path], root: Path) -> list[str]:
    cache: dict[Path, set[str]] = {}
    problems = []
    for source in files:
        text = source.read_text(encoding="utf-8")
        for number, target in links_of(text):
            if not target or is_external(target):
                continue
            path_part, _, anchor = target.partition("#")
            destination = (source if not path_part
                           else Path(os.path.normpath(source.parent / path_part)))
            where = f"{source.relative_to(root).as_posix()}:{number}"
            try:
                destination.relative_to(root)
            except ValueError:
                problems.append(f"{where}: {target} leaves the repository")
                continue
            if not exists_exact(destination):
                problems.append(f"{where}: {target} does not exist")
                continue
            if anchor and destination.suffix.lower() == ".md":
                if destination not in cache:
                    cache[destination] = anchors_of(destination.read_text(encoding="utf-8"))
                if anchor.lower() not in cache[destination]:
                    problems.append(f"{where}: {target} has no such heading")
    return problems


def authored_files(root: Path = REPO_ROOT) -> list[Path]:
    files: list[Path] = []
    for entry in AUTHORED_ROOTS:
        path = root / entry
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(p for p in path.rglob("*.md") if p.is_file()))
    return files


def reachable_from(entries: list[Path], root: Path) -> set[Path]:
    seen: set[Path] = set()
    queue = [e.resolve() for e in entries if e.exists()]
    while queue:
        page = queue.pop()
        if page in seen:
            continue
        seen.add(page)
        if page.suffix.lower() != ".md":
            continue
        for _, target in links_of(page.read_text(encoding="utf-8")):
            if not target or is_external(target):
                continue
            path_part = target.partition("#")[0]
            if not path_part:
                continue
            destination = (page.parent / path_part).resolve()
            if destination.is_dir():
                readme = destination / "README.md"
                if readme.exists():
                    queue.append(readme)
            elif destination.exists():
                queue.append(destination)
    return seen


# -- the real repository -----------------------------------------------------


def test_the_scan_covers_the_authored_documents_and_is_not_vacuous():
    files = {p.relative_to(REPO_ROOT).as_posix() for p in authored_files()}
    assert {"README.md", "CLAUDE.md", "docs/GETTING-STARTED.md",
            "docs/README.md", "docs/SDLE-Reference-Guide.md"} <= files
    assert len(files) >= 30, len(files)
    checked = sum(len(links_of(p.read_text(encoding="utf-8"))) for p in authored_files())
    assert checked >= 50, checked


def test_every_local_link_and_anchor_in_the_authored_documents_resolves():
    problems = broken_links(authored_files(), REPO_ROOT)
    assert problems == [], "\n".join(problems)


def test_every_page_under_docs_is_reachable_from_an_entry_document():
    entries = [REPO_ROOT / e for e in ENTRY_DOCUMENTS]
    reachable = reachable_from(entries, REPO_ROOT)
    docs = {p.resolve() for p in (REPO_ROOT / "docs").rglob("*.md")}
    orphans = sorted(p.relative_to(REPO_ROOT.resolve()).as_posix() for p in docs - reachable)
    assert orphans == [], orphans


# -- the checker can fail ----------------------------------------------------


def write(root: Path, name: str, body: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_a_link_to_a_missing_file_is_reported(tmp_path):
    page = write(tmp_path, "a.md", "See [b](b.md).\n")
    assert broken_links([page], tmp_path) == ["a.md:1: b.md does not exist"]


def test_a_link_to_a_missing_heading_is_reported(tmp_path):
    write(tmp_path, "b.md", "# Real heading\n")
    page = write(tmp_path, "a.md", "See [x](b.md#no-such-heading).\n")
    assert broken_links([page], tmp_path) == ["a.md:1: b.md#no-such-heading has no such heading"]


def test_an_existing_heading_and_a_same_page_anchor_pass(tmp_path):
    write(tmp_path, "b.md", "# Real heading\n\n## 4. A `code` title (extra)\n")
    page = write(tmp_path, "a.md",
                 "# Top\n[ok](b.md#real-heading) [ok2](b.md#4-a-code-title-extra) [self](#top)\n")
    assert broken_links([page], tmp_path) == []


def test_a_duplicate_heading_gets_a_numbered_anchor(tmp_path):
    write(tmp_path, "b.md", "# Same\n\n# Same\n")
    page = write(tmp_path, "a.md", "[first](b.md#same) [second](b.md#same-1) [third](b.md#same-2)\n")
    assert broken_links([page], tmp_path) == ["a.md:1: b.md#same-2 has no such heading"]


def test_a_reference_style_link_is_checked(tmp_path):
    page = write(tmp_path, "a.md", "See [text][ref].\n\n[ref]: gone.md\n")
    assert broken_links([page], tmp_path) == ["a.md:1: gone.md does not exist"]


def test_links_inside_code_are_not_links(tmp_path):
    page = write(tmp_path, "a.md",
                 "Use `[x](nothing.md)`.\n\n```\n[y](also-nothing.md)\n```\n")
    assert broken_links([page], tmp_path) == []


def test_external_urls_are_never_fetched_or_judged(tmp_path):
    page = write(tmp_path, "a.md", "[w](https://example.invalid/x) [m](mailto:a@b.c)\n")
    assert broken_links([page], tmp_path) == []


def test_a_link_with_the_wrong_case_is_reported(tmp_path):
    write(tmp_path, "Real.md", "# T\n")
    page = write(tmp_path, "a.md", "[x](real.md)\n")
    assert broken_links([page], tmp_path) == ["a.md:1: real.md does not exist"]


def test_an_unreachable_page_is_an_orphan(tmp_path):
    entry = write(tmp_path, "README.md", "[linked](docs/a.md)\n")
    write(tmp_path, "docs/a.md", "# A\n")
    write(tmp_path, "docs/lonely.md", "# Nobody links here\n")
    reachable = reachable_from([entry], tmp_path)
    docs = {p.resolve() for p in (tmp_path / "docs").rglob("*.md")}
    assert sorted(p.name for p in docs - reachable) == ["lonely.md"]


@pytest.mark.parametrize("heading, expected", [
    ("Getting started", "getting-started"),
    ("4. Install the Spec Kit integration", "4-install-the-spec-kit-integration"),
    ("`sdle.sh validate` — the check", "sdlesh-validate--the-check"),
    ("Look something up!", "look-something-up"),
])
def test_the_slug_rule_matches_githubs(heading, expected):
    assert slug(heading) == expected
