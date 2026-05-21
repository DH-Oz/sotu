"""Tests for SOTU document parser tool (tools/parse.py)."""

import os

import pytest

from tools import parse

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests",
    "fixtures",
    "speeches",
)


@pytest.fixture
def biden_html() -> str:
    path = os.path.join(FIXTURES_DIR, "biden_2022.html")
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def biden_expected() -> str:
    path = os.path.join(FIXTURES_DIR, "biden_2022.expected.txt")
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def lincoln_html() -> str:
    path = os.path.join(FIXTURES_DIR, "lincoln_1861.html")
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def lincoln_expected() -> str:
    path = os.path.join(FIXTURES_DIR, "lincoln_1861.expected.txt")
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_parse_biden_2022(biden_html: str, biden_expected: str) -> None:
    """Assert that Biden's 2022 HTML is parsed identically to expected text."""
    parsed = parse.parse_speech_html(biden_html)
    assert isinstance(parsed, str)
    assert len(parsed) > 0
    # Clean text should preserve paragraphs and match expected exactly
    assert parsed.strip() == biden_expected.strip()


def test_parse_lincoln_1861(lincoln_html: str, lincoln_expected: str) -> None:
    """Assert that Lincoln's 1861 HTML is parsed identically to expected text."""
    parsed = parse.parse_speech_html(lincoln_html)
    assert isinstance(parsed, str)
    assert len(parsed) > 0
    assert parsed.strip() == lincoln_expected.strip()


def test_paragraph_breaks() -> None:
    """Assert that paragraph breaks are preserved as double newlines."""
    html = (
        "<div class='field-docs-content'>"
        "<p>Paragraph one.</p>"
        "<p>Paragraph two.</p>"
        "</div>"
    )
    parsed = parse.parse_speech_html(html)
    assert parsed == "Paragraph one.\n\nParagraph two."
