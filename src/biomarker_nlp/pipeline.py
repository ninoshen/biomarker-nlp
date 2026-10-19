"""Core extraction pipeline: turn one or more tables of clinical text into
per-note and per-patient biomarker calls.

This module has no dependency on any gold-standard/registry data — it is
the standalone, reusable part of the package. Registry-based evaluation
(for anyone who *does* have gold-standard labels to validate against)
lives separately in `biomarker_nlp.evaluation`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import pandas as pd

from .extractors import extract_biomarkers
from .utils import clean_id, clean_text_series


@dataclass
class SourceColumns:
    """Maps the columns of one input table to the pipeline's standard schema.

    id: column holding the patient identifier
    text: column holding the free text to run extraction on
    date: optional column holding the note/report date
    type: optional column holding a note-type label (e.g. "Pathology Report")
    """

    id: str
    text: str
    date: Optional[str] = None
    type: Optional[str] = None


def _standardize_source(df: pd.DataFrame, columns: SourceColumns, source_label: str) -> pd.DataFrame:
    if columns.id not in df.columns:
        raise KeyError(f"id column '{columns.id}' not found in input table (columns: {list(df.columns)})")
    if columns.text not in df.columns:
        raise KeyError(f"text column '{columns.text}' not found in input table (columns: {list(df.columns)})")

    out = pd.DataFrame()
    out["patient_id"] = df[columns.id]
    out["note_date"] = df[columns.date] if columns.date else pd.NA
    out["text"] = df[columns.text]
    out["note_type"] = df[columns.type] if columns.type else pd.NA
    out["note_source"] = source_label
    return out


def combine_text_sources(sources: Iterable[Tuple[pd.DataFrame, SourceColumns, str]]) -> pd.DataFrame:
    """Combine one or more input tables (e.g. office-visit notes and
    pathology reports, each with their own column names) into a single
    standardized text corpus: patient_id, note_date, text, note_type,
    note_source.

    Rows with empty/missing text are dropped.
    """
    frames = [_standardize_source(df, columns, label) for df, columns, label in sources]
    if not frames:
        raise ValueError("combine_text_sources requires at least one source")

    combined = pd.concat(frames, ignore_index=True)
    combined["patient_id"] = combined["patient_id"].apply(clean_id)
    combined["text"] = clean_text_series(combined["text"])
    combined = combined[combined["text"].str.len() > 0].reset_index(drop=True)
    return combined


def load_text_table(
    df: pd.DataFrame,
    id_column: str,
    text_column: str,
    date_column: Optional[str] = None,
    type_column: Optional[str] = None,
    source_label: str = "note",
) -> pd.DataFrame:
    """Convenience wrapper around combine_text_sources for the common case
    of a single input table (e.g. one CSV of notes).
    """
    columns = SourceColumns(id=id_column, text=text_column, date=date_column, type=type_column)
    return combine_text_sources([(df, columns, source_label)])


def aggregate_status(values) -> Optional[str]:
    """Collapse multiple note-level statuses for one patient into a single
    label, preferring positive > equivocal > negative.
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
    """Runs the ER/PR/HER2/Ki-67 extractors over a standardized text corpus
    and aggregates note-level results to one row per patient.
    """

    def extract(self, corpus: pd.DataFrame) -> pd.DataFrame:
        """Apply the regex extractors to every row of a corpus that has a
        'text' column. Returns the corpus with nlp_er_status, nlp_pr_status,
        nlp_her2_status, nlp_ki67_value columns appended.
        """
        if "text" not in corpus.columns:
            raise KeyError("corpus must have a 'text' column (use load_text_table/combine_text_sources)")

        extracted = corpus["text"].apply(extract_biomarkers)
        extracted_df = pd.DataFrame(extracted.tolist(), index=corpus.index)
        return pd.concat([corpus, extracted_df], axis=1)

    def aggregate(self, note_level: pd.DataFrame, id_column: str = "patient_id") -> pd.DataFrame:
        """Collapse note-level extractions to one row per patient."""
        return (
            note_level.groupby(id_column)
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

    def run(self, corpus: pd.DataFrame, id_column: str = "patient_id") -> dict:
        """Run extraction + aggregation on an already-standardized corpus
        (e.g. one built with combine_text_sources/load_text_table).

        Returns {"note_level": ..., "patient_level": ...}.
        """
        note_level = self.extract(corpus)
        patient_level = self.aggregate(note_level, id_column=id_column)
        return {"note_level": note_level, "patient_level": patient_level}

    def run_from_table(
        self,
        df: pd.DataFrame,
        id_column: str,
        text_column: str,
        date_column: Optional[str] = None,
        type_column: Optional[str] = None,
        source_label: str = "note",
    ) -> dict:
        """Convenience: build the corpus from a single input table and run
        the pipeline in one call. This is the typical entry point when you
        have one table of notes/reports with a patient ID column and a
        free-text column.
        """
        corpus = load_text_table(df, id_column, text_column, date_column, type_column, source_label)
        return self.run(corpus)

    def run_from_sources(self, sources: List[Tuple[pd.DataFrame, SourceColumns, str]]) -> dict:
        """Convenience: combine multiple input tables (e.g. notes +
        pathology reports, each with different column names) and run the
        pipeline in one call.
        """
        corpus = combine_text_sources(sources)
        return self.run(corpus)
