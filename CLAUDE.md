# sotu

Last verified: 2026-05-21

A Python package that ships the full corpus of U.S. Presidential Annual
Messages (1790-1946) and State of the Union Addresses (1947-present)
with a pandas-DataFrame loader and an NLTK-style file-id interface.
Published on PyPI; source at https://github.com/DH-Oz/sotu.

**All text content originates from the UC Santa Barbara American
Presidency Project** (Peters & Woolley,
https://www.presidency.ucsb.edu/). This is non-negotiable: every doc
surface (README, CHANGELOG, CITATION.cff, package `__doc__`, PyPI
description, commit messages) credits UCSB. Future work must preserve
that attribution.

## Tech stack

- Python 3.10+ (CI matrix: 3.10–3.14)
- `pandas>=2.0,<3.0` (only runtime dep)
- `uv` for env management, lock, and build (`uv build`)
- `hatchling` build backend; package = `src/sotu/`
- `ruff` for lint + format (line length 88), `mypy --strict` for types
- `pytest` + `respx` (HTTP mocking) for tests
- `selectolax`, `httpx`, `tenacity` for the build orchestrator only

## Commands

| Task | Command |
|---|---|
| Install dev env | `uv sync --all-extras` |
| Run tests | `uv run pytest` |
| Lint | `uv run ruff check src tests tools` |
| Format check | `uv run ruff format --check src tests tools` |
| Type check | `uv run mypy src tests tools` |
| Rebuild dataset | `uv run python -m tools.build` |
| Verify deterministic build | `uv run python -m tools.build && git diff --exit-code src/sotu/data/` |
| Build wheel + sdist | `uv build` |
| Twine check before publish | `uv run --with twine twine check dist/*` |

## Project structure

- `src/sotu/` — published package (loader, NLTK accessors, packaged data)
- `src/sotu/data/` — the corpus: `metadata.csv`, `manifest.json`, `presidents.csv`, `speeches/*.txt`. Output of `tools/build.py`; byte-deterministic.
- `tools/` — build orchestrator (discover, fetch, parse, classify, validate). NOT shipped in the wheel.
- `raw/ucsb/` — frozen HTML snapshot of every UCSB document the build parses. Committed verbatim so the corpus can be rebuilt without re-scraping.
- `data/sotu_type_overrides.csv` — per-(year, president) overrides for `sotu_type` classification.
- `tests/` — pytest suite (71 cases). Fixtures in `tests/fixtures/` so the suite runs offline.
- `docs/design-plans/` — design plan + audit history (rounds 3, 4). Read before substantive contract changes.
- `RELEASING.md` — release process; PyPI Trusted Publishing setup.

## The locked contract

The masterclass consumer code is:

```python
df = sotu.load()                              # 5 columns, canonical SOTUs only
spoken = df[df.sotu_type == "spoken"]          # vocabulary is {"spoken","written"}, not "speech"
washington = df[df.president == "Washington"]  # surname only
ids = sotu.fileids()                           # ['1790-Washington-1', ...]; no whitespace
text = sotu.raw('1790-Washington-1')           # plain text
print(sotu.COVERAGE)                           # (1790, 2026)
```

These are non-negotiable contracts; any change that breaks them is a
regression. Specifically:

- Default `load()` returns **exactly** `["year","president","party","sotu_type","text"]` in that order, no nulls.
- `sotu_type` unique values are **exactly** `{"spoken","written"}` — never `"speech"`.
- `president` is the surname only (`"Washington"`, `"Van Buren"` with space allowed in the column but **never** in fileids).
- Every fileid is whitespace-free and splits cleanly under `fid.rsplit("-", 2)` → (4-digit year, alpha name, digit index).
- Eight first-year incoming joint-session "Administration Goals" addresses are excluded at discovery time and must never reappear in `fileids()`: 1981-Reagan-1, 1989-Bush-1, 1993-Clinton-1, 2001-Bush-1, 2009-Obama-1, 2017-Trump-1, 2021-Biden-1, 2025-Trump-1.

The tests in `tests/test_schema.py`, `tests/test_coverage.py`, and `tests/test_public_api.py` enforce these. Don't weaken them — round 3 of the audit caught exactly that anti-pattern (the prior author weakened `test_fileids` with `.replace(" ", "")` to mask a Van Buren bug).

## The is_sotu policy

`metadata()` and `load(include_related=True)` return 249 rows; `load()` defaults to the 237 canonical SOTUs (`is_sotu=True`). Twelve UCSB-tagged documents are flagged `is_sotu=False` because they are not the SOTU itself:

- 1945-Roosevelt-2: radio summary of the 1945 written SOTU.
- 1956-Eisenhower-2: supplemental remarks given at Key West.
- 1973-Nixon-2..11: ten policy-specific Special Messages to Congress (Feb 14 – Mar 14, 1973). Only the Feb 2 overview (pid=3996) is the 1973 SOTU.

Years with multiple canonical rows are legitimate spoken+written pairs (Nixon 1972/74, Carter 1978-80) or president-transition years (1790, 1953, 1961). Don't collapse them.

The policy lives in `tools/classify.is_canonical_sotu`. The Nixon-1973 pid list is hardcoded there; if a future review changes which 1973 documents count, edit that frozenset.

## sotu_type classification

Three-stage resolution (`tools/classify.get_sotu_type`):

1. If the URL slug contains `"delivered"` → `"spoken"` unambiguously.
2. Otherwise consult `data/sotu_type_overrides.csv`. Rows match on `(year, president)` — `president` is the surname; an empty value matches any president that year. This is how transition years carry different types per president (1953 Truman written / Eisenhower spoken; 1961 Eisenhower written / Kennedy spoken).
3. Fall back to year heuristic: 1790-1800 spoken, 1801-1912 written, 1913+ spoken.

After per-row classification, `tools/build.py` post-processes each `(year, president)` group: if any row has `delivered` in its slug, the non-delivered siblings are flipped to `"written"`. This handles Nixon 1972/74 and Carter 1978-80 cleanly without needing 30 override rows.

Do **not** classify by `"annual-message"` substring — UCSB uses "Annual Message to the Congress on the State of the Union" as a generic title for both delivered and written-only modern SOTUs, so the bare `annual-message` slug doesn't disambiguate.

## Build determinism

Two consecutive offline builds against the same `raw/ucsb/` snapshot must produce byte-identical `metadata.csv`, `manifest.json`, and every `speeches/*.txt`. CI's `Build & Validate` workflow enforces this on every push by asserting `git diff --exit-code src/sotu/data/` after rebuild.

Required to keep this true:

- No wall-clock timestamps in `manifest.json` (no `build_date`).
- No hardcoded version strings in `manifest.json` (the package version lives in `pyproject.toml` only).
- `tools/build.py` clears `src/sotu/data/speeches/` at the start of each run so stale files from prior builds can't survive.
- Records are sorted by `(year, president, is_sotu, date, source_url)` before fileid assignment; the manifest is written with `sort_keys=False` but files are inserted in fileid-sorted order.

If you add a new build step that introduces non-determinism (a UUID, a clock read, dict-order iteration without sorting), the determinism CI job will fail loudly.

## CI / release pipeline

Three workflows in `.github/workflows/`:

- `ci.yml` — lint + format + mypy + pytest matrix on Python 3.10–3.14; PR-only step that blocks data-changing PRs without a version bump.
- `build-validate.yml` — rebuilds the dataset and asserts the diff is empty.
- `release.yml` — tag-triggered (`v*`); builds with `uv build`; publishes to PyPI via OIDC Trusted Publishing (environment `pypi`).

The `pypi` GitHub environment is locked to refs matching `v*` (tag policy), so only properly tagged commits can publish.

See `RELEASING.md` for the cut-a-release procedure.

## Gotchas (hit in the wild, leave the rubber marks here)

- **PyPI metadata label length cap**: `[project.urls]` labels are limited to 32 characters by the core-metadata spec (`https://packaging.python.org/specifications/core-metadata/`). `twine check` does not enforce this — it's server-side only. The label `"Source Archive (UCSB)"` is the maximum-credit form that fits.
- **`uv exclude-newer-span` bites smoke tests**: a global uv config sets a rolling cutoff that filters out same-day-published packages. To install `sotu==X.Y.Z` immediately after release: `uv pip install --exclude-newer-package sotu=2026-12-31 sotu==X.Y.Z`. The CLI form is `PACKAGE=DATE`.
- **Van Buren has a space in the surname**: `df["president"]` keeps `"Van Buren"` with the space (the natural form), but the fileid normalises to `"VanBuren"` (no space). Round 3 of the audit caught a previous author trying to paper over this with `.replace(" ", "")` in the test instead of fixing the data.
- **`load(full=True)` includes `fileid`**: this was a round-4 fix. Don't drop it. It's the join key consumers use to round-trip from `raw()` back to a DataFrame row.
- **UCSB sometimes files non-SOTUs under the State of the Union taxonomy**: that's why `is_canonical_sotu` exists. If discovery picks up a new auxiliary document on a future build, mark it `is_sotu=False` there rather than excluding it entirely — scholars want to read it.

## Boundaries

- **Always safe to edit**: `src/sotu/`, `tools/`, `tests/`, `docs/`, `README.md`, `CHANGELOG.md`, `RELEASING.md`.
- **Edit carefully**: `pyproject.toml` (URL labels ≤ 32 chars; classifiers and keywords are part of the public PyPI presentation), `data/sotu_type_overrides.csv` (changes classification of real-world historical records — check sources first).
- **Don't edit directly**: `src/sotu/data/*` — these are build artefacts. Change `tools/` and rebuild.
- **Don't edit at all**: `raw/ucsb/*.html` — these are the frozen UCSB source-of-truth. If UCSB updates a document, fetch it fresh and commit the new HTML in a dedicated commit so the provenance is auditable.

## R `sotu` + quanteda equivalence

This package is designed so users coming from R's
[`sotu`](https://CRAN.R-project.org/package=sotu) + quanteda corpus get
the same affordances via pandas. The mapping (in `README.md`) is the
design contract; preserve it when adding API surface:

| R / quanteda | Python (`sotu`) |
|---|---|
| `sotu_meta` | `sotu.metadata()` |
| `sotu_text` | `sotu.load(full=True)["text"]` |
| `corpus(sotu_text, docvars=sotu_meta)` | `sotu.load(full=True)` |
| `docnames(corp)` | `sotu.fileids()` |
| `corpus_subset(corp, sotu_type == "speech")` | `df[df.sotu_type == "spoken"]` |
| `as.character(corp[i])` | `sotu.raw(fileid)` |

Two intentional differences: `sotu_type` vocabulary is `spoken`/`written` (not R's `speech`/`written`), and `president` is the surname (R uses full name).

## Audit history

Three audit rounds documented in `docs/design-plans/`. Round 4
(2026-05-21) was the last; verdict was MERGE after fixes for orphan
`.txt` files in the wheel, doc drift, non-deterministic manifest, and
the over-broad `_is_real_sotu` filter that was actually correct in
context. Read those before making structural changes to the contract
or the build pipeline — they capture the reasoning behind several
non-obvious decisions.
