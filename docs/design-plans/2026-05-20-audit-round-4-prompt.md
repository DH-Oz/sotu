# Audit Prompt — `DH-Oz/sotu` Round 4

You are auditing a Python package that has been through three rounds of human-in-the-loop review with another AI. The author AI's most recent message says all known defects are fixed and the package is "ready for deployment." Treat that claim as a hypothesis. Your job is to falsify or confirm it against runtime reality, not against prose.

## Briefing

`sotu` is a Python package being built for the 2026 DH-Oz Digital Humanities Winter School. It ships every U.S. Presidential Annual Message to Congress (1790–1946) and State of the Union Address (1947–present) as plain UTF-8 text inside the wheel, with a pandas-DataFrame loader and an NLTK-style file-id surface. Source is scraped (once, manually) from the UCSB Presidency Project. Distribution is via PyPI.

Working directory: `/home/brian/people/Mark/sotu/`
Design plan: `docs/design-plans/2026-05-20-dh-oz-sotu.md`
Round-3 audit (which the author has now responded to): `docs/design-plans/2026-05-20-audit-round-3.md`

The round-3 audit's tail contains the author's "Developer Response & Resolution" section claiming every defect is fixed. **Verify each claim against the actual built package. Do not accept prose.**

## The locked contract (this is what "correct" means)

The downstream consumer is a Jupyter masterclass that will import `sotu` and run code like:

```python
import sotu
df = sotu.load()
# expects exactly these 5 columns, in this order:
# ['year', 'president', 'party', 'sotu_type', 'text']
df_spoken = df[df.sotu_type == "spoken"]   # not "speech"
washington = df[df.president == "Washington"]  # last-name only

ids = sotu.fileids()            # ['1790-Washington-1', ...]
text = sotu.raw('1790-Washington-1')   # str
meta = sotu.metadata()          # DataFrame, full metadata view
print(sotu.COVERAGE)            # (1790, <latest_year>)
```

Hard requirements:

1. `sotu.load()` (default) returns a `pandas.DataFrame` with **exactly** these columns in **exactly** this order: `["year", "president", "party", "sotu_type", "text"]`. No nulls in any column.
2. `df["sotu_type"].unique()` is **exactly** `{"spoken", "written"}`. Not `"speech"`. Not anything else.
3. `df["president"]` is **last-name only**, no spaces, no titles. Examples: `"Washington"`, `"Van Buren"` may NOT have a space — must be normalised, but the `president` column is allowed to retain the natural form `"Van Buren"` IF the fileid still has no spaces. The fileid is the strictly-no-space artefact.
4. `sotu.fileids()` returns labels like `"1790-Washington-1"` and `"1837-VanBuren-1"`. **No fileid may contain whitespace.** Each fileid must split cleanly under `fid.rsplit("-", 2) → (year, name, idx)` where `year` is a 4-digit int, `name.isalpha()` is True, `idx` is a digit string.
5. `sotu.load(full=True)` returns a DataFrame that INCLUDES `president_full` (canonical full name like `"Franklin D. Roosevelt"`) plus all other metadata columns.
6. `sotu.metadata()` returns a DataFrame view containing the full metadata schema.
7. The corpus EXCLUDES first-year incoming joint-session addresses (constitutionally not SOTUs). These eight fileids must NOT appear in `sotu.fileids()`:
   - `1981-Reagan-1` (1981-02-18, the-program-for-economic-recovery)
   - `1989-Bush-1` (1989-02-09, administration-goals)
   - `1993-Clinton-1` (1993-02-17, administration-goals)
   - `2001-Bush-1` (2001-02-27, administration-goals)
   - `2009-Obama-1` (2009-02-24, joint-session, no SOTU label)
   - `2017-Trump-1` (2017-02-28, joint-session, no SOTU label)
   - `2021-Biden-1` (2021-04-28, joint-session, no SOTU label)
   - `2025-Trump-1` (2025-03-04, joint-session, no SOTU label)
