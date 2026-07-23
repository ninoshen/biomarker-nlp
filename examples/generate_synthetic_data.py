"""Generate a small synthetic Excel workbook with the same sheet/column
schema the pipeline expects, so the pipeline can be demoed and tested
without any real patient data.

Usage:
    python examples/generate_synthetic_data.py [output_path]
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

SYNTHETIC_PATHOLOGY_TEMPLATES = [
    # (text, registry_er, registry_pr, registry_her2, registry_ki67)
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
        "Triple negative invasive ductal carcinoma. ER-, PR-, HER2 0. "
        "Ki-67 70%.",
        0, 0, 0, "70",
    ),
    (
        "Invasive ductal carcinoma. ER pos 80%, PR pos 30%. HER2 IHC 3+, "
        "FISH amplified, positive. Ki-67 index 25%.",
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


def generate(n_patients: int = 20, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)

    mrns = [f"SYN{100000 + i}" for i in range(n_patients)]

    cohort = pd.DataFrame({"Medical Record Number": mrns, "Enrollment Status": "Enrolled"})

    notes_rows = []
    path_rows = []
    registry_rows = []

    for mrn in mrns:
        template_idx = rng.integers(0, len(SYNTHETIC_PATHOLOGY_TEMPLATES))
        text, er, pr, her2, ki67 = SYNTHETIC_PATHOLOGY_TEMPLATES[template_idx]

        path_rows.append(
            {
                "MRN": mrn,
                "RESULT_TIME": "2025-01-15",
                "PATH_REPORT_TEXT": text,
                "REPORT_TYPE": "Surgical Pathology",
            }
        )

        registry_rows.append(
            {
                "Medical Record Number": mrn,
                "Estrogen Receptor Summary": er,
                "Progesterone Receptor Summary": pr,
                "HER2 Overall Summary": her2,
                "Ki-67": ki67,
            }
        )

        note_text = OFFICE_VISIT_NOTES[rng.integers(0, len(OFFICE_VISIT_NOTES))]
        notes_rows.append(
            {
                "MRN": mrn,
                "contact_date": "2025-01-20",
                "note_text": note_text,
                "note_type": "Office Visit Note",
            }
        )

    notes = pd.DataFrame(notes_rows)
    pathology = pd.DataFrame(path_rows)
    registry = pd.DataFrame(registry_rows)

    return {"Cohort": cohort, "Notes": notes, "Pathology": pathology, "Tumor Registry": registry}


def main() -> None:
    output_path = sys.argv[1] if len(sys.argv) > 1 else "examples/synthetic_data.xlsx"

    sheets = generate()
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"Wrote synthetic workbook to {output_path}")


if __name__ == "__main__":
    main()
