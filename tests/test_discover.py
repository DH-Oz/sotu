import os

import pytest

from tools import discover

# Fixture paths
FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests",
    "fixtures",
    "index",
)


@pytest.fixture
def taxonomy_45_html() -> str:
    path = os.path.join(FIXTURE_DIR, "taxonomy_45.html")
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def taxonomy_400_html() -> str:
    path = os.path.join(FIXTURE_DIR, "taxonomy_400.html")
    with open(path, encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def guidebook_html() -> str:
    path = os.path.join(FIXTURE_DIR, "guidebook.html")
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_parse_taxonomy_page(taxonomy_45_html: str) -> None:
    """Assert that parsing a taxonomy page correctly extracts document URLs."""
    urls = discover.parse_taxonomy_content(taxonomy_45_html)
    assert isinstance(urls, list)
    assert len(urls) > 0

    # Every item must be a relative or absolute URL string
    for url in urls:
        assert isinstance(url, str)
        assert "/documents/" in url or "presidency.ucsb.edu" in url


def test_parse_taxonomy_pagination(taxonomy_45_html: str) -> None:
    """Assert that we find pagination page URLs."""
    page_urls = discover.parse_taxonomy_pagination(taxonomy_45_html)
    assert isinstance(page_urls, list)
    # Pager should have links like ?page=1, ?page=2
    assert len(page_urls) > 0
    for url in page_urls:
        assert "?page=" in url


def test_parse_guidebook_table(guidebook_html: str) -> None:
    """Assert that we extract historical URLs from the main guidebook grid table."""
    urls = discover.parse_guidebook_table(guidebook_html)
    assert isinstance(urls, list)
    assert len(urls) > 0

    # Ensure we get early URLs (like Buchanan or Pierce First Annual Message)
    assert any("first-annual-message" in u for u in urls)
    for url in urls:
        assert isinstance(url, str)
        assert "/documents/" in url or "presidency.ucsb.edu" in url


# ---------------------------------------------------------------------------
# _is_real_sotu — every positive slug below appears verbatim somewhere in
# src/sotu/data/metadata.csv. Every negative slug is a non-SOTU UCSB
# document that must be excluded.
# ---------------------------------------------------------------------------
BASE = "https://www.presidency.ucsb.edu/documents/"

POSITIVE_SLUGS = [
    # Historic Annual Messages (1790s-1900s)
    "first-annual-message",
    "first-annual-message-19",
    "seventh-annual-message",
    "eighth-annual-message-9",
    # Historic "annual-address" variant (Washington-era)
    "first-annual-address-congress",
    "eighth-annual-address-congress",
    # Modern SOTUs — the canonical pattern (with "the-state-the-union")
    "address-before-joint-session-the-congress-the-state-the-union-31",
    "address-before-joint-session-congress-the-state-the-union",
    # Modern SOTUs — the "state-the-union" (no leading "the-") variant
    "state-the-union-address",
    "state-the-union-message-congress",
    # Truman 1948 special: pid-style URL fallback
    "index.php?pid=12979",
]

NEGATIVE_SLUGS = [
    # The eight first-year joint sessions that must not leak in
    "address-program-economic-recovery-0",
    "address-administration-goals-before-joint-session-congress",
    "address-before-joint-session-congress-administration-goals",
    "address-before-joint-session-congress-administration-goals-0",
    "address-before-joint-session-the-congress-1",
    "address-before-joint-session-the-congress-2",
    "address-before-joint-session-the-congress-3",
    "address-before-joint-session-the-congress-4",
    # Other non-SOTU documents
    "inaugural-address-15",
    "remarks-the-press-pool",
    "executive-order-13769",
    "farewell-address-the-nation",
    "proclamation-9844",
]


@pytest.mark.parametrize("slug", POSITIVE_SLUGS)
def test_is_real_sotu_accepts_real_sotu(slug: str) -> None:
    assert discover._is_real_sotu(BASE + slug) is True, slug


@pytest.mark.parametrize("slug", NEGATIVE_SLUGS)
def test_is_real_sotu_rejects_non_sotu(slug: str) -> None:
    assert discover._is_real_sotu(BASE + slug) is False, slug
