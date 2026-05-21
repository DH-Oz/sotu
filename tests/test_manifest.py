import json
import pathlib

import sotu


def _manifest_path() -> pathlib.Path:
    return pathlib.Path(sotu.__file__).parent / "data" / "manifest.json"


def test_manifest_has_no_wall_clock_fields() -> None:
    """Build determinism: manifest contains no timestamps or version strings."""
    manifest = json.loads(_manifest_path().read_text(encoding="utf-8"))
    assert "build_date" not in manifest
    assert "package_version" not in manifest


def test_manifest_files_cover_every_fileid() -> None:
    """Every shipped fileid has a manifest entry, and vice versa."""
    manifest = json.loads(_manifest_path().read_text(encoding="utf-8"))
    manifest_ids = set(manifest["files"].keys())
    assert manifest_ids == set(sotu.fileids())


def test_manifest_entries_have_expected_hash_keys() -> None:
    """Each manifest entry exposes parsed_text_sha256, raw_html_sha256, word_count."""
    manifest = json.loads(_manifest_path().read_text(encoding="utf-8"))
    for fid, entry in manifest["files"].items():
        assert "parsed_text_sha256" in entry, fid
        assert "raw_html_sha256" in entry, fid
        assert "word_count" in entry, fid


def test_manifest_coverage_matches_runtime() -> None:
    """The manifest's coverage tuple agrees with sotu.COVERAGE."""
    manifest = json.loads(_manifest_path().read_text(encoding="utf-8"))
    assert tuple(manifest["coverage"]) == sotu.COVERAGE
