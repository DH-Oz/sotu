"""Validation tool for verifying SOTU package schema, coverage, and determinism.
"""

import hashlib
import json
import os

import pandas as pd

# File paths relative to the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METADATA_CSV = os.path.join(BASE_DIR, "src", "sotu", "data", "metadata.csv")
SPEECHES_DIR = os.path.join(BASE_DIR, "src", "sotu", "data", "speeches")
MANIFEST_JSON = os.path.join(BASE_DIR, "src", "sotu", "data", "manifest.json")
RAW_HTML_DIR = os.path.join(BASE_DIR, "raw", "ucsb")


def compute_sha256(filepath: str) -> str:
    """Compute the SHA-256 hash of a file.

    Parameters
    - filepath (str): Path to the file.

    Returns
    - str: Hex digest of the hash.
    """
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def validate_schema(df: pd.DataFrame) -> None:
    """Validate metadata DataFrame matches the exact schema and constraints.

    Parameters
    - df (pd.DataFrame): Metadata dataframe.
    """
    required_cols = [
        "fileid",
        "year",
        "president_id",
        "president",
        "president_full",
        "party",
        "sotu_type",
        "is_sotu",
        "source_url",
        "word_count",
    ]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Schema violation: Missing column '{col}'")

    # Check non-null constraints
    for col in required_cols:
        if df[col].isnull().any():
            raise ValueError(f"Schema violation: Column '{col}' contains null values")

    # Check data types
    if not pd.api.types.is_integer_dtype(df["year"]):
        raise TypeError("Schema violation: 'year' column must be integer type")
    if not pd.api.types.is_integer_dtype(df["word_count"]):
        raise TypeError("Schema violation: 'word_count' column must be integer type")


def validate_coverage(df: pd.DataFrame) -> None:
    """Validate calendar coverage and speech counts.

    Parameters
    - df (pd.DataFrame): Metadata dataframe.
    """
    years = df["year"].tolist()
    if not years:
        raise ValueError("Coverage violation: No SOTU metadata found")

    min_year = min(years)
    max_year = max(years)

    if min_year != 1790:
        raise ValueError(
            f"Coverage violation: Minimum year is {min_year}, expected 1790"
        )
    if max_year < 2025:
        raise ValueError(
            f"Coverage violation: Maximum year is {max_year}, "
            "expected at least 2025"
        )

    if len(df) < 230:
        raise ValueError(
            f"Coverage violation: Total addresses count is {len(df)}, "
            "expected >= 230"
        )


def validate_determinism(
    df: pd.DataFrame,
    speeches_dir: str,
    raw_html_dir: str,
    manifest_path: str,
) -> None:
    """Verify that speech text files and raw HTML files match the manifest.json hashes.

    Parameters
    - df (pd.DataFrame): Metadata dataframe.
    - speeches_dir (str): Directory containing speech text files.
    - raw_html_dir (str): Directory containing raw HTML files.
    - manifest_path (str): Path to manifest.json file.
    """
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest file not found at {manifest_path}")

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    files_manifest = manifest.get("files", {})

    for _, row in df.iterrows():
        fileid = row["fileid"]
        source_url = row["source_url"]

        if fileid not in files_manifest:
            raise ValueError(
                "Manifest desynchronization: File ID "
                f"'{fileid}' missing from manifest.json"
            )

        entry = files_manifest[fileid]

        # 1. Validate parsed text hash
        speech_path = os.path.join(speeches_dir, f"{fileid}.txt")
        if not os.path.exists(speech_path):
            raise FileNotFoundError(f"Speech file not found at {speech_path}")

        current_text_hash = compute_sha256(speech_path)
        expected_text_hash = entry.get("parsed_text_sha256")
        if current_text_hash != expected_text_hash:
            raise ValueError(
                f"Hash mismatch for parsed text {fileid}.txt:\n"
                f"  Expected: {expected_text_hash}\n"
                f"  Found:    {current_text_hash}"
            )

        # 2. Validate raw HTML hash (if the raw html folder is present)
        if os.path.exists(raw_html_dir):
            from urllib.parse import parse_qs, urlparse
            # Try to map URL to filename exactly as fetch.py does
            parsed = urlparse(source_url)
            query_params = parse_qs(parsed.query)
            if "pid" in query_params:
                filename = f"pid_{query_params['pid'][0]}.html"
            else:
                path = parsed.path.strip("/")
                parts = path.split("/")
                filename = f"{parts[-1]}.html" if parts and parts[-1] else ""

            if filename:
                html_path = os.path.join(raw_html_dir, filename)
                # If the raw HTML was downloaded, check it
                if os.path.exists(html_path):
                    current_html_hash = compute_sha256(html_path)
                    expected_html_hash = entry.get("raw_html_sha256")
                    if current_html_hash != expected_html_hash:
                        raise ValueError(
                            f"Hash mismatch for raw HTML '{filename}':\n"
                            f"  Expected: {expected_html_hash}\n"
                            f"  Found:    {current_html_hash}"
                        )


def main() -> None:
    """CLI entrypoint for tools.validate.
    """
    if not os.path.exists(METADATA_CSV):
        print(f"Error: Metadata CSV not found at {METADATA_CSV}")
        import sys
        sys.exit(1)

    df = pd.read_csv(METADATA_CSV)
    try:
        print("Validating schema...")
        validate_schema(df)
        print("Validating coverage...")
        validate_coverage(df)
        print("Validating determinism...")
        validate_determinism(df, SPEECHES_DIR, RAW_HTML_DIR, MANIFEST_JSON)
        print("Success: Dataset validation passed.")
    except Exception as e:
        print(f"Validation FAILED: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