8. The corpus COUNT should be in the range `240 ≤ len(sotu.load()) ≤ 260`. The R `sotu` CRAN package has ~241 addresses through 2020; through 2026 we expect ~247–250.
9. `sotu.COVERAGE == (1790, 2026)` — the 2026 SOTU is real (Trump, 2026-02-24, UCSB document slug includes `the-state-the-union`).
10. `sotu.raw(fileid)` for every fileid must return a non-empty string that round-trips with `df[df.fileid == fileid]["text"].iloc[0]` if `fileid` is exposed there, otherwise with the corresponding row in `sotu.load(full=True)`.

## Prior drift to specifically look for

Three audits have caught three different failure modes:

- **Round 1:** the `president` column was reverted to full names — broke the consumer contract.
- **Round 2:** plan structurally complete; minor punch-list items.
- **Round 3:** tests green, runtime reality showed `sotu_type` was `"speech"`, all 8 excluded fileids were present, Van Buren fileids had spaces, `load()` default leaked `president_full`. Tests passed because the test suite asserted shape not content.

The author has now claimed all of those are fixed. **Verify directly. Especially check that the fix isn't "weaken the assertion" instead of "fix the data."**

## Verification protocol

Perform these checks in order. Report each as PASS / FAIL with the actual observed value.

### Step 1 — Run the test suite and inspect raw output

```bash
cd /home/brian/people/Mark/sotu
uv run pytest -v 2>&1 | tee /tmp/sotu-audit-pytest.log
```

Expected: all tests pass. **But passing tests are no longer sufficient.** Continue to Step 2 regardless of test outcome.

### Step 2 — Inspect runtime DataFrame against the contract

```bash
cd /home/brian/people/Mark/sotu
uv run python <<'EOF'
import sotu
import pandas as pd

df = sotu.load()
df_full = sotu.load(full=True)
meta = sotu.metadata()
ids = sotu.fileids()

print("=== sotu.COVERAGE ===")
print(sotu.COVERAGE)

print("\n=== default load() columns ===")
print(list(df.columns))

print("\n=== sotu_type unique values ===")
print(sorted(df["sotu_type"].unique().tolist()))

print("\n=== row count ===")
print(len(df))

print("\n=== nulls per column ===")
print(df.isna().sum().to_dict())

print("\n=== fileids with whitespace ===")
print([f for f in ids if " " in f][:10])

print("\n=== excluded-but-present fileids ===")
EXCLUDED = {
    "1981-Reagan-1", "1989-Bush-1", "1993-Clinton-1", "2001-Bush-1",
    "2009-Obama-1", "2017-Trump-1", "2021-Biden-1", "2025-Trump-1",
}
print(sorted(EXCLUDED & set(ids)))

print("\n=== fileid segment-split smoke test (first 5 + last 5) ===")
for fid in ids[:5] + ids[-5:]:
    try:
        year, name, idx = fid.rsplit("-", 2)
        ok = year.isdigit() and len(year) == 4 and name.isalpha() and idx.isdigit()
        print(f"  {fid!r}: split=({year!r}, {name!r}, {idx!r}) ok={ok}")
    except Exception as e:
        print(f"  {fid!r}: SPLIT ERROR: {e}")

print("\n=== load(full=True) extra columns ===")
print(sorted(set(df_full.columns) - set(df.columns)))

print("\n=== source_url administration-goals leakage ===")
if "source_url" in meta.columns:
    bad = meta[meta["source_url"].str.contains("administration-goals", na=False)]
    print(f"  rows with 'administration-goals' in source_url: {len(bad)}")
    if len(bad) > 0:
        print(bad[["fileid" if "fileid" in bad.columns else meta.columns[0], "source_url"]].head().to_string())
else:
    print("  (no source_url column on metadata())")

print("\n=== round-trip raw(fileid) vs full text ===")
sample = ids[0]
text_via_raw = sotu.raw(sample)
# match against full DataFrame
fid_col = "fileid" if "fileid" in df_full.columns else None
if fid_col:
    text_via_df = df_full[df_full[fid_col] == sample]["text"].iloc[0]
    print(f"  {sample}: raw==df? {text_via_raw == text_via_df}, len(raw)={len(text_via_raw)}")
else:
    print("  (no fileid column on load(full=True); cannot round-trip without fileid mapping)")
EOF
```

