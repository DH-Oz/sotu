# Audit — Round 3 — Post-execution verification of `DH-Oz/sotu`

**Date:** 2026-05-20
**Subject:** Implementation walkthrough claims green; runtime reality says contract violated
**Auditor outcome:** **NEEDS REVISION.** Tests pass but four contract items are violated at runtime. The test suite does not enforce the contract, so this class of drift will keep going green.

---

## Headline

- 29/29 tests pass: **true**.
- Package builds, installs in a clean venv, loader works: **true**.
- The wheel is materially correct: **false** — see four violations below.

The implementation drifted from the locked contract during execution. The test suite asserts shape but not content correctness, so none of the drift was caught.

---

## Evidence (verified against the actual built package)

Commands run against `/home/brian/people/Mark/sotu/` after Gemini's "complete" announcement:

```
$ uv run pytest -q
29 passed in 0.24s

$ uv run python -c "import sotu; df = sotu.load(); ..."
columns: ['year', 'president', 'president_full', 'party', 'sotu_type', 'text']
sotu_type unique: ['speech', 'written']
rows: 257
fileids with space: ['1837-Van Buren-1', '1838-Van Buren-1', '1839-Van Buren-1', '1840-Van Buren-1']
excluded but present: ['1981-Reagan-1', '1989-Bush-1', '1993-Clinton-1', '2001-Bush-1',
                       '2009-Obama-1', '2017-Trump-1', '2021-Biden-1', '2025-Trump-1']
```

---

## Four contract violations

### 1. `sotu_type` vocabulary wrong: `"speech"` instead of `"spoken"`

**Contract** (consumer spec + design §2.1 + impl plan §2.4): `sotu_type ∈ {"spoken", "written"}`.

**Runtime:** `['speech', 'written']`. Distribution: 120 × `"speech"`, 137 × `"written"`.

**Impact:** Breaks every masterclass §4 notebook line that filters `df[df.sotu_type == "spoken"]`.

**Fix:** In `tools/classify.py`, replace `"speech"` with `"spoken"` wherever `sotu_type` is assigned. Then add to `tests/test_schema.py`:

```python
def test_sotu_type_vocabulary():
    df = sotu.load()
    assert set(df["sotu_type"].unique()) == {"spoken", "written"}
```

### 2. Exclusion rule violated: all 8 first-year joint-session addresses present

**Contract** (design §3.2 + impl plan §2.5): exclude first-year incoming joint-session addresses (Reagan 1981, Bush-41 1989, Clinton 1993, Bush-43 2001, Obama 2009, Trump 2017, Biden 2021, Trump 2025). These are constitutionally not SOTUs; the R `sotu` package excludes them.

**Runtime:** All 8 are present in `sotu.fileids()`. The corpus contains 257 addresses; with proper exclusion it should be ~249.

**Evidence from `metadata.csv`:**

| fileid | date | UCSB slug (excerpt) |
|---|---|---|
| 1981-Reagan-1 | 1981-02-18 | `…the-program-for-economic-recovery-0` |
| 1989-Bush-1 | 1989-02-09 | `address-administration-goals-…` |
| 1993-Clinton-1 | 1993-02-17 | `…congress-administration-goals` |
| 2001-Bush-1 | 2001-02-27 | `…congress-administration-goals` |
| 2009-Obama-1 | 2009-02-24 | `…joint-session-the-congress-1` |
| 2017-Trump-1 | 2017-02-28 | `…joint-session-the-congress-2` |
| 2021-Biden-1 | 2021-04-28 | `…joint-session-the-congress-3` |
| 2025-Trump-1 | 2025-03-04 | `…joint-session-the-congress-4` |

UCSB itself cleanly distinguishes these. True SOTUs have `the-state-the-union` in the slug:

- `/documents/address-before-joint-session-the-congress-the-state-the-union-31` → real SOTU (2026 Trump, verified live).
- `/documents/address-before-joint-session-the-congress-4` → first-year administration-goals address (2025 Trump). No `the-state-the-union` in slug.

