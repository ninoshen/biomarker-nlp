import math

import pandas as pd
import pytest

from biomarker_nlp.evaluation import evaluate
from biomarker_nlp.pipeline import BiomarkerPipeline, SourceColumns, aggregate_status, combine_text_sources, load_text_table
from biomarker_nlp.registry import normalize_ki67, normalize_registry_status, prepare_gold_standard
from biomarker_nlp.utils import clean_id


def test_clean_id_strips_trailing_zero():
    assert clean_id(12345.0) == "12345"
    assert clean_id("00123") == "00123"
    assert math.isnan(clean_id(float("nan")))


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


def test_load_text_table_cleans_ids_and_drops_empty_text():
    df = pd.DataFrame(
        {
            "id": [1001.0, 1002.0],
            "note": ["Some clinical text.", "   "],
        }
    )
    corpus = load_text_table(df, id_column="id", text_column="note")
    assert list(corpus["patient_id"]) == ["1001"]
    assert list(corpus.columns) == ["patient_id", "note_date", "text", "note_type", "note_source"]


def test_load_text_table_missing_column_raises():
    df = pd.DataFrame({"id": [1], "note": ["text"]})
    with pytest.raises(KeyError):
        load_text_table(df, id_column="id", text_column="does_not_exist")


def test_combine_text_sources_merges_multiple_tables():
    notes = pd.DataFrame({"MRN": [1.0], "note_text": ["Follow-up visit, no concerns."]})
    pathology = pd.DataFrame({"MRN": [1.0], "path_text": ["ER positive 90%. PR positive 60%. HER2 negative. Ki-67 15%."]})

    corpus = combine_text_sources(
        [
            (notes, SourceColumns(id="MRN", text="note_text"), "Office Visit"),
            (pathology, SourceColumns(id="MRN", text="path_text"), "Pathology Report"),
        ]
    )
    assert len(corpus) == 2
    assert set(corpus["note_source"]) == {"Office Visit", "Pathology Report"}
    assert list(corpus["patient_id"].unique()) == ["1"]


def test_pipeline_run_from_table_extracts_and_aggregates():
    df = pd.DataFrame(
        {
            "MRN": [2001.0, 2001.0],
            "text": [
                "ER positive 90%. PR positive 60%. HER2 negative (IHC 1+). Ki-67 15%.",
                "Follow-up visit, no new findings.",
            ],
        }
    )

    pipeline = BiomarkerPipeline()
    result = pipeline.run_from_table(df, id_column="MRN", text_column="text")

    assert len(result["note_level"]) == 2
    patient_row = result["patient_level"].iloc[0]
    assert patient_row["patient_id"] == "2001"
    assert patient_row["nlp_er_status"] == "positive"
    assert patient_row["nlp_her2_status"] == "negative"
    assert patient_row["nlp_ki67_value"] == 15.0


def test_evaluate_scores_extraction_against_gold_standard():
    df = pd.DataFrame(
        {
            "MRN": [3001.0],
            "text": ["ER positive 90%. PR positive 60%. HER2 negative (IHC 1+). Ki-67 15%."],
        }
    )
    pipeline = BiomarkerPipeline()
    result = pipeline.run_from_table(df, id_column="MRN", text_column="text")

    gold_df = pd.DataFrame(
        {
            "Medical Record Number": [3001.0],
            "ER": [1],
            "PR": [1],
            "HER2": [0],
            "Ki67": ["15"],
        }
    )
    gold = prepare_gold_standard(
        gold_df,
        id_column="Medical Record Number",
        er_column="ER",
        pr_column="PR",
        her2_column="HER2",
        ki67_column="Ki67",
    )

    report = evaluate(result["patient_level"], gold)
    assert report["ER"]["n"] == 1
    assert report["ER"]["precision"] == 1.0
    assert report["Ki-67"]["mae"] == 0.0
