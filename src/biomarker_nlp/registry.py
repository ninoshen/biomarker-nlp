"""Optional helpers for normalizing gold-standard biomarker labels (e.g.
from a cancer registry or tumor board export) so extraction output can be
validated against them.

Nothing in the core pipeline (biomarker_nlp.pipeline) depends on this
module — it's only needed if you have gold-standard data to evaluate
against. See biomarker_nlp.evaluation for the actual scoring.
"""

from __future__ import annotations

import pandas as pd

from .utils import clean_id


def normalize_registry_status(x) -> str:
    """Map a registry status code to a text label, using the common
    cancer-registry convention: 1 = positive, 0 = negative, 9 = unknown.

    Adjust before calling this if your source uses a different code scheme.
    """
    if pd.isna(x):
        return "missing"

    try:
        x = float(x)
    except (TypeError, ValueError):
        return "unknown"

    if x == 1:
        return "positive"
    if x == 0:
        return "negative"
    if x == 9:
        return "unknown"
    return "unknown"


def normalize_ki67(x) -> float:
    """Parse a registry Ki-67 value, treating non-numeric 'unknown' codes
    (e.g. 'XXX.9') as missing.
    """
    if pd.isna(x):
        return float("nan")

    x = str(x).strip()
    if "X" in x.upper():
        return float("nan")

    try:
        return float(x)
    except ValueError:
        return float("nan")


def prepare_gold_standard(
    gold_df: pd.DataFrame,
    id_column: str,
    er_column: str,
    pr_column: str,
    her2_column: str,
    ki67_column: str,
) -> pd.DataFrame:
    """Select and normalize gold-standard biomarker columns from a raw
    registry/tumor-board export, using explicit column names (there's no
    universal default naming across institutions, so this requires you to
    say exactly which columns hold what).

    Returns a DataFrame with columns: patient_id, registry_er_status,
    registry_pr_status, registry_her2_status, registry_ki67_value.
    """
    gold = gold_df[[id_column, er_column, pr_column, her2_column, ki67_column]].copy()
    gold.columns = ["patient_id", "registry_er", "registry_pr", "registry_her2", "registry_ki67"]

    gold["patient_id"] = gold["patient_id"].apply(clean_id)
    gold["registry_er_status"] = gold["registry_er"].apply(normalize_registry_status)
    gold["registry_pr_status"] = gold["registry_pr"].apply(normalize_registry_status)
    gold["registry_her2_status"] = gold["registry_her2"].apply(normalize_registry_status)
    gold["registry_ki67_value"] = gold["registry_ki67"].apply(normalize_ki67)

    return gold[
        [
            "patient_id",
            "registry_er_status",
            "registry_pr_status",
            "registry_her2_status",
            "registry_ki67_value",
        ]
    ]
