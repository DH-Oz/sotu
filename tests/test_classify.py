"""Tests for SOTU classification and metadata joining (tools/classify.py).
"""

import pytest

from tools import classify


def test_classify_sotu_types() -> None:
    """Assert SOTU format is correctly classified based on year and overrides."""
    # Heuristic: 1790-1800 is spoken
    assert classify.get_sotu_type(1795) == "spoken"

    # Heuristic: 1801-1912 is written
    assert classify.get_sotu_type(1805) == "written"

    # Heuristic: 1913-present is spoken
    assert classify.get_sotu_type(1915) == "spoken"

    # Overrides
    assert classify.get_sotu_type(1981) == "written"  # Carter override
    assert classify.get_sotu_type(1956) == "written"  # Eisenhower override


def test_classify_sotu_type_from_url_slug() -> None:
    """A "delivered" slug marks the row spoken; sibling reclassification happens at build time.

    classify.get_sotu_type only treats "delivered" as unambiguous spoken;
    everything else falls back to the year heuristic + overrides. UCSB
    uses "annual-message-the-congress-the-state-the-union" as a generic
    tag for both delivered and written-only modern SOTUs, so the slug
    alone cannot decide written vs spoken — the build pipeline's group
    post-pass handles that.
    """
    base = "https://www.presidency.ucsb.edu/documents/"
    # Carter 1978 spoken delivery
    assert classify.get_sotu_type(
        1978,
        url=base + "the-state-the-union-address-delivered-before-joint-session-the-congress-1",
    ) == "spoken"
    # Modern "annual-message" tag: falls through to year heuristic (1978 → spoken)
    assert classify.get_sotu_type(
        1978, url=base + "the-state-the-union-annual-message-the-congress-2"
    ) == "spoken"
    # Nixon 1973 pid URL — no slug info; falls through to override (written)
    assert classify.get_sotu_type(
        1973, url="https://www.presidency.ucsb.edu/ws/index.php?pid=3996"
    ) == "written"


def test_is_canonical_sotu() -> None:
    """is_canonical_sotu excludes auxiliary documents that aren't the SOTU itself."""
    base = "https://www.presidency.ucsb.edu/"
    # Canonical SOTUs
    assert classify.is_canonical_sotu(base + "documents/state-the-union-address")
    assert classify.is_canonical_sotu(base + "documents/annual-message-the-congress")
    assert classify.is_canonical_sotu(base + "ws/index.php?pid=3996")  # Nixon 1973 overview
    # Auxiliaries
    assert not classify.is_canonical_sotu(
        base + "documents/radio-address-summarizing-the-state-the-union-message"
    )
    assert not classify.is_canonical_sotu(
        base + "documents/remarks-the-state-the-union-message-key-west-florida"
    )
    # Nixon 1973 topical Special Messages
    assert not classify.is_canonical_sotu(base + "ws/index.php?pid=4101")
    assert not classify.is_canonical_sotu(base + "ws/index.php?pid=4140")


def test_resolve_president() -> None:
    """Assert presidents are correctly resolved with last name and year."""
    # Theodore Roosevelt vs Franklin D. Roosevelt
    p_tr = classify.resolve_president(1905, "Roosevelt")
    assert p_tr["president_id"] == "roosevelt-26"
    assert p_tr["president_full"] == "Theodore Roosevelt"
    assert p_tr["party"] == "Republican"

    p_fdr = classify.resolve_president(1936, "Roosevelt")
    assert p_fdr["president_id"] == "roosevelt-32"
    assert p_fdr["president_full"] == "Franklin D. Roosevelt"
    assert p_fdr["party"] == "Democratic"

    # John Adams vs John Quincy Adams
    p_ja = classify.resolve_president(1798, "Adams")
    assert p_ja["president_id"] == "adams-1"
    assert p_ja["president_full"] == "John Adams"

    p_jqa = classify.resolve_president(1826, "Adams")
    assert p_jqa["president_id"] == "adams-6"
    assert p_jqa["president_full"] == "John Quincy Adams"


def test_resolve_president_not_found() -> None:
    """Assert resolution throws or returns safe fallback if not found."""
    with pytest.raises(ValueError, match="Could not resolve president"):
        classify.resolve_president(1800, "Nonexistent")
