# SOTU: U.S. State of the Union Addresses & Annual Messages (1790–present)

A Python package containing the full corpus of U.S. Presidential Annual
Messages (1790–1946) and State of the Union Addresses (1947–present),
with a pandas-DataFrame loader and an NLTK-style file-id reader
interface. Designed to give Python users the same affordances as the R
[`sotu`](https://CRAN.R-project.org/package=sotu) package and its
quanteda corpus integration.

This package is for digital humanities scholars, political scientists,
and educators who want clean, offline, citable access to every SOTU
from **1790 through 2026** (and beyond).

> **All text content in this package comes from the UC Santa Barbara
> American Presidency Project** (https://www.presidency.ucsb.edu/),
> the authoritative scholarly archive curated by Gerhard Peters and
> John T. Woolley. This Python package only repackages their texts for
> programmatic access; the scholarly work of transcription, dating,
> classification, and verification is theirs. Please cite them in any
> research that uses this corpus — see [Citation](#citation) below.

---

## Quickstart

### Installation

```bash
uv add sotu
# or using standard pip:
pip install sotu
```

Or directly from source:

```bash
git clone https://github.com/DH-Oz/sotu.git
cd sotu
uv pip install .
```

### Basic Usage

Get every address into a pandas DataFrame in one line:

```python
import sotu

df = sotu.load()
print(df.head())
# Columns: ['year', 'president', 'party', 'sotu_type', 'text']

# Filter by speech type
spoken = df[df.sotu_type == "spoken"]    # delivered orally
written = df[df.sotu_type == "written"]  # submitted as written messages

# Filter by president (last name only — the locked contract uses
# surnames so "Bush" returns both H.W. and W.)
washington = df[df.president == "Washington"]

# Programmatic coverage bounds
print(sotu.COVERAGE)  # (1790, 2026)
```

For full names and disambiguation columns (e.g. `president_full` to
tell George H. W. Bush from George W. Bush), pass `full=True`:

```python
df_full = sotu.load(full=True)
# Adds: 'fileid', 'president_full', 'is_sotu', 'date', 'source_url',
#       'word_count', 'sha256', ...
```

### Canonical SOTUs vs. related UCSB documents

By default `sotu.load()` returns one canonical SOTU per (year, president).
The UCSB archive also tags a small number of related documents under the
"State of the Union" taxonomy that aren't the SOTU itself — Nixon's 1973
series of policy-specific *Special Messages to Congress*, Roosevelt's
1945 radio summary of the written SOTU, Eisenhower's 1956 Key West
remarks. The corpus carries those rows with `is_sotu=False` so scholars
can still access them:

```python
archive = sotu.load(full=True, include_related=True)
related = archive[~archive.is_sotu]
print(related[["year", "president", "source_url"]])
```

Years with multiple canonical rows are legitimate spoken+written pairs —
Nixon 1972/74 and Carter 1978-80 each gave a delivered address *and*
submitted a longer written message to Congress on the same date.

---

## Detailed Usage

### NLTK-style corpus accessors

For NLTK-style access or granular text reading, use the file-id methods:

```python
# Every fileid, sorted chronologically
fileids = sotu.fileids()
print(fileids[:5])
# ['1790-Washington-1', '1790-Washington-2', ...]

# Raw cleaned plain text of a single address
speech_text = sotu.raw('1790-Washington-1')
print(speech_text[:500])

# Complete metadata table without loading the bodies
meta = sotu.metadata()
print(meta.head())
```

### Coming from R `sotu` + quanteda

The R `sotu` package exposes `sotu_meta` (a metadata data frame) and
`sotu_text` (a parallel character vector). Together with
[`quanteda`](https://quanteda.io/) they let you do things like:

```r
library(sotu); library(quanteda)
corp     <- corpus(sotu_text, docvars = sotu_meta)
spoken   <- corpus_subset(corp, sotu_type == "speech")
ndoc(corp)
```

The Python equivalents (working with the same UCSB source texts):

| R / quanteda                                  | Python (`sotu`)                                          |
|-----------------------------------------------|----------------------------------------------------------|
| `sotu_meta`                                   | `sotu.metadata()`                                        |
| `sotu_text`                                   | `sotu.load(full=True)["text"]`                           |
| `corpus(sotu_text, docvars=sotu_meta)`        | `sotu.load(full=True)`  (single joined DataFrame)        |
| `texts(corp)`                                 | `df["text"].tolist()`                                    |
| `docvars(corp)`                               | `df.drop(columns=["text"])`                              |
| `docnames(corp)`                              | `sotu.fileids()` or `df["fileid"]`                       |
| `corpus_subset(corp, sotu_type == "speech")`  | `df[df.sotu_type == "spoken"]`                           |
| `ndoc(corp)`                                  | `len(df)`                                                |
| `as.character(corp[i])`                       | `sotu.raw(fileid)`                                       |

Two intentional differences from the R package:

- **`sotu_type` vocabulary**: this package uses `"spoken"` / `"written"`
  (matching the consumer contract documented for the DH-Oz masterclass).
  The R package uses `"speech"` / `"written"`. Convert with
  `df["sotu_type"].replace({"spoken": "speech"})` if you need R parity.
- **`president` column**: this package's default `president` is the
  surname only (e.g. `"Washington"`, `"Van Buren"`) for stable joins;
  `president_full` carries the full name in `load(full=True)`. R uses
  the full name as the primary `president` field.

To hand the corpus to a Python NLP library like
[spaCy](https://spacy.io/) or [Gensim](https://radimrehurek.com/gensim/):

```python
import sotu, spacy

df = sotu.load(full=True)
nlp = spacy.load("en_core_web_sm")
for fileid, text in zip(df["fileid"], df["text"]):
    doc = nlp(text)
    # ... your analysis here
```

---

## Data Preservation & Provenance

The text corpus is compiled directly from the authoritative scholarly
archive at the **UC Santa Barbara American Presidency Project**
([https://www.presidency.ucsb.edu/](https://www.presidency.ucsb.edu/)),
curated by Gerhard Peters and John T. Woolley.

Unlike many scraped datasets this package:

- Preserves the **exact raw HTML source** files in the repository under
  `raw/ucsb/` for verification and academic reproducibility.
- Ships a **SHA-256 hash manifest** (`manifest.json`) covering every
  parsed plain-text speech and every raw HTML source so byte-level
  determinism can be re-checked at any time.
- Retains the **R `sotu` CRAN package's classification rules** (e.g.
  labelling George Washington's party as `Nonpartisan` and Andrew
  Johnson's as `National Union`) while providing an additive
  disambiguation layer (`president_full`, `president_id`, `date`,
  `source_url`).
- **Flags non-SOTU UCSB documents** (radio summaries, Key West remarks,
  Nixon 1973 topical Special Messages) with `is_sotu=False` so scholars
  can study them without polluting the canonical SOTU view.

The build orchestrator (`uv run python -m tools.build`) is
deterministic — two consecutive offline builds against the same
`raw/ucsb/` snapshot produce byte-identical `metadata.csv`,
`manifest.json`, and `speeches/*.txt` files.

---

## Citation

> **Always cite the UCSB American Presidency Project** when using the
> text content from this corpus. The scholarly transcription,
> classification, and verification of these documents is their work.

### Recommended citation

Peters, Gerhard, and John T. Woolley. *The American Presidency
Project*. University of California, Santa Barbara.
[https://www.presidency.ucsb.edu/](https://www.presidency.ucsb.edu/)

BibTeX:

```bibtex
@misc{peters-woolley-presidency,
  author       = {Peters, Gerhard and Woolley, John T.},
  title        = {The American Presidency Project},
  organization = {University of California, Santa Barbara},
  url          = {https://www.presidency.ucsb.edu/}
}
```

A machine-readable [`CITATION.cff`](./CITATION.cff) is provided at the
repository root for tools that consume it (GitHub, Zotero, etc.).

If you specifically want to cite this Python packaging of the corpus,
also reference the project repository
(`https://github.com/DH-Oz/sotu`), but the primary citation belongs to
UCSB.

### Acknowledgements

- **Gerhard Peters** and **John T. Woolley** for building and
  maintaining the American Presidency Project at UC Santa Barbara since
  1999. Every text in this package is theirs; this project only
  reorganises their work for programmatic access.
- The R [`sotu`](https://CRAN.R-project.org/package=sotu) package
  authors for establishing the classification conventions
  (`sotu_type`, party assignments) that this Python package adopts.

### License

- The Python code and build system are licensed under the **MIT
  License**.
- The SOTU speech texts themselves are works of the United States
  Government and reside in the **public domain** under 17 U.S.C. § 105.
- The HTML markup and editorial structure provided by the UCSB American
  Presidency Project belong to UCSB; this package only redistributes
  the plain-text transcriptions they have made publicly available.
