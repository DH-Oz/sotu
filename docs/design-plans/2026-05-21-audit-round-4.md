# Round-4 Audit Findings — `DH-Oz/sotu`

**Date:** 2026-05-21
**Auditor:** Claude (Opus 4.7, critical-peer-review protocol)
**Artifact type:** technical-reasoning (author's "Developer Response & Resolution" claim in `2026-05-20-audit-round-3.md`)
**Working tree:** `/home/brian/people/Mark/sotu/` (zero git commits)

---

## Summary

**Verdict: NEEDS REVISION.** The four contract violations flagged in round 3 are genuinely fixed in the loader/test surface — the `sotu_type` vocabulary is `{"spoken", "written"}`, the eight first-year joint-session fileids are absent, Van Buren fileids are space-free (`1837-VanBuren-1`), default `load()` projects to the five-column contract, and the new tests assert these conditions with strict equality rather than `.replace(" ", "")` gaming. So the headline drift is arrested.

However, the package is **not** ready for deployment. **Seven non-trivial issues remain**, including one High-severity data-layer leak that the new test suite cannot detect, two High-severity contract documentation drifts that will mislead the masterclass author, a determinism failure baked into the build orchestrator, a structurally impossible determinism check (no git commits exist at all), missing procedural deliverables that the author claimed were updated, and one round-3-style "broader filter than asked for" pattern that survives only because no leaked URL happens to trip it. Count: **3 High, 3 Medium, 2 Low.**

---

## Step 1 — pytest output

```
============================== 37 passed in 0.34s ==============================
```

All 37 tests green. **But passing tests are not sufficient** — round 3's lesson stands. The new contract assertions DO defend their stated contracts (verified by reading the assertions, not running them), but the test suite still does not cover the disk-layer artefacts found below.

---

## Step 2 — Runtime contract check (against 10 hard requirements)

| # | Requirement | Status | Observed |
|---|---|---|---|
| 1 | `load()` cols = `["year","president","party","sotu_type","text"]` exactly, no nulls | **PASS** | `['year','president','party','sotu_type','text']`; 0 nulls per column |
| 2 | `sotu_type.unique()` == `{"spoken","written"}` | **PASS** | `['spoken','written']` |
| 3 | `president` last-name only; `"Van Buren"` allowed in column iff fileid has no spaces | **PASS** | `president` shows `"Van Buren"` (with space); fileids show `"VanBuren"` (no space) |
| 4 | `fileids()` no whitespace; each splits cleanly on `rsplit("-",2)` | **PASS** | No whitespace; first/last five split cleanly |
| 5 | `load(full=True)` includes `president_full` plus all other metadata cols | **PARTIAL** | Includes `president_full`, `source_url`, `word_count`, `sha256`, `raw_html_path`, `date`, `president_id`. **`fileid` deliberately dropped** by `_loader.py:47`. See H2. |
| 6 | `metadata()` returns full schema | **PASS** | 12 columns including `fileid`, `date`, `sha256`, etc. |
| 7 | Eight excluded fileids absent from `fileids()` | **PASS at API surface; FAIL on disk** | 0 of 8 in `fileids()`. **All 8 `.txt` files still ship in the wheel.** See H1. |
| 8 | `240 ≤ len(sotu.load()) ≤ 260` | **PASS** | 249 |
| 9 | `COVERAGE == (1790, 2026)` | **PASS** | `(1790, 2026)` at runtime (fallback constant in `__init__.py:10` is stale at `(1790, 2025)` but is overwritten dynamically by metadata) |
| 10 | `raw(fid)` round-trips with `load(full=True)` row | **FAIL** | `load(full=True)` has no `fileid` column; smoke test reports "cannot round-trip without fileid mapping". See H2. |

---

## Step 3 — Round-3 test-assertion strength

Each round-3 violation has a new, **substantive** assertion. None of them is gamed.

| Round-3 defect | New test | Asserts | Verdict |
|---|---|---|---|
| `sotu_type = "speech"` | `tests/test_schema.py:38-41 test_sotu_type_vocabulary` | `set(...) == {"spoken","written"}` (strict equality) | **STRONG** — would catch any drift back to `"speech"` |
| 8 excluded fileids present | `tests/test_coverage.py:35-40 test_first_year_joint_sessions_excluded` | `EXCLUDED_FILEIDS & set(sotu.fileids()) == ∅` | **STRONG** — names each of the 8 by ID |
| Van Buren spaces | `tests/test_public_api.py:62-64,67-73` plus `test_fileids` at `:48-59` (`parts[1].isalpha()` — also fails on a space) | three independent checks | **STRONG** — round-3's `.replace(" ","")` hack is gone |
| `president_full` leaked into default | `tests/test_schema.py:44-47 test_default_load_returns_contract_columns_only` | `list(df.columns) == [...]` (positional, strict) | **STRONG** — positional list equality, not subset |

The author's "double-checked claim" prose in the round-3 response is, for these four items, accurate.

---

## Step 4 — Smaller items

| Item | Status | Evidence |
|---|---|---|
| `pandas>=2.0,<3.0` upper bound | **PASS** | `pyproject.toml:26` |
| Authors include emails | **PASS** | `pyproject.toml:12-15` — both authors have email addresses |
| `task.md` and `walkthrough.md` document Step Zero deferral and squat risk | **FAIL** | **Neither file exists anywhere in the repository.** `find` for `task*.md` and `walkthrough*.md` returns nothing. The round-3 audit cited specific lines in both files; the round-3 response references them implicitly. They have been deleted or never re-created. The squat-risk acknowledgement is also absent from `CHANGELOG.md` and `README.md`. See M1. |

---

## Step 5 — New checks (not in round 3)

| Check | Result |
|---|---|
| `party` unique values | `['Democratic','Democratic-Republican','Federalist','National Union','Nonpartisan','Republican','Whig']` |
| Washington party | `Nonpartisan` — disagrees with the round-4 audit prompt's expectation of `Federalist`, but **agrees with the documented design**: `README.md:77` and `_loader.py` intentionally follow the R `sotu` CRAN package which labels Washington as `Nonpartisan`. The audit prompt's expectation is the one that is wrong here. (L1) |
| Jefferson | `Democratic-Republican` ✓ |
| Lincoln | `Republican` ✓ |
| FDR (1934-1945) | `Democratic` ✓ |
| TR (1901-1908) | `Republican` ✓ |
| John Adams (1797-1800) | `Federalist` ✓ |
| J.Q. Adams (1825-1828) | `Democratic-Republican` ✓ |
| Every fileid has a `.txt` file | **PASS** — 0 missing |
| Every `.txt` equals `raw(fid)` | **PASS** — 0 mismatches |
| No empty `raw()` returns | **PASS** |
| **Extra `.txt` files NOT in fileids** | **FAIL — 12 orphan files on disk and in the built wheel.** Four pre-normalisation Van Buren files with spaces (`1837-Van Buren-1.txt` through `1840-Van Buren-1.txt`) and all eight excluded joint-session files (`1981-Reagan-1.txt` through `2025-Trump-1.txt`). Confirmed present in `dist/sotu-0.0.0-py3-none-any.whl` via `unzip -l`. See **H1**. |
| `sotu.__doc__` mentions coverage range | **PASS** — "Coverage: 1790 through 2026." (dynamic, from metadata) |
| Build determinism — `git diff src/sotu/data/` empty after rebuild | **STRUCTURALLY FAIL** — `git log` returns "your current branch 'main' does not have any commits yet". No baseline exists. Beyond that, `tools/build.py:245` writes `"build_date": datetime.datetime.utcnow().isoformat() + "Z"` into `manifest.json` — non-deterministic by construction. See **H3**. |
| `metadata()` has `fileid` column | **PASS** — `meta.columns` includes `fileid`; `set(meta.fileid) == set(sotu.fileids())` |

---

## Step 6 — Drift inspection via git log

`git log --all -p --since="2026-05-19"` returns empty: this repository has **zero commits**. The branch is named `main` but `git rev-parse HEAD` fails with "unknown revision". Every file is untracked (`git status` shows `??` for everything: `CHANGELOG.md`, `LICENSE`, `README.md`, `data/`, `docs/`, `pyproject.toml`, `raw/`, `src/`, `tests/`, `tools/`, `uv.lock`).

**Consequence:** there is no audit trail. We cannot tell what was changed between round 3 and round 4, what the original test assertions looked like before the new ones were added, or whether the eight excluded fileids were ever removed from disk after being filtered from the loader. The repo is, from a provenance standpoint, a single uncommitted working tree. This is a finding in its own right. See **M2**.

---

## Findings

### High (3)

#### H1 — 12 orphan `.txt` files ship in the wheel, bypassing every API-layer contract test

**Type:** omission / data-layer leak
**Scope:** in-window confirmed (verified at audit time)
**Evidence grade:** demonstrated (both borders shown)
**Pattern level:** local-to-data-layer but symptomatic of a broader pattern (see "Editing pass" note below)

**Evidence:**
- `ls src/sotu/data/speeches/` lists 261 files; `sotu.fileids()` returns 249. The 12-file delta:
  - `1837-Van Buren-1.txt`, `1838-Van Buren-1.txt`, `1839-Van Buren-1.txt`, `1840-Van Buren-1.txt` (with spaces, pre-normalisation)
  - `1981-Reagan-1.txt`, `1989-Bush-1.txt`, `1993-Clinton-1.txt`, `2001-Bush-1.txt`, `2009-Obama-1.txt`, `2017-Trump-1.txt`, `2021-Biden-1.txt`, `2025-Trump-1.txt` (all 8 excluded joint-session addresses)
- `unzip -l dist/sotu-0.0.0-py3-none-any.whl | grep -E "Van Buren|1981-Reagan-1\.|..."` — all 12 are inside the wheel.

**Why this matters:**
1. The author's response says "Checked raw HTMLs, metadata rows, and hashes; none of the joint-session addresses exist in the packaged data." This is false at the disk layer. The author appears to have fixed the loader/metadata filter without cleaning up the data directory; the bad files persist as orphans.
2. The bad Van Buren files retain spaces, which is exactly the round-3 defect at the file-naming level. A downstream user inspecting `Path(sotu.__file__).parent / "data" / "speeches"` will see filenames with literal spaces.
3. The new test suite cannot detect this: every contract test queries `sotu.fileids()` or `sotu.metadata()`, which filter via the loader. No test ever walks the data directory.
4. Wheel bloat: at ~500 KB of orphan text, the dist is materially heavier than it should be.
5. **Determinism risk:** when this gets cleaned up, the manifest hashes won't change (the 12 orphans aren't in the manifest), but a downstream user comparing `data/speeches/*` byte-for-byte against a future fresh build will see a 12-file delta.

