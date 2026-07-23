import math

import pandas as pd

from biomarker_nlp.pipeline import BiomarkerPipeline, aggregate_status
from biomarker_nlp.registry import clean_mrn, load_registry_gold, normalize_ki67, normalize_registry_status


def test_clean_mrn_strips_trailing_zero():
    assert clean_mrn(12345.0) == "12345"
    assert clean_mrn("00123") == "00123"
    assert math.isnan(clean_mrn(float("nan")))


def test_normalize_registry_status_codes():
    assert normalize_registry_status(1) == "positive"
    assert normalize_registry_status(0) == "negative"
    assert normalize_registry_status(9) == "unknown"
    assert normalize_registry_status(None) == "missing"


def test_normalize_ki67_handles_unknown_codes():
    assert math.isnan(normalize_ki67("XXX.9"))
    assert normalize_ki67("35") == 35.0


def test_aggregate_status_prefers_positive():
    assert aggregate_status(["negative", "positive", "negative"]) == "positive"
    assert aggregate_status(["equivocal", "negative"]) == "equivocal"
    assert aggregate_status(["negative", "negative"]) == "negative"
    assert aggregate_status([None, float("nan")]) is None


def test_load_registry_gold_normalizes_columns():
    registry_df = pd.DataFrame(
        {
            "Medical Record Number": [1001.0, 1002.0],
            "Estrogen Receptor Summary": [1, 0],
            "Progesterone Receptor Summary": [1, 9],
            "HER2 Overall Summary": [0, 1],
            "Ki-67": ["20", "XXX.9"],
        }
    )
    gold = load_registry_gold(registry_df)
    assert list(gold["MRN"]) == ["1001", "1002"]
    assert list(gold["registry_er_status"]) == ["positive", "negative"]
    assert gold["registry_ki67_value"].iloc[0] == 20.0
    assert math.isnan(gold["registry_ki67_value"].iloc[1])


def test_pipeline_end_to_end_with_in_memory_frames():
    notes_df = pd.DataFrame(
        {
            "MRN": [2001.0],
            "contact_date": ["2025-01-01"],
            "note_text": ["Routine follow-up visit, no new findings."],
            "note_type": ["Office Visit Note"],
        }
    )
    pathology_df = pd.DataFrame(
        {
            "MRN": [2001.0],
            "RESULT_TIME": ["2025-01-02"],
            "PATH_REPORT_TEXT": [
                "ER positive 90%. PR positive 60%. HER2 negative (IHC 1+). Ki-67 15%."
            ],
            "REPORT_TYPE": ["Surgical Pathology"],
        }
    )
    registry_df = pd.DataFrame(
        {
            "Medical Record Number": [2001.0],
            "Estrogen Receptor Summary": [1],
            "Progesterone Receptor Summary": [1],
            "HER2 Overall Summary": [0],
            "Ki-67": ["15"],
        }
    )

    pipeline = BiomarkerPipeline()
    result = pipeline.run(notes_df, pathology_df, registry_df)

    patient_row = result["patient_level"].iloc[0]
    assert patient_row["MRN"] == "2001"
    assert patient_row["nlp_er_status"] == "positive"
    assert patient_row["nlp_her2_status"] == "negative"

    analysis_row = result["analysis"].iloc[0]
    assert analysis_row["registry_er_status"] == "positive"
    assert analysis_row["nlp_er_status"] == analysis_row["registry_er_status"]
