import math

from biomarker_nlp.extractors import extract_biomarkers, extract_er, extract_her2, extract_ki67, extract_pr


def test_extract_er_positive():
    assert extract_er("Estrogen receptor: positive, 90% of nuclei.") == "positive"
    assert extract_er("ER 95%") == "positive"


def test_extract_er_negative():
    assert extract_er("ER negative.") == "negative"
    assert extract_er("ER 0%.") == "negative"


def test_extract_er_none():
    assert extract_er("No biomarker information in this note.") is None
    assert extract_er(None) is None
    assert extract_er("") is None


def test_extract_pr_handles_pgr_alias():
    assert extract_pr("PgR positive, 40%.") == "positive"


def test_extract_her2_ihc_scores():
    assert extract_her2("HER2 3+ by IHC.") == "positive"
    assert extract_her2("HER2 2+ by IHC.") == "equivocal"
    assert extract_her2("HER2 0.") == "negative"


def test_extract_her2_fish_overrides_ihc_language():
    text = "HER2 2+ by IHC, equivocal; reflex FISH not amplified, negative."
    assert extract_her2(text) == "negative"


def test_extract_ki67_percentage():
    assert extract_ki67("Ki-67 proliferation index: 35%.") == 35.0
    assert extract_ki67("Ki67 20") == 20.0


def test_extract_ki67_missing():
    assert math.isnan(extract_ki67("No proliferation marker mentioned."))


def test_extract_biomarkers_combines_all_four():
    text = (
        "Invasive ductal carcinoma. ER positive 90%. PR positive 60%. "
        "HER2 negative (IHC 1+). Ki-67 15%."
    )
    result = extract_biomarkers(text)
    assert result == {
        "nlp_er_status": "positive",
        "nlp_pr_status": "positive",
        "nlp_her2_status": "negative",
        "nlp_ki67_value": 15.0,
    }
