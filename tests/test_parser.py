import pytest
from auditor.demo_data import DEMO_PAGES
from auditor.llm import _truncate_words, build_heuristic_recommendations
from auditor.parser import FetchError, analyze_html, validate_public_url


def test_flawed_landing_has_lower_score():
    demo = DEMO_PAGES["flawed-landing"]
    result = analyze_html(demo["html"], url=demo["url"])
    assert result["score"] < 55
    assert result["checks_total"] == 30
    assert result["stats"]["images_missing_alt"] == 2
    assert len(result["headings"]["h1"]) == 2


def test_strong_saas_has_high_score():
    demo = DEMO_PAGES["strong-saas"]
    result = analyze_html(demo["html"], url=demo["url"])
    assert result["score"] >= 88
    assert result["grade"] == "A"
    assert "SoftwareApplication" in result["meta"]["json_ld_types"]


def test_truncate_words_no_dangling_prepositions():
    text = "Узнайте больше про аналитику посадочных страниц и автоматический аудит"
    res = _truncate_words(text, 52)
    assert not res.endswith(" и")
    assert not res.endswith(" про")


def test_heuristic_recommendations_include_head_snippet():
    demo = DEMO_PAGES["flawed-landing"]
    audit = analyze_html(demo["html"], url=demo["url"])
    rec = build_heuristic_recommendations(audit)
    assert rec["mode"] == "heuristic"
    assert len(rec["suggested_titles"]) == 3
    assert "<title>" in rec["head_snippet"]
    assert "application/ld+json" in rec["head_snippet"]


def test_ssrf_blocks_localhost():
    with pytest.raises(FetchError):
        validate_public_url("http://127.0.0.1:8000/admin")
    with pytest.raises(FetchError):
        validate_public_url("http://localhost/secret")
