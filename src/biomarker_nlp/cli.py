"""Command-line entry point for the biomarker NLP pipeline.

Two subcommands:

`extract` — the core, standalone pipeline. Point it at any table of
clinical text (CSV or Excel) with a patient-ID column and a free-text
column, and it writes out extracted ER/PR/HER2/Ki-67 status per patient.
No gold-standard/registry data required.

    biomarker-nlp extract --input notes.csv --id-column MRN \\
        --text-column note_text --output patient_results.csv

`evaluate` — optional. If you separately have gold-standard labels (e.g.
from a cancer registry) to validate extraction quality against, this
scores extract's output against them.

    biomarker-nlp evaluate --results patient_results.csv \\
        --gold registry.csv --gold-id-column MRN \\
        --gold-er-column ER_Summary --gold-pr-column PR_Summary \\
        --gold-her2-column HER2_Summary --gold-ki67-column Ki67
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from .evaluation import evaluate, format_report
from .pipeline import BiomarkerPipeline
from .registry import prepare_gold_standard


def _read_table(path: str, sheet: str = None) -> pd.DataFrame:
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path, sheet_name=sheet if sheet is not None else 0)
    raise ValueError(f"Unsupported input file type: {path} (expected .csv, .xlsx, or .xls)")


def _write_table(df: pd.DataFrame, path: str) -> None:
    if path.lower().endswith(".csv"):
        df.to_csv(path, index=False)
    elif path.lower().endswith((".xlsx", ".xls")):
        df.to_excel(path, index=False)
    else:
        raise ValueError(f"Unsupported output file type: {path} (expected .csv, .xlsx, or .xls)")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="biomarker-nlp", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract ER/PR/HER2/Ki-67 status from a table of clinical text")
    extract_parser.add_argument("--input", required=True, help="Path to input .csv or .xlsx table of notes/reports")
    extract_parser.add_argument("--sheet", default=None, help="Sheet name/index, if --input is an Excel workbook with multiple sheets")
    extract_parser.add_argument("--id-column", required=True, help="Column holding the patient identifier")
    extract_parser.add_argument("--text-column", required=True, help="Column holding the free text to extract from")
    extract_parser.add_argument("--date-column", default=None, help="Optional column holding the note/report date")
    extract_parser.add_argument("--type-column", default=None, help="Optional column holding a note-type label")
    extract_parser.add_argument("--source-label", default="note", help="Label to tag these rows with in note_source (default: 'note')")
    extract_parser.add_argument("--output", required=True, help="Path to write patient-level results (.csv or .xlsx)")
    extract_parser.add_argument("--notes-output", default=None, help="Optional path to also write note-level (per-row) extraction detail")

    evaluate_parser = subparsers.add_parser("evaluate", help="Score extract's output against gold-standard labels (optional)")
    evaluate_parser.add_argument("--results", required=True, help="Path to patient-level results produced by `extract` (.csv or .xlsx)")
    evaluate_parser.add_argument("--results-id-column", default="patient_id", help="Patient ID column in --results (default: patient_id)")
    evaluate_parser.add_argument("--gold", required=True, help="Path to gold-standard labels table (.csv or .xlsx)")
    evaluate_parser.add_argument("--gold-sheet", default=None, help="Sheet name/index, if --gold is an Excel workbook with multiple sheets")
    evaluate_parser.add_argument("--gold-id-column", required=True, help="Patient ID column in --gold")
    evaluate_parser.add_argument("--gold-er-column", required=True, help="ER status column in --gold (1=positive, 0=negative, 9=unknown)")
    evaluate_parser.add_argument("--gold-pr-column", required=True, help="PR status column in --gold (1=positive, 0=negative, 9=unknown)")
    evaluate_parser.add_argument("--gold-her2-column", required=True, help="HER2 status column in --gold (1=positive, 0=negative, 9=unknown)")
    evaluate_parser.add_argument("--gold-ki67-column", required=True, help="Ki-67 numeric value column in --gold")
    evaluate_parser.add_argument("--report", default=None, help="Optional path to write the evaluation report as markdown")

    return parser


def _cmd_extract(args: argparse.Namespace) -> int:
    df = _read_table(args.input, args.sheet)

    pipeline = BiomarkerPipeline()
    result = pipeline.run_from_table(
        df,
        id_column=args.id_column,
        text_column=args.text_column,
        date_column=args.date_column,
        type_column=args.type_column,
        source_label=args.source_label,
    )

    _write_table(result["patient_level"], args.output)
    print(f"Wrote patient-level biomarker extraction for {len(result['patient_level'])} patients to {args.output}")

    if args.notes_output:
        _write_table(result["note_level"], args.notes_output)
        print(f"Wrote note-level extraction detail ({len(result['note_level'])} rows) to {args.notes_output}")

    return 0


def _cmd_evaluate(args: argparse.Namespace) -> int:
    patient_level = _read_table(args.results)
    if args.results_id_column != "patient_id":
        patient_level = patient_level.rename(columns={args.results_id_column: "patient_id"})

    gold_df = _read_table(args.gold, args.gold_sheet)
    gold = prepare_gold_standard(
        gold_df,
        id_column=args.gold_id_column,
        er_column=args.gold_er_column,
        pr_column=args.gold_pr_column,
        her2_column=args.gold_her2_column,
        ki67_column=args.gold_ki67_column,
    )

    report = evaluate(patient_level, gold)
    rendered = format_report(report)
    print(rendered)

    if args.report:
        with open(args.report, "w") as f:
            f.write(rendered + "\n")
        print(f"\nWrote evaluation report to {args.report}")

    return 0


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "extract":
        return _cmd_extract(args)
    if args.command == "evaluate":
        return _cmd_evaluate(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
