"""Loader module for loading SOTU speeches into a pandas DataFrame."""

import pandas as pd

from sotu._corpus import metadata, raw

_CONTRACT_COLUMNS: list[str] = ["year", "president", "party", "sotu_type", "text"]


def load(full: bool = False, include_related: bool = False) -> pd.DataFrame:
    """Load SOTU speeches into a pandas DataFrame.

    Parameters
    ----------
    full
        If True, returns the extended metadata schema (fileid, dates, source
        URLs, hashes, etc.) instead of the five-column contract view.
    include_related
        If True, also returns UCSB documents the corpus carries alongside
        the canonical SOTUs — Nixon's 1973 series of topical Special
        Messages, the 1945 Roosevelt radio summary, the 1956 Eisenhower
        Key West remarks, etc. By default these `is_sotu=False` rows are
        filtered out so the masterclass contract (`df[df.sotu_type ==
        "spoken"]`, `df[df.president == "Washington"]`) returns one
        canonical address per (year, president).
    """
    df = metadata().copy()
    df["text"] = [raw(fid) for fid in df["fileid"]]

    if not include_related:
        df = df[df["is_sotu"]].reset_index(drop=True)

    if not full:
        return df[_CONTRACT_COLUMNS]

    base_cols = [
        "fileid",
        "year",
        "president",
        "party",
        "sotu_type",
        "is_sotu",
        "text",
    ]
    other_cols = [col for col in df.columns if col not in base_cols]
    return df[base_cols + other_cols]
