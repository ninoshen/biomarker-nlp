"""Command-line entry point for the biomarker NLP pipeline.

Examples
--------
Run extraction only (no evaluation):
    biomarker-nlp run --input cohort.xlsx --output patient_results.csv --no-evaluate

Run extraction and evaluate against the registry sheet in the same workbook:
    biomarker-nlp run --input cohort.xlsx --output patient_results.csv
"""

from __future__ import annotations

import argparse
import sys

from .evaluation import evaluate_all, format_report
from .pipeline import BiomarkerPipeline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="biomarker-nlp", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the extraction pipeline on an Excel workbook")
    run_parser.add_argument("--input", required=True, help="Path to the input .xlsx workbook")
    run_parser.add_argument("--output", required=True, help="Path to write patient-level results CSV")
    run_parser.add_argument(
        "--evaluate",
        dest="evaluate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Evaluate NLP output against the registry sheet (default: on; use --no-evaluate to skip)",
    )
    run_parser.add_argument(
        "--report",
        default=None,
        help="Optional path to write a markdown evaluation report",
    )

    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        pipeline = BiomarkerPipeline()
        result = pipeline.run_from_excel(args.input, include_registry=args.evaluate)

        result["patient_level"].to_csv(args.output, index=False)
        print(f"Wrote patient-level results for {len(result['patient_level'])} patients to {args.output}")

        if args.evaluate and result["analysis"] is not None:
            report = evaluate_all(result["analysis"])
            rendered = format_report(report)
            print()
            print(rendered)
            if args.report:
                with open(args.report, "w") as f:
                    f.write(rendered + "\n")
                print(f"\nWrote evaluation report to {args.report}")

        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
