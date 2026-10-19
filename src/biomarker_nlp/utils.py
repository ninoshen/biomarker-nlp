"""Small shared helpers used by both the extraction pipeline and the
optional gold-standard evaluation module.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd


def clean_id(x):
    """Normalize a patient identifier to a plain string, stripping any
    trailing '.0' left over from Excel/pandas coercing IDs to float.
    """
    if pd.isna(x):
        return np.nan
    x = str(x).strip()
    x = re.sub(r"\.0$", "", x)
    return x


def clean_text_series(series: pd.Series) -> pd.Series:
    """Collapse newlines/tabs and strip whitespace from a column of free text."""
    return (
        series.fillna("")
        .astype(str)
        .str.replace("\r", " ", regex=False)
        .str.replace("\n", " ", regex=False)
        .str.replace("\t", " ", regex=False)
        .str.strip()
    )
