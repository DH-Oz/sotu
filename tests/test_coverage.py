import sotu


def test_coverage_bounds() -> None:
    """Assert that the corpus covers the full expected calendar bounds (1790-2026)."""
    assert sotu.COVERAGE == (1790, 2026)

    df = sotu.load()
    years = df["year"].unique()

    assert min(years) == 1790
    assert max(years) == 2026


def test_decade_representation() -> None:
    """Assert that every decade between 1790 and 2020 has SOTU addresses."""
    df = sotu.load()
    years = df["year"].tolist()

    for decade_start in range(1790, 2021, 10):
        decade_years = [y for y in years if decade_start <= y < decade_start + 10]
        assert len(decade_years) > 0, (
            f"No SOTUs found for decade starting {decade_start}"
        )


EXCLUDED_FILEIDS = {
    "1981-Reagan-1",
    "1989-Bush-1",
    "1993-Clinton-1",
    "2001-Bush-1",
    "2009-Obama-1",
    "2017-Trump-1",
    "2021-Biden-1",
    "2025-Trump-1",
}


def test_first_year_joint_sessions_excluded() -> None:
    """Assert that the 8 excluded first-year joint-session addresses
    are not in fileids.
    """
    present = EXCLUDED_FILEIDS & set(sotu.fileids())
    assert not present, f"Excluded addresses leaked into corpus: {present}"


def test_corpus_count_in_expected_range() -> None:
    """Default load() returns one canonical SOTU per (year, president).

    Auxiliary UCSB documents (Nixon's 1973 topical Special Messages, the
    1945 Roosevelt radio summary, the 1956 Eisenhower Key West remarks)
    are filtered out by default — they remain in metadata() with
    is_sotu=False and surface via load(include_related=True). The
    canonical count is ~237 through 2026; we allow [230, 260] to leave
    room for future single-year additions.
    """
    assert 230 <= len(sotu.load()) <= 260


def test_load_includes_related_count_matches_metadata() -> None:
    """include_related=True returns every metadata row."""
    full_archive = sotu.load(include_related=True)
    assert len(full_archive) == len(sotu.metadata())
    assert len(full_archive) >= len(sotu.load())


def test_is_sotu_partitions_corpus() -> None:
    """The is_sotu flag cleanly partitions canonical SOTUs from auxiliaries."""
    meta = sotu.metadata()
    assert meta["is_sotu"].dtype == bool
    canonical = meta[meta["is_sotu"]]
    related = meta[~meta["is_sotu"]]
    # Sanity: at least one auxiliary exists (this audit caught 12).
    assert len(related) >= 1
    # No (year, president) appears as canonical more than the natural max
    # for that pair. The masterclass contract is "one canonical per year
    # per president", so a (year, president) group can hold at most as
    # many canonical rows as the natural count (Washington had 2 in 1790).
    assert canonical.groupby(["year", "president"]).size().max() <= 2


def test_no_administration_goals_urls() -> None:
    """Assert that no 'administration-goals' addresses exist in metadata."""
    meta = sotu.metadata()
    bad = meta[meta["source_url"].str.contains("administration-goals", na=False)]
    bad_list = bad["fileid"].tolist()
    assert bad.empty, f"administration-goals addresses present: {bad_list}"