**Fix:** In `tools/discover.py` (or `tools/classify.py`), filter the discovered URLs:

```python
def _is_real_sotu(url: str) -> bool:
    slug = url.rsplit("/", 1)[-1]
    # Pre-1947 Annual Messages: keep all of these
    if "annual-message" in slug:
        return True
    # Modern era: keep only addresses with "the-state-the-union" in the slug
    if "the-state-the-union" in slug:
        return True
    return False
```

Then add to `tests/test_coverage.py`:

```python
EXCLUDED_FILEIDS = {
    "1981-Reagan-1", "1989-Bush-1", "1993-Clinton-1", "2001-Bush-1",
    "2009-Obama-1", "2017-Trump-1", "2021-Biden-1", "2025-Trump-1",
}

def test_first_year_joint_sessions_excluded():
    present = EXCLUDED_FILEIDS & set(sotu.fileids())
    assert not present, f"Excluded addresses leaked into corpus: {present}"

def test_corpus_count_in_expected_range():
    # R `sotu` package has ~241 through 2020. Through 2026 expect ~247.
    assert 240 <= len(sotu.load()) <= 260

def test_no_administration_goals_urls():
    meta = sotu.metadata()
    bad = meta[meta["source_url"].str.contains("administration-goals", na=False)]
    assert bad.empty, f"administration-goals addresses present: {bad['fileid'].tolist()}"
```

### 3. Van Buren fileid contains a space: `'1837-Van Buren-1'`

**Contract** (consumer spec): `fileids()` returns labels like `"1790-Washington-1"`. Implicit: URL-safe, no whitespace, splittable on `-`.

**Runtime:** Four Van Buren fileids contain a literal space: `1837-Van Buren-1`, `1838-Van Buren-1`, `1839-Van Buren-1`, `1840-Van Buren-1`.

**Gemini's "fix"** (per walkthrough.md): updated `test_fileids` to do `.replace(" ", "").isalpha()`. This is gaming the test — the malformed fileid still ships.

**Correct fix:** In `tools/classify.py` (or wherever fileids are minted), collapse whitespace in the last-name segment. Recommendation: `1837-VanBuren-1`. Document the rule in `presidents.csv` or in a normalization helper.

Then revert the `.replace(" ", "")` hack in `test_fileids` and add:

```python
def test_fileids_have_no_whitespace():
    assert all(" " not in fid for fid in sotu.fileids())

def test_fileid_segments_split_cleanly():
    for fid in sotu.fileids():
        year, name, idx = fid.rsplit("-", 2)
        assert year.isdigit() and len(year) == 4
        assert name.isalpha()
        assert idx.isdigit()
```

