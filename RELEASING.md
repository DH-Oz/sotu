# Releasing `sotu`

How to cut a new release of the `sotu` Python package to PyPI.

The release pipeline uses **PyPI Trusted Publishing (OIDC)** — no API
tokens are stored anywhere. GitHub mints a short-lived OIDC token; PyPI
exchanges it for a one-shot publish credential. The configuration that
makes this work lives in two places:

- `.github/workflows/release.yml` — the workflow that publishes on tag.
- The PyPI Trusted Publisher config at
  https://pypi.org/manage/project/sotu/settings/publishing/ (registered
  via the Pending Publisher flow on the very first release).

## Cutting a release (steady state, after the first one)

1. **Verify clean.** `uv run pytest`, `uv run ruff check src tests
   tools`, `uv run ruff format --check src tests tools`, `uv run mypy
   src tests tools`. All must pass.

2. **Rebuild the dataset** if anything under `tools/`, `data/`, or
   `raw/` changed:

   ```bash
   uv run python -m tools.build
   git diff --exit-code src/sotu/data/   # must be empty
   ```

   The build is deterministic — a clean diff is the contract.

3. **Bump the version** in `pyproject.toml` (semver). For data-only
   changes the CI `Assert Version Bump on Data Changes` step will
   reject a PR that touches `src/sotu/data/` without a version bump,
   so this is enforced.

4. **Update the CHANGELOG.** Rename the `## [Unreleased]` heading to
   `## [X.Y.Z] - YYYY-MM-DD` and start a new empty `[Unreleased]`
   section above it.

5. **Build and check locally** to catch any packaging mistake before
   the workflow runs:

   ```bash
   rm -f dist/*.whl dist/*.tar.gz
   uv build
   uv run --with twine twine check dist/*
   ```

6. **Commit** the version bump and CHANGELOG together:

   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "release: vX.Y.Z"
   git push
   ```

7. **Tag** with an annotated tag carrying release notes:

   ```bash
   git tag -a vX.Y.Z -m "Release X.Y.Z"
   git push origin vX.Y.Z
   ```

   The tag push triggers `.github/workflows/release.yml`, which:

   - Checks out at the tagged commit.
   - Builds the wheel and sdist with `uv build`.
   - Uploads to the `pypi` GitHub environment (OIDC token issued).
   - Calls `pypa/gh-action-pypi-publish@release/v1` to publish.

8. **Verify**:

   ```bash
   # Wait ~30s for PyPI's CDN.
   pip download --no-deps -d /tmp sotu==X.Y.Z
   python -m venv /tmp/verify && /tmp/verify/bin/pip install sotu==X.Y.Z
   /tmp/verify/bin/python -c "import sotu; print(sotu.COVERAGE, len(sotu.load()))"
   ```

9. **Create a GitHub Release** at the tag with the CHANGELOG entry as
   the release notes:

   ```bash
   gh release create vX.Y.Z --notes-file <(awk '/^## \[X.Y.Z\]/,/^## \[/' CHANGELOG.md | head -n -1)
   ```

## First-release setup (one-time, ~5 minutes)

The OIDC trust relationship between GitHub and PyPI must be registered
once *before* the first publish. PyPI calls this a **Pending Publisher**
because the project doesn't exist on PyPI yet.

1. **Create a PyPI account** at https://pypi.org/account/register/ if
   you don't have one. Two-factor authentication is required for
   trusted publishing.

2. **Register the Pending Publisher** at
   https://pypi.org/manage/account/publishing/. Fill the form:

   | Field | Value |
   |---|---|
   | PyPI Project Name | `sotu` |
   | Owner | `DH-Oz` |
   | Repository name | `sotu` |
   | Workflow filename | `release.yml` |
   | Environment name | `pypi` |

   Save.

3. **Confirm the GitHub `pypi` environment exists** on the repo. It's
   referenced by `release.yml` via `environment: name: pypi`. If you
   haven't created it yet:

   ```bash
   gh api -X PUT repos/DH-Oz/sotu/environments/pypi
   ```

   You can also add deploy-protection rules (e.g. only allow refs
   matching `refs/tags/v*`) on the GitHub Settings → Environments →
   pypi page.

4. **Push the first tag** as described in the steady-state procedure.
   The Pending Publisher entry is consumed on first publish and the
   project is created on PyPI with the trusted publisher already
   attached, so future releases don't need any extra config.

## Troubleshooting

**Workflow fails at the `id-token` permission step.**
Check the `permissions:` block in `release.yml`. The
`publish-to-pypi` job needs `id-token: write` at the job level.

**Workflow runs but PyPI returns 403.**
The Trusted Publisher config doesn't match. Verify all five fields on
the PyPI publishing settings page exactly match the values above
(`owner`, `repository`, `workflow`, `environment` are
case-sensitive). The PyPI project name must already exist (for
post-first-release publishes); otherwise use Pending Publisher again.

**Workflow can't access the `pypi` environment.**
The `pypi` environment doesn't exist on the GitHub repo. Create it
via `gh api -X PUT repos/DH-Oz/sotu/environments/pypi`.

**`uv build` produces no `dist/` files.**
Make sure `src/sotu/` and `src/sotu/data/` exist. The hatchling
backend is configured in `pyproject.toml`
(`[tool.hatch.build.targets.wheel] packages = ["src/sotu"]`).

**The data files are missing from the wheel.**
`src/sotu/data/**` is included by default because it lives under the
package directory. If a refactor moves it, add an explicit
`force-include` clause to `[tool.hatch.build]`.

## What gets attributed

Every release of this package is built from text content sourced from
the **UC Santa Barbara American Presidency Project** (Peters & Woolley,
https://www.presidency.ucsb.edu/). The README, the CHANGELOG, the
CITATION.cff, the package `__doc__`, and the PyPI project description
all foreground that attribution. Please keep it that way.
