import pandas as pd

import sotu


def test_dataframe_dtypes() -> None:
    """Assert that columns in load() have correct types and non-null values."""
    df = sotu.load()
    
    # Types checking
    assert pd.api.types.is_integer_dtype(df["year"])
    assert pd.api.types.is_string_dtype(df["president"])
    assert pd.api.types.is_string_dtype(df["party"])
    assert pd.api.types.is_string_dtype(df["sotu_type"])
    assert pd.api.types.is_string_dtype(df["text"])

    # No null values allowed
    assert df["year"].notna().all()
    assert df["president"].notna().all()
    assert df["party"].notna().all()
    assert df["sotu_type"].notna().all()
    assert df["text"].notna().all()


def test_full_dataframe_dtypes() -> None:
    """Assert that full columns in load(full=True) have correct types."""
    df = sotu.load(full=True)
    
    assert "source_url" in df.columns
    assert "word_count" in df.columns
    assert "president_full" in df.columns
    
    assert pd.api.types.is_string_dtype(df["source_url"])
    assert pd.api.types.is_integer_dtype(df["word_count"])
    assert pd.api.types.is_string_dtype(df["president_full"])


def test_sotu_type_vocabulary() -> None:
    """Assert that sotu_type vocabulary is strictly {'spoken', 'written'}."""
    df = sotu.load()
    assert set(df["sotu_type"].unique()) == {"spoken", "written"}


def test_default_load_returns_contract_columns_only() -> None:
    """Assert that load() by default returns only the 5 contract columns."""
    df = sotu.load()
    assert list(df.columns) == ["year", "president", "party", "sotu_type", "text"]


def test_load_full_includes_disambiguation() -> None:
    """Assert that load(full=True) returns the extended columns
    including president_full.
    """
    df = sotu.load(full=True)
    assert "president_full" in df.columns
