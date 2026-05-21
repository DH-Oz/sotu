import pathlib

import sotu


def test_roundtrip_text_equivalence() -> None:
    """For every fileid, raw(fid) equals the matching row's text in the full archive."""
    df_full = sotu.load(full=True, include_related=True)
    fileids = sotu.fileids()

    assert len(df_full) == len(fileids)
    by_fileid = df_full.set_index("fileid")

    for fid in fileids:
        df_text = by_fileid.loc[fid, "text"]
        assert sotu.raw(fid) == df_text
        year_str, _name, _seq = fid.rsplit("-", 2)
        assert int(year_str) == by_fileid.loc[fid, "year"]


def test_data_dir_matches_fileids() -> None:
    """No .txt orphans on disk, no missing files. The package ships exactly fileids()."""
    data_dir = pathlib.Path(sotu.__file__).parent / "data" / "speeches"
    on_disk = {p.stem for p in data_dir.glob("*.txt")}
    expected = set(sotu.fileids())

    orphans = on_disk - expected
    missing = expected - on_disk

    assert not orphans, f"Orphan .txt files in data dir: {sorted(orphans)}"
    assert not missing, f"Missing .txt files for fileids: {sorted(missing)}"


def test_load_full_has_fileid_column_for_round_trip() -> None:
    """load(full=True) must expose fileid so consumers can join raw() and the DataFrame."""
    df_full = sotu.load(full=True)
    assert "fileid" in df_full.columns

    sample = sotu.fileids()[0]
    row_text = df_full.loc[df_full["fileid"] == sample, "text"].iloc[0]
    assert row_text == sotu.raw(sample)
