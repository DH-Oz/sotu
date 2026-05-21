"""Classification and president metadata joining tool for SOTU corpus."""

import csv
import os

# File paths relative to the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRESIDENTS_CSV = os.path.join(BASE_DIR, "src", "sotu", "data", "presidents.csv")
OVERRIDES_CSV = os.path.join(BASE_DIR, "data", "sotu_type_overrides.csv")


# UCSB records a handful of documents in the "State of the Union" taxonomy
# that aren't the SOTU itself — auxiliary summaries, supplemental remarks,
# or Nixon's 1973 series of topical Special Messages to Congress (only the
# Feb 2 overview, pid=3996, is the SOTU). We retain these in the corpus so
# scholars can study them, but mark them is_sotu=False so default loaders
# return the canonical address per (year, president). See the
# `is_canonical_sotu` policy below; the round-4 audit captures the reasoning.
_NIXON_1973_NON_SOTU_PIDS = frozenset(
    {"4101", "4102", "4111", "4112", "4117", "4121", "4128", "4134", "4135", "4140"}
)


def is_canonical_sotu(url: str) -> bool:
    """Classify whether a UCSB document is the canonical SOTU itself.

    Rules:
    - Radio summaries ("radio-address-summarizing-...") are auxiliary.
    - "remarks-..." slugs are auxiliary (e.g. Eisenhower's 1956 Key West remarks).
    - Nixon's 1973 series: only the Feb 2 overview (pid=3996) is the SOTU;
      the ten policy-specific Special Messages to Congress are auxiliary.
    - Everything else passing _is_real_sotu is canonical.
    """
    slug = url.rsplit("/", 1)[-1]
    if slug.startswith("radio-address-summarizing"):
        return False
    if slug.startswith("remarks-"):
        return False
    if "?pid=" in url:
        pid = url.rsplit("pid=", 1)[-1].split("&", 1)[0]
        if pid in _NIXON_1973_NON_SOTU_PIDS:
            return False
    return True


def slug_indicates_delivered(url: str) -> bool:
    """True if the slug contains the unambiguous "delivered" marker.

    UCSB uses two distinct slug patterns when a president produced both a
    spoken delivery and a written submission in the same year (e.g.
    Nixon 1972/74, Carter 1978-80). The delivered version's slug always
    contains "delivered"; the written submission's does not. UCSB's
    generic "annual-message-the-congress-the-state-the-union" tag is
    used for both delivered and written-only SOTUs in the modern era, so
    "annual-message" alone is not a reliable written-form signal.
    """
    slug = url.rsplit("/", 1)[-1].split("?", 1)[0]
    return "delivered" in slug


def get_sotu_type(year: int, url: str = "", president: str = "") -> str:
    """Classify the SOTU format from year, URL slug, and president last name.

    Resolution order:
    1. If the slug contains "delivered" the classification is
       unambiguously "spoken".
    2. The overrides file is consulted next. A row matches when its year
       equals `year` AND its president (if specified) equals `president`.
       This lets transition years like 1953 (Truman/Eisenhower) and 1961
       (Eisenhower/Kennedy) carry different sotu_types per president.
    3. Year heuristic: 1790-1800 spoken, 1801-1912 written, 1913+ spoken.

    Build-time post-processing in tools/build.py then walks (year,
    president) groups and flips the non-delivered sibling to "written"
    when a delivered row exists alongside it.
    """
    if url and slug_indicates_delivered(url):
        return "spoken"

    if os.path.exists(OVERRIDES_CSV):
        with open(OVERRIDES_CSV, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row["year"]) != year:
                    continue
                row_pres = row.get("president", "").strip()
                if row_pres and president and row_pres != president:
                    continue
                return row["sotu_type"]

    if 1790 <= year <= 1800:
        return "spoken"
    if 1801 <= year <= 1912:
        return "written"
    return "spoken"


def resolve_president(year: int, president_last: str) -> dict[str, str]:
    """Resolve a president record based on last name and year.

    Parameters
    - year (int): Year of the SOTU.
    - president_last (str): President's last name.

    Returns
    - dict[str, str]: The matched president row details.
    """
    if not os.path.exists(PRESIDENTS_CSV):
        raise FileNotFoundError(f"Presidents CSV not found at {PRESIDENTS_CSV}")

    last_lower = president_last.lower().strip()

    with open(PRESIDENTS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_last = row["president_last"].lower().strip()
            # Handle special cases or direct last name matches
            if row_last == last_lower:
                start = int(row["start_year"])
                end = int(row["end_year"])
                # We do start-1 to end+1 to account for transition edge cases
                # where a president gives an address in early Jan or late Dec
                # outside their exact calendar election term years.
                if (start - 1) <= year <= (end + 1):
                    return {
                        "president_id": row["president_id"],
                        "president_full": row["president_full"],
                        "party": row["party"],
                    }

    raise ValueError(
        f"Could not resolve president for year {year} and name '{president_last}'"
    )
