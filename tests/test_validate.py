import pandas as pd
import pytest

from tools import validate


def test_validate_schema_missing_col() -> None:
    """Assert that a missing required column triggers a ValueError."""
    # Create invalid dataframe missing 'party'
    df = pd.DataFrame({
        "fileid": ["1790-Washington-1"],
        "year": [1790],
        "president_id": ["washington"],
        "president": ["Washington"],
        "president_full": ["George Washington"],
        "sotu_type": ["spoken"],
        "is_sotu": [True],
        "source_url": ["http://test.com"],
        "word_count": [1000],
    })
    
    with pytest.raises(ValueError, match="Schema violation: Missing column 'party'"):
        validate.validate_schema(df)


def test_validate_schema_null_value() -> None:
    """Assert that null values in required columns trigger a ValueError."""
    df = pd.DataFrame({
        "fileid": ["1790-Washington-1"],
        "year": [1790],
        "president_id": ["washington"],
        "president": ["Washington"],
        "president_full": ["George Washington"],
        "party": [None],  # Null value
        "sotu_type": ["spoken"],
        "is_sotu": [True],
        "source_url": ["http://test.com"],
        "word_count": [1000],
    })
    
    msg = "Schema violation: Column 'party' contains null values"
    with pytest.raises(ValueError, match=msg):
        validate.validate_schema(df)


def test_validate_schema_incorrect_type() -> None:
    """Assert that incorrect column datatypes trigger a TypeError."""
    df = pd.DataFrame({
        "fileid": ["1790-Washington-1"],
        "year": ["1790"],  # String instead of int
        "president_id": ["washington"],
        "president": ["Washington"],
        "president_full": ["George Washington"],
        "party": ["Nonpartisan"],
        "sotu_type": ["spoken"],
        "is_sotu": [True],
        "source_url": ["http://test.com"],
        "word_count": [1000],
    })
    
    msg = "Schema violation: 'year' column must be integer type"
    with pytest.raises(TypeError, match=msg):
        validate.validate_schema(df)


def test_validate_coverage_bounds() -> None:
    """Assert that invalid bounds (e.g. starting at 1800) trigger a ValueError."""
    df = pd.DataFrame({
        "fileid": ["1800-Adams-1"],
        "year": [1800],  # Min year is 1800, expected 1790
        "president_id": ["adams-1"],
        "president": ["Adams"],
        "president_full": ["John Adams"],
        "party": ["Federalist"],
        "sotu_type": ["spoken"],
        "is_sotu": [True],
        "source_url": ["http://test.com"],
        "word_count": [1000],
    })
    
    msg = "Coverage violation: Minimum year is 1800, expected 1790"
    with pytest.raises(ValueError, match=msg):
        validate.validate_coverage(df)


def test_validate_coverage_too_few_records() -> None:
    """Assert that having too few addresses triggers a ValueError."""
    df = pd.DataFrame({
        "fileid": ["1790-Washington-1", "2025-Trump-1"],
        "year": [1790, 2025],
        "president_id": ["washington", "trump-2"],
        "president": ["Washington", "Trump"],
        "president_full": ["George Washington", "Donald J. Trump"],
        "party": ["Nonpartisan", "Republican"],
        "sotu_type": ["spoken", "spoken"],
        "is_sotu": [True, True],
        "source_url": ["http://test.com", "http://test.com"],
        "word_count": [1000, 1200],
    })
    
    msg = "Coverage violation: Total addresses count is 2, expected >= 230"
    with pytest.raises(ValueError, match=msg):
        validate.validate_coverage(df)
