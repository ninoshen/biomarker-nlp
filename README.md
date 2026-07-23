# breast-cancer-biomarker-nlp

A rule-based NLP pipeline that extracts breast cancer biomarker status —
**ER, PR, HER2, and Ki-67** — from unstructured clinical notes and pathology
reports, and validates the extraction against gold-standard cancer registry
labels.

This started as a capstone project analyzing an institutional cohort; this
repo is a reusable, dependency-light package extracted from that analysis —
the extraction logic, aggregation, and evaluation are unchanged from what was
validated on that cohort, just organized as a library instead of a notebook.

## ⚠️ Data / PHI disclaimer

This code processes clinical text and is designed to run on **de-identified**
data. **No real patient data is included in this repository.** `examples/`
contains only synthetically generated text for demonstration and testing.

If you use this on real clinical data:
- Never commit real patient data, MRNs, or note text to this or any public repo.
- Ensure you have appropriate IRB/data-use approval and that data is handled
  per your institution's policies (e.g. HIPAA in the US).
- The `.gitignore` blocks `*.xlsx`/`*.xls` by default for this reason.

## What it does

1. **Loads** clinical notes, pathology reports, and registry ("gold
   standard") data from an Excel workbook.
2. **Builds a text corpus** combining office-visit notes and pathology
   reports per patient.
3. **Extracts** ER, PR, HER2, and Ki-67 status from each note/report using
   regex-based rules (`biomarker_nlp.extractors`).
4. **Aggregates** note-level extractions to one status per patient
   (positive > equivocal > negative precedence; max value for Ki-67).
5. **Evaluates** patient-level NLP output against registry labels:
   precision/recall/F1/confusion matrix for ER/PR/HER2, and
   MAE/median error/correlation for Ki-67.

### Validation results (original cohort)

For reference, here's what this pipeline's logic achieved on the original
(de-identified, IRB-approved) validation cohort — included to document
expected performance, not as data included in this repo:

| Biomarker | Cases | TP  | FP | FN  | TN  | Precision | Recall | F1    |
| --------- | ----: | --: | -: | --: | --: | --------: | -----: | ----: |
| ER        |   356 | 163 |  8 | 141 |  44 |     0.953 |  0.536 | 0.686 |
| PR        |   355 | 136 | 18 | 134 |  67 |     0.883 |  0.504 | 0.642 |
| HER2      |   293 |  19 | 13 |  26 | 235 |     0.594 |  0.422 | 0.494 |

| Biomarker | Cases | MAE   | Median AE | Within 5pts | Within 10pts | Correlation |
| --------- | ----: | ----: | --------: | -----------: | ------------: | ----------: |
| Ki-67     |   125 | 5.389 |     0.000 |         80.0% |          88.0% |       0.851 |

ER/PR precision is high but recall is moderate — the extractor is
conservative and tends to default to "negative" when a note doesn't state
status explicitly. HER2 is harder because IHC scores are used inconsistently
across notes. See `biomarker_nlp/extractors.py` if you want to tune the
rules for your own note templates.

## Installation

```bash
git clone <your-repo-url>
cd breast-cancer-biomarker-nlp
pip install -e ".[dev]"
```

Requires Python 3.9+.

## Quickstart

Generate a synthetic demo workbook (no real data) and run the pipeline on it:

```bash
python examples/generate_synthetic_data.py examples/synthetic_data.xlsx
biomarker-nlp run --input examples/synthetic_data.xlsx --output patient_results.csv
```

This prints an evaluation report and writes per-patient biomarker calls to
`patient_results.csv`.

## Input data schema

The pipeline expects an Excel workbook with:

| Sheet                          | Required columns                                                    |
| ------------------------------- | --------------------------------------------------------------------- |
| `Notes`                         | `MRN`, `contact_date`, `note_text`, `note_type`                       |
| a sheet with "Pathology" in its name | `MRN`, `RESULT_TIME`, `PATH_REPORT_TEXT`, `REPORT_TYPE`           |
| a sheet with "Tumor" in its name (registry) | `Medical Record Number`, `Estrogen Receptor Summary`, `Progesterone Receptor Summary`, `HER2 Overall Summary`, `Ki-67` |

Registry ER/PR/HER2 columns use the common registry convention: `1` =
positive, `0` = negative, `9` = unknown.

If your source system uses different column names, pass a custom
`ColumnMap` instead of relying on the defaults (see below) — no need to
rename columns in your export.

## Programmatic usage

```python
from biomarker_nlp import BiomarkerPipeline, ColumnMap
from biomarker_nlp.evaluation import evaluate_all, format_report

pipeline = BiomarkerPipeline()  # or BiomarkerPipeline(ColumnMap(...)) for custom schemas
result = pipeline.run_from_excel("cohort.xlsx")

result["patient_level"]   # one row per patient: nlp_er_status, nlp_pr_status, ...
result["analysis"]        # patient_level merged with registry gold labels

report = evaluate_all(result["analysis"])
print(format_report(report))
```

To point the pipeline at a workbook with different column names:

```python
from biomarker_nlp import BiomarkerPipeline, ColumnMap

column_map = ColumnMap(
    notes_columns={"mrn": "PatientID", "date": "NoteDate", "text": "NoteBody", "type": "NoteType"},
)
pipeline = BiomarkerPipeline(column_map)
```

## CLI reference

```
biomarker-nlp run --input <workbook.xlsx> --output <results.csv> [--no-evaluate] [--report <report.md>]
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