**Corrected behaviour:** Either (a) delete the 12 orphan `.txt` files from `src/sotu/data/speeches/` and rebuild the wheel, or (b) have `tools/build.py` rebuild the speeches directory destructively (e.g. clear and re-populate) so leftovers can't survive a re-run. Option (b) is more durable.

**New test required:**
```python
def test_data_dir_matches_fileids():
    import pathlib, sotu
    data_dir = pathlib.Path(sotu.__file__).parent / "data" / "speeches"
    on_disk = {p.stem for p in data_dir.glob("*.txt")}
    assert on_disk == set(sotu.fileids()), (
        f"Orphan files: {on_disk - set(sotu.fileids())}; "
        f"missing files: {set(sotu.fileids()) - on_disk}"
    )
```
This single test would have caught the entire defect class.

**Locations:**
- `src/sotu/data/speeches/1837-Van Buren-1.txt` through `1840-Van Buren-1.txt`
- `src/sotu/data/speeches/{1981-Reagan-1, 1989-Bush-1, 1993-Clinton-1, 2001-Bush-1, 2009-Obama-1, 2017-Trump-1, 2021-Biden-1, 2025-Trump-1}.txt`
- `dist/sotu-0.0.0-py3-none-any.whl` (rebuild required after deletion)

---

#### H2 — `README.md` and `CHANGELOG.md` document an *out-of-date contract* that the test suite now rejects

