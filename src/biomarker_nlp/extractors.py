"""Rule-based extraction of ER, PR, HER2, and Ki-67 status from free text.

Each function takes a single note/report string and returns a normalized
label. These are pure functions with no I/O, so they can be tested,
reused, or swapped out independently of the rest of the pipeline.
"""

from __future__ import annotations

import re
from typing import Optional

import numpy as np


def _search(pattern: str, text: str, flags: int = re.IGNORECASE) -> Optional[re.Match]:
    return re.search(pattern, text, flags)


def extract_er(text: Optional[str]) -> Optional[str]:
    """Return 'positive', 'negative', or None for estrogen receptor status."""
    if not isinstance(text, str) or not text.strip():
        return None

    if _search(r"\bER[\s\-:]?pos(itive)?\b", text):
        return "positive"
    if _search(r"estrogen\s+receptor[^.\n]{0,100}\bpositive\b", text):
        return "positive"
    if _search(r"estrogen\s+receptor[^.\n]{0,100}\bpos\b", text):
        return "positive"
    if _search(r"\bER\s*\+\b", text):
        return "positive"

    m = _search(r"\bER[^%\n]{0,80}?(\d{1,3})\s*%", text)
    if m:
        try:
            if int(m.group(1)) >= 1:
                return "positive"
        except ValueError:
            pass

    if _search(r"\bER[\s\-:]?neg(ative)?\b", text):
        return "negative"
    if _search(r"estrogen\s+receptor[^.\n]{0,100}\bnegative\b", text):
        return "negative"
    if _search(r"estrogen\s+receptor[^.\n]{0,100}\bneg\b", text):
        return "negative"
    if _search(r"\bER\s*-\b", text):
        return "negative"
    if _search(r"\bER[^%\n]{0,80}?<\s*1\s*%", text):
        return "negative"
    if _search(r"\bER[^%\n]{0,80}?\b0\s*%", text):
        return "negative"

    return None


def extract_pr(text: Optional[str]) -> Optional[str]:
    """Return 'positive', 'negative', or None for progesterone receptor status."""
    if not isinstance(text, str) or not text.strip():
        return None

    t = re.sub(r"\bPgR\b", "PR", text, flags=re.IGNORECASE)

    if _search(r"\bPR[\s\-:]?pos(itive)?\b", t):
        return "positive"
    if _search(r"progesterone\s+receptor[^.\n]{0,100}\bpositive\b", t):
        return "positive"
    if _search(r"progesterone\s+receptor[^.\n]{0,100}\bpos\b", t):
        return "positive"
    if _search(r"\bPR\s*\+\b", t):
        return "positive"

    m = _search(r"\bPR[^%\n]{0,80}?(\d{1,3})\s*%", t)
    if m:
        try:
            if int(m.group(1)) >= 1:
                return "positive"
        except ValueError:
            pass

    if _search(r"\bPR[\s\-:]?neg(ative)?\b", t):
        return "negative"
    if _search(r"progesterone\s+receptor[^.\n]{0,100}\bnegative\b", t):
        return "negative"
    if _search(r"progesterone\s+receptor[^.\n]{0,100}\bneg\b", t):
        return "negative"
    if _search(r"\bPR\s*-\b", t):
        return "negative"
    if _search(r"\bPR[^%\n]{0,80}?<\s*1\s*%", t):
        return "negative"
    if _search(r"\bPR[^%\n]{0,80}?\b0\s*%", t):
        return "negative"

    return None


def extract_her2(text: Optional[str]) -> Optional[str]:
    """Return 'positive', 'negative', 'equivocal', or None for HER2 status."""
    if not isinstance(text, str) or not text.strip():
        return None

    if _search(r"\b(?:FISH|ISH)[^.\n]{0,100}\bnot\s+amplified\b", text):
        return "negative"
    if _search(r"\b(?:FISH|ISH)[^.\n]{0,100}\bnegative\b", text):
        return "negative"
    if _search(r"\b(?:FISH|ISH)[^.\n]{0,100}\bamplified\b", text):
        return "positive"
    if _search(r"\b(?:FISH|ISH)[^.\n]{0,100}\bpositive\b", text):
        return "positive"

    if _search(r"\bHER2\b[^.\n]{0,80}\b3\s*\+", text) or _search(r"\bHER-2\b[^.\n]{0,80}\b3\s*\+", text):
        return "positive"

    if _search(r"\bHER2\b[^.\n]{0,80}\b2\s*\+", text) or _search(r"\bHER-2\b[^.\n]{0,80}\b2\s*\+", text):
        return "equivocal"

    if _search(r"\bHER2\b[^.\n]{0,80}\b1\s*\+", text) or _search(r"\bHER-2\b[^.\n]{0,80}\b1\s*\+", text):
        return "negative"

    if _search(r"\bHER2\b[^.\n]{0,80}\b0\b", text) or _search(r"\bHER-2\b[^.\n]{0,80}\b0\b", text):
        return "negative"

    if _search(r"\bHER2[^.\n]{0,80}\bpositive\b", text) or _search(r"\bHER-2[^.\n]{0,80}\bpositive\b", text):
        return "positive"
    if _search(r"\bHER2[^.\n]{0,80}\bnegative\b", text) or _search(r"\bHER-2[^.\n]{0,80}\bnegative\b", text):
        return "negative"
    if _search(r"\bHER2[^.\n]{0,80}\bequivocal\b", text) or _search(r"\bHER-2[^.\n]{0,80}\bequivocal\b", text):
        return "equivocal"

    return None


def extract_ki67(text: Optional[str]) -> float:
    """Return the Ki-67 proliferation index as a float percentage, or NaN."""
    if not isinstance(text, str) or not text.strip():
        return np.nan

    patterns = [
        r"\bKi[-\s]?67\b[^%\n]{0,100}?(\d{1,3}(?:\.\d+)?)\s*%",
        r"\bKi[-\s]?67\b[^.\n]{0,100}?\b(\d{1,3}(?:\.\d+)?)\b",
    ]

    for pattern in patterns:
        m = _search(pattern, text)
        if m:
            try:
                val = float(m.group(1))
                if 0 <= val <= 100:
                    return val
            except ValueError:
                pass

    return np.nan


def extract_biomarkers(text: Optional[str]) -> dict:
    """Run all four extractors on a single note/report and return a flat dict."""
    return {
        "nlp_er_status": extract_er(text),
        "nlp_pr_status": extract_pr(text),
        "nlp_her2_status": extract_her2(text),
        "nlp_ki67_value": extract_ki67(text),
    }
