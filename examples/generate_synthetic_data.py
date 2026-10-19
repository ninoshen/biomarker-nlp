"""Generate small synthetic datasets for demoing the pipeline, so it can be
tried end-to-end without any real patient data.

Produces two files:
  - synthetic_notes.csv: one row per note/report, the input to `extract`.
  - synthetic_gold_standard.csv: matching gold-standard labels, only needed
    if you want to try the optional `evaluate` step.

Usage:
    python examples/generate_synthetic_data.py [output_dir]
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

# (pathology_text, gold_er, gold_pr, gold_her2, gold_ki67) using the common
# registry convention: 1 = positive, 0 = negative.
SYNTHETIC_PATHOLOGY_TEMPLATES = [
    (
        "Invasive ductal carcinoma. Estrogen receptor: positive, 90% of tumor "
        "cell nuclei. Progesterone receptor: positive, 60%. HER2: negative "
        "(IHC 1+). Ki-67 proliferation index: 15%.",
        1, 1, 0, "15",
    ),
    (
        "Invasive lobular carcinoma. ER negative (<1%). PR negative (0%). "
        "HER2: 3+ by IHC, positive. Ki-67: 45%.",
        0, 0, 1, "45",
    ),
    (
        "Invasive ductal carcinoma, grade 2. Estrogen receptor positive "
        "(95%). Progesterone receptor negative. HER2 2+ by IHC, equivocal; "
        "reflex FISH not amplified, negative. Ki67 proliferation index "
        "approximately 20%.",
        1, 0, 0, "20",
    ),
    (
        "Triple negative invasive ductal carcinoma. ER negative, PR "
        "negative, HER2 0. Ki-67 70%.",
        0, 0, 0, "70",
    ),
    (
        "Invasive ductal carcinoma. ER positive 80%, PR positive 30%. HER2 "
        "IHC 3+, FISH amplified, positive. Ki-67 index 25%.",
        1, 1, 1, "25",
    ),
]

OFFICE_VISIT_NOTES = [
    "Patient seen in clinic for follow-up after biopsy. Discussed pathology "
    "results and treatment planning. Tolerating therapy well, no new "
    "concerns today.",
    "Routine oncology follow-up visit. Reviewed prior pathology report. "
    "Patient reports mild fatigue, otherwise doing well.",
    "New patient consult for recently diagnosed breast cancer. Reviewed "
    "outside pathology; will obtain repeat biomarker testing at our "
    "institution.",
]


def generate(n_patients: int = 20, seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    mrns = [f"SYN{100000 + i}" for i in range(n_patients)]

    note_rows = []
    gold_rows = []

    for mrn in mrns:
        template_idx = rng.integers(0, len(SYNTHETIC_PATHOLOGY_TEMPLATES))
        text, er, pr, her2, ki67 = SYNTHETIC_PATHOLOGY_TEMPLATES[template_idx]

        note_rows.append(
            {
                "MRN": mrn,
                "note_date": "2025-01-15",
                "note_type": "Surgical Pathology",
                "text": text,
            }
        )
        note_rows.append(
            {
                "MRN": mrn,
                "note_date": "2025-01-20",
                "note_type": "Office Visit Note",
                "text": OFFICE_VISIT_NOTES[rng.integers(0, len(OFFICE_VISIT_NOTES))],
            }
        )

        gold_rows.append(
            {
                "MRN": mrn,
                "ER_Summary": er,
                "PR_Summary": pr,
                "HER2_Summary": her2,
                "Ki67": ki67,
            }
        )

    notes_df = pd.DataFrame(note_rows)
    gold_df = pd.DataFrame(gold_rows)
    return notes_df, gold_df


def main() -> None:
    output_dir = sys.argv[1] if len(sys.argv) > 1 else "examples"
    os.makedirs(output_dir, exist_ok=True)

    notes_df, gold_df = generate()

    notes_path = os.path.join(output_dir, "synthetic_notes.csv")
    gold_path = os.path.join(output_dir, "synthetic_gold_standard.csv")

    notes_df.to_csv(notes_path, index=False)
    gold_df.to_csv(gold_path, index=False)

    print(f"Wrote {len(notes_df)} synthetic notes to {notes_path}")
    print(f"Wrote {len(gold_df)} synthetic gold-standard rows to {gold_path}")


if __name__ == "__main__":
    main()