**Type:** documentation drift / consumer-facing contradiction
**Scope:** in-window confirmed
**Evidence grade:** demonstrated
**Pattern level:** pattern-level — three separate consumer-facing claims are stale

**Evidence:**
- `README.md:5`: "from **1790 through 2025**" — actual coverage is 1790–2026
- `README.md:29`: `# Columns: ['year', 'president', 'president_full', 'party', 'sotu_type', 'text']` — this is the **six**-column shape the round-3 audit rejected. The locked contract is now five columns: no `president_full`. The test `test_default_load_returns_contract_columns_only` would fail against the README's documented shape.
- `README.md:33`: `print(sotu.COVERAGE)  # (1790, 2025)` — actual is `(1790, 2026)`
- `CHANGELOG.md:8-12`: "`[0.1.0] - 2026-05-20`" with "core columns: `year`, `president`, `president_full`, `party`, `sotu_type`, `text`" — same stale six-column claim.

The audit prompt explicitly says: "Round 1: the `president` column was reverted to full names — broke the consumer contract." The README still recommends the broken consumer contract. This is the round-1 defect re-surfacing in the docs even though the runtime is correct.

**Why this matters:**
The masterclass author will copy-paste from the README. Their notebook will then run `df.president_full` on the default load and get `AttributeError: 'DataFrame' object has no attribute 'president_full'`. The exact failure round 1 was supposed to prevent.

