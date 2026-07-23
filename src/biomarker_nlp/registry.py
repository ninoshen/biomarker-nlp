"""Helpers for cleaning and normalizing gold-standard registry/tumor-board data
so it can be compared against NLP-extracted biomarker status.
"""

from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd

# Default registry columns, as found in a typical cancer registry / tumor
# board export. Override via BiomarkerPipeline's ColumnMap if your source
# system uses different column names.
DEFAULT_REGISTRY_COLUMNS = {
    "mrn": "Medical Record Number",
    "er": "Estrogen Receptor Summary",
    "pr": "Progesterone Receptor Summary",
    "her2": "HER2 Overall Summary",
    "ki67": "Ki-67",
}


def clean_mrn(x) -> Optional[str]:
    """Normalize an MRN to a plain string, stripping any trailing '.0'
    left over from Excel's numeric coercion.
    """
    if pd.isna(x):
        return np.nan
    x = str(x).strip()
    x = re.sub(r"\.0$", "", x)
    return x


def normalize_registry_status(x) -> str:
    """Map registry status codes (1/0/9 convention) to a text label."""
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
    """Parse a registry Ki-67 value, treating 'XXX.9'-style unknown codes as NaN."""
    if pd.isna(x):
        return np.nan

    x = str(x).strip()
    if "X" in x.upper():
        return np.nan

    try:
        return float(x)
    except ValueError:
        return np.nan


def load_registry_gold(
    registry_df: pd.DataFrame,
    columns: dict = None,
) -> pd.DataFrame:
    """Select and normalize the gold-standard biomarker columns from a raw
    registry export.

    Parameters
    ----------
    registry_df:
        Raw registry/tumor-board dataframe.
    columns:
        Mapping with keys mrn, er, pr, her2, ki67 -> source column names.
        Defaults to DEFAULT_REGISTRY_COLUMNS.

    Returns
    -------
    DataFrame with columns: MRN, registry_er_status, registry_pr_status,
    registry_her2_status, registry_ki67_value.
    """
    cols = {**DEFAULT_REGISTRY_COLUMNS, **(columns or {})}

    gold = registry_df[[cols["mrn"], cols["er"], cols["pr"], cols["her2"], cols["ki67"]]].copy()
    gold.columns = ["MRN", "registry_er", "registry_pr", "registry_her2", "registry_ki67"]

    gold["MRN"] = gold["MRN"].apply(clean_mrn)
    gold["registry_er_status"] = gold["registry_er"].apply(normalize_registry_status)
    gold["registry_pr_status"] = gold["registry_pr"].apply(normalize_registry_status)
    gold["registry_her2_status"] = gold["registry_her2"].apply(normalize_registry_status)
    gold["registry_ki67_value"] = gold["registry_ki67"].apply(normalize_ki67)

    return gold[
        [
            "MRN",
            "registry_er_status",
            "registry_pr_status",
            "registry_her2_status",
            "registry_ki67_value",
        ]
    ]
