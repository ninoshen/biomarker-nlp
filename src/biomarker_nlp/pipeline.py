"""End-to-end orchestration: load clinical text + registry data, run the
NLP extractors, aggregate to patient level, and (optionally) join against
gold-standard registry labels for evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from .extractors import extract_biomarkers
from .registry import DEFAULT_REGISTRY_COLUMNS, clean_mrn, load_registry_gold

DEFAULT_NOTES_COLUMNS = {
    "mrn": "MRN",
    "date": "contact_date",
    "text": "note_text",
    "type": "note_type",
}

DEFAULT_PATHOLOGY_COLUMNS = {
    "mrn": "MRN",
    "date": "RESULT_TIME",
    "text": "PATH_REPORT_TEXT",
    "type": "REPORT_TYPE",
}


@dataclass
class ColumnMap:
    """Configurable column names, so the pipeline can be pointed at a
    different EHR/registry export without touching any code.
    """

    notes_columns: dict = field(default_factory=lambda: dict(DEFAULT_NOTES_COLUMNS))
    pathology_columns: dict = field(default_factory=lambda: dict(DEFAULT_PATHOLOGY_COLUMNS))
    registry_columns: dict = field(default_factory=lambda: dict(DEFAULT_REGISTRY_COLUMNS))
    notes_sheet: str = "Notes"
    pathology_sheet_contains: str = "Pathology"
    registry_sheet_contains: str = "Tumor"


def _select_sheet(xls: pd.ExcelFile, contains: str) -> str:
    matches = [s for s in xls.sheet_names if contains.lower() in s.lower()]
    if not matches:
        raise ValueError(f"No sheet name containing '{contains}' found in workbook: {xls.sheet_names}")
    return matches[0]


def aggregate_status(values) -> Optional[str]:
    """Collapse multiple note-level statuses for one patient into a single
    label, preferring positive > equivocal > negative > unknown/missing.
    """
    values = [v for v in values if pd.notna(v)]
    if "positive" in values:
        return "positive"
    if "equivocal" in values:
        return "equivocal"
    if "negative" in values:
        return "negative"
    return None


class BiomarkerPipeline:
    """Runs the ER/PR/HER2/Ki-67 extraction pipeline over clinical text and
    optionally validates against gold-standard registry labels.
    """

    def __init__(self, column_map: Optional[ColumnMap] = None):
        self.column_map = column_map or ColumnMap()

    def load_workbook(self, path: str) -> dict:
        """Load notes, pathology, and registry sheets from an Excel workbook."""
        cm = self.column_map
        xls = pd.ExcelFile(path)

        notes = pd.read_excel(path, sheet_name=cm.notes_sheet)
        pathology = pd.read_excel(path, sheet_name=_select_sheet(xls, cm.pathology_sheet_contains))
        registry = pd.read_excel(path, sheet_name=_select_sheet(xls, cm.registry_sheet_contains))

        return {"notes": notes, "pathology": pathology, "registry": registry}

    def build_text_corpus(self, notes_df: pd.DataFrame, pathology_df: pd.DataFrame) -> pd.DataFrame:
        """Combine notes + pathology reports into one long text corpus:
        columns MRN, note_date, text, note_type, note_source.
        """
        cm = self.column_map

        notes_nlp = notes_df[list(cm.notes_columns.values())].copy()
        notes_nlp.columns = ["MRN", "note_date", "text", "note_type"]
        notes_nlp["note_source"] = "Office Visit"

        path_nlp = pathology_df[list(cm.pathology_columns.values())].copy()
        path_nlp.columns = ["MRN", "note_date", "text", "note_type"]
        path_nlp["note_source"] = "Pathology Report"

        all_text = pd.concat([notes_nlp, path_nlp], ignore_index=True)
        all_text["MRN"] = all_text["MRN"].apply(clean_mrn)

        all_text["text"] = (
            all_text["text"]
            .fillna("")
            .astype(str)
            .str.replace("\r", " ", regex=False)
            .str.replace("\n", " ", regex=False)
            .str.replace("\t", " ", regex=False)
            .str.strip()
        )
        all_text = all_text[all_text["text"].str.len() > 0].reset_index(drop=True)

        return all_text

    def run_note_level_extraction(self, all_text: pd.DataFrame) -> pd.DataFrame:
        """Apply the regex extractors to every row of the text corpus."""
        extracted = all_text["text"].apply(extract_biomarkers)
        extracted_df = pd.DataFrame(extracted.tolist(), index=all_text.index)
        return pd.concat([all_text, extracted_df], axis=1)

    def aggregate_to_patient_level(self, note_level_results: pd.DataFrame) -> pd.DataFrame:
        """Collapse note-level extractions to one row per patient (MRN)."""
        return (
            note_level_results.groupby("MRN")
            .agg(
                {
                    "nlp_er_status": aggregate_status,
                    "nlp_pr_status": aggregate_status,
                    "nlp_her2_status": aggregate_status,
                    "nlp_ki67_value": "max",
                }
            )
            .reset_index()
        )

    def run(
        self,
        notes_df: pd.DataFrame,
        pathology_df: pd.DataFrame,
        registry_df: Optional[pd.DataFrame] = None,
    ) -> dict:
        """Run the full pipeline: build corpus -> extract -> aggregate ->
        (optionally) join with registry gold-standard labels.

        Returns a dict with keys: note_level, patient_level, analysis
        (analysis is None if no registry_df was supplied).
        """
        all_text = self.build_text_corpus(notes_df, pathology_df)
        note_level = self.run_note_level_extraction(all_text)
        patient_level = self.aggregate_to_patient_level(note_level)

        analysis = None
        if registry_df is not None:
            registry_gold = load_registry_gold(registry_df, self.column_map.registry_columns)
            analysis = patient_level.merge(registry_gold, on="MRN", how="inner")

        return {
            "note_level": note_level,
            "patient_level": patient_level,
            "analysis": analysis,
        }

    def run_from_excel(self, path: str, include_registry: bool = True) -> dict:
        """Convenience wrapper: load an Excel workbook and run the full pipeline."""
        data = self.load_workbook(path)
        registry_df = data["registry"] if include_registry else None
        return self.run(data["notes"], data["pathology"], registry_df)
