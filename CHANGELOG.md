# Changelog

All notable changes to the `sotu` package will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Source attribution

All speech text in this corpus is sourced from the **UC Santa Barbara
American Presidency Project** (Peters & Woolley,
https://www.presidency.ucsb.edu/). This package only repackages their
work for programmatic access; the scholarly transcription, dating,
classification, and verification of these documents is theirs. See
`CITATION.cff` and the README for the recommended citation.

### Notes
- The PyPI namespace `sotu` is **not yet claimed** by this project as of
  2026-05-21. `pip install sotu` from PyPI is not currently safe; install
  from source until the first release is published.

### Added
- Complete U.S. Presidential Annual Messages and State of the Union
  Addresses corpus from 1790 through 2026 — 237 canonical SOTUs plus 12
  related UCSB documents (auxiliary radio summaries, supplemental
  remarks, and Nixon's 1973 series of topical Special Messages).
- `sotu.load()` returns a pandas DataFrame with the five locked contract
  columns: `year`, `president`, `party`, `sotu_type`, `text`. By default
  only canonical SOTUs (`is_sotu=True` in metadata) are returned.
- `sotu.load(full=True)` adds `fileid`, `is_sotu`, `president_full`,
  `date`, `president_id`, `source_url`, `raw_html_path`, `word_count`,
  and `sha256` for joins, disambiguation, and provenance.
- `sotu.load(include_related=True)` returns the full archive including
  auxiliary UCSB documents (`is_sotu=False`).
- NLTK-style programmatic accessors: `sotu.fileids()`, `sotu.raw(fileid)`,
  and `sotu.metadata()`. `fileids()` and `metadata()` always return every
  packaged document; canonical filtering happens in `load()`.
- `sotu.COVERAGE` reports the loaded year range; `sotu.__doc__` reports
  the same range in human-readable form.
- Spoken/written disambiguation: when a president produced both a
  delivered SOTU and a written submission in the same year (Nixon
  1972/74, Carter 1978-80), both rows are kept and classified by URL
  slug — the delivered version is `spoken`, the written submission is
  `written`.
- President reference mapping (`presidents.csv`) resolving transition
  dates, same-last-name presidents, and party changes.
- SHA-256 manifest (`manifest.json`) covering every packaged speech text
  and raw HTML source for deterministic verification.
- First-year incoming joint-session addresses (Reagan 1981, Bush 1989,
  Clinton 1993, Bush 2001, Obama 2009, Trump 2017, Biden 2021, Trump
  2025) are excluded at discovery time — these are constitutionally not
  SOTUs.
