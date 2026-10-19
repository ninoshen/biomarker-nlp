"""Rule-based NLP pipeline for extracting breast cancer biomarker status
(ER, PR, HER2, Ki-67) from unstructured clinical notes and pathology reports.
"""

from .extractors import extract_biomarkers, extract_er, extract_pr, extract_her2, extract_ki67
from .pipeline import BiomarkerPipeline, SourceColumns, combine_text_sources, load_text_table
from .evaluation import evaluate, evaluate_all
from .registry import prepare_gold_standard

__all__ = [
    "extract_biomarkers",
    "extract_er",
    "extract_pr",
    "extract_her2",
    "extract_ki67",
    "BiomarkerPipeline",
    "SourceColumns",
    "combine_text_sources",
    "load_text_table",
    "evaluate",
    "evaluate_all",
    "prepare_gold_standard",
]

__version__ = "0.1.0"
