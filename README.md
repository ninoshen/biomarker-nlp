# biomarker-nlp

A rule-based NLP pipeline that extracts breast cancer biomarker status —
**ER, PR, HER2, and Ki-67** — from unstructured clinical notes and
pathology reports, and outputs one row per patient with the extracted
status. No gold-standard/registry data is required to use it.

This started as a capstone project analyzing an institutional cohort; this
repo is a reusable, dependency-light package extracted from that analysis —
the extraction logic is unchanged from what was validated on that cohort,
just organized as a standalone library/CLI instead of a notebook tied to
one specific dataset.

## ⚠️ Data / PHI disclaimer

This code processes clinical text and is designed to run on
**de-identified** data. **No real patient data is included in this
repository.** `examples/` contains only synthetically generated text for
demonstration and testing.

If you use this on real clinical data:
- Never commit real patient data, MRNs, or note text to this or any public repo.
- Ensure you have appropriate IRB/data-use approval and that data is handled
  per your institution's policies (e.g. HIPAA in the US).
- `.gitignore` blocks `*.xlsx`/`*.xls` by default for this reason.

## What it does

The core pipeline (`biomarker_nlp.pipeline`) has no dependency on any
gold-standard data:

1. **Standardizes** one or more input tables (notes, pathology reports,
   whatever you have) into a common schema, regardless of their original
   column names.
2. **Extracts** ER, PR, HER2, and Ki-67 status from each row using
   regex-based rules (`biomarker_nlp.extractors`).
3. **Aggregates** note-level extractions to one row per patient
   (positive > equivocal > negative precedence; max value for Ki-67).

A separate, optional module (`biomarker_nlp.evaluation`) lets you score
that output against gold-standard labels *if you happen to have them* —
useful for validating the pipeline on your own cohort, but not required to
run extraction.

## Installation

```bash
git clone https://github.com/ninoshen/biomarker-nlp.git
cd biomarker-nlp
pip install -e ".[dev]"
```

Requires Python 3.9+.

## Quickstart

Generate synthetic demo data (no real patient data) and run extraction on it:

```bash
python examples/generate_synthetic_data.py examples
biomarker-nlp extract \
    --input examples/synthetic_notes.csv \
    --id-column MRN \
    --text-column text \
    --output patient_results.csv
```

This writes one row per patient with `nlp_er_status`, `nlp_pr_status`,
`nlp_her2_status`, `nlp_ki67_value` columns to `patient_results.csv`. Add
`--notes-output notes_detail.csv` if you also want the per-note extraction
trace (useful for auditing which note a call came from).

Your input just needs **any table with a patient-ID column and a free-text
column** — CSV or Excel, any column names (you tell the CLI which columns
to use via `--id-column`/`--text-column`). No fixed schema is assumed.

### Optional: evaluate against gold-standard labels

If you separately have gold-standard biomarker labels (e.g. from a cancer
registry) and want to check extraction quality:

```bash
biomarker-nlp evaluate \
    --results patient_results.csv \
    --gold examples/synthetic_gold_standard.csv \
    --gold-id-column MRN \
    --gold-er-column ER_Summary --gold-pr-column PR_Summary \
    --gold-her2-column HER2_Summary --gold-ki67-column Ki67
```

This prints precision/recall/F1 for ER/PR/HER2 and MAE/correlation for
Ki-67. Gold-standard ER/PR/HER2 columns should use the common registry
convention: `1` = positive, `0` = negative, `9` = unknown.

## Programmatic usage

Single input table (most common case — one dataframe with a patient ID
column and a text column):

```python
from biomarker_nlp import BiomarkerPipeline

pipeline = BiomarkerPipeline()
result = pipeline.run_from_table(df, id_column="MRN", text_column="note_text")

result["patient_level"]  # one row per patient: nlp_er_status, nlp_pr_status, ...
result["note_level"]     # one row per input row, with the same columns appended
```

Multiple input tables with different column names (e.g. notes + pathology
reports, each from a different export):

```python
from biomarker_nlp import BiomarkerPipeline, SourceColumns

pipeline = BiomarkerPipeline()
result = pipeline.run_from_sources([
    (notes_df, SourceColumns(id="MRN", text="note_text", date="contact_date"), "Office Visit"),
    (pathology_df, SourceColumns(id="MRN", text="PATH_REPORT_TEXT"), "Pathology Report"),
])
```

Optional evaluation against gold-standard labels:

```python
from biomarker_nlp import prepare_gold_standard, evaluate
from biomarker_nlp.evaluation import format_report

gold = prepare_gold_standard(
    registry_df,
    id_column="Medical Record Number",
    er_column="Estrogen Receptor Summary",
    pr_column="Progesterone Receptor Summary",
    her2_column="HER2 Overall Summary",
    ki67_column="Ki-67",
)
report = evaluate(result["patient_level"], gold)
print(format_report(report))
```

## CLI reference

```
biomarker-nlp extract --input <table.csv|.xlsx> --id-column <col> --text-column <col>
    --output <patient_results.csv|.xlsx>
    [--sheet <name>] [--date-column <col>] [--type-column <col>]
    [--source-label <label>] [--notes-output <notes_detail.csv>]

biomarker-nlp evaluate --results <patient_results.csv|.xlsx> --gold <gold.csv|.xlsx>
    --gold-id-column <col> --gold-er-column <col> --gold-pr-column <col>
    --gold-her2-column <col> --gold-ki67-column <col>
    [--results-id-column <col>] [--gold-sheet <name>] [--report <report.md>]
```

## Extending the extractors

`biomarker_nlp/extractors.py` contains four independent, pure functions —
`extract_er`, `extract_pr`, `extract_her2`, `extract_ki67` — each taking a
string and returning a normalized label. They're plain regex rules, so you
can add patterns for note templates specific to your institution without
touching the rest of the pipeline. `tests/test_extractors.py` has examples
of the expected input/output shape.

## Running tests

```bash
pytest
```

## License

MIT — see [LICENSE](LICENSE).
