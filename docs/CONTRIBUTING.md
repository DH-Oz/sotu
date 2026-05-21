# Contributing & Yearly SOTU Bump Runbook

This guide describes the manual yearly bump procedure and guidelines for maintaining the `sotu` package. 

Because SOTU addresses occur on a predictable calendar cadence, this package uses a robust, manual, once-per-year bump workflow. This guarantees that all published versions of the package are hermetically sealed, verified, and completely deterministic.

---

## Yearly SOTU Bump Procedure

When a new State of the Union address is delivered, follow this sequence to update the package:

### 1. Update President Term Boundaries (if applicable)
If a presidential transition occurred:
- Open `src/sotu/data/presidents.csv`.
- Update the outgoing president's `end_year` or add the new president's row with their canonical spelling, last name, political party, and term years.

### 2. Check for SOTU Format Overrides
By default, the package assumes any SOTU delivered after 1913 is a `"spoken"`.
- If a post-1913 SOTU was delivered *only* as a written message, open `data/sotu_type_overrides.csv` and append the new year along with `written`.

### 3. Increment the Package Version
Following our versioning policy:
- Open `pyproject.toml` and increment the minor version (e.g. `0.1.0` -> `0.2.0`).
- Add a new section in `CHANGELOG.md` detailing the update.

> [!IMPORTANT]
> A CI workflow guards data modifications. Pull requests modifying files under `src/sotu/data/` *must* be accompanied by an incremented version number in `pyproject.toml`, or the lint check will fail.

### 4. Run the Rebuild & Scraper
Run the orchestrator script to automatically parse the central guidebook table, scrape the new address from UCSB Presidency Project, extract and clean the text, match metadata, update the file list, and regenerate the hashes:

```bash
# Run the build orchestrator
PYTHONPATH=. uv run python tools/build.py --delay 2.0
```

*The fetcher automatically respects caching and will only download the newly discovered HTML file. The polite 2-second rate-limiting delay ensures we do not hammer the UCSB servers.*

### 5. Verify the Dataset
The build process automatically runs the validator tool (`tools/validate.py`) upon completion. It asserts:
- Column schemas and datatype constraints.
- Full calendar coverage from 1790 to the new year.
- Determinism and SHA-256 integrity checks.

To manually trigger the validator:
```bash
PYTHONPATH=. uv run python tools/validate.py
```

### 6. Run the Test Suite
Ensure that the entire public API, schema constraints, decade counts, and roundtrip assertions pass:

```bash
uv run pytest
```

### 7. Commit & Release
Once all checks pass, commit all files (including the newly added raw HTML in `raw/ucsb/`, parsed text in `src/sotu/data/speeches/`, and updated metadata/manifest files) and push your changes.

When a git tag is created (e.g., `v0.2.0`), the GitHub Actions release workflow will automatically build the wheel and publish it to PyPI via trusted OIDC publishing.
