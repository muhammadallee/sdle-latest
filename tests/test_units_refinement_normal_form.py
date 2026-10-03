"""The presentation-neutral normal form of a requirements document, and the content
digest built on it.

Pure functions, so these tests build every input as a string at runtime. Nothing here
reads the checkout: a checked-in document can arrive with either line ending depending
on the platform and the git settings, and the line-ending rule is exactly what is being
tested.
"""

from __future__ import annotations

import hashlib

import pytest

from conftest import sdle

normal = sdle.requirements_normal_form
digest = sdle.requirements_content_digest


def neutral(before: str, after: str) -> bool:
    return normal(before) == normal(after)


# -- line endings come first ----------------------------------------------------------


@pytest.mark.parametrize("ending", ["\r\n", "\r"])
def test_every_line_ending_convention_has_one_normal_form(ending):
    lines = ["# Title", "", "First paragraph.", "Second line."]
    assert neutral("\n".join(lines) + "\n", ending.join(lines) + ending)


def test_a_hard_break_survives_windows_line_endings():
    """The carriage return must be gone before the trailing-whitespace rule runs,
    or it would read as trailing whitespace and the two spaces would be judged
    against it. With CRLF the hard break is still a hard break."""
    crlf = "First instruction.  \r\nSecond instruction.\r\n"
    assert normal(crlf) == "First instruction.  \nSecond instruction.\n"
    assert neutral(crlf, "First instruction.  \nSecond instruction.\n")
    assert not neutral(crlf, "First instruction.\r\nSecond instruction.\r\n"), (
        "removing a hard break changes what renders, so it is not neutral")


# -- trailing whitespace: the one asymmetry on purpose ---------------------------------


def test_trailing_whitespace_on_a_prose_line_is_not_neutral():
    assert not neutral("A line.  \nNext.", "A line.\nNext.")
    assert not neutral("A line.\nNext.", "A line.   \nNext.")
    assert not neutral("A line.\t\nNext.", "A line.\nNext.")


def test_trailing_whitespace_is_neutral_where_it_cannot_matter():
    assert neutral("a\n   \nb", "a\n\nb")                      # a blank line
    assert neutral("| a | b |   \n", "| a | b |\n")             # a table row
    assert neutral("```\ncode   \n```\n", "```\ncode\n```\n")  # a fenced block


# -- runs of spaces ------------------------------------------------------------------------


def test_runs_of_spaces_inside_prose_text_are_neutral():
    assert neutral("The  service   must   respond.", "The service must respond.")


def test_leading_indentation_is_preserved():
    assert not neutral("  Indented prose.", "Indented prose.")
    assert not neutral("   Indented prose.", "  Indented prose.")


def test_code_spans_keep_their_spacing():
    assert neutral("use  `a  b`   here", "use `a  b` here")
    assert not neutral("use `a  b` here", "use `a b` here")
    assert neutral("run ``a ` b``  now", "run ``a ` b`` now")


def test_indented_lines_are_left_as_written():
    """Four-space indentation is code or a continuation, so its spacing is not
    touched - the conservative reading, which can only ask a human more often."""
    assert not neutral("    code  here", "    code here")


def test_a_table_rows_spacing_is_preserved():
    assert not neutral("| a  | b |", "| a | b |")


# -- fenced blocks ------------------------------------------------------------------------------


def test_a_fenced_block_keeps_its_internal_spacing_and_blank_lines():
    fenced = "```\nx  =  1\n\n\ny = 2\n```\n"
    assert normal(fenced) == fenced
    assert not neutral(fenced, "```\nx = 1\n\ny = 2\n```\n")
    assert not neutral(fenced, "```\nx  =  1\n\ny = 2\n```\n")


def test_tilde_fences_and_longer_fences_close_correctly():
    assert normal("~~~\na  b\n~~~\nc   d\n") == "~~~\na  b\n~~~\nc d\n"
    # A four-backtick fence is not closed by three; the span after it stays code.
    assert normal("````\na  b\n```\nc  d\n````\ne   f\n") == (
        "````\na  b\n```\nc  d\n````\ne f\n")


def test_an_unclosed_fence_runs_to_the_end_of_the_document():
    assert normal("```\na  b\nc   d\n") == "```\na  b\nc   d\n"


# -- blank lines and the end of the file -----------------------------------------------------


def test_runs_of_blank_lines_collapse_to_one():
    assert neutral("a\n\n\n\nb", "a\n\nb")
    assert neutral("a\n \n\t\n \nb", "a\n\nb")
    assert not neutral("a\nb", "a\n\nb"), "a paragraph break is not neutral"


def test_the_end_of_the_file_is_neutral():
    assert neutral("x", "x\n")
    assert neutral("x\n", "x\n\n\n")
    assert normal("") == ""
    assert normal("\n\n") == ""


# -- nothing else is normalised -----------------------------------------------------------------


@pytest.mark.parametrize("before, after", [
    ("The service must respond.", "The service should respond."),
    ("- first\n- second", "* first\n* second"),
    ("# Title", "## Title"),
    ("a *word* here", "a **word** here"),
    ("see [the spec](a.md)", "see [the spec](b.md)"),
    ("| a | b |\n|---|---|\n| 1 | 2 |", "| a | b |\n|---|---|\n| 1 | 3 |"),
    ("one\n\ntwo", "two\n\none"),
])
def test_a_change_to_what_the_document_says_is_never_neutral(before, after):
    assert not neutral(before, after)


# -- the property that makes it usable ---------------------------------------------------------


SAMPLES = [
    "",
    "plain",
    "# T\r\n\r\n\r\n- a  b\r\n  - c\r\n\r\n```\r\nx  \r\n```\r\n",
    "a  \nb\n\n\n| t |  \n\n    code  \n`x  y`   z  \n",
    "~~~\nunclosed  \n\n\n",
    "   \n\n  lead  text   \n",
]


@pytest.mark.parametrize("text", SAMPLES)
def test_the_normal_form_is_idempotent(text):
    assert normal(normal(text)) == normal(text)


# -- the content digest -----------------------------------------------------------------------


def test_the_digest_ignores_presentation_and_notices_content():
    base = {"requirements/a.md": b"# A\n\nThe  service  must respond.\n"}
    same = {"requirements/a.md": b"# A\r\n\r\n\r\nThe service must respond.\r\n"}
    changed = {"requirements/a.md": b"# A\n\nThe service should respond.\n"}
    assert digest(base) == digest(same)
    assert digest(base) != digest(changed)


def test_the_digest_is_not_the_raw_bytes_digest():
    raw = b"# A\r\n\r\nx\r\n"
    assert digest({"a.md": raw}) != hashlib.sha256(raw).hexdigest()


def test_the_digest_does_not_depend_on_insertion_order():
    one = {"b.md": b"b\n", "a.md": b"a\n"}
    two = {"a.md": b"a\n", "b.md": b"b\n"}
    assert digest(one) == digest(two)


def test_the_digest_is_over_paths_as_well_as_content():
    assert digest({"a.md": b"x\n"}) != digest({"b.md": b"x\n"})


def test_a_removed_hard_break_changes_the_digest():
    kept = {"a.md": b"first.  \nsecond.\n"}
    lost = {"a.md": b"first.\nsecond.\n"}
    assert digest(kept) != digest(lost)
