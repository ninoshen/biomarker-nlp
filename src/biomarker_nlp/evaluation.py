"""Evaluate NLP-extracted biomarker status against gold-standard registry
labels: precision/recall/F1/confusion matrix for ER, PR, HER2, and
agreement statistics (MAE, correlation) for Ki-67.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    precision_score,
    recall_score,
)


def evaluate_classification(
    analysis_df: pd.DataFrame,
    nlp_col: str,
    registry_col: str,
    fillna_value: str = "negative",
    equivocal_as: Optional[str] = None,
) -> dict:
    """Compute precision/recall/F1/confusion matrix for one binary biomarker
    (ER, PR, or HER2), treating 'positive' as the positive class.

    Rows where the registry label isn't 'positive'/'negative' are excluded
    (unknown/missing gold-standard can't be scored against).
    """
    df = analysis_df[analysis_df[registry_col].isin(["positive", "negative"])].copy()

    pred = df[nlp_col]
    if equivocal_as is not None:
        pred = pred.replace("equivocal", equivocal_as)
    pred = pred.fillna(fillna_value)

    true_bin = (df[registry_col] == "positive").astype(int)
    pred_bin = (pred == "positive").astype(int)

    cm = confusion_matrix(true_bin, pred_bin, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    return {
        "n": len(df),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "precision": precision_score(true_bin, pred_bin, zero_division=0),
        "recall": recall_score(true_bin, pred_bin, zero_division=0),
        "f1": f1_score(true_bin, pred_bin, zero_division=0),
    }


def evaluate_ki67(
    analysis_df: pd.DataFrame,
    nlp_col: str = "nlp_ki67_value",
    registry_col: str = "registry_ki67_value",
) -> dict:
    """Compute agreement statistics between NLP-extracted and registry
    Ki-67 proliferation index values.
    """
    df = analysis_df[analysis_df[registry_col].notna() & analysis_df[nlp_col].notna()].copy()

    if len(df) == 0:
        return {"n": 0, "mae": None, "median_ae": None, "within_5": None, "within_10": None, "correlation": None}

    abs_error = (df[nlp_col] - df[registry_col]).abs()

    return {
        "n": len(df),
        "mae": mean_absolute_error(df[registry_col], df[nlp_col]),
        "median_ae": abs_error.median(),
        "within_5": (abs_error <= 5).mean(),
        "within_10": (abs_error <= 10).mean(),
        "correlation": df[[registry_col, nlp_col]].corr().iloc[0, 1],
    }


def evaluate_all(analysis_df: pd.DataFrame) -> dict:
    """Run the standard evaluation suite (ER, PR, HER2, Ki-67) on a merged
    analysis dataframe (patient-level NLP results joined with registry gold).

    HER2 treats 'equivocal' NLP predictions as negative, matching the
    original validation protocol, since equivocal cases route to reflex
    ISH testing rather than being called positive outright.
    """
    return {
        "ER": evaluate_classification(analysis_df, "nlp_er_status", "registry_er_status"),
        "PR": evaluate_classification(analysis_df, "nlp_pr_status", "registry_pr_status"),
        "HER2": evaluate_classification(
            analysis_df, "nlp_her2_status", "registry_her2_status", equivocal_as="negative"
        ),
        "Ki-67": evaluate_ki67(analysis_df),
    }


def format_report(report: dict) -> str:
    """Render an evaluate_all() report as a markdown summary table."""
    lines = [
        "| Biomarker | Cases | TP | FP | FN | TN | Precision | Recall | F1 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in ("ER", "PR", "HER2"):
        r = report[name]
        lines.append(
            f"| {name} | {r['n']} | {r['tp']} | {r['fp']} | {r['fn']} | {r['tn']} "
            f"| {r['precision']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} |"
        )

    ki = report["Ki-67"]
    lines.append("")
    if ki["n"] > 0:
        lines.append("| Biomarker | Cases | MAE | Median AE | Within 5pts | Within 10pts | Correlation |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        lines.append(
            f"| Ki-67 | {ki['n']} | {ki['mae']:.3f} | {ki['median_ae']:.3f} "
            f"| {ki['within_5']:.1%} | {ki['within_10']:.1%} | {ki['correlation']:.3f} |"
        )
    else:
        lines.append("Ki-67: no comparable cases (no overlapping non-missing values).")

    return "\n".join(lines)