Report the actual output verbatim.

### Step 3 — Compare against the round-3 audit's specific claims

Open `/home/brian/people/Mark/sotu/docs/design-plans/2026-05-20-audit-round-3.md` and read the "Developer Response & Resolution" section at the end. For each of the four numbered contract violations:

- The author claims the issue is fixed and lists a specific assertion. Find that assertion in the test files. Verify it actually asserts what the author claims it asserts. (A trivially-true assertion that happens to pass is the same failure mode as round 3.)
- Verify the test FAILS if you temporarily break the data. (You don't have to actually break the data — just read the assertion and judge whether it would catch the specific defect it claims to defend against.)

### Step 4 — Check the smaller items the author says are fixed

- `pyproject.toml` `pandas` constraint: must be `>=2.0,<3.0` (or stricter).
- `pyproject.toml` `authors`: must include emails.
- Step Zero PyPI claim: author says deferred per user instruction. Confirm `task.md` and `walkthrough.md` explicitly document this deferral and the squat risk, rather than just leaving an in-progress checkbox.

### Step 5 — Sanity-check the contract that the round-3 audit did not specify

These are NEW checks (not previously called out — extend the audit, don't just re-run the prior one):

- The `party` column has exactly which unique values? Spot-check: Washington should be `Federalist`, Jefferson `Democratic-Republican`, Lincoln `Republican`, FDR `Democratic`. If any of these is wrong, party-join is broken.
- For every fileid, the `.txt` file under `src/sotu/data/speeches/<fileid>.txt` must exist and must equal `sotu.raw(fileid)`.
- `sotu.__doc__` should mention the coverage range. Read it. Confirm it says something like "1790 through 2026" (or the equivalent).
- Re-run the build orchestrator (`uv run python tools/build.py` or `uv run sotu-build`) against the existing committed `raw/ucsb/` snapshots. The resulting `src/sotu/data/` must be **byte-identical** to the committed version (`git status` clean, or `git diff src/sotu/data/` empty). This is the determinism check from the original design's DoD #11.
- Check `sotu.metadata()` for the presence of a `fileid` column. Without it, downstream code can't join the metadata view to `sotu.raw()` results.

### Step 6 — Inspect for any new drift

Look at `git log -p --since="2026-05-19"` on the sotu repo. Identify any commit message or diff that suggests the author "weakened a test to pass" rather than "fixed code to match the test." That was the round-3 failure mode for Van Buren.

## What to report

A single markdown report with this structure:

```
# Round-4 Audit Findings

## Summary
[One paragraph. PASS or FAIL overall. If FAIL, count of violations.]

## Step 1: pytest output
[Verbatim summary line + any failure traces.]

## Step 2: Runtime contract check
[For each of the 10 hard requirements above, PASS or FAIL with observed value.]

## Step 3: Test-assertion strength check
[For each of the 4 round-3 violations, does the new test actually defend the contract? FAIL if the test is structurally weak.]

## Step 4: Smaller items
[pandas pin / authors emails / Step Zero deferral documentation.]

## Step 5: New checks
[party values / .txt round-trip / __doc__ coverage / determinism re-run / metadata fileid column.]

## Step 6: Drift inspection
[Anything in git history that looks like test-weakening.]

## Verdict
[Recommend MERGE / NEEDS REVISION. If NEEDS REVISION, list the specific files and lines to change.]
```

## Hard rules

- Do not modify any code or data. Read-only audit.
- Do not accept the author's prose claims without runtime verification.
- If a verification command fails or returns ambiguous output, say so. Don't paper over.
- If the test suite passes but the runtime contract is violated, the test suite is incomplete. Say that explicitly.
- Australian English in your report (this is a Macquarie University project).

When in doubt, falsify.
