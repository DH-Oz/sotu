"""Corpus module providing NLTK-style fileids and raw speech accessors."""

import os

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
METADATA_CSV = os.path.join(DATA_DIR, "metadata.csv")
SPEECHES_DIR = os.path.join(DATA_DIR, "speeches")


def metadata() -> pd.DataFrame:
    """Return the complete metadata DataFrame from the packaged CSV.

    Returns
    - pd.DataFrame: Full metadata rows.
    """
    if not os.path.exists(METADATA_CSV):
        raise FileNotFoundError(
            f"SOTU metadata file not found at {METADATA_CSV}. "
            "Please run the build script 'sotu-build' to generate the package data."
        )
    return pd.read_csv(METADATA_CSV)


def fileids() -> list[str]:
    """Return a list of all speech file identifiers sorted chronologically.

    Returns
    - list[str]: Unique fileids.
    """
    df = metadata()
    return list(df["fileid"].tolist())


def raw(fileid: str) -> str:
    """Return the raw text of the given speech fileid.

    Parameters
    - fileid (str): The unique speech fileid (e.g. '1790-Washington-1').

    Returns
    - str: Raw text content of the speech.
    """
    if not SPEECHES_DIR:
        raise FileNotFoundError("Speeches directory is not defined.")

    speech_path = os.path.join(SPEECHES_DIR, f"{fileid}.txt")
    if not os.path.exists(speech_path):
        raise FileNotFoundError(
            f"SOTU speech file '{fileid}' not found at {speech_path}. "
            "Please run the build script 'sotu-build' to generate the package data."
        )

    with open(speech_path, encoding="utf-8") as f:
        return f.read()