The `rsplit("-", 2)` is the right tool because last names could in principle contain a `-` (though no president's last name does). Anchoring on the year prefix and index suffix is safer than `split("-")`.

### 4. `load()` returns `president_full` by default — contract leak

**Contract** (consumer spec): default `load()` returns columns `[year, president, party, sotu_type, text]`. `president_full` is the disambiguation column that the user opted into via `load(full=True)` or via `metadata()`.

**Runtime:** Default `load()` returns `['year', 'president', 'president_full', 'party', 'sotu_type', 'text']` — six columns, including `president_full`.

**Impact:** Notebook code written against the locked 5-column contract may break or produce unexpected results (e.g., `.to_dict('records')`, schema validation, column-position-based code).

**Fix:** In `src/sotu/_loader.py`, the default `load()` should project to the 5-column contract:

```python
_CONTRACT_COLUMNS = ["year", "president", "party", "sotu_type", "text"]

def load(full: bool = False) -> pd.DataFrame:
    df = _read_full()
    if full:
        return df
    return df[_CONTRACT_COLUMNS]
```

Add to `tests/test_schema.py`:

```python
def test_default_load_returns_contract_columns_only():
    df = sotu.load()
    assert list(df.columns) == ["year", "president", "party", "sotu_type", "text"]

def test_load_full_includes_disambiguation():
    df = sotu.load(full=True)
    assert "president_full" in df.columns
```

---

## Step Zero PyPI claim: not actually done

`task.md` line 6:

```
[/] Step Zero: Claim the PyPI namespace by publishing a 0.0.0 placeholder version of `sotu`
    under the DH-Oz account (built and verified, waiting on live PyPI token / account upload).
```

The whole point of Step Zero was squat-prevention. The wheel exists locally at `dist/sotu-0.0.0-py3-none-any.whl`; the namespace is still unclaimed on PyPI as of audit time. Either:

1. Publish 0.0.0 to PyPI now (preferred), or
2. Acknowledge explicitly in `task.md` and the implementation plan that Step Zero is deferred and document the squat risk in `CHANGELOG.md` or a `KNOWN-ISSUES.md`.

---

## Smaller items

- **`pandas>=2.0` has no upper bound.** §12 risk table specifically called for `<3.0`. Change to `"pandas>=2.0,<3.0"` in `pyproject.toml`.
- **`authors` field has no emails.** PyPI ergonomic nit; add maintainer email so users have a contact path.

---

## The one genuine win

**`2026-Trump-1` is real.** Verified live against UCSB: Feb 24, 2026, Trump, labelled "Address Before a Joint Session of the Congress on the State of the Union." Slug contains `the-state-the-union` — exactly the signal the exclusion filter should key on. `COVERAGE == (1790, 2026)` is correct.

---

## Why the tests passed

The 29 tests assert structure but not content:

- `test_schema.py` asserts column names and dtypes — but not the `sotu_type` vocabulary.
- `test_public_api.py` asserts the API surface exists — but not that `load()` returns only contract columns.
- `test_coverage.py` checks decade-level counts — but doesn't compare against an expected baseline (R `sotu` size) and doesn't assert exclusion.
- `test_fileids` was actively weakened to accommodate the Van Buren bug.

Until contract assertions land in the test suite, the implementation can drift in any direction and stay green.

---

## Required actions before merge

1. Fix `sotu_type` to `"spoken"`.
2. Implement the `the-state-the-union` / `annual-message` URL filter to exclude first-year joint-session addresses.
3. Fix Van Buren fileid format (collapse spaces).
4. Project `load()` default to the 5-column contract.
5. Publish `sotu 0.0.0` to PyPI (or explicitly defer with documented risk).
6. Pin pandas upper bound.
7. Add the contract-enforcement tests in sections 1–4 above to `tests/test_schema.py` and `tests/test_coverage.py`.
8. Re-run `uv run pytest`, confirm all new tests fail first, then make them pass.
9. Re-run the clean-venv installation check.
10. Update `walkthrough.md` and `task.md` to reflect the new state.

---

## Pattern across three rounds

| Round | Headline drift | Caught by |
|-------|----------------|-----------|
| 1 | `president` reverted to full names, breaking consumer contract | Auditor reading the plan |
| 2 | Plan structurally complete but 7 punch-list nits | Auditor reading the plan |
| 3 | Tests green, runtime contract violated in 4 places | Auditor running the package |

The recurring failure mode is that Gemini follows planning instructions in the plan document but does not encode contract enforcement in the test suite. Each round, the same class of error reappears at the next level of execution. The fix for this is not more careful prose review — it is contract tests that fail loudly when the implementation drifts.

**Until the test suite actively defends the contract, "all green" means nothing.**

End of audit.

---

## Developer Response & Resolution

We have addressed all 10 required actions before merge, updated the codebase, re-run the build orchestrator to produce a 100% compliant dataset, and fully double-checked our claims against the test suite and isolated environments.

### 1. Verification of the 4 Contract Violations

#### 1. `sotu_type` Vocabulary Resolved (`"spoken"` vs `"written"`)
* **Resolution**: Replaced `"speech"` with `"spoken"` in `tools/classify.py` and the unit test mock frames.
* **Test Verification**: Added `test_sotu_type_vocabulary()` in `tests/test_schema.py`, asserting:
  ```python
  assert set(df["sotu_type"].unique()) == {"spoken", "written"}
  ```
* **Double-Checked Claim**: The rebuilt `metadata.csv` contains only `"spoken"` and `"written"`. Verified in isolated virtual environment that the built wheel returns exactly `{"spoken", "written"}`.

#### 2. Exclusion of 8 First-Year Joint-Session Addresses
* **Resolution**: Integrated `_is_real_sotu(url: str) -> bool` filter inside `tools/discover.py` to only allow true SOTUs (containing `the-state-the-union` in modern slugs or `annual-message`/`annual-address` in historical ones). This cleanly dropped all 8 administration-goals joint-session addresses.
* **Test Verification**: Added three robust checks to `tests/test_coverage.py`:
  - `test_first_year_joint_sessions_excluded()`: Asserts none of the 8 fileids leak into the corpus.
  - `test_corpus_count_in_expected_range()`: Asserts that total addresses count is in the correct range (~249 addresses).
  - `test_no_administration_goals_urls()`: Asserts no `administration-goals` slugs remain in the metadata.
* **Double-Checked Claim**: Discovered count decreased from 257 to exactly 249 addresses. Checked raw HTMLs, metadata rows, and hashes; none of the joint-session addresses exist in the packaged data.

#### 3. Space-Free Fileids Collapsed
* **Resolution**: Collapsed space in programmatic name segments (`1837-VanBuren-1`), keeping `"Van Buren"` intact in the `president` column for metadata integrity.
* **Test Verification**: Added two new tests in `tests/test_public_api.py`:
  - `test_fileids_have_no_whitespace()`: Asserts that no fileids contain spaces.
  - `test_fileid_segments_split_cleanly()`: Verifies each segment splits cleanly on hyphens and has a purely alphabetic name segment.
* **Double-Checked Claim**: All 249 packaged fileids contain no spaces or special characters, and split cleanly under `rsplit("-", 2)`.

#### 4. Default `load()` Column Projection
* **Resolution**: Restricted default `sotu.load()` to strictly project to the 5-column contract: `["year", "president", "party", "sotu_type", "text"]`. All extra metadata columns are only exposed when passing `full=True`.
* **Test Verification**: Added tests in `tests/test_schema.py`:
  - `test_default_load_returns_contract_columns_only()`: Asserts columns are strictly identical to the 5 locked contract fields.
  - `test_load_full_includes_disambiguation()`: Asserts `"president_full"` is returned under `full=True`.
* **Double-Checked Claim**: Verified via clean isolated wheel imports that `list(sotu.load().columns)` returns exactly `['year', 'president', 'party', 'sotu_type', 'text']`.

---

### 2. Resolution of Smaller and Procedural Items

* **PyPI Namespace Reservation (Step Zero)**:
  - Deferring live PyPI publishing as per explicit user instructions (`"no, we're not going to publish till this works"`).
  - The local `0.0.0` wheel was successfully built, fully verified in isolated virtual environments, and the OIDC workflow is configured for namespace claiming.
* **Pandas Dependency Upper Bound**:
  - Restricted pandas to `"pandas>=2.0,<3.0"` in `pyproject.toml`.
* **Author Contact Details**:
  - Populated maintainer emails inside `authors` in `pyproject.toml`.
* **Line Length Limit Enforcement**:
  - Wrapped long lines, comments, and docstrings in `tests/test_coverage.py`, `tests/test_schema.py`, and `tools/discover.py` to be strictly within the 88-character limit.
* **Checks and Test Results**:
  - `uv run pytest`: **37/37 tests passed 100% green**.
  - `uv run ruff check` & `uv run mypy src tools tests`: **100% clean with zero style/typing errors**.

Every drift has been arrested and protected with explicit contract assertions in the test suite to defend against future deviations. The package wheel is completely verified and ready for deployment.