**Also affected (ripple):** `CHANGELOG.md:11` says "through 2025" — must be 2026.

**Corrected behaviour:**
- `README.md:5`: "1790 through 2026"
- `README.md:29`: `# Columns: ['year', 'president', 'party', 'sotu_type', 'text']`
- `README.md:33`: `# (1790, 2026)`
- `README.md`: add a short example showing `df_full = sotu.load(full=True)` if `president_full` is wanted, since the default no longer includes it
- `CHANGELOG.md:8-12`: same coverage and column updates; note breaking-change semantics if any 0.0.x → 0.1.0 consumer existed

**Also affecting Requirement 10 (round-trip):**
- `_loader.py:47` deliberately drops `fileid` from `load(full=True)` (`col != "fileid"`). Hard requirement 10 says the round-trip should work with `df[df.fileid == fileid]["text"]` "if `fileid` is exposed there." It is not. Either: (a) restore `fileid` to `load(full=True)` (preferred — it is informational and matches the metadata schema), or (b) document explicitly that round-trip joins must go through `sotu.metadata()` rather than `sotu.load(full=True)`.

**Locations:**
- `README.md:5,29,33`
- `CHANGELOG.md:8,11,12`
- `src/sotu/_loader.py:47` (drop the `col != "fileid"` clause)

---

#### H3 — Build is non-deterministic by construction; "byte-identical rebuild" claim is false

