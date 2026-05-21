"""sotu — U.S. Presidential Annual Messages and State of the Union Addresses.

Provides programmatic, offline access to the full corpus of U.S. Presidential
Annual Messages (1790–1946) and State of the Union Addresses (1947–present).

All text content originates from the UC Santa Barbara American Presidency
Project (https://www.presidency.ucsb.edu/), curated by Gerhard Peters and
John T. Woolley. Please cite the American Presidency Project in any research
that uses this corpus.
"""

from sotu._corpus import fileids, metadata, raw
from sotu._loader import load

def _coverage_from_metadata() -> tuple[int, int]:
    """Derive (min_year, max_year) from the packaged metadata table.

    The metadata CSV is the single source of truth — the package version,
    docstring, and COVERAGE all agree because they all read this.
    """
    meta_df = metadata()
    if meta_df.empty:
        raise RuntimeError("sotu metadata is empty; corpus failed to load")
    return int(meta_df["year"].min()), int(meta_df["year"].max())


COVERAGE: tuple[int, int] = _coverage_from_metadata()

__doc__ = f"{__doc__ or 'SOTU Package.'}\n\nCoverage: {COVERAGE[0]} through {COVERAGE[1]}."

__all__ = ["COVERAGE", "fileids", "load", "metadata", "raw"]
