import pandas as pd
import pytest

import sotu


def test_coverage_constant() -> None:
    """Assert that the COVERAGE tuple exists and has expected shape."""
    assert hasattr(sotu, "COVERAGE")
    assert isinstance(sotu.COVERAGE, tuple)
    assert len(sotu.COVERAGE) == 2
    assert isinstance(sotu.COVERAGE[0], int)
    assert isinstance(sotu.COVERAGE[1], int)


def test_load_dataframe() -> None:
    """Assert that load() returns a valid pandas DataFrame with locked columns."""
    df = sotu.load()
    assert isinstance(df, pd.DataFrame)
    expected_cols = [
        "year",
        "president",
        "party",
        "sotu_type",
        "text",
    ]
    assert list(df.columns) == expected_cols
    assert len(df) >= 230


def test_load_full_dataframe() -> None:
    """Assert that load(full=True) returns a valid DataFrame with more columns."""
    df = sotu.load(full=True)
    assert isinstance(df, pd.DataFrame)
    expected_cols = {
        "year",
        "president",
        "president_full",
        "party",
        "sotu_type",
        "text",
        "source_url",
        "word_count",
    }
    assert expected_cols.issubset(df.columns)


def test_fileids() -> None:
    """Assert that fileids() returns a list of formatted strings."""
    ids = sotu.fileids()
    assert isinstance(ids, list)
    assert len(ids) >= 240
    for fileid in ids:
        assert isinstance(fileid, str)
        parts = fileid.split("-")
        assert len(parts) == 3
        assert parts[0].isdigit()  # year
        assert parts[1].isalpha()  # President Last Name (no spaces or punctuation)
        assert parts[2].isdigit()  # index within year


def test_fileids_have_no_whitespace() -> None:
    """Assert that no fileids contain whitespace."""
    assert all(" " not in fid for fid in sotu.fileids())


def test_fileid_segments_split_cleanly() -> None:
    """Assert that fileid segments split cleanly on hyphens."""
    for fid in sotu.fileids():
        year, name, idx = fid.rsplit("-", 2)
        assert year.isdigit() and len(year) == 4
        assert name.isalpha()
        assert idx.isdigit()


def test_raw() -> None:
    """Assert that raw(fileid) returns the speech content as a string."""
    ids = sotu.fileids()
    if not ids:
        pytest.fail("No fileids returned to test raw()")
    fid = ids[0]
    content = sotu.raw(fid)
    assert isinstance(content, str)
    assert len(content) > 0


def test_metadata() -> None:
    """Assert that metadata() returns the full DataFrame matching metadata.csv."""
    meta = sotu.metadata()
    assert isinstance(meta, pd.DataFrame)
    assert "fileid" in meta.columns
    assert len(meta) > 230
