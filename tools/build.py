"""Build orchestrator for SOTU package.
Scrapes, parses, classifies, and validates the SOTU dataset.
"""

import argparse
import csv
import datetime
import json
import os
import shutil
import subprocess
import sys
from typing import Any

import pandas as pd
from selectolax.lexbor import LexborHTMLParser

from tools import classify, discover, parse, validate

# Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "raw", "ucsb")
DATA_DIR = os.path.join(BASE_DIR, "src", "sotu", "data")
SPEECHES_DIR = os.path.join(DATA_DIR, "speeches")
METADATA_CSV = os.path.join(DATA_DIR, "metadata.csv")
MANIFEST_JSON = os.path.join(DATA_DIR, "manifest.json")
GUIDEBOOK_FIXTURE = os.path.join(
    BASE_DIR, "tests", "fixtures", "index", "guidebook.html"
)


def parse_date(date_str: str) -> datetime.date:
    """Parse common UCSB date formats into a datetime.date object.

    Parameters
    - date_str (str): E.g. "January 28, 2003" or "December 03, 1861".

    Returns
    - datetime.date
    """
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not parse date string: '{date_str}'")


def build_dataset(delay: float = 0.1, max_speeches: int | None = None) -> None:
    """Extract, download, parse, and build the SOTU database.
    """
    print("Starting SOTU build process...")
    
    # Ensure directories exist. Speeches dir is cleared so stale files from
    # earlier builds (e.g. pre-normalisation Van Buren names, or addresses
    # subsequently excluded by _is_real_sotu) can't survive a rebuild.
    os.makedirs(RAW_DIR, exist_ok=True)
    if os.path.exists(SPEECHES_DIR):
        shutil.rmtree(SPEECHES_DIR)
    os.makedirs(SPEECHES_DIR, exist_ok=True)

    # 1. Discover SOTU URLs from local guidebook snapshot
    print(f"Discovering SOTU URLs from {GUIDEBOOK_FIXTURE}...")
    if not os.path.exists(GUIDEBOOK_FIXTURE):
        print(f"Error: Guidebook fixture not found at {GUIDEBOOK_FIXTURE}")
        sys.exit(1)

    with open(GUIDEBOOK_FIXTURE, encoding="utf-8") as f:
        guidebook_html = f.read()

    # Get all URLs from guidebook
    urls = discover.parse_guidebook_table(guidebook_html)
    print(f"Discovered {len(urls)} SOTU URLs.")

    if max_speeches is not None:
        urls = urls[:max_speeches]
        print(f"Limiting to first {max_speeches} speeches for testing/speed.")

    # 2. Save URLs list to file for the fetcher
    urls_file = os.path.join(BASE_DIR, "discovered_urls.txt")
    with open(urls_file, "w", encoding="utf-8") as f:
        for url in urls:
            f.write(f"{url}\n")

    # 3. Fetch all raw HTML files
    print(f"Fetching raw HTML files (delay={delay}s)...")
    # Run fetch.py script as a subprocess or call its main logic
    cmd = [
        sys.executable,
        os.path.join(BASE_DIR, "tools", "fetch.py"),
        "--urls-file", urls_file,
        "--out-dir", RAW_DIR,
        "--delay", str(delay),
        "--full-scrape"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error fetching HTML files:\n{result.stderr}")
        sys.exit(1)
    print("Raw HTML fetching completed successfully.")

    # 4. Parse and classify each fetched speech
    print("Parsing and classifying speeches...")
    parsed_records: list[dict[str, Any]] = []
    
    # We will map each URL to its HTML filename to parse it
    for idx, url in enumerate(urls):
        from tools.fetch import url_to_filename
        filename = url_to_filename(url)
        filepath = os.path.join(RAW_DIR, filename)

        if not os.path.exists(filepath):
            print(f"Warning: HTML file not found for {url} at {filepath}")
            continue

        with open(filepath, encoding="utf-8") as f:
            html_content = f.read()

        # Parse text
        text = parse.parse_speech_html(html_content)
        if not text:
            print(f"Warning: Empty text parsed for {url}")
            continue

        # Extract President and Date from HTML page
        html_parser = LexborHTMLParser(html_content)
        
        # Date extraction
        date_elem = html_parser.css_first(
            ".field-docs-start-date-time, .date-display-single"
        )
        if not date_elem:
            print(f"Warning: No date element found in {filename}. Skipping.")
            continue
        date_str = date_elem.text().strip()
        try:
            speech_date = parse_date(date_str)
        except Exception as e:
            print(
                f"Warning: Date parsing failed for '{date_str}' "
                f"in {filename}: {e}. Skipping."
            )
            continue
            
        year = speech_date.year

        # President name extraction
        pres_elem = html_parser.css_first(".field-docs-person")
        if not pres_elem:
            print(f"Warning: No president element found in {filename}. Skipping.")
            continue
        pres_full_name = pres_elem.text().strip().split("\n")[0].strip()

        # Clean any parenthetical terms or suffixes
        # E.g. "Donald J. Trump (1st Term)" -> "Donald J. Trump"
        # E.g. "Joseph R. Biden, Jr." -> "Joseph R. Biden"
        import re
        clean_name = pres_full_name
        clean_name = re.sub(r"\(.*?\)", "", clean_name).strip()
        clean_name = re.sub(r",?\s+Jr\.?$", "", clean_name).strip()

        # Extract last name for resolution
        pres_last = clean_name.split(" ")[-1]
        if "Buren" in clean_name:
            pres_last = "Van Buren"
        elif "Quincy Adams" in clean_name or "J.Q. Adams" in clean_name:
            pres_last = "Adams"
        
        # Apply classification logic to join presidents.csv
        try:
            pres_info = classify.resolve_president(year, pres_last)
        except Exception as e:
            print(
                f"Warning: President resolution failed for {pres_full_name} "
                f"({year}): {e}. Skipping."
            )
            continue

        # SOTU type logic: URL slug first (distinguishes spoken/written for
        # presidents who produced both in the same year), then the year +
        # president overrides file, then the year heuristic.
        sotu_type = classify.get_sotu_type(year, url=url, president=pres_last)

        parsed_records.append({
            "year": year,
            "date": speech_date.isoformat(),
            "president_id": pres_info["president_id"],
            "president": pres_last,
            "president_full": pres_info["president_full"],
            "party": pres_info["party"],
            "sotu_type": sotu_type,
            "source_url": url,
            "raw_html_path": os.path.relpath(filepath, BASE_DIR),
            "text": text,
            "word_count": len(text.split()),
            "raw_html_sha256": validate.compute_sha256(filepath),
        })

    # Sort records chronologically
    parsed_records.sort(key=lambda r: (r["date"], r["source_url"]))

    # Mark non-canonical entries (related UCSB documents that aren't the SOTU).
    # See classify.is_canonical_sotu for the policy; the metadata schema's
    # is_sotu column lets the loader filter by default and lets consumers
    # opt in to the auxiliary documents.
    for r in parsed_records:
        r["is_sotu"] = classify.is_canonical_sotu(r["source_url"])

    # Spoken/written disambiguation post-pass. For each (year, president)
    # group, if a "delivered" row exists, its sibling rows are the written
    # submission and must be reclassified — UCSB uses the generic
    # "annual-message-the-congress-the-state-the-union" tag for both
    # delivered and written-only SOTUs in the modern era, so the year
    # heuristic cannot tell them apart in mixed years (Nixon 1972/74,
    # Carter 1978-80).
    by_group: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for r in parsed_records:
        by_group.setdefault((r["year"], r["president"]), []).append(r)
    for group in by_group.values():
        delivered_rows = [
            r for r in group if classify.slug_indicates_delivered(r["source_url"])
        ]
        if not delivered_rows:
            continue
        for r in group:
            if classify.slug_indicates_delivered(r["source_url"]):
                r["sotu_type"] = "spoken"
            else:
                r["sotu_type"] = "written"

    # Group by (year, president) to assign within_year_idx and fileid.
    # Canonical SOTUs get the lowest index within a group so consumers can
    # rely on "<year>-<president>-1" being the canonical SOTU.
    print("Assigning unique chronological fileids...")
    counts: dict[tuple[int, str], int] = {}
    final_records: list[dict[str, Any]] = []

    parsed_records.sort(
        key=lambda r: (
            r["year"],
            r["president"],
            0 if r["is_sotu"] else 1,
            r["date"],
            r["source_url"],
        )
    )

    for r in parsed_records:
        key = (r["year"], r["president"])
        idx = counts.get(key, 0) + 1
        counts[key] = idx

        fileid = f"{r['year']}-{r['president'].replace(' ', '')}-{idx}"
        r["fileid"] = fileid

        # Write speech text to its final packaged path
        speech_filename = f"{fileid}.txt"
        speech_path = os.path.join(SPEECHES_DIR, speech_filename)

        with open(speech_path, "w", encoding="utf-8") as f:
            f.write(r["text"])

        r["sha256"] = validate.compute_sha256(speech_path)
        final_records.append(r)

    # 5. Write metadata.csv
    print(f"Writing packaged metadata to {METADATA_CSV}...")
    headers = [
        "fileid",
        "year",
        "date",
        "president_id",
        "president",
        "president_full",
        "party",
        "sotu_type",
        "is_sotu",
        "source_url",
        "raw_html_path",
        "word_count",
        "sha256",
    ]
    with open(METADATA_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in final_records:
            # We omit the massive text content from the metadata CSV
            row = {h: r[h] for h in headers}
            writer.writerow(row)

    # 6. Generate manifest.json. Deterministic: no wall-clock fields, no
    # hardcoded version. Coverage is derived from the data; the package
    # version belongs in pyproject.toml, not duplicated here.
    print(f"Generating packaged manifest to {MANIFEST_JSON}...")
    manifest_data: dict[str, Any] = {
        "coverage": [1790, max(int(r["year"]) for r in final_records)],
        "total_addresses": len(final_records),
        "files": {},
    }
    for r in sorted(final_records, key=lambda r: r["fileid"]):
        manifest_data["files"][r["fileid"]] = {
            "parsed_text_sha256": r["sha256"],
            "raw_html_sha256": r["raw_html_sha256"],
            "word_count": r["word_count"],
        }
    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, sort_keys=False)
        f.write("\n")

    # Clean up temporary URL list file
    if os.path.exists(urls_file):
        os.remove(urls_file)

    print("Package data build complete!")

    # 7. Run validator to verify correctness
    print("Running package validation...")
    metadata_df = pd.read_csv(METADATA_CSV)
    validate.validate_schema(metadata_df)
    validate.validate_coverage(metadata_df)
    validate.validate_determinism(metadata_df, SPEECHES_DIR, RAW_DIR, MANIFEST_JSON)
    print("Validation passed successfully!")


def main() -> None:
    """CLI entrypoint for tools.build.
    """
    parser = argparse.ArgumentParser(
        description="Build packaged SOTU dataset."
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Delay in seconds between scrape requests.",
    )
    parser.add_argument(
        "--max-speeches",
        type=int,
        help="Optional limit on the number of speeches to build (for testing).",
    )
    args = parser.parse_args()

    build_dataset(delay=args.delay, max_speeches=args.max_speeches)


if __name__ == "__main__":
    main()