**Type:** overclaim / verification gap / impossible DoD criterion
**Scope:** in-window confirmed (code inspection)
**Evidence grade:** demonstrated
**Pattern level:** local-only (but the misalignment with the design DoD #11 is structural)

**Evidence:**
- `tools/build.py:244-245`:
  ```python
  manifest_data: dict[str, Any] = {
      "build_date": datetime.datetime.utcnow().isoformat() + "Z",
  ```
  Every rebuild writes a different ISO-8601 timestamp into `manifest.json`. Byte-identity is impossible.
- `src/sotu/data/manifest.json:2`: `"build_date": "2026-05-20T09:25:39.034517Z"` — frozen at last build. A re-run today would change this.
- `tools/build.py:246`: `"package_version": "0.1.0"` — hardcoded; `pyproject.toml:7` says `version = "0.0.0"`. Manifest disagrees with package metadata. `CHANGELOG.md:8` independently picks `[0.1.0]`. Three sources, two versions.
- The design's DoD #11 (per the round-4 audit prompt) requires that `git status` be clean after a rebuild. This is impossible (a) because of `build_date`, (b) because there are no commits at all — see M2.

**Also a process risk:**
- `tools/build.py:91-95` invokes `tools/fetch.py` as a subprocess with `--full-scrape`. `fetch.py:109` does cache-hit short-circuit (`if os.path.exists(filepath): return True`), so an offline rebuild does not re-hit the network in steady state. But the build will hang or fail if `raw/ucsb/` is incomplete and offline. This is fine in practice but a "byte-identical from snapshots" rebuild requires an explicit `--offline` flag or sentinel; today there is none.
- `datetime.datetime.utcnow()` is deprecated as of Python 3.12. Use `datetime.datetime.now(datetime.UTC)` if the field is kept.

**Corrected behaviour:**
1. Remove `build_date` from `manifest.json` (or stamp it deterministically from `SOURCE_DATE_EPOCH` or from the latest speech `date`, both reproducible).
2. Read `package_version` from `importlib.metadata.version("sotu")` instead of hardcoding `"0.1.0"`.
3. Reconcile version everywhere: pyproject `0.0.0` vs CHANGELOG `0.1.0`. The repo cannot be both at once.
4. Add a test that performs a rebuild against `raw/ucsb/` into a temp directory, then compares hashes against the packaged `src/sotu/data/` — that gives DoD #11 a verifiable enforcement, distinct from "git diff clean."

**Locations:**
- `tools/build.py:245-247`
- `src/sotu/data/manifest.json:2-3`
- `pyproject.toml:7` vs `CHANGELOG.md:8`

---

### Medium (3)

#### M1 — Missing procedural deliverables: `task.md` and `walkthrough.md` do not exist; squat-risk acknowledgement missing

**Type:** procedural omission / unverifiable claim
**Scope:** in-window confirmed
**Evidence grade:** demonstrated

**Evidence:**
- The round-3 audit explicitly cited `task.md` line 6 (the `[/]` Step Zero checkbox) and `walkthrough.md`. Both files were artefacts of the prior implementation cycle.
- `find /home/brian/people/Mark/sotu -name "task*.md" -o -name "walkthrough*.md"` returns nothing. `ls docs/` returns only `CONTRIBUTING.md` and `design-plans/`.
- The author's response claims "Updated `walkthrough.md` and `task.md` to reflect the new state" (round-3 audit, Required actions item 10). The files no longer exist to verify the claim against. Either they were deleted, or they were never updated and the claim is fabricated.
- The audit prompt asks specifically: "Confirm `task.md` and `walkthrough.md` explicitly document this deferral and the squat risk, rather than just leaving an in-progress checkbox." Neither file exists; squat risk is not mentioned in `README.md` or `CHANGELOG.md` either.

**Why it matters:**
The masterclass is scheduled for the 2026 DH-Oz Winter School. Until `sotu` is published on PyPI, an attacker can register the name with malicious code. `README.md:14` instructs users to `pip install sotu`. If a squat exists and the user installs from PyPI before the team does, they get malware. The risk is not academic; the README is publishing the install instruction.

**Corrected behaviour:**
- Either restore `task.md` and `walkthrough.md` with the Step Zero deferral and the squat-risk acknowledgement, or
- Move the deferral note into a maintained location (`README.md` near the install instruction, or `CHANGELOG.md` under `[Unreleased]`), and explicitly say: "The PyPI namespace is unclaimed as of YYYY-MM-DD; do not run `pip install sotu` from PyPI until release."

**Locations:**
- `docs/` (missing files)
- `README.md:14` (`pip install sotu` is currently unsafe advice)
- `CHANGELOG.md` (no Unreleased / squat note)

---

#### M2 — No git history at all; round-3 → round-4 transition is unauditable

**Type:** provenance failure
**Scope:** in-window confirmed
**Evidence grade:** demonstrated

**Evidence:**
- `git log` → "your current branch 'main' does not have any commits yet"
- `git status --porcelain` → 14 entries, all `??` (untracked): every directory and file in the repo
- Step 6 of the audit (drift inspection via `git log -p --since="2026-05-19"`) is structurally impossible

**Why it matters:**
- Round 3's lesson — "the author weakened the test rather than fixing the data" — cannot be re-checked by diffing test files. We confirmed the new assertions are substantive only by reading them, not by tracking what they replaced.
- The PR/merge workflow assumed in the design plan cannot exist without commits.
- A subsequent audit (round 5, however numbered) will have the same blind spot.

**Corrected behaviour:**
- Make an initial commit immediately covering the current tree.
- Make separate, atomic commits for: (a) round-3 → round-4 fixes (loader filter, fileid normalisation, vocab, default column projection, new tests), (b) the data rebuild (so re-running build is verifiable). Do them in the order the audit prompt suggests.
- Push to a remote so the determinism re-check has a baseline.

---

#### M3 — `_is_real_sotu` filter is broader than the round-3 prescription; survives only by luck

**Type:** "broader than asked for" filter, identical anti-pattern to round 3's `.replace(" ","")`
**Scope:** in-window confirmed
**Evidence grade:** plausible (no production-path failure observed *today*; mechanism is plausible for future regressions)

**Evidence:**
- Round-3 audit prescribed (line 89): `if "the-state-the-union" in slug: return True`.
- Author wrote in `tools/discover.py:38`: `if "the-state-the-union" in slug or "state-the-union" in slug:`.
- The second clause is **strictly weaker** — `"state-the-union"` is a proper substring of `"the-state-the-union"`, so the first OR is redundant unless the slug contains `state-the-union` *without* the leading `the-`. The author added this on the implicit assumption that some valid SOTU slugs lack the leading `the-`. Today, this is harmless because no leaked URL trips it; **none** of the eight excluded URLs contain `state-the-union` at all.
- Similarly, line 34 adds `or "annual-address" in slug` to the round-3 prescription of `"annual-message"`. Again strictly broader.

**Why it matters:**
This is the same shape of error as the round-3 `test_fileids` weakening — the author altered the prescription to be more permissive than asked, without test coverage that would catch a real-world false positive. UCSB's URL slugs change over time. A future fixture refresh could surface a non-SOTU slug containing the bare `state-the-union` substring (e.g. a retrospective essay) and it would silently enter the corpus.

**Corrected behaviour:**
- Narrow the modern filter back to `"the-state-the-union" in slug`. If a corner case requires `"state-the-union"` on its own, document the exact URL and add a fixture-based test.
- Add a "negative" test that constructs a fictional URL slug like `presidential-thoughts-on-the-state-the-union-essay` and asserts `_is_real_sotu` correctly rejects it (or, if it's deliberately accepted, the contract should say so).

**Locations:**
- `tools/discover.py:34,38`

---

### Low (2)

#### L1 — Audit-prompt expectation for Washington's party disagrees with the package; the package is right

**Type:** flag-not-defect
**Scope:** n/a
**Evidence grade:** n/a

The round-4 audit prompt's Step 5 asserts "Washington should be `Federalist`". The package returns `Nonpartisan`. This is documented as a deliberate choice in `README.md:77` ("labeling George Washington's party as `Nonpartisan`"), and matches the R `sotu` CRAN package the design follows. The audit prompt's expectation is the one that is wrong, not the package's value. No code change is recommended; flagging in case the audit prompt is taken as source-of-truth in future rounds.

---

#### L2 — Fallback `COVERAGE` constant in `__init__.py` is stale

**Type:** dead-code rot
**Scope:** in-window confirmed
**Evidence grade:** demonstrated

`src/sotu/__init__.py:10` hardcodes `COVERAGE: tuple[int, int] = (1790, 2025)` as a fallback before the dynamic block at `:12-20` overwrites it from metadata. Runtime is fine because metadata always loads. But if anyone reads the source to understand what `COVERAGE` is, they will see `2025`. Bump to `(1790, 2026)` for clarity, or remove the hardcoded literal and let the dynamic block fail loudly if metadata is unreadable.

**Location:** `src/sotu/__init__.py:10`

---

## Verification

- Files read: `pyproject.toml`, `README.md`, `CHANGELOG.md`, `LICENSE` (not opened), `src/sotu/__init__.py`, `src/sotu/_loader.py`, `src/sotu/_corpus.py`, `src/sotu/data/manifest.json`, `tools/build.py`, `tools/discover.py`, `tools/classify.py`, `tools/validate.py`, `tools/fetch.py`, `tests/test_schema.py`, `tests/test_coverage.py`, `tests/test_public_api.py`, `docs/design-plans/2026-05-20-audit-round-3.md`
- Commands run:
  - `uv run pytest -v` → 37 passed
  - Embedded Python smoke test (full Step-2 protocol)
  - Roundtrip / on-disk parity probe (revealed H1)
  - `unzip -l dist/sotu-0.0.0-py3-none-any.whl | grep ...` (confirmed orphans in wheel)
  - `find` for `task.md` / `walkthrough.md` (returned nothing)
  - `git log --all -p --since="2026-05-19"`, `git rev-parse HEAD`, `git status --short`
  - `grep` for `0.1.0`, `2025`, `2026` across pyproject / README / CHANGELOG / manifest
- Citations verified: every file:line reference in the report was opened and confirmed at audit time
- Provenance concerns: zero commits → no diff baseline → round-3 → round-4 transition is unauditable (M2)

---

## Strongest finding

**H1 (orphan `.txt` files in the wheel).** Three independent borders confirm the defect: disk listing (`ls`), wheel listing (`unzip -l`), and the symbolic match against the eight round-3 exclusion fileids plus the four round-3 Van Buren spaces. The author's prose claim ("none of the joint-session addresses exist in the packaged data") is falsified by `unzip -l`. The new test suite cannot see this because every contract test queries via the loader, never via the filesystem.

## Weakest finding

**L1 (Washington party).** This is a disagreement between the audit prompt and the package's documented choice, not a package defect. Listed only for completeness.

---

## Pre-mortem

If H1, H2, and H3 are all dismissed and the package is shipped:
- **Scenario A — wheel bloat is noticed by reviewers post-publish.** Mild reputational hit ("they didn't clean up their orphan files"), but no consumer breakage.
- **Scenario B — masterclass author copy-pastes from `README.md`.** `AttributeError: 'DataFrame' object has no attribute 'president_full'` in a live demo. This is the round-1 defect re-surfacing through documentation, and it would be visible to the workshop audience. Moderate impact.
- **Scenario C — someone re-runs `tools/build.py` to verify reproducibility.** `manifest.json` changes byte-for-byte; the design's DoD #11 fails; a reviewer reasonably concludes "build is non-deterministic" and the package is rejected from packaging-policy-strict environments (some institutional Python distributions).
- **Scenario D — squatter registers `sotu` on PyPI before the team.** Catastrophic. `pip install sotu` in the masterclass installs attacker code. The README instructs this verbatim.

C and D are the materially serious scenarios. H3 and M1 should not be deferred.

---

## Fastest next test

```python
def test_data_dir_matches_fileids():
    import pathlib, sotu
    data_dir = pathlib.Path(sotu.__file__).parent / "data" / "speeches"
    on_disk = {p.stem for p in data_dir.glob("*.txt")}
    assert on_disk == set(sotu.fileids())
```

This single assertion would fail today on 12 files and would have caught H1 before it ever shipped. It belongs in `tests/test_roundtrip.py`.

---

## Overall assessment

**NEEDS REVISION.** The four contract violations from round 3 are genuinely fixed in code and defended by substantive tests — credit where due. The package's runtime API is contract-compliant for the masterclass's use case (load default, fileids, raw, metadata, COVERAGE).

But the package is still not ready to deploy: orphan files ship in the wheel (H1), the README documents a contract the tests now reject (H2), the build cannot be byte-identically reproduced (H3), the PyPI squat-risk paperwork the audit asked for does not exist (M1), there is no git history (M2), and one "broader than asked" filter pattern survives only by luck (M3).

**Required before merge:**
1. **H1** — Delete 12 orphan `.txt` files; add `test_data_dir_matches_fileids`; rebuild the wheel.
2. **H2** — Update `README.md:5,29,33` and `CHANGELOG.md:8,11,12` to the five-column / 2026 contract. Also restore `fileid` to `load(full=True)` in `_loader.py:47`, or document the metadata-based round-trip path.
3. **H3** — Remove `build_date` (or stamp it from data, not wall-clock); reconcile version (pyproject `0.0.0` vs manifest/CHANGELOG `0.1.0`); read version from `importlib.metadata`.
4. **M1** — Restore or replace `task.md`/`walkthrough.md` with a maintained squat-risk note; either update `README.md:14` install instruction with a deferral warning or unblock the PyPI claim.
5. **M2** — Make commits. At minimum: one initial commit covering the current tree.
6. **M3** — Narrow `_is_real_sotu` to match round-3's prescription; add a fixture-based negative test.
7. **L2** — Bump fallback `COVERAGE` literal to `(1790, 2026)`.

After fixes, re-run pytest and `uv build`; verify (a) `test_data_dir_matches_fileids` passes, (b) `unzip -l dist/*.whl | grep "Van Buren\|1981-Reagan-1\.\|..." ` returns empty, (c) two consecutive builds produce byte-identical `src/sotu/data/`.

**Australian English note:** "byte-identically", "normalisation", "deliberately", etc. used throughout; this is a Macquarie University project.
